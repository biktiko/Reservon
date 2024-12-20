from authentication.models import PushSubscription
from salons.models import Appointment
from django.db.models.signals import post_save
from django.dispatch import receiver
from .tasks import send_push_notification_task

import json
import logging

logger = logging.getLogger('main')

@receiver(post_save, sender=Appointment)
def notify_admins_on_new_booking(sender, instance, created, **kwargs):
    if created:
        salon = instance.salon
        admins = salon.admins.all()
        for admin in admins:
            push_subscriptions = PushSubscription.objects.filter(user=admin)
            for subscription in push_subscriptions:
                subscription_info = {
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    }
                }
                payload = {
                    "head": "Новое бронирование",
                    "body": f"Пользователь {instance.user.username} успешно забронировал услугу.",
                    "icon": "/static/main/img/notification-icon.png",
                    "url": "/user_account/bookings/"
                }
                send_push_notification_task.delay(subscription_info, json.dumps(payload))
                logger.info(f"Задача на отправку уведомления создана для {admin.username}.")