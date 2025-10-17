from models import db
from utils.auth import hash_password
from config import Config

class Admin(db.Model):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    @classmethod
    def create_admin(cls, username, password):
        password_hash = hash_password(password)
        admin = cls(username=username, password_hash=password_hash)
        db.session.add(admin)
        db.session.commit()
        return admin

    @classmethod
    def get_by_username(cls, username):
        return cls.query.filter_by(username=username).first()

def init_admin():
    existing = Admin.query.filter_by(username=Config.ADMIN_USERNAME).first()
    if not existing:
        Admin.create_admin(Config.ADMIN_USERNAME, Config.ADMIN_PASSWORD)
        print(f"Admin user '{Config.ADMIN_USERNAME}' created.")