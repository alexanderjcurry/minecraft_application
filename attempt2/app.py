from flask import Flask, render_template, request, redirect, url_for
import docker
from docker.errors import APIError
import itertools
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///containers.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
    container = Container.query.filter_by(port=port, status='running').first()
    return container is not None

def generate_container_name_and_port():
    base_name = "mine_server"
    for suffix, port in itertools.product(range(1, 1000000), range(25566, 25600)):
        container_name = f"{base_name}{str(suffix).zfill(6)}"
        existing_container = Container.query.filter_by(name=container_name).first()
        if not existing_container and not is_port_in_use(port):
            return container_name, port
    raise Exception("No available container names or ports")

def add_container_to_db(name, port, status='running'):
    new_container = Container(name=name, port=port, status=status)
    db.session.add(new_container)
    db.session.commit()

def update_container_status(name, status):
    container = Container.query.filter_by(name=name).first()
    if container:
        container.status = status
        db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
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
            message = f"Server started with name: {container_name} on port {port}"
        except APIError as e:
            message = f"Error: {e.explanation}"
        except Exception as e:
            message = str(e)

        return render_template('status.html', message=message)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)