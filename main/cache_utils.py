# C:\Reservon\Reservon\main\cache_utils.py
import hashlib
from django.db.models.signals import post_save, post_delete
from django.core.cache import cache
from django.dispatch import receiver
import json
import logging
from salons.models import BarberAvailability, AppointmentBarberService

logger = logging.getLogger('main')

def generate_safe_cache_key(
    salon_id, date_str, hours, booking_details, cache_time_str, selected_barber_id='any'
):
    """Формирует ключ для кэша, используя хеш от параметров."""
    raw = json.dumps({
        "salon_id": salon_id,
        "date_str": date_str,
        "hours": hours,
        "booking_details": booking_details,
        "cache_time": cache_time_str,
        "selected_barber_id": selected_barber_id
    }, sort_keys=True)
    h = hashlib.md5(raw.encode('utf-8')).hexdigest()
    return f"avail_minutes_{h}"

@receiver([post_save, post_delete], sender=BarberAvailability)
def increment_cache_version_on_availability_change(sender, instance, **kwargs):
    salon_id = instance.barber.salon.id
    current_version = cache.get(f"available_minutes_version_{salon_id}", 1)
    cache.set(f"available_minutes_version_{salon_id}", current_version + 1, None)
    logger.debug(f"Версия кэша для салона {salon_id} увеличена до {current_version + 1} из-за изменения расписания барбера.")

@receiver([post_save, post_delete], sender=AppointmentBarberService)
def increment_cache_version_on_appointment_change(sender, instance, **kwargs):
    salon_id = instance.appointment.salon.id
    current_version = cache.get(f"available_minutes_version_{salon_id}", 1)
    cache.set(f"available_minutes_version_{salon_id}", current_version + 1, None)
    logger.debug(f"Версия кэша для салона {salon_id} увеличена до {current_version + 1} из-за изменения бронирования.")

def get_cache_version(salon_id):
    version = cache.get(f"available_minutes_version_{salon_id}", 1)
    return version