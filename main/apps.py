
# main/apps.py

from django.apps import AppConfig

class MainConfig(AppConfig):
    name = 'main'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from simple_history import register
        from django.contrib.auth.models import User
        register(User, app=self.name)