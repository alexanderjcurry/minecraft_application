from flask import Flask, render_template, request, redirect, url_for
import docker
from docker.errors import APIError
import itertools

app = Flask(__name__)

# Initialize Docker client
docker_client = docker.from_env()

def is_port_in_use(port):
    containers = docker_client.containers.list(all=True)
    ports_in_use = [int(container.attrs['NetworkSettings']['Ports']['25565/tcp'][0]['HostPort'])
                    for container in containers if container.attrs['NetworkSettings']['Ports'].get('25565/tcp')]
    return port in ports_in_use

def generate_container_name_and_port():
    base_name = "mine_server"
    for suffix, port in itertools.product(range(1, 1000000), range(25566, 25600)):
        container_name = f"{base_name}{str(suffix).zfill(6)}"
        if not docker_client.containers.list(filters={'name': container_name}):
            if not is_port_in_use(port):
                return container_name, port
    raise Exception("No available container names or ports")

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
            message = f"Server started with name: {container_name} on port {port}"
        except APIError as e:
            message = f"Error: {e.explanation}"
        except Exception as e:
            message = str(e)

        return render_template('status.html', message=message)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)