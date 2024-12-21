# C:\Reservon\Reservon\main\tasks.py
from celery import shared_task
from pywebpush import webpush, WebPushException
from django.conf import settings
import time

import logging

logger = logging.getLogger('main')

@shared_task
def send_push_notification_task(subscription_info, payload):
    try:
        response = webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=settings.WEBPUSH_SETTINGS["VAPID_PRIVATE_KEY"],
            vapid_claims={
                "sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}",
            }
        )
        logger.info(f"Уведомление успешно отправлено: {response}")
        return response
    except WebPushException as ex:
        logger.error(f"Ошибка при отправке push уведомления: {ex}")
        if ex.response and ex.response.json():
            logger.error(f"Детали ошибки: {ex.response.json()}")
        return None
    
@shared_task
def add(x, y):
    time.sleep(5)  # Симуляция долгой задачи
    return x + y