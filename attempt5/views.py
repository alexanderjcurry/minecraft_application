from flask import render_template, request, redirect, url_for, jsonify
import stripe
from app import app, db, docker_client, Container, generate_container_name_and_port, add_container_to_db

# Mapping from Stripe price IDs to memory limits
price_plan_to_memory = {
    'price_1OOrfWJxVhVlFzT6yrZsLu8m': '2g',  # 2GB for $10 plan
    'price_1OOrfmJxVhVlFzT6Jsrxd3W6': '4g',  # 4GB for $20 plan
    'price_1OOrg7JxVhVlFzT68Xzkdgc9': '8g'   # 8GB for $40 plan
}

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/rent_server', methods=['POST'])
def rent_server():
    price_id = request.form.get('server_type')
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('index', _external=True),
        )
        return redirect(session.url, code=303)
    except Exception as e:
        error_message = str(e)
        print(error_message)  # Log to console for debugging
        return render_template('error.html', error_message=error_message)

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/cancel')
def cancel():
    return render_template('cancel.html')

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    server_created = False

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, app.config['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Attempt to retrieve the subscription ID
        subscription_id = session.get('subscription')
        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
            price_id = subscription['items']['data'][0]['price']['id']

            # Get the memory limit based on the selected plan
            memory_limit = price_plan_to_memory.get(price_id, '2g')  # default to 2g if not found

            try:
                container_name, port = generate_container_name_and_port()
                container = docker_client.containers.run(
                    "itzg/minecraft-server",
                    detach=True,
                    environment={"EULA": "TRUE"},
                    ports={'25565/tcp': ('0.0.0.0', port)},
                    name=container_name,
                    mem_limit=memory_limit
                )
                add_container_to_db(container_name, port)
                server_created = True  # Server was created successfully
                print(f"Server started with name: {container_name} on port {port}")
            except Exception as e:
                error_message = f"Docker Error: {str(e)}"
                print(error_message)  # Log to console for debugging

    return redirect(url_for('server_status', created=server_created))

@app.route('/server_status')
def server_status():
    created = request.args.get('created', type=lambda v: v.lower() == 'true')
    if created:
        message = "Your Minecraft server is now being set up!"
    else:
        message = "Failed to create the Minecraft server. Please try again."

    return render_template('server_status.html', message=message)