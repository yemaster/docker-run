from flask import Flask
from flask_socketio import SocketIO
from config import Config
from dotenv import load_dotenv
from utils.docker import start_health_check_thread

# -------- DB ---------
from models.db import init_db

# -------- Blueprints ---------
from blueprints.main import main_bp
from blueprints.auth import auth_bp
from blueprints.template import template_bp
from blueprints.container import container_bp
from blueprints.logs import logs_bp

# -------- Sockets ---------
from sockets.container_logs import ContainerLogsNamespace
from sockets.container_terminal import ContainerTerminalNamespace

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

socketio = SocketIO(app,
        cors_allowed_origins='*',
        cors_allowed_methods=["GET", "POST", "OPTIONS"],  # 允许的 HTTP 方法
        cors_allowed_headers=["Content-Type"])

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(template_bp)
app.register_blueprint(container_bp)
app.register_blueprint(logs_bp)

# Register socket namespaces
socketio.on_namespace(ContainerLogsNamespace('/container_logs'))
socketio.on_namespace(ContainerTerminalNamespace('/container_terminal'))

# Initialize
init_db()
start_health_check_thread()

if __name__ == '__main__':
    socketio.run(app, debug=True)