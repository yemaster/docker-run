from models import db

class SystemSettings(db.Model):
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(255), unique=True, index=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)

    @classmethod
    def get_by_key(cls, key):
        return cls.query.filter_by(key=key).first()

    @classmethod
    def set_setting(cls, key, value):
        setting = cls.get_by_key(key)
        if setting:
            setting.value = value
        else:
            setting = cls(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return setting

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value
        }
    
default_settings = [
    {'key':'MAX_EDIT_SIZE', 'value':"102400", "decription": "最大编辑大小(单位：字节)"},
]

def initialize_default_settings():
    for setting in default_settings:
        existing_setting = SystemSettings.get_by_key(setting['key'])
        if not existing_setting:
            new_setting = SystemSettings(
                key=setting['key'],
                value=setting['value'],
                description=setting.get('description', '')
            )
            db.session.add(new_setting)
    db.session.commit()