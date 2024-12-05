# bookings/utils.py
from salons.models import Barber, AppointmentBarberService
import random

def get_random_available_barber(start_datetime, end_datetime, salon):
    # Получаем всех мастеров в салоне
    barbers = Barber.objects.filter(salon=salon)

    # Идентификаторы занятых мастеров
    busy_barber_ids = AppointmentBarberService.objects.filter(
        start_datetime__lt=end_datetime,
        end_datetime__gt=start_datetime
    ).values_list('barber_id', flat=True)

    # Доступные мастера
    available_barbers = barbers.exclude(id__in=busy_barber_ids)

    if available_barbers.exists():
        return random.choice(available_barbers)
    else:
        return None
