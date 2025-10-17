from models import db
from datetime import datetime

class Log(db.Model):
    __tablename__ = 'logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(255))
    action = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def create_log(cls, user_id, action, details):
        log_entry = cls(user_id=user_id, action=action, details=details)
        db.session.add(log_entry)
        db.session.commit()
        return log_entry