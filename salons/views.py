# salons/views.py
from django.shortcuts import render, get_object_or_404
from .models import Salon, Appointment, Barber, Service, ServiceCategory, AppointmentBarberService, BarberAvailability, BarberService
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta, time, timezone as dt_timezone
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
import json
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch
from collections import defaultdict
from django.core.cache import cache
from django.dispatch import receiver
from main.tasks import send_push_notification_task
from authentication.models import PushSubscription
from django.views.decorators.cache import never_cache
from django.conf import settings
from reservon.utils.twilio_service import send_whatsapp_message

import logging

logger = logging.getLogger('booking')

# @cache_page(60 * 15)
@never_cache
def main(request):
    query = request.GET.get('q', '')
    if query:
        salons = Salon.objects.filter(
            Q(name__icontains=query) | Q(address__icontains=query)
        )
    else:
        salons = Salon.objects.filter(status='active')
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

            barbers = Barber.objects.filter(categories=category, salon=salon)

            barbers_list = []
            for barber in barbers:
                barbers_list.append({
                    'id': barber.id,
                    'name': barber.name,
                    'avatar': barber.get_avatar_url(),
                    'description': barber.description or ''
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
                barber_services__category=category
            ).distinct()

            barbers_list = []

            for barber in barbers:
                barbers_list.append({
                    'id': barber.id,
                    'name': barber.name,
                    'avatar': barber.get_avatar_url(),
                    'description': barber.description or ''
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
        barber = Barber.objects.get(id=barber_id)
        availability = barber.availability
        return JsonResponse({'availability': availability})
    except Barber.DoesNotExist:
        return JsonResponse({'error': 'Barber not found'}, status=404)
    
from collections import defaultdict
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db.models import Prefetch
from django.utils import timezone
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
import logging

from salons.models import (
    Salon, BarberAvailability,
    AppointmentBarberService, ServiceCategory, Barber
)
# Если у вас есть настройки логгера
logger = logging.getLogger(__name__)

@api_view(['POST'])
def get_available_minutes(request):
    """Получение доступных 5-минутных слотов на указанные часы.

    Тело (request.data):
    {
      "salon_id": <int>,
      "date": "YYYY-MM-DD",
      "hours": [int, int, ...],
      "booking_details": [
          {
            "categoryId": str/int,
            "services": [{ "serviceId": int, "duration": int}, ...],
            "barberId": "any" или str(int),
            "duration": int
          },
          ...
      ],
      "selected_barber_id": "any" или str(...)? (опционально)
      "total_service_duration": int
    }
    """

    data = request.data

    # Логируем входные данные
    logger.info("Request data = %r", data)

    salon_id = data.get('salon_id')
    booking_details = data.get('booking_details', [])
    date_str = data.get('date')
    hours = data.get('hours', [])
    selected_barber_id = data.get('selected_barber_id', 'any')

    # total_service_duration может быть строкой. Попробуем int(...)
    try:
        total_service_duration = int(data.get('total_service_duration', 0))
    except (ValueError, TypeError) as e:
        logger.error("total_service_duration не является целым числом: %r", e)
        return Response(
            {"available_minutes": {}, "error": "Неверный тип total_service_duration."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Проверка обязательных полей
    if not salon_id or not date_str or not hours:
        logger.error("Отсутствуют обязательные поля salon_id/date_str/hours.")
        return Response(
            {'available_minutes': {}, 'error': 'Отсутствуют обязательные поля (salon_id, date, hours).'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Проверяем, что hours — список целых
    if not isinstance(hours, list) or not all(isinstance(h, int) for h in hours):
        logger.error("Поле 'hours' должно быть списком целых чисел, а получено: %r", hours)
        return Response(
            {'available_minutes': {}, 'error': "Поле 'hours' должно быть списком целых чисел."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Логируем основные поля
    logger.info("Parsed fields: salon_id=%r, date=%r, hours=%r, total_service_duration=%r, selected_barber_id=%r",
                salon_id, date_str, hours, total_service_duration, selected_barber_id)
    logger.info("Booking details = %r", booking_details)

    # Загружаем салон
    try:
        salon = Salon.objects.prefetch_related(
            Prefetch('barbers__availabilities', queryset=BarberAvailability.objects.all())
        ).get(id=salon_id)
    except Salon.DoesNotExist:
        logger.error("Салон с ID %r не найден.", salon_id)
        return Response(
            {'available_minutes': {}, 'error': f'Салон с ID={salon_id} не найден.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Парсим дату
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError as e:
        logger.error("Ошибка форматирования даты '%r': %r", date_str, e)
        return Response(
            {'available_minutes': {}, 'error': 'Некорректный формат даты (ожидается YYYY-MM-DD).'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # day_code
    day_code = date.strftime('%A').lower()
    logger.info("Day code = %r", day_code)

    # Предзагружаем барберов
    barbers = salon.barbers.all()
    logger.info("Found %d barbers in salon %r", len(barbers), salon.name)

    # Собираем barber_availability
    barber_availability = {}
    for b in barbers:
        avails = b.availabilities.filter(day_of_week=day_code)
        local_list = []
        for interval in avails:
            local_list.append({
                'start_time': interval.start_time,
                'end_time': interval.end_time,
                'is_available': interval.is_available
            })
        barber_availability[b.id] = local_list

    logger.info("barber_availability = %r", barber_availability)

    # Находим занятые интервалы
    busy_appointments = AppointmentBarberService.objects.filter(
        barber__salon=salon,
        start_datetime__date=date
    ).select_related('barber')

    barber_busy_times = defaultdict(list)
    for appbs in busy_appointments:
        barber_busy_times[appbs.barber_id].append((appbs.start_datetime, appbs.end_datetime))

    logger.info("Found busy appointments: %r", barber_busy_times)

    # Обработка booking_details
    active_categories = []
    if booking_details:
        for cat_detail in booking_details:
            cat_id = cat_detail.get('categoryId')
            services_list = cat_detail.get('services', [])
            barber_id_ = cat_detail.get('barberId', 'any')
            # duration
            try:
                dur_ = int(cat_detail.get('duration', 0))
            except (ValueError, TypeError):
                logger.warning("Некорректная длительность в booking_details: %r", cat_detail)
                dur_ = 0

            active_categories.append({
                'category_id': cat_id,
                'services': services_list,
                'barber_id': barber_id_,
                'duration': dur_
            })
    logger.info("active_categories = %r", active_categories)

    available_minutes = defaultdict(set)
    logger.info("Start building available_minutes...")

    now = timezone.now()

    # Цикл по часам
    for hour in hours:
        try:
            naive_dt = datetime.combine(date, datetime.strptime(str(hour), "%H").time())
            start_of_hour = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except ValueError as e:
            logger.error("Ошибка при создании datetime для hour=%r: %r", hour, e)
            available_minutes[hour] = []
            continue

        if booking_details:
            # Общая длительность
            total_cat_duration = sum(c['duration'] for c in active_categories)

            for minute in range(0, 60, 5):
                minute_start = start_of_hour + timedelta(minutes=minute)
                minute_end = minute_start + timedelta(minutes=total_cat_duration)

                # Пропускаем прошедшее время
                if minute_start < now:
                    continue

                schedule_possible = True
                # Слоты, занятые в рамках текущего цикла
                barber_schedules = defaultdict(list)

                # Проходим по всем "категориям" (блокам)
                local_start = minute_start
                for cat_obj in active_categories:
                    cat_id = cat_obj['category_id']
                    dur_cat = cat_obj['duration']
                    barb_id = cat_obj['barber_id']
                    end_cat = local_start + timedelta(minutes=dur_cat)

                    if barb_id != 'any':
                        # Конкретный барбер
                        try:
                            b_int = int(barb_id)
                        except (ValueError, TypeError):
                            logger.warning("Некорректный barberId=%r", barb_id)
                            schedule_possible = False
                            break

                        bbb = barbers.filter(id=b_int).first()
                        if not bbb:
                            logger.warning("Барбер с ID %r не найден в салоне %r", b_int, salon.name)
                            schedule_possible = False
                            break

                        if is_barber_busy(bbb.id, local_start, end_cat, barber_busy_times):
                            schedule_possible = False
                            break

                        if not is_barber_available_in_memory(bbb, local_start.time(), end_cat.time(), barber_availability):
                            schedule_possible = False
                            break

                        if has_overlap(barber_schedules[bbb.id], local_start, end_cat):
                            schedule_possible = False
                            break

                        # Добавляем слот
                        barber_schedules[bbb.id].append({'start': local_start, 'end': end_cat})
                    else:
                        # any barber in that category
                        try:
                            sc = ServiceCategory.objects.get(id=cat_id)
                        except (ValueError, TypeError, ServiceCategory.DoesNotExist):
                            logger.warning("Категория %r не найдена.", cat_id)
                            schedule_possible = False
                            break

                        candidate_barbers = sc.barbers.filter(salon=salon)
                        found_barber = False

                        for cb in candidate_barbers:
                            if is_barber_busy(cb.id, local_start, end_cat, barber_busy_times):
                                continue
                            if not is_barber_available_in_memory(cb, local_start.time(), end_cat.time(), barber_availability):
                                continue
                            if has_overlap(barber_schedules[cb.id], local_start, end_cat):
                                continue
                            # use this barber
                            barber_schedules[cb.id].append({'start': local_start, 'end': end_cat})
                            found_barber = True
                            break

                        if not found_barber:
                            schedule_possible = False
                            break

                    # Сдвигаем начало
                    local_start = end_cat

                if schedule_possible:
                    available_minutes[hour].add(minute)

        else:
            # Нет booking_details
            dur = total_service_duration or salon.default_duration
            if not dur:
                dur = 30  # fallback, чтобы не было TypeError если default_duration=None

            for minute in range(0, 60, 5):
                minute_start = start_of_hour + timedelta(minutes=minute)
                minute_end = minute_start + timedelta(minutes=dur)

                if minute_start < now:
                    continue

                # Нужен хоть один барбер
                free_barber = False
                for b_obj in barbers:
                    if is_barber_busy(b_obj.id, minute_start, minute_end, barber_busy_times):
                        continue
                    if is_barber_available_in_memory(b_obj, minute_start.time(), minute_end.time(), barber_availability):
                        free_barber = True
                        break
                if free_barber:
                    available_minutes[hour].add(minute)

    # Преобразуем set -> sorted list
    available_minutes_response = {}
    for h, mins in available_minutes.items():
        available_minutes_response[str(h)] = sorted(mins)

    logger.info("Final available_minutes = %r", available_minutes_response)

    # Кэш
    # cache_time_str = f"{(timezone.now().minute // 5)*5}"
    # cache_key = generate_safe_cache_key(
    #     salon_id, date_str, hours, booking_details, cache_time_str, selected_barber_id=selected_barber_id
    # )

    # cached_response = cache.get(cache_key)
    # if cached_response:
    #     logger.debug("Данные получены из кэша. Ключ=%r", cache_key)
    #     return Response(cached_response)

    response = {'available_minutes': available_minutes_response}
    # cache.set(cache_key, response, timeout=30)
    # logger.debug("Кеширование результатов. Ключ=%r", cache_key)

    return Response(response)

# ---------- HELPER FUNCTIONS ------------------------

def is_barber_busy(barber_id, start_dt, end_dt, barber_busy_times):
    """Проверяем пересечение [start_dt, end_dt) с занятыми интервалами барбера."""
    intervals = barber_busy_times.get(barber_id, [])
    for (bs, be) in intervals:
        if bs < end_dt and be > start_dt:
            return True
    return False

def has_overlap(schedule_list, start_dt, end_dt):
    """Проверяем перекрытие внутри уже найденных интервалов schedule_list = [{'start': dt, 'end': dt}, ...]."""
    for sched in schedule_list:
        if sched['start'] < end_dt and sched['end'] > start_dt:
            return True
    return False

def is_barber_available_in_memory(barber, start_t, end_t, barber_availability):
    """
    Проверяем, есть ли в barber_availability[barber.id] интервал is_available=True,
    который покрывает [start_t..end_t].
    start_t, end_t — это time() в рамках одного дня.
    """
    intervals = barber_availability.get(barber.id, [])
    for block in intervals:
        if block['is_available']:
            if block['start_time'] <= start_t and block['end_time'] >= end_t:
                return True
    return False




def is_barber_busy(barber_id, start_dt, end_dt, barber_busy_times):
    """Проверяем, заняты ли у барбера промежутки [start_dt, end_dt)."""
    busy_list = barber_busy_times.get(barber_id, [])
    for busy_start, busy_end in busy_list:
        # Если пересекаются
        if busy_start < end_dt and busy_end > start_dt:
            return True
    return False


def has_overlap(schedules, start_dt, end_dt):
    """Проверка перекрытия в рамках уже добавленных интервалов schedules 
       (список словарей [{start: dt, end: dt}, ...])."""
    for sched in schedules:
        if sched['start'] < end_dt and sched['end'] > start_dt:
            return True
    return False


@transaction.atomic
def book_appointment(request, id):
    logger.debug("Начало обработки запроса на бронирование")

    try:
        if request.method != "POST":
            logger.warning(f"Некорректный метод запроса: {request.method}")
            return JsonResponse({'error': 'Некорректный метод запроса.'}, status=400)
        
        salon = get_object_or_404(Salon, id=id)
    
        # Проверяем, является ли запрос JSON
        if request.headers.get('Content-Type') == 'application/json':
            try:
                data = json.loads(request.body)
                logger.debug(f"Получены данные бронирования: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON: {e}")
                return JsonResponse({'error': 'Некорректный формат данных.'}, status=400)
        else:
            # Если запрос не является JSON, возвращаем ошибку
            logger.error("Некорректный формат данных. Ожидается JSON.")
            return JsonResponse({'error': 'Некорректный формат данных.'}, status=400)

        salonMod = data.get('salonMod', 'category')

        date_str = data.get("date")
        time_str = data.get("time")
        booking_details = data.get("booking_details", [])
        total_service_duration = data.get("total_service_duration", salon.default_duration)
        user_comment = data.get("user_comment", "")  # Пустая строка по умолчанию

        # Валидация даты
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка форматирования даты: {e}")
            return JsonResponse({'error': 'Некорректный формат даты.'}, status=400)
    
        # Валидация времени
        try:
            start_time = datetime.strptime(time_str, '%H:%M').time()
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка форматирования времени: {e}")
            return JsonResponse({'error': 'Некорректный формат времени.'}, status=400)
    
        # Рассчитываем start_datetime и end_datetime
        start_datetime_naive = datetime.combine(date, start_time)
        start_datetime = timezone.make_aware(start_datetime_naive, timezone.get_current_timezone())
        initial_start_datetime = start_datetime  # Сохраняем начальное время
    
        if booking_details:
            try:
                total_service_duration = sum(int(category['duration']) for category in booking_details)
            except (KeyError, TypeError, ValueError) as e:
                logger.error(f"Ошибка при расчёте общей длительности услуг: {e}")
                return JsonResponse({'error': 'Некорректные данные о длительности услуг.'}, status=400)
        else:
            try:
                total_service_duration = int(total_service_duration)
            except (TypeError, ValueError) as e:
                logger.error(f"Ошибка при преобразовании длительности по умолчанию: {e}")
                total_service_duration = salon.default_duration  # Используем длительность по умолчанию
    
        end_datetime = start_datetime + timedelta(minutes=total_service_duration)

        # Создаем Appointment
        appointment = Appointment(
            salon=salon,
            user=request.user if request.user.is_authenticated else None,
            start_datetime=initial_start_datetime,
            end_datetime=end_datetime,
            user_comment=user_comment,
        )
        appointment.save()
        logger.debug(f"Создано Appointment: {appointment}")
        # Список для хранения созданных AppointmentBarberService
        appointments_to_create = []
    
        if not booking_details:
            # Нет выбранных услуг
            busy_barber_ids = AppointmentBarberService.objects.filter(
                start_datetime__lt=end_datetime,
                end_datetime__gt=start_datetime
            ).values_list('barber_id', flat=True)
            logger.info(f"Busy barber IDs: {list(busy_barber_ids)}")
    
            available_barber = Barber.objects.select_for_update().filter(
                salon=salon,
                availabilities__day_of_week=start_datetime.strftime('%A').lower(),
                availabilities__start_time__lte=start_datetime.time(),
                availabilities__end_time__gte=end_datetime.time(),
                availabilities__is_available=True
            ).exclude(
                id__in=busy_barber_ids
            ).order_by('id').first()

            if not available_barber:
                logger.warning("Нет доступных мастеров на выбранное время.")
                return JsonResponse({'error': 'Нет доступных мастеров на выбранное время.'}, status=400)
    
            # Проверка доступности по расписанию (дополнительно)
            if not is_barber_available(available_barber, start_datetime, end_datetime):
                logger.info(f"Барбер {available_barber.name} недоступен по расписанию.")
                return JsonResponse({'error': f"Барбер {available_barber.name} недоступен по расписанию."}, status=400)
    
            appointment_barber_service = AppointmentBarberService(
                appointment=appointment,
                barber=available_barber,
                start_datetime=start_datetime,
                end_datetime=end_datetime
            )
            appointment_barber_service.save()
            appointments_to_create.append(appointment_barber_service)
    
        else:
            # Есть booking_details
            print('salon Mod', salonMod)

            for category_detail in booking_details:
                category_id = category_detail.get('categoryId')
                services = category_detail.get('services', [])
                barber_id = category_detail.get('barberId', 'any')
                duration = category_detail.get('duration')
    
                try:
                    duration = int(duration)
                except (TypeError, ValueError):
                    logger.error(f"Некорректная длительность услуги: {duration}")
                    return JsonResponse({'error': 'Некорректная длительность услуги.'}, status=400)
    
                interval_end = start_datetime + timedelta(minutes=duration)
    
                if barber_id != 'any':
                    try:
                        barber = Barber.objects.select_for_update().get(id=barber_id, salon=salon)
                        logger.debug(f"Выбран барбер {barber.name} (ID: {barber.id}) для категории {category_id}")
                    except Barber.DoesNotExist:
                        logger.warning(f"Барбер с ID {barber_id} не найден в салоне {salon}")
                        return JsonResponse({'error': 'Выбранный барбер не найден.'}, status=400)
    
                    # Проверка занятости другим бронированием
                    overlapping = AppointmentBarberService.objects.filter(
                        barber=barber,
                        start_datetime__lt=interval_end,
                        end_datetime__gt=start_datetime
                    ).exists()
    
                    if overlapping:
                        logger.info(f"Барбер {barber.name} недоступен для выбранного времени (занят).")
                        return JsonResponse({'error': f"Барбер {barber.name} недоступен для выбранного времени."}, status=400)
                else:
                    # barber_id = 'any', выбираем любого доступного барбера данной категории
                    busy_barber_ids = AppointmentBarberService.objects.filter(
                        barber__categories__id=category_id,  # Фильтрация по категории
                        start_datetime__lt=interval_end,
                        end_datetime__gt=start_datetime
                    ).values_list('barber_id', flat=True)
                    logger.info(f"Busy barber IDs for category {category_id}: {list(busy_barber_ids)}")
    
                    # Логирование параметров фильтрации
                    logger.info(
                        f"Selecting available barber in salon={salon.id}, category={category_id}, "
                        f"day_of_week={start_datetime.strftime('%A').lower()}, "
                        f"start_time={start_datetime.time()}, end_time={interval_end.time()}, "
                        f"is_available=True"
                    )
    
                    available_barber = Barber.objects.select_for_update().filter(
                        salon=salon,
                        categories__id=category_id,
                        availabilities__day_of_week=start_datetime.strftime('%A').lower(),
                        availabilities__start_time__lte=start_datetime.time(),
                        availabilities__end_time__gte=interval_end.time(),
                        availabilities__is_available=True
                    ).exclude(
                        id__in=busy_barber_ids
                    ).first()
    
                    if available_barber:
                        barber = available_barber
                        logger.debug(f"Автоматически выбран барбер {barber.name} (ID: {barber.id}) для категории {category_id}")
                    else:
                        logger.warning(f"Нет доступных барберов для категории {category_id}")
                        return JsonResponse({'error': 'Нет доступных барберов для одной из категорий.'}, status=400)
    
                # Проверка доступности по расписанию (дополнительно)
                if not is_barber_available(barber, start_datetime, interval_end):
                    logger.info(f"Барбер {barber.name} недоступен по расписанию.")
                    return JsonResponse({'error': f"Барбер {barber.name} недоступен по расписанию."}, status=400)
    
                # Создаем AppointmentBarberService
                appointment_barber_service = AppointmentBarberService(
                    appointment=appointment,
                    barber=barber,
                    start_datetime=start_datetime,
                    end_datetime=interval_end
                )
                appointment_barber_service.save()
    
                # Присваиваем услуги
                for service_info in services:
                    service_id = service_info.get('serviceId')
                    if salonMod == 'barber':
                        # === РЕЖИМ БАРБЕРА ===
                        try:
                            barber_service = BarberService.objects.get(id=service_id, barber=barber)
                            appointment_barber_service.barberServices.add(barber_service)
                            logger.debug(
                                f"[BARBER MODE] Добавлена barberService '{barber_service.name}' "
                                f"(ID: {barber_service.id}) к AppointmentBarberService"
                            )
                        except BarberService.DoesNotExist:
                            logger.warning(f"BarberService с ID {service_id} не найдена или не привязана к {barber.name}")
                            return JsonResponse({'error': f"BarberService с ID {service_id} не найдена."}, status=400)
                    
                    else:
                        # === РЕЖИМ КАТЕГОРИИ ===
                        try:
                            service = Service.objects.get(id=service_id, salon=salon)
                            appointment_barber_service.services.add(service)
                            logger.debug(
                                f"[CATEGORY MODE] Добавлена Service '{service.name}' "
                                f"(ID: {service.id}) к AppointmentBarberService"
                            )
                        except Service.DoesNotExist:
                            logger.warning(f"Услуга с ID {service_id} не найдена в салоне {salon}")
                            return JsonResponse({'error': f"Услуга с ID {service_id} не найдена в салоне."}, status=400)

                appointments_to_create.append(appointment_barber_service)
    
                # Обновляем start_datetime для следующей услуги
                start_datetime = interval_end
    
        # Связываем созданные AppointmentBarberService с Appointment
        if appointments_to_create:
            appointment.barber_services.set(appointments_to_create)

        if not settings.DEBUG:
            admins = salon.admins.all()
            for admin in admins:
                profile = admin.main_profile  # вот объект Profile

                 # Получаем номер телефона пользователя
                if request.user.is_authenticated:
                    try:
                        user_phone_number = request.user.main_profile.phone_number
                    except AttributeError:
                        logger.warning("Профиль пользователя не найден.")
                        user_phone_number = "Неизвестен"
                else:
                    user_phone_number = "Неизвестен"

                # whatsapp
                if profile.whatsapp:
                    TEMPLATE_SID = "HXa27885cd64b14637a00e845fbbfaa326"
       
                    datetime_str = (
                        appointment.start_datetime.strftime("%d.%m %H:%M")
                        + "-" +
                        appointment.end_datetime.strftime("%H:%M")
                    )

                    barbers_qs = appointment.barbers.all()
                    master_names = ", ".join(b.name for b in barbers_qs) if barbers_qs else "Без мастера"

                    dataTest = {
                        "client_phoneNumber": user_phone_number,
                        "datetime": datetime_str,
                        "master_name": master_names,
                        "admin_number": profile.whatsapp_phone_number
                    }

                    content_variables_dict = {
                        "1": dataTest["datetime"],
                        "2": dataTest["master_name"],
                        "3": dataTest["client_phoneNumber"]
                    }

                    # Преобразуем словарь в JSON
                    variables_str = json.dumps(content_variables_dict, ensure_ascii=False)

                    # Вызываем нашу функцию из twilio_service.py
                    send_whatsapp_message(dataTest["admin_number"], TEMPLATE_SID, variables_str)

                # push-уведомления
                if profile.push_subscribe:
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
                            "body": f"Пользователь успешно забронировал услугу.",
                            "icon": "/static/main/img/notification-icon.png",
                            "url": "/user-account/bookings/"                }
                        send_push_notification_task.delay(subscription_info, json.dumps(payload))
                        logger.info(f"Задача на отправку уведомления создана для {admin.username}.")

            logger.info(f"Бронирование успешно создано для пользователя - {request.user if request.user.is_authenticated else 'Анонимный пользователь'}")
        else:
            pass

        return JsonResponse({'success': True, 'message': 'Бронирование успешно создано!'})
    
    except Exception as e:
        logger.error(f"Необработанное исключение при бронировании: {e}", exc_info=True)
        return JsonResponse({'error': 'Внутренняя ошибка сервера.'}, status=500)

def is_barber_available(barber, start_datetime, end_datetime):
    day_code = start_datetime.strftime('%A').lower()
    intervals = BarberAvailability.objects.filter(barber=barber, day_of_week=day_code)

    if not intervals.exists():
        # Нет записей на этот день: считаем день полностью выходным
        return False

    request_start = start_datetime.time()
    request_end = end_datetime.time()

    # Проверим, есть ли недоступные интервалы, пересекающие запрошенный интервал
    if intervals.filter(is_available=False, start_time__lt=request_end, end_time__gt=request_start).exists():
        # Есть недоступный интервал, пересекающий запрошенное время
        return False

    # Проверяем доступные интервалы, должен быть хотя бы один, покрывающий весь [request_start, request_end]
    if intervals.filter(is_available=True, start_time__lte=request_start, end_time__gte=request_end).exists():
        return True

    return False

def is_barber_available_in_memory(barber, request_start_time, request_end_time, barber_availability):
    """
    Проверяет доступность барбера на основе предварительно загруженных данных.

    :param barber: Объект барбера.
    :param request_start_time: Время начала бронирования (time).
    :param request_end_time: Время окончания бронирования (time).
    :param barber_availability: Словарь с расписанием барберов.
    :return: True, если барбер доступен, иначе False.
    """
    intervals = barber_availability.get(barber.id, [])

    if not intervals:
        # Нет записей на этот день: считаем день полностью выходным
        return False

    # Проверяем, есть ли недоступные интервалы, пересекающие запрошенный интервал
    for interval in intervals:
        is_available = interval.get('is_available', True)  # Используем get с значением по умолчанию
        if not is_available:
            if interval['start_time'] < request_end_time and interval['end_time'] > request_start_time:
                return False

    # Проверяем доступные интервалы, должен быть хотя бы один, покрывающий весь [request_start_time, request_end_time]
    for interval in intervals:
        is_available = interval.get('is_available', True)  # Используем get с значением по умолчанию
        if is_available:
            if interval['start_time'] <= request_start_time and interval['end_time'] >= request_end_time:
                return True

    return False



from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import hashlib

# def generate_safe_cache_key(salon_id, date_str, hours, booking_details, cache_time_str, selected_barber_id='any'):
#     """
#     Генерирует безопасный ключ кэша, используя хеширование параметров запроса.

#     :param salon_id: ID салона
#     :param date_str: Дата бронирования в формате 'YYYY-MM-DD'
#     :param hours: Список часов (целые числа)
#     :param booking_details: Список деталей бронирования (словари)
#     :param cache_time_str: Строка округленного времени кэша (например, '45' для минут)
#     :param selected_barber_id: ID выбранного барбера или 'any' для любого
#     :return: Строка безопасного ключа кэша
#     """
#     key_string = (
#         f"available_minutes_{salon_id}_v{get_cache_version(salon_id)}_"
#         f"{date_str}_{json.dumps(hours, sort_keys=True)}_"
#         f"{json.dumps(booking_details, sort_keys=True)}_"
#         f"{selected_barber_id}_{cache_time_str}"
#     )
#     key_hash = hashlib.md5(key_string.encode('utf-8')).hexdigest()
#     return f"available_minutes_{salon_id}_v{get_cache_version(salon_id)}_{key_hash}"

import hashlib, json
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