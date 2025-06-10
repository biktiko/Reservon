# salons/views.py
from django.shortcuts import render, get_object_or_404
from .models import Salon, Barber, Service, ServiceCategory, AppointmentBarberService, BarberAvailability, BarberService
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
import json
from collections import defaultdict
from django.core.cache import cache
from django.dispatch import receiver
from .utils import get_candidate_slots, format_free_ranges, parse_booking_request, allocate_barbers, save_appointment, notify_barbers, choose_user
from django.views.decorators.csrf import csrf_exempt
from django.db.models.signals import post_save, post_delete
import hashlib
import logging
from .errors import BookingError, ClientError


logger = logging.getLogger('booking')

# @cache_page(60 * 15)
def main(request):
    query = request.GET.get('q', '')
    city_filter = request.GET.get('city', '')
    category_filter = request.GET.get('category', '')
    if query:
        salons = Salon.objects.filter(
            Q(name__icontains=query) | Q(address__icontains=query)
        )
    else:
        salons = Salon.objects.filter(status='active')
    if city_filter:
        salons = salons.filter(city=city_filter)
    if category_filter:
        salons = salons.filter(category__iexact=category_filter)
    context = {
        'salons': salons,
        'q': query,
    }
    return render(request, 'salons/salons.html', context)


def get_cache_version(salon_id):
    version = cache.get(f"available_minutes_version_{salon_id}", 1)
    return version

def salon_detail(request, id):
    # Получаем салон по ID
    salon = get_object_or_404(Salon, id=id)

    if salon.mod=='category':
        # Получаем категории услуг, имеющие активные услуги в данном салоне
        service_categories = ServiceCategory.objects.filter(
            services__salon=salon,
            services__status='active'
        ).distinct()

        # Создаем структуру данных: {category: [services]}
        categories_with_services = []
        for category in service_categories:
            services = Service.objects.filter(
                salon=salon,
                status='active',
                category=category
            )
            if services.exists():
                categories_with_services.append({
                    'category': category,
                    'services': services
                })

        # Собираем барберов по категориям
        barbers_by_category = {}
        for entry in categories_with_services:
            category = entry['category']

            barbers = Barber.objects.filter(categories=category, salon=salon, status='active')

            barbers_list = []
            for barber in barbers:
                barbers_list.append({
                    'id': barber.id,
                    'name': barber.name,
                    'avatar': barber.get_avatar_url(),
                    'description': barber.description or '',
                })
            barbers_by_category[category.id] = barbers_list

        # Подготовка данных для передачи в JavaScript (если необходимо)
        barbers_by_category_json = json.dumps(barbers_by_category, cls=DjangoJSONEncoder)
        # print('barbersByCategory', barbers_by_category_json)
        context = {
            'salon': salon,
            'categories_with_services': categories_with_services,
            'barbers_by_category': barbers_by_category,
            'barbers_by_category_json': barbers_by_category_json,
        }
    elif salon.mod == 'barber':
        # Режим barber: используем BarberService
        service_categories = ServiceCategory.objects.filter(
            barber_services__barber__salon=salon,
            barber_services__status='active'
        ).distinct()

        categories_with_barber_services = []
        for category in service_categories:
            barber_services = BarberService.objects.filter(
                category=category,
                barber__salon=salon,
                status='active'
            ).select_related('barber')
            if barber_services.exists():
                categories_with_barber_services.append({
                    'category': category,
                    'services': barber_services
                })

        # Собираем барберов по категориям
        barbers_by_category = {}
        for entry in categories_with_barber_services:
            category = entry['category']

            barbers = Barber.objects.filter(
                categories=category,
                salon=salon,
                barber_services__category=category,
                status='active'
            ).distinct()
            
            barbers_list = []

            for barber in barbers:
                barbers_list.append({
                    'id': barber.id,
                    'name': barber.name,
                    'avatar': barber.get_avatar_url(),
                    'description': barber.description or '',
                })
            barbers_by_category[category.id] = barbers_list

        # Подготовка данных для передачи в JavaScript (если необходимо)
        barbers_by_category_json = json.dumps(barbers_by_category, cls=DjangoJSONEncoder)

        context = {
            'salon': salon,
            'categories_with_services': categories_with_barber_services,
            'barbers_by_category': barbers_by_category,
            'barbers_by_category_json': barbers_by_category_json,
        }
    else:
        context = {
            'salon': salon,
            'mode':'unknown mode'
        }
    
    return render(request, 'salons/salon-detail.html', context)

def get_barber_availability(request, barber_id):
    try:
        barber = Barber.objects.get(id=barber_id, status='active')
        availability = barber.availability
        return JsonResponse({'availability': availability})
    except Barber.DoesNotExist:
        return JsonResponse({'error': 'Barber not found'}, status=404)
    
from rest_framework.decorators import api_view, permission_classes
@api_view(['POST'])
def get_available_minutes(request):
    data = request.data
    salon_id = data.get('salon_id')
    date_str = data.get('date')
    hours = data.get('hours', [])
    booking_details = data.get('booking_details', [])
    selected_barber_id = data.get('selected_barber_id', 'any')

    try:
        total_duration = int(data.get('total_service_duration', 0))
    except (ValueError, TypeError):
        return Response({'available_minutes': {}, 'error': 'Invalid total_service_duration.'}, status=400)

    if not salon_id or not date_str or not hours:
        return Response({'available_minutes': {}, 'error': 'Missing required fields.'}, status=400)
    if not all(isinstance(h, int) for h in hours):
        return Response({'available_minutes': {}, 'error': 'Field hours must be list of ints.'}, status=400)

    slots = get_candidate_slots(salon_id, date_str, booking_details, total_duration, selected_barber_id)
    by_hour = defaultdict(list)
    for slot in slots:
        if slot.hour in hours:
            by_hour[slot.hour].append(slot.minute)

    avail = {str(h): sorted(set(by_hour.get(h, []))) for h in hours}
    return Response({'available_minutes': avail})

@api_view(['POST'])
def get_nearest_available_time(request):
    data = request.data
    try:
        salon_id = data['salon_id']
        date_str = data['date']
        chosen_hour = int(data['chosen_hour'])
    except (KeyError, ValueError):
        return Response({'error': 'Missing or invalid fields.'}, status=400)

    booking_details = data.get('booking_details', [])
    selected_barber_id = data.get('selected_barber_id', 'any')
    try:
        total_duration = int(data.get('total_service_duration', 0))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid total_service_duration.'}, status=400)

    slots = get_candidate_slots(salon_id, date_str, booking_details, total_duration, selected_barber_id)
    if not slots:
        return Response({'nearest_before': None, 'nearest_after': None})

    ref_naive = datetime.strptime(f"{date_str} {chosen_hour:02d}:00", '%Y-%m-%d %H:%M')
    ref_time = timezone.make_aware(ref_naive, timezone.get_current_timezone())

    before = [s for s in slots if s <= ref_time]
    after = [s for s in slots if s >= ref_time]
    nb = max(before) if before else None
    na = min(after) if after else None

    # Если оба варианта в пределах ±30 мин и очень близки, оставляем только nb
    if nb and na:
        diff = abs((nb - na).total_seconds()) / 60
        if diff < 30:
            na = None

    fmt = '%H:%M'
    return Response({
        'nearest_before': nb.strftime(fmt) if nb else None,
        'nearest_after': na.strftime(fmt) if na else None,
    })

@api_view(['POST'])
def get_free_time_ranges(request):
    data = request.data
    salon_id = data.get('salon_id')
    date_str = data.get('date')
    booking_details = data.get('booking_details', [])
    selected_barber_id = data.get('selected_barber_id', 'any')
    try:
        total_duration = int(data.get('total_service_duration', 0))
    except (ValueError, TypeError):
        return Response({'error': 'Invalid total_service_duration.'}, status=400)

    slots = get_candidate_slots(salon_id, date_str, booking_details, total_duration, selected_barber_id)
    ranges = format_free_ranges(slots)
    result = [f"{r[0].strftime('%H:%M')}-{r[1].strftime('%H:%M')}" for r in ranges]

    return Response({'free_time_ranges': result})

@csrf_exempt
@transaction.atomic
def book_appointment(request, id):
    logger.debug(f"book_appointment called with salon_id={id}")
    try:
        salon, mode, start, end, details, total, comment, phone = parse_booking_request(request, id)
        user = choose_user(request, phone)
        assignments = allocate_barbers(salon, start, end, details, total)
        appt = save_appointment(salon, user, start, end, comment, assignments, mode)
        notify_barbers(appt)
        logger.info(f"Booking {appt.id} created successfully")
        return JsonResponse({'success': True, 'message': 'Booking created'})
    except BookingError as e:
        logger.warning(f"BookingError: {e.message}")
        return JsonResponse({'error': e.message, 'nearest_before': e.nearest_before, 'nearest_after': e.nearest_after}, status=400)
    except ClientError as e:
        logger.warning(f"ClientError: {e.message}")
        return JsonResponse({'error': e.message}, status=e.status)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)

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

def normalize_phone(phone: str) -> str:
    """
    Нормализует номер телефона в формат E.164 (например, +374...), 
    удаляя лишние символы и пробелы.
    """
    if not phone:
        return ""
    phone = phone.strip()
    allowed_chars = set("0123456789+")
    phone = "".join(ch for ch in phone if ch in allowed_chars)
    # Если телефон не начинается с '+', добавляем
    if not phone.startswith("+"):
        phone = "+" + phone
    return phone

