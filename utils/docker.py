import docker
import threading
import time
from datetime import datetime

from models.db import execute_query
from utils.logger import log_action

docker_client = docker.from_env()

def health_check():
    print("Starting health check thread...")
    while True:
        containers = execute_query('SELECT * FROM containers WHERE status != "removed"')
        for cont in containers:
            try:
                docker_cont = docker_client.containers.get(cont['docker_id'])
                if docker_cont.status != cont['status']:
                    execute_query('UPDATE containers SET status = %s WHERE id = %s',
                               (docker_cont.status, cont['id']))
                
                # 检查到期时间
                if cont['destroy_time'] < datetime.now():
                    docker_cont.remove(force=True)
                    execute_query('UPDATE containers SET status = %s WHERE id = %s', ('removed', cont['id']))
                    log_action(f'Auto-remove container {cont["docker_id"]}', 'system')
            except docker.errors.NotFound:
                execute_query('UPDATE containers SET status = %s WHERE id = %s', ('removed', cont['id']))
                log_action(f'Delete non-existent container {cont["docker_id"]}', 'system')
        time.sleep(60)  # 每60秒检查一次

def start_health_check_thread():
    threading.Thread(target=health_check, daemon=True).start()