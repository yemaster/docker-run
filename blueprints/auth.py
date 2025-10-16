
import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.db import select_one

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = select_one('SELECT * FROM admins WHERE username = %s', (username,))
        if admin and bcrypt.checkpw(password.encode('utf-8'), admin['password_hash'].encode('utf-8')):
            session['admin'] = username
            flash('登录成功')
            return redirect(url_for('main.index'))
        
        flash('登录失败')
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('main.index'))