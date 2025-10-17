from flask import Blueprint, render_template, session
from models.template import Template
from models.container import Container

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    total_templates = Template.query.count()
    running_containers = Container.query.filter_by(status='running').count()
    total_containers = Container.query.count()
    total_users = Container.query.with_entities(Container.user_id).distinct().count()

    is_admin = 'admin' in session
    return render_template('index.html', is_admin=is_admin, total_templates=total_templates,
                           running_containers=running_containers, total_containers=total_containers,
                           total_users=total_users)