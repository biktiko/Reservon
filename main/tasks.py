# C:\Reservon\Reservon\main\tasks.py
from celery import shared_task
from pywebpush import webpush, WebPushException
from django.conf import settings
from authentication.models import PushSubscription
import logging

logger = logging.getLogger('main')

# @shared_task
# def send_push_notification_task(subscription_info, payload):
#     try:
#         response = webpush(
#             subscription_info=subscription_info,
#             data=payload,
#             vapid_private_key=settings.WEBPUSH_SETTINGS["VAPID_PRIVATE_KEY"],
#             vapid_claims={
#                 "sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}",
#             }
#         )
#         logger.info(f"Уведомление успешно отправлено: {response}")
#         return {"status": response.status_code, "reason": response.reason}
#     except WebPushException as ex:
#         logger.error(f"Ошибка при отправке push уведомления: {ex}")
#         if ex.response and ex.response.json():
#             logger.error(f"Детали ошибки: {ex.response.json()}")
#         return None

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
        return {"status": response.status_code, "reason": response.reason}
    except WebPushException as ex:
        logger.error(f"Ошибка при отправке push уведомления: {ex}")
        if ex.response is not None:
            code = ex.response.status_code
            logger.error(f"HTTP code: {code}")
            # Выведем ещё reason, если есть
            logger.error(f"Reason: {ex.response.reason}")
            
            # Удаляем «битую» подписку
            if code in [400, 404, 410]:  # 410 Gone тоже часто означает что подписка недействительна
                endpoint = subscription_info.get("endpoint")
                logger.error(f"Подписка endpoint={endpoint} будет удалена (status_code={code}).")
                from authentication.models import PushSubscription  # или где у вас хранится
                PushSubscription.objects.filter(endpoint=endpoint).delete()
        return None
