# Dockerfile

# Используем официальный образ Python
FROM python:3.12

# Устанавливаем рабочую директорию
WORKDIR /code

# Копируем файл зависимостей
COPY requirements.txt /code/

# Устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Копируем остальную часть проекта
COPY . /code/

# Открываем порт (опционально)
EXPOSE 8000
EXPOSE 5555

# Команда по умолчанию (можно переопределить в docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
