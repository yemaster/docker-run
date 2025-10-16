from flask import session, redirect, url_for, flash
import bcrypt
import random

def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def admin_required(f):
    def wrap(*args, **kwargs):
        if 'admin' not in session:
            flash('需要管理员权限')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

def get_random_user_id():
    adjs = ["quick", "lazy", "sleepy", "noisy", "hungry", "happy", "sad", "brave", "calm", "eager", "fancy", "jolly", "kind", "lucky", "proud", "silly", "witty", "zealous", "bold", "clever"]
    nouns = ["fox", "dog", "head", "leg", "tail", "cat", "mouse", "house", "car", "bike", "tree", "river", "cloud", "star", "moon", "sun", "sky", "ocean", "mountain", "field", "forest"]
    return random.choice(adjs) + "_" + random.choice(nouns) + str(random.randint(100, 999))


def get_user_id():
    if 'admin' in session:
        return session['admin']
    if 'user_id' not in session:
        session['user_id'] = get_random_user_id()
    return session['user_id']
