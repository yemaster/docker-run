import select
import socket as std_socket
import time
import os
from flask_socketio import Namespace, emit, disconnect
from flask import request, session
from utils.docker import docker_client
from models.db import select_one
from utils.auth import get_user_id


class ContainerTerminalNamespace(Namespace):
    def __init__(self, namespace=None):
        super().__init__(namespace or '/terminal')
        # 记录 sid -> {container_id, exec_id, socket, last_activity}
        self.terminal_sessions = {}

    def on_connect(self):
        """客户端连接时触发"""
        pass

    def on_start_terminal(self, data):
        """启动终端会话"""
        container_id = data.get('container_id')
        command = data.get('command')
        cols = data.get('cols')
        rows = data.get('rows')
        sid = request.sid

        if not container_id or not command or not cols or not rows:
            emit('error', {'message': 'Missing container_id, command, cols, or rows'})
            return

        user_id = get_user_id()
        is_admin = 'admin' in session

        cont = select_one(
            'SELECT * FROM containers WHERE id = %s AND status != "removed"',
            (container_id,)
        )
        if not cont or (not is_admin and cont['user_id'] != user_id):
            emit('error', {'message': '无权限'})
            return

        # 关闭已有的 terminal session（同容器只允许一个）
        sessions_to_remove = [
            s for s, info in self.terminal_sessions.items()
            if info['container_id'] == container_id
        ]
        for s in sessions_to_remove:
            try:
                self.emit(
                    'terminal_output',
                    {'output': '\r\n[SYSTEM] Terminal session killed by new connection.\r\n'},
                    room=s
                )
            except Exception:
                pass
            self.kill_terminal_session(s)

        try:
            # 创建 exec 会话
            exec_id = docker_client.api.exec_create(
                cont['docker_id'],
                command,
                tty=True,
                stdin=True,
                stdout=True,
                stderr=True
            )['Id']

            docker_socket = docker_client.api.exec_start(exec_id, socket=True, tty=True)

            time.sleep(0.5)  # 延迟，等待启动

            # 初始 resize
            try:
                docker_client.api.exec_resize(exec_id, width=cols, height=rows)
            except Exception as resize_error:
                print(f"Initial resize failed (common): {resize_error}")
                time.sleep(0.2)
                try:
                    docker_client.api.exec_resize(exec_id, width=cols, height=rows)
                except Exception as retry_error:
                    print(f"Retry resize failed: {retry_error}")

            self.terminal_sessions[sid] = {
                'container_id': container_id,
                'exec_id': exec_id,
                'socket': docker_socket,
                'last_activity': time.time()
            }

            # 启动后台任务，读取终端输出
            from app import socketio  # 避免循环导入
            socketio.start_background_task(self.read_terminal_output, sid, docker_socket, exec_id)

            emit('terminal_started')

        except Exception as e:
            emit('error', {'message': f'Error: {str(e)}'})

    def read_terminal_output(self, sid, docker_socket, exec_id):
        """后台线程，实时读取 docker exec 输出并发送给客户端"""
        try:
            docker_socket._sock.settimeout(None)  # 无限等待

            while True:
                readable, _, _ = select.select([docker_socket._sock], [], [], None)
                if readable:
                    output = docker_socket._sock.recv(1024)
                    if not output:
                        # EOF，检查退出码
                        exec_info = docker_client.api.exec_inspect(exec_id)
                        exit_code = exec_info['ExitCode']
                        self.emit('terminal_exit', {'exit_code': exit_code}, room=sid)
                        break
                    self.emit(
                        'terminal_output',
                        {'output': output.decode('utf-8', errors='replace')},
                        room=sid
                    )
        except Exception as e:
            if isinstance(e, std_socket.timeout):
                self.emit('error', {'message': 'Terminal timed out, but retrying...'}, room=sid)
            else:
                self.emit('error', {'message': f'Terminal output error: {str(e)}'}, room=sid)
        finally:
            self.kill_terminal_session(sid)

    def on_terminal_input(self, data):
        """前端发送输入"""
        sid = request.sid
        input_data = data.get('input')
        if not input_data or sid not in self.terminal_sessions:
            return

        try:
            docker_socket = self.terminal_sessions[sid]['socket']
            docker_socket._sock.send(input_data.encode('utf-8'))
        except Exception as e:
            emit('error', {'message': f'Error sending input: {str(e)}'})

    def on_disconnect(self):
        """客户端断开时清理"""
        sid = request.sid
        if sid in self.terminal_sessions:
            self.kill_terminal_session(sid)

    def kill_terminal_session(self, sid):
        """清理终端 session，关闭 socket，杀掉进程"""
        session_info = self.terminal_sessions.pop(sid, None)
        if not session_info:
            return

        exec_id = session_info['exec_id']
        try:
            pid = docker_client.api.exec_inspect(exec_id).get("Pid", 0)
            if pid and pid > 0:
                os.kill(pid, 9)
        except Exception:
            pass

        try:
            session_info['socket']._sock.close()
        except Exception:
            pass
