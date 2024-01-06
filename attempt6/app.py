from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import docker
import stripe
import itertools

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///containers.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Stripe configuration
app.config['STRIPE_PUBLIC_KEY'] = 'pk_test_51OOrdBJxVhVlFzT6OiXm7CHTdha9KbmWYIBbH6rVE3lu0oE1niiL9ICECqEjDrxj91Jjf0hSJ930YMUSAwvUzUSJ00Q6Xb1t1f'
app.config['STRIPE_SECRET_KEY'] = 'sk_test_51OOrdBJxVhVlFzT6R5aUvfjWylPxQL9hStgb7wl3ilvzcozq43IhaDgQ9AQaV2nqJX1Dr8wTIz8KOJmWj4EyILJl00U6T4T3iu'
app.config['STRIPE_WEBHOOK_SECRET'] = 'whsec_a11df43f0859ebda9e32248536b3562e547760102bd8a41636fee195401c31cd'
stripe.api_key = app.config['STRIPE_SECRET_KEY']

# Initialize Docker client
docker_client = docker.from_env()

# Database model for containers
class Container(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    port = db.Column(db.Integer, unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    subscription_plan = db.Column(db.String(20), nullable=False)
    docker_id = db.Column(db.String(64), unique=True, nullable=False)  # New field for Docker container ID

    def __repr__(self):
        return f'<Container {self.name}>'

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

def add_container_to_db(name, port, status, subscription_plan, docker_id):
    new_container = Container(name=name, port=port, status=status, subscription_plan=subscription_plan, docker_id=docker_id)
    db.session.add(new_container)
    db.session.commit()

# Import the views after the Flask app is created and configured
from views import *

if __name__ == '__main__':
    app.run(debug=True, port=4242)