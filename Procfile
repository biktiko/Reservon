web: gunicorn reservon.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A reservon.celery_app worker -l info -P solo
