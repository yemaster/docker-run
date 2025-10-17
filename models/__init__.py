from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = None

def init_db(app):
    global migrate
    db.init_app(app)
    migrate = Migrate(app, db)

    with app.app_context():
        from models.admin import init_admin
        db.create_all()
        init_admin()
