import itertools
from models import Container
from extensions import db
import docker

docker_client = docker.from_env()

def generate_container_name_and_port():
    base_name = "minecraft_server"
    for suffix, port in itertools.product(range(1, 1000000), range(25565, 25600)):
        container_name = f"{base_name}_{suffix}"
        if not Container.query.filter_by(name=container_name).first() and not is_port_in_use(port):
            return container_name, port
    raise Exception("No available container names or ports")

def is_port_in_use(port):
    container = Container.query.filter_by(port=port).first()
    return container is not None if container else False

def add_container_to_db(name, port, status, subscription_plan, docker_id, user_id):
    new_container = Container(name=name, port=port, status=status, subscription_plan=subscription_plan, docker_id=docker_id, user_id=user_id)
    db.session.add(new_container)
    db.session.commit()

# Add any additional business logic functions here