from flask import Flask, render_template, request, redirect, url_for
import docker
from docker.errors import APIError, NotFound
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
    return Container.query.filter_by(port=port).first() is not None

def generate_container_name_and_port():
    base_name = "mine_server"
    containers = Container.query.order_by(Container.name).all()

    # Find the first non-used server number and port number
    server_number = 1
    port = 25565
    if containers:
        existing_numbers = sorted(int(container.name[len(base_name):]) for container in containers)
        existing_ports = sorted(container.port for container in containers)
        server_number = next((x for x in range(1, max(existing_numbers) + 2) if x not in existing_numbers), 1)
        port = next((x for x in range(25565, 25565 + len(containers) + 1) if x not in existing_ports), 25565)
    container_name = f"{base_name}{str(server_number).zfill(6)}"
    return container_name, port

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
            docker_client.containers.run(
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

@app.route('/admin', methods=['GET'])
def admin():
    containers = Container.query.all()
    for container in containers:
        try:
            docker_container = docker_client.containers.get(container.name)
            container.status = 'running' if docker_container.status == 'running' else 'stopped'
        except NotFound:
            db.session.delete(container)
        except APIError as e:
            print(f"Error fetching container status: {e.explanation}")
        db.session.commit()
    return render_template('admin.html', containers=containers)

@app.route('/toggle_container/<int:container_id>', methods=['POST'])
def toggle_container(container_id):
    container = Container.query.get(container_id)
    if container:
        try:
            docker_container = docker_client.containers.get(container.name)
            if container.status == 'running':
                docker_container.stop()
                container.status = 'stopped'
            else:
                docker_container.start()
                container.status = 'running'
        except NotFound:
            db.session.delete(container)
        except APIError as e:
            print(f"Error toggling container: {e.explanation}")
        db.session.commit()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)