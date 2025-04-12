# salons/views.py
from django.shortcuts import render, get_object_or_404
from .models import Salon, Appointment, Barber, Service, ServiceCategory, AppointmentBarberService, BarberAvailability, BarberService
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta, timezone as dt_timezone, time as dtime
import time
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
import json
from django.db.models import Prefetch
from collections import defaultdict
from django.core.cache import cache
from django.dispatch import receiver
from django.views.decorators.cache import never_cache
from django.conf import settings
from reservon.utils.twilio_service import send_whatsapp_message
from authentication.models import Profile, User
from django.db import IntegrityError
from .utils import round_down_to_5
from django.views.decorators.csrf import csrf_exempt
from main.tasks import send_push_notification_task
from authentication.models import PushSubscription

import logging

logger = logging.getLogger('booking')

# @cache_page(60 * 15)
def main(request):
    query = request.GET.get('q', '')
    city_filter = request.GET.get('city', '')
    if query:
        salons = Salon.objects.filter(
            Q(name__icontains=query) | Q(address__icontains=query)
        )
    else:
        salons = Salon.objects.filter(status='active')
    if city_filter:
        salons = salons.filter(city=city_filter)
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
        total_service_duration = int(data.get('total_service_duration', sum(int(cat['duration']) for cat in booking_details)))
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
            # total_cat_duration = sum(c['duration'] for c in active_categories)

            try:
                total_cat_duration = sum(int(category.get('duration', 0)) for category in booking_details)
            except Exception as e:
                logger.error("Ошибка при расчёте общей длительности услуг: %r", e)
                total_cat_duration = salon.default_duration or 30

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
                    dur_cat = int(cat_obj.get('duration', 0))
                    end_cat = local_start + timedelta(minutes=dur_cat)
                    barb_id = cat_obj['barber_id']
                    local_start = end_cat

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

@api_view(['POST'])
def get_nearest_available_time(request):
    """
    Новый режим "auto":
    При выборе клиентом часа (например, 11:00) сервер ищет все возможные 5-минутные старты в течение дня 
    (например, в диапазоне работы салона 9-22) и возвращает ближайшие варианты для начала бронирования.
    
    Особенность доработки:
      Если в пределах ±30 минут от выбранного времени уже есть записи, то предлагаем начать бронирование
      как продолжение (то есть, сразу после окончания предыдущей записи) или так, чтобы завершиться непосредственно
      перед началом следующей записи.
    
    Request data (JSON):
    {
      "salon_id": <int>,
      "date": "YYYY-MM-DD",
      "chosen_hour": <int>,      # выбранный клиентом час (например, 11)
      "booking_details": [
          {
              "categoryId": str/int,
              "services": [{ "serviceId": int, "duration": int}, ...],
              "barberId": "any" или str(int),
              "duration": int
          },
          ...
      ],
      "selected_barber_id": "any" или str(...)? (опционально),
      "total_service_duration": int
    }
    """
    data = request.data
    logger.info("Request data (nearest available time) = %r", data)
    
    # Проверка обязательных полей и приведение к нужным типам
    try:
        salon_id = data['salon_id']
        date_str = data['date']
        chosen_hour = int(data['chosen_hour'])
    except (KeyError, ValueError, TypeError) as e:
        logger.error("Обязательные поля отсутствуют или имеют неверный формат: %r", e)
        return Response({'error': 'Отсутствуют обязательные поля или неверный формат.'},
                        status=status.HTTP_400_BAD_REQUEST)
    
    try:
        total_service_duration = int(data.get('total_service_duration', 0))
    except (ValueError, TypeError) as e:
        logger.error("total_service_duration не является целым числом: %r", e)
        return Response({"error": "Неверный тип total_service_duration."},
                        status=status.HTTP_400_BAD_REQUEST)
    
    booking_details = data.get('booking_details', [])
    selected_barber_id = data.get('selected_barber_id', 'any')
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError as e:
        logger.error("Ошибка форматирования даты '%r': %r", date_str, e)
        return Response({'error': 'Некорректный формат даты (ожидается YYYY-MM-DD).'},
                        status=status.HTTP_400_BAD_REQUEST)
    
    day_code = date.strftime('%A').lower()
    logger.info("Day code = %r", day_code)
    
    # Загружаем салон с предзагрузкой availabilities
    try:
        salon = Salon.objects.prefetch_related(
            Prefetch('barbers__availabilities', queryset=BarberAvailability.objects.all())
        ).get(id=salon_id)
    except Salon.DoesNotExist:
        logger.error("Салон с ID %r не найден.", salon_id)
        return Response({'error': f'Салон с ID={salon_id} не найден.'},
                        status=status.HTTP_404_NOT_FOUND)
    
    barbers = salon.barbers.all()
    logger.info("Найдено %d барберов в салоне %r", len(barbers), salon.name)
    
    # Формируем словарь доступности барберов
    barber_availability = {
        b.id: [{
            'start_time': interval.start_time,
            'end_time': interval.end_time,
            'is_available': interval.is_available
        } for interval in b.availabilities.filter(day_of_week=day_code)]
        for b in barbers
    }
    logger.info("barber_availability = %r", barber_availability)
    
    # Загружаем занятые интервалы и сразу преобразуем их в локальное время
    busy_appointments = AppointmentBarberService.objects.filter(
        barber__salon=salon,
        start_datetime__date=date
    ).select_related('barber')
    barber_busy_times = defaultdict(list)
    for app in busy_appointments:
        start_local = timezone.localtime(app.start_datetime)
        end_local = timezone.localtime(app.end_datetime)
        barber_busy_times[app.barber_id].append((start_local, end_local))
    
    # Обрабатываем booking_details для формирования active_categories
    active_categories = []
    # logger.info("Обработка booking_details: %r", booking_details)
    for cat_detail in booking_details:
        try:
            dur_ = int(cat_detail.get('duration', 0))
        except (ValueError, TypeError):
            logger.warning("Некорректная длительность в booking_details: %r", cat_detail)
            dur_ = 0
        active_categories.append({
            'category_id': cat_detail.get('categoryId'),
            'services': cat_detail.get('services', []),
            'barber_id': cat_detail.get('barberId', 'any'),
            'duration': dur_
        })
    logger.info("active_categories = %r", active_categories)
    
    now = timezone.now()
    
    # Генерируем кандидатные слоты (каждые 5 минут) в рабочем интервале (например, 9-22)
    start_work = 9
    end_work = 21
    candidate_slots = []
    for hour in range(start_work, end_work):
        try:
            naive_dt = datetime.combine(date, dtime(hour, 0))
            hour_start = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except Exception as e:
            logger.error("Ошибка при создании datetime для hour=%r: %r", hour, e)
            continue
        for minute in range(0, 60, 5):
            candidate = hour_start + timedelta(minutes=minute)
            if candidate < now:
                continue
            # Если есть активные категории, проверяем последовательность услуг
            if active_categories:
                schedule_possible = True
                barber_schedules = defaultdict(list)
                local_start = candidate
                for cat_obj in active_categories:
                    dur_cat = cat_obj['duration']
                    end_cat = local_start + timedelta(minutes=dur_cat)
                    if cat_obj['barber_id'] != 'any':
                        try:
                            barber_int = int(cat_obj['barber_id'])
                        except (ValueError, TypeError):
                            schedule_possible = False
                            break
                        barber_obj = barbers.filter(id=barber_int).first()
                        if not barber_obj:
                            schedule_possible = False
                            break
                        if is_barber_busy(barber_obj.id, local_start, end_cat, barber_busy_times):
                            schedule_possible = False
                            break
                        if not is_barber_available_in_memory(barber_obj, local_start.time(), end_cat.time(), barber_availability):
                            schedule_possible = False
                            break
                        if has_overlap(barber_schedules[barber_obj.id], local_start, end_cat):
                            schedule_possible = False
                            break
                        barber_schedules[barber_obj.id].append({'start': local_start, 'end': end_cat})
                    else:
                        try:
                            sc = ServiceCategory.objects.get(id=cat_obj['category_id'])
                        except (ValueError, TypeError, ServiceCategory.DoesNotExist):
                            schedule_possible = False
                            break
                        candidate_barbers = sc.barbers.filter(salon=salon)
                        found = False
                        for cb in candidate_barbers:
                            if is_barber_busy(cb.id, local_start, end_cat, barber_busy_times):
                                continue
                            if not is_barber_available_in_memory(cb, local_start.time(), end_cat.time(), barber_availability):
                                continue
                            if has_overlap(barber_schedules[cb.id], local_start, end_cat):
                                continue
                            barber_schedules[cb.id].append({'start': local_start, 'end': end_cat})
                            found = True
                            break
                        if not found:
                            schedule_possible = False
                            break
                    local_start = end_cat  # сдвигаем начало для следующего блока
                if schedule_possible:
                    candidate_slots.append(candidate)
            else:
                # Если активных категорий нет, ищем слот для всего салона (barber_id="any")
                dur = total_service_duration or salon.default_duration or 30
                candidate_end = candidate + timedelta(minutes=dur)

                # Проверяем, что хотя бы у одного барбера расписание позволяет работать в этот промежуток
                works = any(
                    is_barber_available_in_memory(b, candidate.time(), candidate_end.time(), barber_availability)
                    for b in barbers if barber_availability.get(b.id)
                )

                # Собираем все занятые интервалы из всех барберов в единый список
                union_busy = []
                for intervals in barber_busy_times.values():
                    union_busy.extend(intervals)

                # Проверяем, есть ли конфликт с любым занятым интервалом
                conflict = any(candidate < busy_end and candidate_end > busy_start for (busy_start, busy_end) in union_busy)

                if works and not conflict:
                    candidate_slots.append(candidate)
                    
                    if not candidate_slots:
                        return Response({'error': 'Нет доступного времени для бронирования в этот день.'},
                                        status=status.HTTP_200_OK)
                    
    candidate_slots.sort()
    reference_naive = datetime.combine(date, dtime(chosen_hour, 0))
    reference_time = timezone.make_aware(reference_naive, timezone.get_current_timezone())
    
    slots_before = [slot for slot in candidate_slots if slot <= reference_time]
    nearest_before = max(slots_before) if slots_before else None
    slots_after = [slot for slot in candidate_slots if slot >= reference_time]
    nearest_after = min(slots_after) if slots_after else None
    
    # (b) ±30 минут
    window_start = reference_time - timedelta(minutes=30)
    window_end = reference_time + timedelta(minutes=30)

    adjusted_before = []
    adjusted_after = []

    # Если booking_details переданы, вычисляем суммарную длительность из активных категорий,
    # иначе используем total_service_duration (с fallback)
    if active_categories:
        computed_total_duration = sum(cat['duration'] for cat in active_categories)
    else:
        computed_total_duration = total_service_duration or salon.default_duration or 30

    # Проходим по всем занятым интервалам (объединённо по всем барберам)
    for busy_list in barber_busy_times.values():
        for start_dt, end_dt in busy_list:
            # Если busy appointment начинается до reference_time (в окне),
            # то предлагаем слот, который завершится ровно к началу busy appointment.
            if window_start <= start_dt < reference_time:
                candidate = round_down_to_5(start_dt - timedelta(minutes=computed_total_duration))
                adjusted_before.append(candidate)
            # Если busy appointment заканчивается после reference_time (в окне),
            # то предлагаем слот, который начнётся сразу после окончания busy appointment.
            if reference_time < end_dt <= window_end:
                candidate = round_down_to_5(end_dt)
                adjusted_after.append(candidate)

    if adjusted_before:
        nearest_before = max(adjusted_before)
    if adjusted_after:
        nearest_after = min(adjusted_after)

    # Если оба варианта существуют, и разница меньше порога (например, 10 минут),
    # оставляем только один вариант (предпочтительно раннее)
    fmt = "%H:%M"
    if nearest_before and nearest_after:
        diff = abs((nearest_before - nearest_after).total_seconds()) / 60.0
        threshold = 30
        if diff < threshold:
            candidate = min(nearest_before, nearest_after)
            nearest_before = candidate
            nearest_after = None
    
    response_data = {
        "nearest_before": nearest_before.strftime(fmt) if nearest_before else None,
        "nearest_after": nearest_after.strftime(fmt) if nearest_after else None,
    }
    logger.info("Результат get_nearest_available_time: %r", response_data)
    return Response(response_data, status=status.HTTP_200_OK)

# ---------- HELPER UNCTIONS ------------------------

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

def get_nearest_suggestion(salon_id, date_str, chosen_hour, booking_details, total_service_duration):
    """
    Аналог get_nearest_available_time, но без DRF-вьюхи:
      1) Генерируем candidate_slots (каждые 5 минут с 9:00 до 21:00).
      2) Делим их на before/after относительно chosen_hour.
      3) Корректируем с учётом занятых интервалов (окно ±30 мин).
      4) Возвращаем {"nearest_before": ..., "nearest_after": ...}.
    """
    from datetime import datetime, timedelta, time as dtime
    from django.utils import timezone
    from django.db.models import Prefetch
    from collections import defaultdict

    # Функция округления времени вниз до ближайших 5 минут
    def round_down_to_5(dt):
        return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)

    # Предполагаются функции is_barber_busy, is_barber_available_in_memory и has_overlap,
    # работающие по следующей логике (полуинтервал [start, end)):
    #
    # def is_barber_busy(barber_id, start_dt, end_dt, barber_busy_times):
    #     for (bs, be) in barber_busy_times.get(barber_id, []):
    #         if bs < end_dt and be > start_dt:
    #             return True
    #     return False
    #
    # def has_overlap(schedule_list, start_dt, end_dt):
    #     for sched in schedule_list:
    #         if sched['start'] < end_dt and sched['end'] > start_dt:
    #             return True
    #     return False
    #
    # def is_barber_available_in_memory(barber, req_start, req_end, barber_availability):
    #     intervals = barber_availability.get(barber.id, [])
    #     for block in intervals:
    #         if block['is_available']:
    #             if block['start_time'] <= req_start and block['end_time'] >= req_end:
    #                 return True
    #     return False

    # 1) Парсим дату
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return {"nearest_before": None, "nearest_after": None}

    # 2) Загружаем салон с предзагрузкой availabilities
    try:
        salon = Salon.objects.prefetch_related(
            Prefetch('barbers__availabilities', queryset=BarberAvailability.objects.all())
        ).get(id=salon_id)
    except Salon.DoesNotExist:
        return {"nearest_before": None, "nearest_after": None}

    barbers = salon.barbers.all()
    day_code = date.strftime('%A').lower()

    # Формируем словарь доступности барберов для данного дня
    barber_availability = {
        b.id: [{
            'start_time': interval.start_time,
            'end_time': interval.end_time,
            'is_available': interval.is_available
        } for interval in b.availabilities.filter(day_of_week=day_code)]
        for b in barbers
    }

    # Получаем занятые интервалы (busy) для данного дня
    busy_appointments = AppointmentBarberService.objects.filter(
        barber__salon=salon,
        start_datetime__date=date
    ).select_related('barber')

    barber_busy_times = defaultdict(list)
    for app in busy_appointments:
        start_local = timezone.localtime(app.start_datetime)
        end_local = timezone.localtime(app.end_datetime)
        barber_busy_times[app.barber_id].append((start_local, end_local))

    # 3) Обрабатываем booking_details → active_categories
    active_categories = []
    for cat_detail in booking_details:
        try:
            dur_ = int(cat_detail.get('duration', 0))
        except (ValueError, TypeError):
            dur_ = 0
        active_categories.append({
            'category_id': cat_detail.get('categoryId'),
            'services': cat_detail.get('services', []),
            'barber_id': cat_detail.get('barberId', 'any'),
            'duration': dur_
        })

    # Если booking_details не пусты, суммарная длительность берётся из active_categories,
    # иначе используем total_service_duration или default
    if active_categories:
        computed_total_duration = sum(cat['duration'] for cat in active_categories)
    else:
        computed_total_duration = total_service_duration or salon.default_duration or 30

    now = timezone.now()

    # 4) Генерируем candidate_slots (каждые 5 минут с 9:00 до 21:00)
    start_work = 9
    end_work = 21
    candidate_slots = []

    for hour in range(start_work, end_work):
        try:
            naive_dt = datetime.combine(date, dtime(hour, 0))
            hour_start = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except Exception:
            continue

        for minute in range(0, 60, 5):
            candidate = hour_start + timedelta(minutes=minute)
            if candidate < now:
                continue

            if active_categories:
                schedule_possible = True
                barber_schedules = defaultdict(list)
                local_start = candidate

                for cat_obj in active_categories:
                    dur_cat = cat_obj['duration']
                    end_cat = local_start + timedelta(minutes=dur_cat)
                    barber_id_ = cat_obj['barber_id']

                    if barber_id_ != 'any':
                        try:
                            barber_int = int(barber_id_)
                        except (ValueError, TypeError):
                            schedule_possible = False
                            break
                        barber_obj = barbers.filter(id=barber_int).first()
                        if not barber_obj:
                            schedule_possible = False
                            break
                        if is_barber_busy(barber_obj.id, local_start, end_cat, barber_busy_times):
                            schedule_possible = False
                            break
                        if not is_barber_available_in_memory(barber_obj, local_start.time(), end_cat.time(), barber_availability):
                            schedule_possible = False
                            break
                        if has_overlap(barber_schedules[barber_obj.id], local_start, end_cat):
                            schedule_possible = False
                            break
                        barber_schedules[barber_obj.id].append({'start': local_start, 'end': end_cat})
                    else:
                        if cat_obj.get('category_id') in [None, 'any']:
                            candidate_barbers = barbers
                        else:
                            try:
                                sc = ServiceCategory.objects.get(id=cat_obj['category_id'])
                                candidate_barbers = sc.barbers.filter(salon=salon)
                            except (ValueError, TypeError, ServiceCategory.DoesNotExist):
                                schedule_possible = False
                                break

                        found_barber = False
                        for cb in candidate_barbers:
                            if is_barber_busy(cb.id, local_start, end_cat, barber_busy_times):
                                continue
                            if not is_barber_available_in_memory(cb, local_start.time(), end_cat.time(), barber_availability):
                                continue
                            if has_overlap(barber_schedules[cb.id], local_start, end_cat):
                                continue
                            barber_schedules[cb.id].append({'start': local_start, 'end': end_cat})
                            found_barber = True
                            break
                        if not found_barber:
                            schedule_possible = False
                            break

                    local_start = end_cat

                if schedule_possible:
                    candidate_slots.append(candidate)
            else:
                # Если booking_details пуст, проверяем слот для всего салона (barber_id="any")
                dur = computed_total_duration
                candidate_end = candidate + timedelta(minutes=dur)
                works = any(
                    is_barber_available_in_memory(b, candidate.time(), candidate_end.time(), barber_availability)
                    for b in barbers if barber_availability.get(b.id)
                )
                union_busy = []
                for intervals in barber_busy_times.values():
                    union_busy.extend(intervals)
                conflict = any(candidate < busy_end and candidate_end > busy_start 
                               for (busy_start, busy_end) in union_busy)
                if works and not conflict:
                    candidate_slots.append(candidate)

    candidate_slots.sort()
    reference_naive = datetime.combine(date, dtime(chosen_hour, 0))
    reference_time = timezone.make_aware(reference_naive, timezone.get_current_timezone())

    if not candidate_slots:
        return {"nearest_before": None, "nearest_after": None}

    # (a) Разбиваем candidate_slots относительно reference_time
    slots_before = [s for s in candidate_slots if s <= reference_time]
    nearest_before = max(slots_before) if slots_before else None
    slots_after = [s for s in candidate_slots if s >= reference_time]
    nearest_after = min(slots_after) if slots_after else None

    # (b) Корректировка с учётом занятых интервалов в окне ±30 мин.
    window_start = reference_time - timedelta(minutes=30)
    window_end = reference_time + timedelta(minutes=30)
    adjusted_before = []
    adjusted_after = []

    # Собираем все busy-интервалы
    union_busy = []
    for intervals in barber_busy_times.values():
        union_busy.extend(intervals)

    # Если есть booking_details (active_categories не пусты), рассчитываем корректировку независимо
    for (busy_start, busy_end) in union_busy:
        # Если busy_start попадает в окно перед reference_time
        if window_start <= busy_start < reference_time:
            candidate_adj = round_down_to_5(busy_start - timedelta(minutes=computed_total_duration))
            adjusted_before.append(candidate_adj)
        # Если busy_end попадает в окно после reference_time
        if reference_time < busy_end <= window_end:
            candidate_adj = round_down_to_5(busy_end)
            adjusted_after.append(candidate_adj)

    if active_categories and (adjusted_before or adjusted_after):
        # Если скорректированные варианты найдены, переопределяем nearest_before/after
        if adjusted_before:
            nearest_before = max(adjusted_before)
        else:
            nearest_before = None
        if adjusted_after:
            nearest_after = min(adjusted_after)
        else:
            nearest_after = None

    # (c) Если оба варианта очень близки (разница < threshold), оставляем один вариант
    fmt = "%H:%M"
    if nearest_before and nearest_after:
        diff = abs((nearest_before - nearest_after).total_seconds()) / 60.0
        threshold = 30
        if diff < threshold:
            candidate_adj = min(nearest_before, nearest_after)
            nearest_before = candidate_adj
            nearest_after = None

    return {
        "nearest_before": nearest_before.strftime(fmt) if nearest_before else None,
        "nearest_after": nearest_after.strftime(fmt) if nearest_after else None
    }


class BookingError(Exception):
    def __init__(self, message, nearest_before=None, nearest_after=None):
        super().__init__(message)
        self.message = message
        self.nearest_before = nearest_before
        self.nearest_after = nearest_after

class ClientError(Exception):
    def __init__(self, message, status=400):
        self.message = message
        self.status = status

@transaction.atomic
@csrf_exempt
def book_appointment(request, id):
    logger.debug("Start processing booking request (Approach A)")

    try:
        # -----------------------------------
        # 1) Проверка метода и парсинг JSON
        # -----------------------------------
        if request.method != "POST":
            logger.warning(f"Invalid request method: {request.method}")
            raise ClientError("Invalid request method", status=400)

        if request.headers.get('Content-Type') != 'application/json':
            logger.error("Invalid data format. JSON expected.")
            raise ClientError("Invalid data format (JSON expected)", status=400)

        try:
            data = json.loads(request.body)
            logger.debug(f"Booking data received: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error: {e}")
            raise ClientError("Invalid JSON format", status=400)

        # -----------------------------------
        # 2) Получаем объекты (Salon, ...)
        # -----------------------------------
        salon = get_object_or_404(Salon, id=id)

        salonMod = data.get('salonMod', 'category')
        date_str = data.get("date")
        time_str = data.get("time")
        booking_details = data.get("booking_details", [])
        total_service_duration = data.get("total_service_duration", salon.default_duration)
        user_comment = data.get("user_comment", "")

        # -----------------------------------
        # 3) Разбор даты и времени
        # -----------------------------------
        try:
            date_object = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            logger.error("Date formatting error")
            raise ClientError("Invalid date format", status=400)

        try:
            start_time = datetime.strptime(time_str, '%H:%M').time()
        except (ValueError, TypeError):
            logger.error("Time formatting error")
            raise ClientError("Invalid time format (HH:MM)", status=400)

        start_datetime_naive = datetime.combine(date_object, start_time)
        start_datetime = timezone.make_aware(start_datetime_naive, timezone.get_current_timezone())

        # -----------------------------------
        # 4) Считаем общую длительность
        # -----------------------------------
        if booking_details:
            try:
                total_service_duration = sum(int(cat['duration']) for cat in booking_details)
            except (KeyError, TypeError, ValueError) as e:
                logger.error(f"Error calculating total duration: {e}")
                raise ClientError("Invalid duration in booking_details", status=400)
        else:
            try:
                total_service_duration = int(total_service_duration)
            except (TypeError, ValueError):
                logger.error("Error converting default duration")
                total_service_duration = salon.default_duration or 30

        end_datetime = start_datetime + timedelta(minutes=total_service_duration)

        # -----------------------------------
        # 5) Находим или создаём юзера
        # -----------------------------------
        phone_number = data.get("phone_number")
        if phone_number:
            logger.info("phone_number=%s", phone_number)
            user, profile = get_or_create_user_by_phone(phone_number)
            logger.info("User object: %r", user)
        else:
            logger.info("No phone number provided.")
            user = request.user if request.user.is_authenticated else None

        # ---------------------------------------------
        # 6) Проверяем логику бронирования (НЕ СОХРАНЯЕМ!)
        # ---------------------------------------------
        # Собираем информацию о том, какие барберы/интервалы/услуги
        # потом создадим Appointment и AppointmentBarberService, если всё ок
        final_barbers_data = []  # список кортежей (barber, slot_start, slot_end, services)

        if not booking_details:
            # --- СЛУЧАЙ: нет booking_details => ищем одного барбера для [start_datetime..end_datetime]
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
                availabilities__is_available=True,
                status='active'
            ).exclude(
                id__in=busy_barber_ids
            ).first()

            if not available_barber or not is_barber_available(available_barber, start_datetime, end_datetime):
                logger.warning("No available barbers for the chosen time.")
                # Ищем "ближайшее" время:
                suggestion = get_nearest_suggestion(
                    salon_id=salon.id,
                    date_str=date_str,
                    chosen_hour=start_datetime.hour,
                    booking_details=[],
                    total_service_duration=total_service_duration
                )
                raise BookingError("Barber is busy",
                                   nearest_before=suggestion["nearest_before"],
                                   nearest_after=suggestion["nearest_after"])

            # Успех: запоминаем
            final_barbers_data.append((available_barber, start_datetime, end_datetime, []))

        else:
            # --- СЛУЧАЙ: booking_details не пуст
            local_start = start_datetime
            for cat_detail in booking_details:
                cat_id = cat_detail.get('categoryId', 'any')
                services = cat_detail.get('services', [])
                barber_id = cat_detail.get('barberId', 'any')
                duration_raw = cat_detail.get('duration', 30)

                try:
                    dur = int(duration_raw)
                except (TypeError, ValueError):
                    logger.error(f"Invalid service duration: {duration_raw}")
                    raise ClientError("Invalid service duration", status=400)

                interval_end = local_start + timedelta(minutes=dur)

                # Ищем барбера
                found_barber = None

                if barber_id != 'any':
                    # Пытаемся взять конкретного барбера
                    try:
                        found_barber = Barber.objects.select_for_update().get(
                            id=barber_id,
                            salon=salon,
                            status='active'
                        )
                    except Barber.DoesNotExist:
                        logger.warning(f"Barber with ID {barber_id} not found in salon {salon}")
                        suggestion = get_nearest_suggestion(
                            salon_id=salon.id,
                            date_str=date_str,
                            chosen_hour=local_start.hour,
                            booking_details=booking_details,
                            total_service_duration=total_service_duration
                        )
                        raise BookingError("Barber is busy",
                                           nearest_before=suggestion["nearest_before"],
                                           nearest_after=suggestion["nearest_after"])

                    # Проверяем overlapping
                    overlapping = AppointmentBarberService.objects.filter(
                        barber=found_barber,
                        start_datetime__lt=interval_end,
                        end_datetime__gt=local_start
                    ).exists()

                    if overlapping or not is_barber_available(found_barber, local_start, interval_end):
                        logger.info(f"Barber {found_barber.name} is busy at chosen time.")
                        suggestion = get_nearest_suggestion(
                            salon_id=salon.id,
                            date_str=date_str,
                            chosen_hour=local_start.hour,
                            booking_details=booking_details,
                            total_service_duration=total_service_duration
                        )
                        raise BookingError("Barber is busy",
                                           nearest_before=suggestion["nearest_before"],
                                           nearest_after=suggestion["nearest_after"])
                else:  # barber_id == 'any'
                    if cat_id == 'any':
                        busy_barber_ids = AppointmentBarberService.objects.filter(
                            start_datetime__lt=end_datetime,
                            end_datetime__gt=start_datetime
                        ).values_list('barber_id', flat=True)
                        logger.info(f"Busy barber IDs: {list(busy_barber_ids)}")

                        candidate_barbers = Barber.objects.select_for_update().filter(
                            salon=salon,
                            availabilities__day_of_week=start_datetime.strftime('%A').lower(),
                            availabilities__start_time__lte=start_datetime.time(),
                            availabilities__end_time__gte=start_datetime.time(),
                            availabilities__is_available=True,
                            status='active'
                        ).exclude(id__in=busy_barber_ids)

                    else:  # cat_id != 'any'
                        busy_barber_ids = AppointmentBarberService.objects.filter(
                            barber__categories__id=cat_id,
                            start_datetime__lt=interval_end,
                            end_datetime__gt=local_start
                        ).values_list('barber_id', flat=True)

                        candidate_barbers = Barber.objects.select_for_update().filter(
                            salon=salon,
                            categories__id=cat_id,
                            availabilities__day_of_week=local_start.strftime('%A').lower(),
                            availabilities__start_time__lte=local_start.time(),
                            availabilities__end_time__gte=interval_end.time(),
                            availabilities__is_available=True,
                            status='active'
                        ).exclude(id__in=busy_barber_ids)

                    # Теперь проверяем, есть ли вообще кандидаты
                    if not candidate_barbers.exists():
                        logger.warning("No available barbers for the chosen time.")
                        suggestion = get_nearest_suggestion(
                            salon_id=salon.id,
                            date_str=date_str,
                            chosen_hour=start_datetime.hour,
                            booking_details=booking_details,
                            total_service_duration=total_service_duration
                        )
                        raise BookingError(
                            "Barber is busy",
                            nearest_before=suggestion["nearest_before"],
                            nearest_after=suggestion["nearest_after"]
                        )

                    # Берём первого подходящего барбера
                    found_barber = candidate_barbers.first()

                    # Проверяем расписание и доступность именно этого барбера
                    if not is_barber_available(found_barber, local_start, interval_end):
                        logger.warning(f"No available barbers for category {cat_id} (barber {found_barber} not available by schedule).")
                        suggestion = get_nearest_suggestion(
                            salon_id=salon.id,
                            date_str=date_str,
                            chosen_hour=local_start.hour,
                            booking_details=booking_details,
                            total_service_duration=total_service_duration
                        )
                        raise BookingError(
                            "Barber is busy",
                            nearest_before=suggestion["nearest_before"],
                            nearest_after=suggestion["nearest_after"]
                        )

                # Если дошли сюда, значит found_barber есть, и он свободен
                logger.debug(f"Selected barber {found_barber.name} (ID: {found_barber.id}) for category {cat_id}")

                # Запоминаем в final_barbers_data
                final_barbers_data.append((found_barber, local_start, interval_end, services))

                # Сдвигаем local_start
                local_start = interval_end

        # Если мы дошли сюда — значит все проверки прошли, ошибка не выброшена
        # => можно создавать запись

        # -------------------------------------------------
        # 7) Только теперь создаём Appointment
        # -------------------------------------------------
        appointment = Appointment(
            salon=salon,
            user=user,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            user_comment=user_comment
        )
        appointment.save()
        logger.debug(f"Appointment created: {appointment}")

        # -------------------------------------------------
        # 8) Создаём AppointmentBarberService
        # -------------------------------------------------
        appointments_to_create = []
        for (barber, slot_start, slot_end, services_list) in final_barbers_data:
            abs_obj = AppointmentBarberService(
                appointment=appointment,
                barber=barber,
                start_datetime=slot_start,
                end_datetime=slot_end
            )
            abs_obj.save()

            # Привязка услуг (барбер- или обычные)
            for service_info in services_list:
                service_id = service_info.get('serviceId')
                if salonMod == 'barber':
                    try:
                        barber_service = BarberService.objects.get(id=service_id, barber=barber)
                        abs_obj.barberServices.add(barber_service)
                        logger.debug(f"[BARBER MODE] Added barberService {barber_service.name} (ID: {barber_service.id})")
                    except BarberService.DoesNotExist:
                        logger.warning(f"BarberService with ID {service_id} not found for {barber.name}")
                        raise ClientError(f"BarberService with ID {service_id} not found.", status=400)
                else:
                    try:
                        serv = Service.objects.get(id=service_id, salon=salon)
                        abs_obj.services.add(serv)
                        logger.debug(f"[CATEGORY MODE] Added Service {serv.name} (ID: {serv.id})")
                    except Service.DoesNotExist:
                        logger.warning(f"Service with ID {service_id} not found in salon {salon}")
                        raise ClientError(f"Service with ID {service_id} not found in salon.", status=400)

            appointments_to_create.append(abs_obj)

        # Связываем
        if appointments_to_create:
            appointment.barber_services.set(appointments_to_create)

        # -------------------------------------------------
        # 9) Отправка уведомлений (если не DEBUG)
        # -------------------------------------------------
        if not settings.DEBUG:
            notified_barber_ids = set()
            # Итерируем по созданным AppointmentBarberService (appointments_to_create)
            unique_barbers = {abs_obj.barber for abs_obj in appointments_to_create}
            master_names = ", ".join(b.name for b in unique_barbers)
            for abs_obj in appointments_to_create:
                barber = abs_obj.barber
                if barber.id in notified_barber_ids:
                    continue  # уже уведомляли этого барбера
                notified_barber_ids.add(barber.id)
                
                # Получаем профиль барбера через связанного пользователя
                try:
                    profile = barber.user.main_profile  # объект Profile
                except AttributeError:
                    logger.warning("Профиль барбера %r не найден.", barber)
                    continue

                # Получаем номер телефона клиента (если пользователь аутентифицирован)
                if request.user.is_authenticated:
                    try:
                        client_phone_number = request.user.main_profile.phone_number
                    except AttributeError:
                        logger.warning("Профиль клиента не найден.")
                        client_phone_number = "Неизвестен"
                else:
                    client_phone_number = "Неизвестен"

                # Отправка уведомления через WhatsApp, если профиль барбера подписан на WhatsApp
                if profile.whatsapp:
                    TEMPLATE_SID = "HXa27885cd64b14637a00e845fbbfaa326"
                    datetime_str = (
                        appointment.start_datetime.strftime("%d.%m %H:%M") +
                        "-" +
                        appointment.end_datetime.strftime("%H:%M")
                    )
                    dataTest = {
                        "client_phoneNumber": client_phone_number if client_phone_number else "Неизвестен",
                        "datetime": datetime_str,
                        "master_name": master_names,
                        "admin_number": profile.whatsapp_phone_number
                    }

                    content_variables_dict = {
                        "1": dataTest["datetime"],
                        "2": dataTest["master_name"],
                        "3": dataTest["client_phoneNumber"]
                    }
                    logger.info('dataTest[admin_number]')
                    logger.info(dataTest["admin_number"])
                    variables_str = json.dumps(content_variables_dict, ensure_ascii=False)
                    logger.info("ContentVariables JSON: %s", variables_str)

                    try:
                        send_whatsapp_message(dataTest["admin_number"], TEMPLATE_SID, variables_str)
                    except Exception as e:
                        logger.error("Ошибка при отправке WhatsApp уведомления для барбера %r: %s", barber, e)

                # Отправка push-уведомлений для барбера (а не админа)
                if profile.push_subscribe:
                    push_subscriptions = PushSubscription.objects.filter(user=barber.user)
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
                            "body": f"Пользователь успешно забронировал услугу для {barber.name}.",
                            "icon": "/static/main/img/notification-icon.png",
                            "url": "/user-account/bookings/"
                        }
                        try:
                            # Обратите внимание: ошибка "Missing 'aud' from claims" возникает, если в настройках VAPID
                            # не указан параметр "aud". Для исправления необходимо в настройках вашего сервиса
                            # (например, в settings.py или при инициализации pywebpush) установить 'aud' равным URL вашего сайта.
                            send_push_notification_task.delay(subscription_info, json.dumps(payload))
                            logger.info(f"Задача на отправку push уведомления создана для барбера {barber.name}.")
                        except Exception as e:
                            logger.error("Ошибка при отправке push уведомления для барбера %r: %s", barber, e)
            pass

        logger.info("Booking successfully created (Approach A).")
        return JsonResponse({'success': True, 'message': 'Booking created successfully!'})

    # -----------------------------------------
    # 10) Обработка исключений
    # -----------------------------------------
    except BookingError as e:
        # Исключение внутри @transaction.atomic => откат
        logger.warning(f"BookingError: {e.message}")
        return JsonResponse({
            'error': e.message,
            'nearest_before': e.nearest_before,
            'nearest_after': e.nearest_after
        }, status=400)

    except ClientError as e:
        logger.warning(f"ClientError: {e.message}")
        return JsonResponse({'error': e.message}, status=e.status)

    except Exception as e:
        logger.error(f"Unhandled exception in booking (Approach A): {e}", exc_info=True)
        return JsonResponse({'error': 'Internal server error.'}, status=500)

def get_or_create_user_by_phone(phone_number: str):

    # 1) создаём/находим user
    user, created = User.objects.get_or_create(
        username=phone_number
    )
    if created:
        user.set_unusable_password()
        user.save()

    # 2) создаём/находим profile
    # В случае параллельного обращения может выдать IntegrityError, придётся ловить
    for attempt in range(5):
        try:
            profile, created = Profile.objects.get_or_create(
                phone_number=phone_number,
                defaults={'user': user, 'status': 'verified'}
            )
            return profile.user, profile
        except IntegrityError:
            time.sleep(0.2)

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

