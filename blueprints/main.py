from flask import Blueprint, render_template, session
from models.db import select_one

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    total_templates = select_one('SELECT COUNT(*) cnt FROM templates')['cnt']
    running_containers = select_one('SELECT COUNT(*) cnt FROM containers WHERE status = "running"')['cnt']
    total_containers = select_one('SELECT COUNT(*) cnt FROM containers')['cnt']
    total_users = select_one('SELECT COUNT(DISTINCT user_id) cnt FROM containers')['cnt']

    is_admin = 'admin' in session
    return render_template('index.html', is_admin=is_admin, total_templates=total_templates,
                           running_containers=running_containers, total_containers=total_containers,
                           total_users=total_users)