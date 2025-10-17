from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.template import Template
from models import db
from utils.auth import admin_required
from utils.logger import log_action

template_bp = Blueprint('template', __name__, url_prefix='/template')

@template_bp.route('/market')
def market():
    is_admin = 'admin' in session
    templates = Template.query.all()
    templates_list = [t.to_dict() for t in templates]
    return render_template('template/market.html', templates=templates_list, is_admin=is_admin)

@template_bp.route('/list')
@admin_required
def get_list():
    is_admin = 'admin' in session
    templates = Template.query.all()
    return render_template('template/list.html', templates=templates, is_admin=is_admin)

@template_bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add():
    if request.method == 'POST':
        try:
            template = Template(
                name = request.form['name'],
                description = request.form.get('description', ''),
                image = request.form['image'],
                tags = request.form.get('tags', ''),
                cpu_limit = request.form['cpu_limit'],
                mem_limit = request.form['mem_limit'],
                disk_limit = request.form['disk_limit'],
                command = request.form.get('command', ''),
                available_command = request.form.get('available_command', '/bin/sh'),
                container_port = int(request.form['container_port'])
            )

            db.session.add(template)
            db.session.commit()
        
            log_action('Create template', session['admin'])
            flash('模板创建成功')
            return redirect(url_for('template.get_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建模板失败: {str(e)}')

    is_admin = 'admin' in session
    return render_template('template/add.html', is_admin=is_admin)

@template_bp.route('/delete', methods=['POST'])
@admin_required
def delete():
    temp_id = request.form.get('template_id')
    try:
        template = Template.query.get(temp_id)
        if not template:
            return {'success': False, 'message': '模板不存在'}
        
        db.session.delete(template)
        db.session.commit()

        log_action(f'Delete template {temp_id}', session['admin'])
        return {'success': True, 'message': '删除成功', 'redirect': url_for('template.get_list')}
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': f'删除失败: {str(e)}'}