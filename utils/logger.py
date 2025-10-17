from models import db
from models.log import Log
from datetime import datetime

def log_action(action, user_id):
    log_entry = Log(
        user_id=user_id, 
        action=action, 
        timestamp=datetime.utcnow()
    )
    db.session.add(log_entry)
    db.session.commit()