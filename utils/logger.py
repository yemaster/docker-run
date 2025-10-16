from models.db import execute_query
from datetime import datetime

def log_action(action, user_id):
    execute_query('INSERT INTO logs (action, user_id, timestamp) VALUES (%s, %s, %s)',
                   (action, user_id, datetime.now().isoformat()))