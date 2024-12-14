# user_account/apps.py

from django.apps import AppConfig

class UserAccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_account'        # Указывает на директорию приложения
    label = 'user_account'       # Уникальная метка приложения
