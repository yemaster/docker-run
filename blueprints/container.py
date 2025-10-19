import os
import random
import base64
from datetime import datetime, timedelta
from docker.errors import NotFound

from flask import Blueprint, render_template, request, session, url_for, flash, redirect, current_app
from models.template import Template
from models.container import Container
from models import db
from utils.auth import get_user_id
from utils.docker import docker_client
from utils.logger import log_action

from utils.settings import get_setting

container_bp = Blueprint('container', __name__, url_prefix='/container')

MAX_PER_USER = 3
MAX_TOTAL = 20

def check_limits(user_id):
    user_count = Container.query.filter_by(user_id=user_id).filter(Container.status != 'removed').count()
    total_count = Container.query.filter(Container.status != 'removed').count()
    if user_count >= MAX_PER_USER:
        return False, '每个用户最多 3 个容器'
    if total_count >= MAX_TOTAL:
        return False, '总容器数已达上限'
    return True, ''

@container_bp.route('/create', methods=['POST'])
def create():
    user_id = get_user_id()
    template_id = request.form.get('template_id')
    container_name = request.form.get('container_name', '').strip()
    if not template_id:
        return {'success': False, 'message': '模板 ID 必须提供'}
    ok, msg = check_limits(user_id)
    if not ok:
        return {'success': False, 'message': msg}

    template = Template.query.get(template_id)
    if not template:
        return {'success': False, 'message': '模板不存在'}
    
    if container_name == '':
        container_name = f"{template.name}_{random.randint(1000,9999)}"
    
    if not all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in container_name):
        return {'success': False, 'message': '容器名称只能包含字母、数字、下划线和中划线'}

    # 自动分配主机端口
    used_ports = [c.host_port for c in Container.query.filter(Container.status != 'removed').all()]
    host_port = 30000
    while host_port in used_ports:
        host_port += 1

    # 创建 Docker 容器
    try:
        container_config = {
            "image": template.image,
            "detach": True,
            "ports": {f"{template.container_port}/tcp": host_port},
            "cpu_quota": int(float(template.cpu_limit) * 100000) if template.cpu_limit else None,
            "mem_limit": template.mem_limit if template.mem_limit else None,
            "name": f"{user_id}_{container_name}"
        }
        if len(template.command.strip()) > 0:
            container_config["command"] = template.command

        container = docker_client.containers.run(**container_config)
        docker_id = container.id

        # 默认 2 小时后销毁
        destroy_time = datetime.now() + timedelta(hours=2)
        container = Container(
            name=container_name,
            user_id=user_id,
            template_id=template.id,
            docker_id=docker_id,
            host_port=host_port,
            status='running',
            destroy_time=destroy_time
        )
        db.session.add(container)
        db.session.commit()
        log_action(f'Create container {docker_id}', user_id)
        return {'success': True, 'message': '容器创建成功', 'redirect': url_for('container.get_list')}
    except Exception as e:
        return {'success': False, 'message': f'容器创建失败: {str(e)}'}
    
@container_bp.route('/list')
def get_list():
    user_id = get_user_id()
    is_admin = 'admin' in session

    page = request.args.get('page', 1, type=int)
    per_page = 6
    offset = (page - 1) * per_page

    if is_admin:
        cont_query = Container.query.order_by(Container.id.desc())
    else:
        cont_query = Container.query.filter_by(user_id=user_id).filter(Container.status != 'removed').order_by(Container.id.desc())
    
    total_items = cont_query.count()
    containers = cont_query.offset(offset).limit(per_page).all()
    total_pages = (total_items - 1) // per_page + 1
    
    return render_template(
        'container/list.html',
        containers=containers, 
        per_page=per_page, 
        current_page=page, 
        total_items=total_items, 
        total_pages=total_pages, 
        is_admin=is_admin
    )

@container_bp.route('/<int:cont_id>/stat')
def stat(cont_id):
    user_id = get_user_id()
    is_admin = 'admin' in session
    
    cont = Container.query.filter_by(id=cont_id).filter(Container.status != 'removed').first()
    if not cont or (not is_admin and cont.user_id != user_id):
        flash('无权限')
        return redirect(url_for('container.get_list'))
    try:
        docker_cont = docker_client.containers.get(cont.docker_id)
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
    
@container_bp.route('/<int:cont_id>/overview')
def overview(cont_id):
    user_id = get_user_id()
    is_admin = 'admin' in session

    cont = Container.get_with_template_info(cont_id)
    if not cont or (not is_admin and cont["user_id"] != user_id):
        flash('无权限')
        return redirect(url_for('container.get_list'))
    
    # 获取容器的网络信息
    try:
        docker_cont = docker_client.containers.get(cont["docker_id"])
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
    return render_template(
        'container/overview.html', 
        container=cont, 
        host_ip=current_app.config["HOST_IP"], 
        is_admin=is_admin
    )

@container_bp.route('/<int:cont_id>/logs')
def logs(cont_id):
    user_id = get_user_id()
    is_admin = 'admin' in session

    cont = Container.get_with_template_info(cont_id)
    if not cont or (not is_admin and cont["user_id"] != user_id):
        flash('无权限')
        return redirect(url_for('container.get_list'))
    
    return render_template(
        'container/logs.html', 
        container=cont, 
        host_ip=current_app.config["HOST_IP"], 
        is_admin=is_admin
    )

@container_bp.route('/<int:cont_id>/terminal')
def terminal(cont_id):
    user_id = get_user_id()
    is_admin = 'admin' in session
    
    cont = Container.get_with_template_info(cont_id)
    if not cont or (not is_admin and cont["user_id"] != user_id):
        flash('无权限')
        return redirect(url_for('container.get_list'))
    
    return render_template(
        'container/terminal.html', 
        container=cont, 
        is_admin=is_admin, 
        host_ip=current_app.config["HOST_IP"]
    )

@container_bp.route('/<int:cont_id>/files')
def files(cont_id):
    user_id = get_user_id()
    is_admin = 'admin' in session
    
    cont = Container.get_with_template_info(cont_id)
    if not cont or (not is_admin and cont["user_id"] != user_id):
        flash('无权限')
        return redirect(url_for('container.get_list'))
    
    container = docker_client.containers.get(cont["docker_id"])
    workdir = container.attrs['Config']['WorkingDir'] or '/'
    return render_template('container/files.html', container=cont, current_path=workdir, host_ip=current_app.config["HOST_IP"], is_admin=is_admin)

@container_bp.route('/<int:cont_id>/files/<action>', methods=['GET', 'POST'])
def files_action(cont_id, action):
    user_id = get_user_id()
    is_admin = 'admin' in session
    
    cont = Container.get_with_template_info(cont_id)
    if not cont or (not is_admin and cont["user_id"] != user_id):
        return {
            'success': False,
            'message': "无权限"
        }
    
    try:
        # 获取容器详细信息
        container = docker_client.containers.get(cont["docker_id"])
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
            files.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))
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
                MAX_EDIT_SIZE = get_setting('MAX_EDIT_SIZE', default=102400, type_cast=int)
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
                response = current_app.response_class(generate(), mimetype='application/octet-stream')
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
        
    except NotFound:
        return {
            'success': False,
            'message': '容器不存在'
        }
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }

@container_bp.route('/<int:cont_id>/manage/<action>', methods=['GET', 'POST'])
def manage(cont_id, action):
    user_id = get_user_id()
    is_admin = 'admin' in session

    cont = Container.query.filter_by(id=cont_id).filter(Container.status != 'removed').first()
    if not cont or (not is_admin and cont.user_id != user_id):
        return {'success': False, 'message': '无权限'}

    try:
        docker_cont = docker_client.containers.get(cont.docker_id)
        if action == 'start':
            docker_cont.start()
            cont.status = docker_cont.status
            db.session.commit()

        elif action == 'stop':
            docker_cont.stop()
            cont.status = docker_cont.status
            db.session.commit()

        elif action == 'remove':
            cont.status = 'removed'
            db.session.commit()
            docker_cont.remove(force=True)
        elif action == 'extend':
            remaining = cont.destroy_time - datetime.now()
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
            new_destroy_time = cont.destroy_time + timedelta(hours=1)
            cont.destroy_time = new_destroy_time
            cont.extended_times += 1
            db.session.commit()

            log_action(f'Extend container {cont.docker_id}', user_id)
            
            return {
                'success': True,
                'new_destroy_time': new_destroy_time.isoformat()
            }
        
        log_action(f'{action} container {cont.docker_id}', user_id)
        return {'success': True, 'message': f'操作 {action} 成功', 'redirect': url_for('container.get_list')}
    except Exception as e:
        return {'success': False, 'message': f'操作失败: {str(e)}'}