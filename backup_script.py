import json
import os
import django
from django.core import serializers

# Установите переменную окружения для Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reservon.settings')
django.setup()

# Инициализируйте список для хранения всех данных
all_data = []

# Итерация по всем моделям вашего проекта
for model in django.apps.apps.get_models():
    try:
        # Получите все объекты текущей модели
        queryset = model.objects.all()
        
        # Сериализуйте объекты в формат JSON
        serialized = serializers.serialize('json', queryset, indent=4)
        
        # Загрузите сериализованные данные и добавьте их в общий список
        all_data.extend(json.loads(serialized))
        
        print(f"Сериализовано {queryset.count()} объектов из модели {model.__name__}.")
    except Exception as e:
        print(f"Ошибка при сериализации модели {model.__name__}: {e}")

# Запишите все данные в файл с кодировкой utf-8
with open('backup.json', 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=4)

print("Резервное копирование завершено успешно.")
