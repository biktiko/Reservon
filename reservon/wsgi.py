import os
import sys

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

# Укажите путь к проекту и виртуальной среде
sys.path.append('/home/reservon/repositories/Reservon')  # Путь к проекту
venv_path = '/home/reservon/venv/bin/activate_this.py'   # Путь к виртуальной среде

# Активируйте виртуальное окружение
with open(venv_path) as f:
    exec(f.read(), dict(__file__=venv_path))

# Загружаем настройки среды
load_dotenv()

# Укажите модуль настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservon.settings')

# Создаем WSGI-приложение
application = get_wsgi_application()
