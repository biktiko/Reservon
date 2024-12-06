# salons/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, Barber, BarberAvailability
from datetime import time

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

receiver(post_save, sender=Barber)
def create_default_availability(sender, instance, created, **kwargs):
    if created:
        # Определяем дни недели с понедельника по пятницу
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        for day in weekdays:
            # Доступное время до ланча
            BarberAvailability.objects.create(
                barber=instance,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(13, 0),
                is_available=True
            )
            # Ланч
            BarberAvailability.objects.create(
                barber=instance,
                day_of_week=day,
                start_time=time(13, 0),
                end_time=time(14, 0),
                is_available=False
            )
            # Доступное время после ланча
            BarberAvailability.objects.create(
                barber=instance,
                day_of_week=day,
                start_time=time(14, 0),
                end_time=time(18, 0),
                is_available=True
            )