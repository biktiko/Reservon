# authentication/signals.py

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile
import logging

logger = logging.getLogger(__name__)

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
