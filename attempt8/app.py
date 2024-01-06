from flask import Flask
import docker
import stripe
from extensions import db, bcrypt, login_manager
from models import User

app = Flask(__name__)
app.config.from_object('config.Config')  # Load configurations from config.py

db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

docker_client = docker.from_env()
stripe.api_key = app.config['STRIPE_SECRET_KEY']

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# Import views after the Flask app has been initialized
from views import *

if __name__ == '__main__':
    app.run(debug=True, port=4242)