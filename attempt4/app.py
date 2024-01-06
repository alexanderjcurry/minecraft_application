from flask import Flask, render_template, request, redirect, url_for, jsonify
import docker
from docker.errors import APIError
import itertools
from flask_sqlalchemy import SQLAlchemy
import stripe

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///containers.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Stripe configuration
app.config['STRIPE_PUBLIC_KEY'] = 'pk_test_51OOrdBJxVhVlFzT6OiXm7CHTdha9KbmWYIBbH6rVE3lu0oE1niiL9ICECqEjDrxj91Jjf0hSJ930YMUSAwvUzUSJ00Q6Xb1t1f'
app.config['STRIPE_SECRET_KEY'] = 'sk_test_51OOrdBJxVhVlFzT6R5aUvfjWylPxQL9hStgb7wl3ilvzcozq43IhaDgQ9AQaV2nqJX1Dr8wTIz8KOJmWj4EyILJl00U6T4T3iu'
app.config['STRIPE_WEBHOOK_SECRET'] = 'whsec_a11df43f0859ebda9e32248536b3562e547760102bd8a41636fee195401c31cd'
stripe.api_key = app.config['STRIPE_SECRET_KEY']

# Database model for containers
class Container(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    port = db.Column(db.Integer, unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<Container {self.name}>'

# Initialize Docker client
docker_client = docker.from_env()

# Create the database and tables within app context
with app.app_context():
    db.create_all()

def is_port_in_use(port):
    container = Container.query.filter_by(port=port).first()
    return container is not None if container else False

def generate_container_name_and_port():
    base_name = "minecraft_server"
    for suffix, port in itertools.product(range(1, 1000000), range(25565, 25600)):
        container_name = f"{base_name}_{suffix}"
        if not Container.query.filter_by(name=container_name).first() and not is_port_in_use(port):
            return container_name, port
    raise Exception("No available container names or ports")

def add_container_to_db(name, port, status='running'):
    new_container = Container(name=name, port=port, status=status)
    db.session.add(new_container)
    db.session.commit()

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
    try:
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get('Stripe-Signature')
        event = stripe.Webhook.construct_event(
            payload, sig_header, app.config['STRIPE_WEBHOOK_SECRET']
        )

        if event['type'] == 'checkout.session.completed':
            try:
                container_name, port = generate_container_name_and_port()
                container = docker_client.containers.run(
                    "itzg/minecraft-server",
                    detach=True,
                    environment={"EULA": "TRUE"},
                    ports={'25565/tcp': ('0.0.0.0', port)},
                    name=container_name
                )
                add_container_to_db(container_name, port)
                print(f"Server started with name: {container_name} on port {port}")
            except Exception as e:
                error_message = f"Docker Error: {str(e)}"
                print(error_message)  # Log to console for debugging
                return render_template('error.html', error_message=error_message)

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        error_message = str(e)
        print(error_message)  # Log to console for debugging
        return render_template('error.html', error_message=error_message)

if __name__ == '__main__':
    app.run(debug=True, port=4242)