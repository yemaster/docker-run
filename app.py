import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB

from dotenv import load_dotenv

import docker
import threading
import time
import random
import os
import base64
import bcrypt
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit, disconnect

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

HOST_IP = os.environ.get('HOST_IP', '127.0.0.1')
MAX_EDIT_SIZE = int(os.environ.get('MAX_EDIT_SIZE', 100 * 1024))

socketio = SocketIO(app,
        cors_allowed_origins='*',
        cors_allowed_methods=["GET", "POST", "OPTIONS"],  # 允许的 HTTP 方法
        cors_allowed_headers=["Content-Type"])

# Docker 客户端
docker_client = docker.from_env()

db_pool = PooledDB(
    creator=pymysql,
    mincached=1,
    maxcached=5,
    maxconnections=10,
    blocking=True,
    host=os.environ.get('DB_HOST', 'localhost'),
    user=os.environ.get('DB_USER', 'root'),
    password=os.environ.get('DB_PASS', ''),
    database=os.environ.get('DB_NAME', 'docker_run'),
    port=int(os.environ.get('DB_PORT', 3306)),
    charset='utf8mb4',
    cursorclass=DictCursor
)

def execute_query(sql, args=None):
    with db_pool.connection() as conn:
        with conn.cursor() as cursor:
            if args is None:
                cursor.execute(sql)
            else:
                cursor.execute(sql, args)
            if sql.strip().upper().startswith("SELECT"):
                res = cursor.fetchall()
                return res
            else:
                conn.commit()
                if sql.strip().upper().startswith("INSERT"):
                    return cursor.lastrowid
                return cursor.rowcount

def select_one(sql, args=None):
    with db_pool.connection() as conn:
        with conn.cursor() as cursor:
            if args is None:
                cursor.execute(sql)
            else:
                cursor.execute(sql, args)
            return cursor.fetchone()

def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# 初始化数据库
def init_db():
    execute_query('''
        CREATE TABLE IF NOT EXISTS admins (
            id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(255) UNIQUE,
            password_hash VARCHAR(255)
        )
    ''')
    execute_query('''
        CREATE TABLE IF NOT EXISTS templates (
            id INT PRIMARY KEY AUTO_INCREMENT,
            description TEXT,
            name VARCHAR(255),
            image VARCHAR(255),
            cpu_limit VARCHAR(50),
            mem_limit VARCHAR(50),
            disk_limit VARCHAR(50),
            command TEXT,
            available_command TEXT,
            tags TEXT,
            container_port INT
        )
    ''')
    execute_query('''
        CREATE TABLE IF NOT EXISTS containers (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255),
            user_id VARCHAR(255),
            template_id INT,
            docker_id VARCHAR(255),
            host_port INT,
            status VARCHAR(50),
            extended_times INT DEFAULT 0,
            destroy_time TIMESTAMP
        )
    ''')
    execute_query('''
        CREATE TABLE IF NOT EXISTS logs (
            id INT PRIMARY KEY AUTO_INCREMENT,
            action TEXT,
            user_id VARCHAR(255),
            timestamp TIMESTAMP
        )
    ''')
    hashed = hash_password(os.environ.get('ADMIN_PASSWORD', 'admin'))
    execute_query('INSERT IGNORE INTO admins (username, password_hash) VALUES (%s, %s)', (os.environ.get('ADMIN_USERNAME', 'admin'), hashed))

init_db()

# 登录检查装饰器
def admin_required(f):
    def wrap(*args, **kwargs):
        if 'admin' not in session:
            flash('需要管理员权限')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

def get_random_user_id():
    adjs = ["quick", "lazy", "sleepy", "noisy", "hungry", "happy", "sad", "brave", "calm", "eager", "fancy", "jolly", "kind", "lucky", "proud", "silly", "witty", "zealous", "bold", "clever"]
    nouns = ["fox", "dog", "head", "leg", "tail", "cat", "mouse", "house", "car", "bike", "tree", "river", "cloud", "star", "moon", "sun", "sky", "ocean", "mountain", "field", "forest"]
    return random.choice(adjs) + "_" + random.choice(nouns) + str(random.randint(100, 999))

# 获取用户 ID (游客用 session.sid)
def get_user_id():
    if 'admin' in session:
        return session['admin']
    if 'user_id' not in session:
        session['user_id'] = get_random_user_id()
    return session['user_id']

# 限制检查
MAX_PER_USER = 3
MAX_TOTAL = 20

def check_limits(user_id):
    user_count = select_one('SELECT COUNT(*) cnt FROM containers WHERE user_id = %s AND status != "removed"', (user_id,))['cnt']
    total_count = select_one('SELECT COUNT(*) cnt FROM containers WHERE status != "removed"')['cnt']
    if user_count >= MAX_PER_USER:
        return False, '每个用户最多 3 个容器'
    if total_count >= MAX_TOTAL:
        return False, '总容器数已达上限'
    return True, ''

# 记录日志
def log_action(action, user_id):
    execute_query('INSERT INTO logs (action, user_id, timestamp) VALUES (%s, %s, %s)',
                   (action, user_id, datetime.now().isoformat()))

# 定时检查容器健康
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

threading.Thread(target=health_check, daemon=True).start()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = select_one('SELECT * FROM admins WHERE username = %s', (username,))
        if admin and bcrypt.checkpw(password.encode('utf-8'), admin['password_hash'].encode('utf-8')):
            session['admin'] = username
            flash('登录成功')
            return redirect(url_for('index'))
        
        flash('登录失败')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    total_templates = select_one('SELECT COUNT(*) cnt FROM templates')['cnt']
    running_containers = select_one('SELECT COUNT(*) cnt FROM containers WHERE status = "running"')['cnt']
    total_containers = select_one('SELECT COUNT(*) cnt FROM containers')['cnt']
    total_users = select_one('SELECT COUNT(DISTINCT user_id) cnt FROM containers')['cnt']

    is_admin = 'admin' in session
    return render_template('index.html', is_admin=is_admin, total_templates=total_templates,
                           running_containers=running_containers, total_containers=total_containers,
                           total_users=total_users)

@app.route('/template/market')
def template_market():
    is_admin = 'admin' in session
    templates = execute_query('SELECT * FROM templates')
    return render_template('template_market.html', templates=templates, is_admin=is_admin)

@app.route('/container/create', methods=['POST'])
def create_container():
    user_id = get_user_id()
    template_id = request.form.get('template_id')
    container_name = request.form.get('container_name', '').strip()
    if not template_id:
        return {'success': False, 'message': '模板 ID 必须提供'}
    ok, msg = check_limits(user_id)
    if not ok:
        return {'success': False, 'message': msg}

    template = select_one('SELECT * FROM templates WHERE id = %s', (template_id,))
    if not template:
        return {'success': False, 'message': '模板不存在'}
    
    if container_name == '':
        container_name = f"{template['name']}_{random.randint(1000,9999)}"
    
    if not all(c.isalnum() or c in ('_', '-') for c in container_name):
        return {'success': False, 'message': '容器名称只能包含字母、数字、下划线和中划线'}

    # 自动分配主机端口
    used_ports = [c['host_port'] for c in execute_query('SELECT host_port FROM containers WHERE status != "removed"')]
    host_port = 30000
    while host_port in used_ports:
        host_port += 1

    # 创建 Docker 容器
    try:
        container_config = {
            "image": template['image'],
            "detach": True,
            "ports": {f"{template['container_port']}/tcp": host_port},
            "cpu_quota": int(float(template['cpu_limit']) * 100000) if template['cpu_limit'] else None,
            "mem_limit": template['mem_limit'] if template['mem_limit'] else None,
            "name": f"{user_id}_{container_name}"
        }
        if len(template['command'].strip()) > 0:
            container_config["command"] = template['command']
        container = docker_client.containers.run(**container_config)
        docker_id = container.id

        # 默认 2 小时后销毁
        destroy_time = datetime.now() + timedelta(hours=2)
        execute_query('INSERT INTO containers (user_id, name, template_id, docker_id, host_port, status, destroy_time) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                   (user_id, container_name, template_id, docker_id, host_port, 'running', destroy_time.isoformat()))
        log_action(f'Create container {docker_id}', user_id)
        return {'success': True, 'message': '容器创建成功', 'redirect': url_for('containers')}
    except Exception as e:
        return {'success': False, 'message': f'容器创建失败: {str(e)}'}

@app.route('/templates')
@admin_required
def templates():
    temps = execute_query('SELECT * FROM templates')
    is_admin = 'admin' in session
    return render_template('templates.html', templates=temps, is_admin=is_admin)

@app.route('/template/add', methods=['GET', 'POST'])
@admin_required
def template_add():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        image = request.form['image']
        tags = request.form.get('tags', '')
        cpu_limit = request.form['cpu_limit']
        mem_limit = request.form['mem_limit']
        disk_limit = request.form['disk_limit']
        command = request.form.get('command', '')
        available_command = request.form.get('available_command', '/bin/sh')
        container_port = int(request.form['container_port'])
        
        execute_query('INSERT INTO templates (name, description, image, tags, cpu_limit, mem_limit, disk_limit, command, available_command, container_port) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                       (name, description, image, tags, cpu_limit, mem_limit, disk_limit, command, available_command, container_port))
        log_action('Create template', session['admin'])
        flash('模板创建成功')
        return redirect(url_for('templates'))
    is_admin = 'admin' in session
    return render_template('template_add.html', is_admin=is_admin)

@app.route('/template/delete', methods=['POST'])
@admin_required
def templates_delete():
    temp_id = request.form.get('template_id')
    try:
        execute_query('DELETE FROM templates WHERE id = %s', (temp_id,))
        log_action(f'Delete template {temp_id}', session['admin'])
    except Exception as e:
        return {'success': False, 'message': f'删除失败: {str(e)}'}
    return {'success': True, 'message': '删除成功', 'redirect': url_for('templates')}

@app.route('/containers')
def containers():
    user_id = get_user_id()
    is_admin = 'admin' in session

    page = request.args.get('page', 1, type=int)
    per_page = 6
    offset = (page - 1) * per_page

    if is_admin:
        conts = execute_query('SELECT * FROM containers ORDER BY id desc LIMIT %s OFFSET %s', (per_page, offset))
        total_items = select_one('SELECT COUNT(*) cnt FROM containers')['cnt']
    else:
        conts = execute_query('SELECT * FROM containers WHERE user_id = %s AND status != "removed" ORDER BY id desc LIMIT %s OFFSET %s', (user_id, per_page, offset))
        total_items = select_one('SELECT COUNT(*) cnt FROM containers WHERE user_id = %s AND status != "removed"', (user_id,))['cnt']
    
    total_pages = (total_items - 1) // per_page + 1
    
    return render_template('containers.html', containers=conts, per_page=per_page, current_page=page, total_items=total_items, total_pages=total_pages, is_admin=is_admin)

@app.route('/container/<int:cont_id>/stat')
def container_info(cont_id):
    # 获取容器的 CPU 占用率和内存使用情况，用 json 返回
    user_id = get_user_id()
    is_admin = 'admin' in session
    
    cont = select_one('SELECT * FROM containers WHERE id = %s AND status != "removed"', (cont_id,))
    if not cont or (not is_admin and cont['user_id'] != user_id):
        flash('无权限')
        return redirect(url_for('containers'))
    try:
        docker_cont = docker_client.containers.get(cont['docker_id'])
        stats = docker_cont.stats(stream=False)
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_cpu_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
        cpu_count = len(stats['cpu_stats']['cpu_usage'].get('percpu_usage', []))
        cpu_percent = (cpu_delta / system_cpu_delta) * cpu_count * 100.0 if system_cpu_delta > 0 else 0.0
        mem_usage = stats['memory_stats']['usage']
        mem_limit = stats['memory_stats']['limit']
        mem_percent = (mem_usage / mem_limit) * 100.0 if mem_limit > 0 else 0.0
        return {
            'success': True,
            'cpu_percent': round(cpu_percent, 2),
            'mem_usage': mem_usage,
            'mem_limit': mem_limit,
            'mem_percent': round(mem_percent, 2)
        }
    except Exception as e:
        return {'error': str(e)}

@app.route('/container/<int:cont_id>/overview')
def container_overview(cont_id):
    user_id = get_user_id()
    is_admin = 'admin' in session

    cont = select_one('''
        SELECT c.*, t.name AS template_name, t.image, t.cpu_limit, t.mem_limit, t.disk_limit, t.command, t.tags, t.container_port, t.description
        FROM containers c
        JOIN templates t ON c.template_id = t.id
        WHERE c.id = %s AND c.status != "removed"
    ''', (cont_id,))
    if not cont or (not is_admin and cont['user_id'] != user_id):
        flash('无权限')
        return redirect(url_for('containers'))
    
    # 获取容器的网络信息
    try:
        docker_cont = docker_client.containers.get(cont['docker_id'])
        net_info = docker_cont.attrs['NetworkSettings']
        cont = dict(cont)
        cont['ip_address'] = net_info['IPAddress']
        cont['net_mode'] = docker_cont.attrs['HostConfig']['NetworkMode']
        cont['ports'] = net_info['Ports']
    except Exception as e:
        cont = dict(cont)
        cont['ip_address'] = 'N/A'
        cont['net_mode'] = 'N/A'
        cont['ports'] = 'N/A'
    is_admin = 'admin' in session
    return render_template('container_overview.html', container=cont, host_ip=HOST_IP, is_admin=is_admin)

@app.route('/container/<int:cont_id>/logs')
def container_logs(cont_id):
    user_id = get_user_id()
    is_admin = 'admin' in session

    # 联合查询获取模板信息
    cont = select_one('''
        SELECT c.*, t.name AS template_name, t.image, t.cpu_limit, t.mem_limit, t.disk_limit, t.tags, t.container_port, t.description
        FROM containers c
        JOIN templates t ON c.template_id = t.id
        WHERE c.id = %s AND c.status != "removed"
    ''', (cont_id,))
    if not cont or (not is_admin and cont['user_id'] != user_id):
        flash('无权限')
        return redirect(url_for('containers'))
    
    return render_template('container_logs.html', container=cont, host_ip=HOST_IP, is_admin=is_admin)

@app.route('/container/<int:cont_id>/terminal')
def container_terminal(cont_id):
    user_id = get_user_id()
    is_admin = 'admin' in session
    # 联合查询获取模板信息
    cont = select_one('''
        SELECT c.*, t.name AS template_name, t.image, t.cpu_limit, t.mem_limit, t.disk_limit, t.tags, t.container_port, t.available_command, t.description
        FROM containers c
        JOIN templates t ON c.template_id = t.id
        WHERE c.id = %s AND c.status != "removed"
    ''', (cont_id,))
    if not cont or (not is_admin and cont['user_id'] != user_id):
        flash('无权限')
        return redirect(url_for('containers'))
    return render_template('container_terminal.html', container=cont, is_admin=is_admin, host_ip=HOST_IP)

@app.route('/container/<int:cont_id>/files')
def container_files(cont_id):
    user_id = get_user_id()
    is_admin = 'admin' in session
    # 联合查询获取模板信息
    cont = select_one('''
        SELECT c.*, t.name AS template_name, t.image, t.cpu_limit, t.mem_limit, t.disk_limit, t.tags, t.container_port, t.description
        FROM containers c
        JOIN templates t ON c.template_id = t.id
        WHERE c.id = %s AND c.status != "removed"
    ''', (cont_id,))
    if not cont or (not is_admin and cont['user_id'] != user_id):
        flash('无权限')
        return redirect(url_for('containers'))
    container = docker_client.containers.get(cont['docker_id'])
    workdir = container.attrs['Config']['WorkingDir'] or '/'
    return render_template('container_files.html', container=cont, current_path=workdir, host_ip=HOST_IP, is_admin=is_admin)

@app.route('/container/<int:cont_id>/files/<action>', methods=['GET', 'POST'])
def container_files_action(cont_id, action):
    user_id = get_user_id()
    is_admin = 'admin' in session
    # 联合查询获取模板信息
    cont = select_one('''
        SELECT c.*, t.name AS template_name, t.image, t.cpu_limit, t.mem_limit, t.disk_limit, t.tags, t.container_port, t.description
        FROM containers c
        JOIN templates t ON c.template_id = t.id
        WHERE c.id = %s AND c.status != "removed"
    ''', (cont_id,))
    if not cont or (not is_admin and cont['user_id'] != user_id):
        return {
            'success': False,
            'message': "无权限"
        }
    
    try:
        # 获取容器详细信息
        container = docker_client.containers.get(cont['docker_id'])
        path = request.args.get('path', '/')
        if not path.startswith('/'):
            path = '/' + path
        
        container_info = container.attrs
        
        # 获取容器在主机上的根文件系统路径
        # 对于overlay2驱动，路径格式通常为/var/lib/docker/overlay2/<id>/merged
        graph_driver = container_info['GraphDriver']
        if graph_driver['Name'] != 'overlay2':
            raise Exception(f"不支持的存储驱动: {graph_driver['Name']}，仅支持overlay2")
            
        overlay_mount = graph_driver['Data']['MergedDir']
        if not os.path.exists(overlay_mount):
            raise Exception(f"容器文件系统路径不存在: {overlay_mount}")
        
        # 构建主机上对应的路径
        host_path = os.path.normpath(os.path.join(overlay_mount, path.lstrip('/')))

        if not os.path.exists(host_path) or not host_path.startswith(overlay_mount):
            raise Exception(f"容器内路径不存在: {path}")
            
        if not os.path.isdir(host_path):
            raise Exception(f"容器内路径不是目录: {path}")
        
        if action == 'get_list':
            files = []
            for entry in os.scandir(host_path):
                # 跳过特殊目录
                if entry.name in ('.', '..'):
                    continue
                    
                # 获取文件类型
                try:
                    entry_type = 'dir' if entry.is_dir() else 'file'
                
                    # 获取创建时间
                    stat_info = entry.stat()
                    created_time = datetime.fromtimestamp(stat_info.st_ctime)
                    
                    files.append({
                        'type': entry_type,
                        'name': entry.name,
                        'size': stat_info.st_size,
                        'created_time': created_time
                    })
                except Exception as e:
                    pass
            return {
                'success': True,
                'files': files
            }
        elif action == 'download' or action == 'view':
            filename = request.args.get('file')
            if not filename:
                return {
                    'success': False,
                    'message': '必须提供文件名'
                }
            if '/' in filename or '\\' in filename:
                return {
                    'success': False,
                    'message': '文件名不能包含路径分隔符'
                }
            file_path = os.path.join(host_path, filename)
            if not os.path.exists(file_path) or not os.path.isfile(file_path) or not file_path.startswith(overlay_mount):
                return {
                    'success': False,
                    'message': '文件不存在'
                }
            if action == 'view':
                if os.path.getsize(file_path) > MAX_EDIT_SIZE:
                    return {
                        'success': False,
                        'message': f'文件过大，仅支持编辑小于 {MAX_EDIT_SIZE // 1024} KB 的文件'
                    }
                with open(file_path, 'rb') as f:
                    content = f.read()
                encoded_content = base64.b64encode(content).decode('utf-8')
                return {
                    'success': True,
                    'filename': filename,
                    'content_base64': encoded_content
                }
            else:  # download
                def generate():
                    with open(file_path, 'rb') as f:
                        while True:
                            chunk = f.read(4096)
                            if not chunk:
                                break
                            yield chunk
                response = app.response_class(generate(), mimetype='application/octet-stream')
                response.headers.set('Content-Disposition', 'attachment', filename=filename)
                response.headers.set('Content-Length', os.path.getsize(file_path))
                return response

        if request.method == "POST":
            if action == "edit":
                filename = request.args.get('file')
                if not filename:
                    return {
                        'success': False,
                        'message': '必须提供文件名'
                    }
                if '/' in filename or '\\' in filename:
                    return {
                        'success': False,
                        'message': '文件名不能包含路径分隔符'
                    }
                file_path = os.path.join(host_path, filename)
                if not os.path.exists(file_path) or not os.path.isfile(file_path) or not file_path.startswith(overlay_mount):
                    return {
                        'success': False,
                        'message': '文件不存在'
                    }
                data = request.get_json()
                content_base64 = data.get('content_base64')
                if content_base64 is None:
                    return {
                        'success': False,
                        'message': '必须提供文件内容'
                    }
                try:
                    content = base64.b64decode(content_base64)
                except Exception as e:
                    return {
                        'success': False,
                        'message': f'Base64 解码失败: {str(e)}'
                    }
                with open(file_path, 'wb') as f:
                    f.write(content)
                return {
                    'success': True,
                    'message': '文件保存成功'
                }
            elif action == 'delete':
                filename = request.args.get('file')
                if not filename:
                    return {
                        'success': False,
                        'message': '必须提供文件名'
                    }
                if '/' in filename or '\\' in filename:
                    return {
                        'success': False,
                        'message': '文件名不能包含路径分隔符'
                    }
                file_path = os.path.join(host_path, filename)
                if not os.path.exists(file_path) or not os.path.isfile(file_path) or not file_path.startswith(overlay_mount):
                    return {
                        'success': False,
                        'message': '文件或目录不存在'
                    }
                if os.path.isdir(file_path):
                    os.rmdir(file_path)
                else:
                    os.remove(file_path)
                return {
                    'success': True,
                    'message': '删除成功'
                }
            elif action == 'create':
                filename = request.args.get('file')
                ftype = request.args.get('type')  # 'file' or 'dir'
                if not filename or ftype not in ('file', 'dir'):
                    return {
                        'success': False,
                        'message': '必须提供有效的文件名和类型'
                    }
                if '/' in filename or '\\' in filename:
                    return {
                        'success': False,
                        'message': '文件名不能包含路径分隔符'
                    }
                file_path = os.path.join(host_path, filename)
                if not file_path.startswith(overlay_mount):
                    return {
                        'success': False,
                        'message': '无效的文件路径'
                    }
                if os.path.exists(file_path):
                    return {
                        'success': False,
                        'message': '文件或目录已存在'
                    }
                if ftype == 'dir':
                    os.mkdir(file_path)
                else:
                    with open(file_path, 'wb') as f:
                        pass
                return {
                    'success': True,
                    'message': '创建成功'
                }
            elif action == 'upload':
                if 'file' not in request.files:
                    return {
                        'success': False,
                        'message': '必须提供上传的文件'
                    }
                upload_file = request.files['file']
                if upload_file.filename == '':
                    return {
                        'success': False,
                        'message': '文件名不能为空'
                    }
                if '/' in upload_file.filename or '\\' in upload_file.filename:
                    return {
                        'success': False,
                        'message': '文件名不能包含路径分隔符'
                    }
                file_path = os.path.join(host_path, upload_file.filename)
                if not file_path.startswith(overlay_mount):
                    return {
                        'success': False,
                        'message': '无效的文件路径'
                    }
                upload_file.save(file_path)
                return {
                    'success': True,
                    'message': '上传成功'
                }
        
    except docker.errors.NotFound:
        return {
            'success': False,
            'message': '容器不存在'
        }
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }

@app.route('/container/<int:cont_id>/manage/<action>', methods=['GET', 'POST'])
def manage_container(cont_id, action):
    user_id = get_user_id()
    is_admin = 'admin' in session
    cont = select_one('SELECT * FROM containers WHERE id = %s AND status != "removed"', (cont_id,))
    if not cont or (not is_admin and cont['user_id'] != user_id):
        return {'success': False, 'message': '无权限'}

    try:
        docker_cont = docker_client.containers.get(cont['docker_id'])
        if action == 'start':
            docker_cont.start()
            execute_query('UPDATE containers SET status = %s WHERE id = %s', (docker_cont.status, cont_id))
        elif action == 'stop':
            docker_cont.stop()
            execute_query('UPDATE containers SET status = %s WHERE id = %s', (docker_cont.status, cont_id))
        elif action == 'remove':
            execute_query('UPDATE containers SET status = %s WHERE id = %s', ('removed', cont_id))
            docker_cont.remove(force=True)
        elif action == 'extend':
            remaining = cont['destroy_time'] - datetime.now()
            if remaining > timedelta(minutes=20):
                return {
                    'success': False,
                    'message': '只有剩余时间少于20分钟才能延长'
                }
            if cont['extended_times'] >= 2:
                return {
                    'success': False,
                    'message': '每个容器最多只能延长2次'
                }
            new_destroy_time = cont['destroy_time'] + timedelta(hours=1)
            execute_query('UPDATE containers SET destroy_time = %s, extended_times = extended_times + 1 WHERE id = %s',
                       (new_destroy_time.isoformat(), cont_id))
            log_action(f'Extend container {cont["docker_id"]}', user_id)
            
            return {
                'success': True,
                'new_destroy_time': new_destroy_time.isoformat()
            }
        
        log_action(f'{action} container {cont["docker_id"]}', user_id)
        return {'success': True, 'message': f'操作 {action} 成功', 'redirect': url_for('containers')}
    except Exception as e:
        return {'success': False, 'message': f'操作失败: {str(e)}'}

@app.route('/logs')
@admin_required
def logs():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    logs = execute_query('SELECT * FROM logs ORDER BY id DESC LIMIT %s OFFSET %s', (per_page, offset))
    total_logs = select_one('SELECT COUNT(*) cnt FROM logs')['cnt']
    total_pages = (total_logs - 1) // per_page + 1
    is_admin = 'admin' in session
    return render_template('logs.html', logs=logs, per_page=per_page, current_page=page, total_items=total_logs, total_pages=total_pages, is_admin=is_admin)

@socketio.on('connect', namespace='/logs')
def handle_connect():
    pass

@socketio.on('start_logs', namespace='/logs')
def handle_start_logs(data):
    container_id = data.get('container_id')
    user_id = get_user_id()
    is_admin = 'admin' in session
    cont = select_one('SELECT * FROM containers WHERE id = %s AND status != "removed"', (container_id,))
    if not cont or (not is_admin and cont['user_id'] != user_id):
        emit('log_message', '无权限', namespace='/logs')
        disconnect()
        return

    try:
        container = docker_client.containers.get(cont['docker_id'])
        # 先获取最近的100行日志
        logs = container.logs(tail=100).decode('utf-8')
        emit('log_message', logs, namespace='/logs')
        # 然后持续获取新的日志
        for log in container.logs(stream=True, follow=True):
            emit('log_message', log.decode('utf-8'), namespace='/logs')
    except docker.errors.NotFound:
        emit('log_message', '容器不存在', namespace='/logs')
        disconnect()
    except Exception as e:
        emit('log_message', f'错误: {str(e)}', namespace='/logs')
        disconnect()

@socketio.on('disconnect', namespace='/logs')
def handle_disconnect():
    pass  # 客户端断开时无需额外操作

@socketio.on('connect', namespace='/terminal')
def terminal_connect():
    pass

terminal_sessions = {}

@socketio.on('closing_existing', namespace='/terminal')
def closing_existing(data):
    container_id = data.get('container_id')
    if not container_id:
        emit('error', {'message': 'No container_id provided for close_existing'})
        return

    for session_id, session_info in list(terminal_sessions.items()):
        if session_info['container_id'] == container_id:
            try:
                session_info['socket']._sock.close()
                print(f"Closed terminal session {session_id} for container {session_info['container_id']}")
            except Exception as e:
                print(f"Error closing session {session_id}: {str(e)}")
            del terminal_sessions[session_id]
    emit('closed_existing', {'message': 'Existing terminal sessions closed'})


@socketio.on('start_terminal', namespace='/terminal')
def start_terminal(data):
    container_id = data.get('container_id')
    command = data.get('command')
    cols = data.get('cols')
    rows = data.get('rows')
    sid = request.sid
    print(sid, container_id, command, cols, rows)
    if not container_id or not command or not cols or not rows:
        emit('error', {'message': 'Missing container_id, command, cols, or rows'})
        return
    
    for session_id, session_info in terminal_sessions.items():
        if session_info['container_id'] == container_id:
            # Kill exec id
            try:
                session_info['socket']._sock.close()
                print(f"Closed previous terminal session {session_id} for container {session_info['container_id']}")
            except Exception as e:
                print(f"Error closing previous session {session_id}: {str(e)}")
    
    try:
        user_id = get_user_id()
        is_admin = 'admin' in session
        cont = select_one('SELECT * FROM containers WHERE id = %s AND status != "removed"', (container_id,))
        if not cont or (not is_admin and cont['user_id'] != user_id):
            emit('error', {'message': '无权限'})
            return
        
        exec_id = docker_client.api.exec_create(
            cont['docker_id'],
            command,
            tty=True,
            stdin=True,
            stdout=True,
            stderr=True
        )['Id']
        
        docker_socket = docker_client.api.exec_start(exec_id, socket=True, tty=True)

        time.sleep(0.5)  # 500ms 延迟
        
        # 设置初始大小
        try:
            docker_client.api.exec_resize(exec_id, width=cols, height=rows)
        except docker.errors.DockerException as resize_error:
            print(f"Initial resize failed (common): {resize_error}")
            # 可选：重试
            time.sleep(0.2)
            try:
                docker_client.api.exec_resize(exec_id, width=cols, height=rows)
            except docker.errors.DockerException as retry_error:
                print(f"Retry resize failed: {retry_error}")
        
        terminal_sessions[sid] = {
            'container_id': container_id,
            'exec_id': exec_id,
            'socket': docker_socket
        }
        
        socketio.start_background_task(read_terminal_output, sid, docker_socket, docker_client, exec_id)
        emit('terminal_output', {'output': '\r\nTerminal connected\r\n'})
        
    except docker.errors.DockerException as e:
        emit('error', {'message': f'Docker error: {str(e)}'})
    except Exception as e:
        emit('error', {'message': f'Error: {str(e)}'})

def read_terminal_output(sid, docker_socket, client, exec_id):
    try:
        while True:
            output = docker_socket._sock.recv(1024)
            if not output:
                # 检查进程退出状态
                exec_info = client.api.exec_inspect(exec_id)
                exit_code = exec_info['ExitCode']
                socketio.emit('terminal_exit', {'exit_code': exit_code}, namespace='/terminal', to=sid)
                break
            socketio.emit('terminal_output', {'output': output.decode('utf-8', errors='replace')}, namespace='/terminal', to=sid)
    except Exception as e:
        socketio.emit('error', {'message': f'Terminal output error: {str(e)}'}, namespace='/terminal', to=sid)
    finally:
        try:
            docker_socket._sock.close()
        except:
            pass
        if sid in terminal_sessions:
            del terminal_sessions[sid]

@socketio.on('terminal_input', namespace='/terminal')
def terminal_input(data):
    sid = request.sid
    input_data = data.get('input')
    if not input_data or sid not in terminal_sessions:
        return
    
    try:
        docker_socket = terminal_sessions[sid]['socket']
        docker_socket._sock.send(input_data.encode('utf-8'))
    except Exception as e:
        emit('error', {'message': f'Error sending input: {str(e)}'})

@socketio.on('disconnect', namespace='/terminal')
def terminal_disconnect():
    sid = request.sid
    if sid in terminal_sessions:
        try:
            terminal_sessions[sid]['socket']._sock.close()
        except:
            pass
        del terminal_sessions[sid]

if __name__ == '__main__':
    socketio.run(app, debug=True)