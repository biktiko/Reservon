# C:\Reservon\Reservon\reservon\celery_app.py

import os
from celery import Celery

# Установите переменную окружения Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservon.settings')  # Обратите внимание на регистр

app = Celery('reservon')  # Имя проекта должно соответствовать названию пакета

# Загрузка конфигурации Celery из Django settings с префиксом 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматическое обнаружение задач в приложениях Django
app.autodiscover_tasks()
