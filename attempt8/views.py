from flask import render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_user, current_user, logout_user, login_required
import stripe
from app import app, docker_client
from extensions import db, bcrypt
from models import User, Container, CheckoutSession
from forms import RegistrationForm, LoginForm
from services import generate_container_name_and_port, add_container_to_db  # Import functions from services

# Stripe configuration
stripe.api_key = app.config['STRIPE_SECRET_KEY']

# Mapping from Stripe price IDs to memory limits
price_plan_to_memory = {
    'price_1OOrfWJxVhVlFzT6yrZsLu8m': '2g',
    'price_1OOrfmJxVhVlFzT6Jsrxd3W6': '4g',
    'price_1OOrg7JxVhVlFzT68Xzkdgc9': '8g'
}

# Mapping from Stripe price IDs to subscription plan names
price_id_to_plan_name = {
    'price_1OOrfWJxVhVlFzT6yrZsLu8m': '2GB Plan',
    'price_1OOrfmJxVhVlFzT6Jsrxd3W6': '4GB Plan',
    'price_1OOrg7JxVhVlFzT68Xzkdgc9': '8GB Plan',
}

@app.route('/test')
def test_route():
    return "Flask routing is working!"

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)  # Now it uses the remember field
            next_page = request.args.get('next') or url_for('dashboard')
            return redirect(next_page)
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_containers = Container.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', containers=user_containers)

@app.route('/rent_server', methods=['POST'])
@login_required
def rent_server():
    price_id = request.form.get('server_type')
    container_name, port = generate_container_name_and_port()  # Generate name and port
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
            client_reference_id=current_user.id  # Associate session with user
        )
        new_checkout_session = CheckoutSession(
            session_id=session.id,
            user_id=current_user.id,
            container_name=container_name,
            port=port
        )
        db.session.add(new_checkout_session)
        db.session.commit()
        return redirect(session.url, code=303)
    except Exception as e:
        error_message = str(e)
        print(error_message)
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

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, app.config['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        checkout_session = CheckoutSession.query.filter_by(session_id=session.id).first()
        if checkout_session:
            user = User.query.get(checkout_session.user_id)
            if user:
                # Use the container name and port from the CheckoutSession
                container_name = checkout_session.container_name
                port = checkout_session.port
                subscription = stripe.Subscription.retrieve(session.subscription)
                price_id = subscription['items']['data'][0]['price']['id']
                memory_limit = price_plan_to_memory.get(price_id, '2g')  # Default to 2g if not found
                container = docker_client.containers.run(
                    "itzg/minecraft-server",
                    detach=True,
                    environment={"EULA": "TRUE"},
                    ports={'25565/tcp': port},
                    name=container_name,
                    mem_limit=memory_limit
                )
                add_container_to_db(container_name, port, 'running', price_id_to_plan_name.get(price_id, 'Unknown Plan'), container.id, user.id)
                return 'Success', 200
        else:
            return 'Checkout session not found', 400

    # For all other events, acknowledge without action
    print(f'Received unhandled event type: {event["type"]}')
    return 'Received unhandled event type', 200

@app.route('/server_status')
def server_status():
    created = request.args.get('created', type=lambda v: v.lower() == 'true')
    message = "Your Minecraft server is now being set up!" if created else "Failed to create the Minecraft server. Please try again."
    return render_template('server_status.html', message=message)

@app.route('/admin', methods=['GET'])
@login_required
def admin():
    if current_user.is_admin:  # Assuming you have an is_admin field in User model
        containers = Container.query.all()
        return render_template('admin.html', containers=containers)
    else:
        flash('Access denied: You are not authorized to view this page.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/start_server', methods=['POST'])
@login_required
def start_server():
    data = request.get_json()
    container_db_entry = Container.query.get(data['container_id'])
    if container_db_entry and container_db_entry.user_id == current_user.id:
        try:
            container = docker_client.containers.get(container_db_entry.docker_id)
            container.start()
            container_db_entry.status = 'running'
            db.session.commit()
            return jsonify({'status': 'Server started'})
        except Exception as e:
            return jsonify({'status': 'Error', 'message': str(e)}), 500
    return jsonify({'status': 'Error', 'message': 'Container not found or access denied'}), 404

@app.route('/stop_server', methods=['POST'])
@login_required
def stop_server():
    data = request.get_json()
    container_db_entry = Container.query.get(data['container_id'])
    if container_db_entry and container_db_entry.user_id == current_user.id:
        try:
            container = docker_client.containers.get(container_db_entry.docker_id)
            container.stop()
            container_db_entry.status = 'stopped'
            db.session.commit()
            return jsonify({'status': 'Server stopped'})
        except Exception as e:
            return jsonify({'status': 'Error', 'message': str(e)}), 500
    return jsonify({'status': 'Error', 'message': 'Container not found or access denied'}), 404

@app.route('/view_server/<int:server_id>')
@login_required
def view_server(server_id):
    container = Container.query.get_or_404(server_id)
    if container.user_id != current_user.id:
        flash('You do not have permission to view this server.', 'danger')
        return redirect(url_for('dashboard'))
    # Render the server overview page with start/stop and cancel subscription options
    return render_template('server_view.html', container=container)

@app.route('/restart_server/<int:server_id>')
@login_required
def restart_server(server_id):
    # Your logic to restart the server
    # ...
    return redirect(url_for('view_server', server_id=server_id))

@app.route('/configure_server/<int:server_id>', methods=['GET', 'POST'])
@login_required
def configure_server(server_id):
    # Here you would add logic to handle the server configuration
    pass

@app.route('/terminal_server/<int:server_id>')
@login_required
def terminal_server(server_id):
    # Here you would add logic to handle the server terminal access
    pass

@app.route('/cancel_subscription/<int:server_id>')
@login_required
def cancel_subscription(server_id):
    # Placeholder for cancellation logic
    flash('Subscription cancellation feature coming soon!', 'info')
    return redirect(url_for('view_server', server_id=server_id))