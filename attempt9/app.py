from flask import Flask
import docker
import stripe
from extensions import db, bcrypt, login_manager
from models import User
from flask_socketio import SocketIO
import threading
import os

# Initialize Flask app
app = Flask(__name__)
app.config.from_object('config.Config')  # Load configurations from config.py

# Initialize Flask extensions
db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Docker and Stripe
docker_client = docker.from_env()
stripe.api_key = app.config['STRIPE_SECRET_KEY']

# Initialize SocketIO
socketio = SocketIO(app, async_mode='threading')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# Docker Terminal Functions
def attach_to_container(container):
    socket = container.attach_socket(params={'stdin': 1, 'stdout': 1, 'stderr': 1, 'stream': 1})
    return socket._sock

def stream_docker_output():
    try:
        container = docker_client.containers.get('minecraft_server_1')
        for line in container.attach(stream=True, logs=True):
            socketio.emit('docker_output', {'output': line.decode('utf-8', 'ignore')})
    except Exception as e:
        socketio.emit('docker_output', {'output': f'Error: {str(e)}'})

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    threading.Thread(target=stream_docker_output, daemon=True).start()

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('send_command')
def handle_send_command(data):
    command = data['command'].strip() + "\n"
    if command:
        try:
            container = docker_client.containers.get('minecraft_server_1')
            docker_socket = attach_to_container(container)
            os.write(docker_socket.fileno(), command.encode('utf-8'))
            docker_socket.close()
        except Exception as e:
            socketio.emit('command_output', {'output': f'Error: {str(e)}'})

# Import views after the Flask app has been initialized
from views import *

if __name__ == '__main__':
    # Start the Flask app with SocketIO support
    socketio.run(app, debug=True, port=4242)

