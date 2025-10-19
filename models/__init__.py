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
        from models.settings import initialize_default_settings
        db.create_all()
        init_admin()
        initialize_default_settings()
