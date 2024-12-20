# authentication/signals.py

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile, PushSubscription
from salons.models import Appointment
from django.conf import settings
from pywebpush import webpush, WebPushException
import json
import logging

logger = logging.getLogger('myapp.adapter')

logger.debug('signals.py loaded')

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    # Пропускаем обработку для админских пользователей
    if instance.is_staff or instance.is_superuser:
        logger.debug(f"Skipping profile creation for admin user: {instance.username}")
        return

    if created:
        # Используем username как phone_number
        phone_number = instance.username
        Profile.objects.create(user=instance, phone_number=phone_number)
        logger.debug(f"Created profile for user: {instance.username} with phone_number: {phone_number}")
    else:
        try:
            profile = instance.main_profile
            phone_number = instance.username
            if phone_number:
                profile.phone_number = phone_number
                profile.save()
                logger.debug(f"Updated profile for user: {instance.username} with phone_number: {phone_number}")
            else:
                logger.debug(f"No phone_number provided for user: {instance.username}, skipping update")
        except Profile.DoesNotExist:
            # Если профиль не существует, создаём его
            phone_number = instance.username
            Profile.objects.create(user=instance, phone_number=phone_number)
            logger.debug(f"Created profile for user: {instance.username} with phone_number: {phone_number}")
        except Exception as e:
            logger.error(f"Error updating profile for user: {instance.username} - {e}")

@receiver(post_save, sender=Appointment)
def notify_admins_on_new_booking(sender, instance, created, **kwargs):
    if created:
        salon = instance.salon  # Предполагаем, что модель Booking связана с Salon
        admins = salon.admins.all()  # Предполагаем, что у Salon есть поле admins, связанное с User
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
                try:
                    webpush(
                        subscription_info=subscription_info,
                        data=json.dumps(payload),
                        vapid_private_key=settings.WEBPUSH_SETTINGS["VAPID_PRIVATE_KEY"],
                        vapid_claims={
                            "sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}",
                        }
                    )
                    logger.info(f"Уведомление отправлено администратору {admin.username}.")
                except WebPushException as ex:
                    logger.error(f"Ошибка при отправке уведомления пользователю {admin.username}: {ex}")