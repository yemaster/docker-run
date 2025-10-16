from flask import Blueprint, render_template, request, session
from models.db import execute_query, select_one
from utils.auth import admin_required

logs_bp = Blueprint('logs', __name__, url_prefix='/logs')

@logs_bp.route('/list')
@admin_required
def logs_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    logs = execute_query('SELECT * FROM logs ORDER BY id DESC LIMIT %s OFFSET %s', (per_page, offset))
    total_logs = select_one('SELECT COUNT(*) cnt FROM logs')['cnt']
    total_pages = (total_logs - 1) // per_page + 1
    is_admin = 'admin' in session
    return render_template('logs/list.html', logs=logs, per_page=per_page, current_page=page, total_items=total_logs, total_pages=total_pages, is_admin=is_admin)