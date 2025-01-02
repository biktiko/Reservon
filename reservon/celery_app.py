# C:\Reservon\Reservon\reservon\celery_app.py

import os
from celery import Celery

# переменную окружения Django settings
settings_module = os.getenv('DJANGO_SETTINGS_MODULE', 'reservon.settings')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

app = Celery('reservon')

# Загрузка конфигурации Celery из Django settings с префиксом 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматическое обнаружение задач в приложениях Django
app.autodiscover_tasks()

# # для локальной разработки
# if os.getenv('DJANGO_DEVELOPMENT') == 'True':
#     app.conf.update(
#         broker_url='memory://',
#         result_backend='django-db',
#         task_always_eager=True,
#         task_eager_propagates=True,
#     )