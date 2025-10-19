from models.settings import SystemSettings

def get_setting(key, default=None, type_cast=str):
    try:
        setting = SystemSettings.get_by_key(key)
        if setting:
            return type_cast(setting.value)
        else:
            return default
    except (ValueError, TypeError):
        return default