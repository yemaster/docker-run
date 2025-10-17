from flask import session
from flask_socketio import Namespace, disconnect
from utils.docker import docker_client
from utils.auth import get_user_id
from models.container import Container
from docker.errors import NotFound

class ContainerLogsNamespace(Namespace):
    def on_connect(self):
        pass

    def on_start_logs(self, data):
        container_id = data.get('container_id')
        user_id = get_user_id()
        is_admin = 'admin' in session
        cont = Container.query.filter_by(id=container_id).filter(Container.status != 'removed').first()
        if not cont or (not is_admin and cont.user_id != user_id):
            self.emit('log_message', '无权限')
            disconnect()
            return

        try:
            container = docker_client.containers.get(cont.docker_id)
            for log in container.logs(stream=True, follow=True):
                self.emit('log_message', log.decode('utf-8'))
        except NotFound:
            self.emit('log_message', '容器不存在')
            disconnect()
        except Exception as e:
            self.emit('log_message', f'错误: {str(e)}')
            disconnect()

    def on_disconnect(self):
        pass