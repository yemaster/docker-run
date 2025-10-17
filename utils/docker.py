# docker.py
import docker
import threading
import time
from datetime import datetime
from models import db
from models.container import Container
from utils.logger import log_action
from flask import current_app

docker_client = docker.from_env()

def health_check():
    print("Starting health check thread...")
    while True:
        with current_app.app_context():
            containers = Container.query.filter(Container.status != 'removed').all()
            for cont in containers:
                try:
                    docker_cont = docker_client.containers.get(cont.docker_id)
                    if docker_cont.status != cont.status:
                        cont.status = docker_cont.status
                        db.session.commit()

                    if cont.destroy_time < datetime.now():
                        docker_cont.remove(force=True)
                        cont.status = 'removed'
                        db.session.commit()
                        log_action(f'Auto-remove container {cont.docker_id}', 'system')

                except docker.errors.NotFound:
                    cont.status = 'removed'
                    db.session.commit()
                    log_action(f'Delete non-existent container {cont.docker_id}', 'system')

        time.sleep(60)

def start_health_check_thread(app):
    threading.Thread(target=lambda: health_check_with_app(app), daemon=True).start()

def health_check_with_app(app):
    with app.app_context():
        health_check()
