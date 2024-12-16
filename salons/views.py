# salons/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import Salon, Appointment, Barber, Service, ServiceCategory, AppointmentBarberService, BarberAvailability
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta, time, timezone as dt_timezone
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
import pytz
import json
import logging
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch
from collections import defaultdict
from django.core.cache import cache

logger = logging.getLogger('booking')

@cache_page(60 * 15)
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
    logger.debug(f"Passing 'q' to context: '{query}'")
    return render(request, 'salons/salons.html', context)

def salon_detail(request, id):
    # salon = get_object_or_404(Salon, id=id)
    salon = get_object_or_404(Salon.objects.prefetch_related(
        'services__category',       # Предварительная загрузка услуг и их категорий
        'barbers__categories'      # Предварительная загрузка барберов и их категорий
    ), id=id)

    service_categories = ServiceCategory.objects.filter(
        services__salon=salon, 
        services__status='active'
    ).distinct()

    # Собираем барберов по категориям
    barbers_by_category = {}
    for category in service_categories:
        barbers = Barber.objects.filter(categories=category, salon=salon)
        barbers_list = []
        for barber in barbers:
            barbers_list.append({
                'id': barber.id,
                'name': barber.name,
                'avatar': barber.get_avatar_url(),
                'description': barber.description or ''
            })
        barbers_by_category[f'category_{category.id}'] = barbers_list

    # Собираем услуги по категориям
    services_by_category = {}
    for category in service_categories:
        services = Service.objects.filter(
            category=category, 
            salon=salon, 
            status='active'
        )
        services_list = []
        for service in services:
            services_list.append({
                'id': service.id,
                'name': service.name,
                'price': service.price,  # DecimalField, будет обработан DjangoJSONEncoder
                'duration': int(service.duration.total_seconds() / 60),  # Преобразование timedelta в минуты
                # Добавьте другие необходимые поля
            })
        services_by_category[f'category_{category.id}'] = services_list

    # Сериализуем в JSON с использованием DjangoJSONEncoder
    barbers_by_category_json = json.dumps(barbers_by_category, cls=DjangoJSONEncoder)
    services_by_category_json = json.dumps(services_by_category, cls=DjangoJSONEncoder)

    context = {
        'salon': salon,
        'service_categories': service_categories,
        'barbers_by_category_json': barbers_by_category_json,
        'services_by_category_json': services_by_category_json,
    }

    return render(request, 'salons/salon-detail.html', context)

    
def get_barber_availability(request, barber_id):
    try:
        barber = Barber.objects.get(id=barber_id)
        availability = barber.availability  # Предполагается, что availability хранит расписание в JSON
        return JsonResponse({'availability': availability})
    except Barber.DoesNotExist:
        return JsonResponse({'error': 'Barber not found'}, status=404)
    
@api_view(['POST'])
def get_available_minutes(request):
    try:
        data = request.data
        salon_id = data.get('salon_id')
        booking_details = data.get('booking_details', [])
        date_str = data.get('date')
        hour_str = data.get('hour')
        total_service_duration = int(data.get('total_service_duration', 0))

        # Валидация обязательных полей
        if not all([salon_id, date_str, hour_str]):
            logger.error("Отсутствуют обязательные поля в запросе.")
            return Response({'available_minutes': [], 'error': 'Отсутствуют обязательные поля.'}, status=status.HTTP_400_BAD_REQUEST)

        # Создаём ключ для кеша
        cache_key = f'available_minutes_{salon_id}_{date_str}_{hour_str}_{json.dumps(booking_details, sort_keys=True)}'
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.debug("Возвращаем данные из кеша.")
            return Response(cached_response)

        # Получаем объект салона с предварительной загрузкой барберов и их расписания
        salon = Salon.objects.prefetch_related(
            Prefetch('barbers__availabilities', queryset=BarberAvailability.objects.all())
        ).get(id=salon_id)

        # Парсим дату и время
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            hour = int(hour_str)
            start_datetime_naive = datetime.combine(date, time(hour, 0))
            start_datetime = timezone.make_aware(start_datetime_naive, pytz.UTC)
            end_datetime = start_datetime + timedelta(hours=1)
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка форматирования даты или времени: {e}")
            return Response({'available_minutes': [], 'error': 'Некорректный формат даты или времени.'}, status=status.HTTP_400_BAD_REQUEST)

        day_code = start_datetime.strftime('%A').lower()

        # Предварительно загружаем всех барберов и их расписание на день
        barbers = salon.barbers.all()
        barber_availability = {}
        for barber in barbers:
            availability = []
            for interval in barber.availabilities.filter(day_of_week=day_code):
                availability.append({
                    'is_available': interval.is_available,
                    'start_time': interval.start_time,
                    'end_time': interval.end_time
                })
            barber_availability[barber.id] = availability

        # Получаем все занятые барберы за час одним запросом
        busy_appointments = AppointmentBarberService.objects.filter(
            barber__salon=salon,
            start_datetime__lt=end_datetime,
            end_datetime__gt=start_datetime
        ).select_related('barber')

        barber_busy_times = defaultdict(list)
        for appointment in busy_appointments:
            barber_busy_times[appointment.barber_id].append((appointment.start_datetime, appointment.end_datetime))

        # Подготавливаем категории услуг, если есть
        active_categories = []
        if booking_details:
            for category_detail in booking_details:
                category_id = category_detail.get('categoryId')
                services = category_detail.get('services', [])
                barber_id = category_detail.get('barberId', 'any')
                duration = int(category_detail.get('duration', 0))

                active_categories.append({
                    'category_id': category_id,
                    'services': services,
                    'barber_id': barber_id,
                    'duration': duration
                })

        available_minutes = set()

        for minute in range(0, 60, 5):
            minute_start_datetime = start_datetime + timedelta(minutes=minute)

            if booking_details:
                total_duration = sum(category['duration'] for category in active_categories)
                minute_end_datetime = minute_start_datetime + timedelta(minutes=total_duration)

                now = timezone.now()
                if minute_start_datetime < now or minute_end_datetime > end_datetime:
                    continue

                schedule_possible = True
                current_time = minute_start_datetime
                barber_schedules = defaultdict(list)

                for category in active_categories:
                    category_id = category['category_id']
                    duration = category['duration']
                    barber_id = category['barber_id']
                    interval_end = current_time + timedelta(minutes=duration)

                    if barber_id != 'any':
                    # Фиксируем барбера по ID
                        try:
                            barber_id_int = int(barber_id)
                            barber = barbers.filter(id=barber_id_int).first()
                            if not barber:
                                raise StopIteration
                        except (ValueError, StopIteration):
                            logger.warning(f"Барбер с ID {barber_id} не найден в салоне {salon}")
                            schedule_possible = False
                            break

                        # Проверка занятости барбера
                        busy = False
                        for busy_start, busy_end in barber_busy_times.get(barber.id, []):
                            if busy_start < interval_end and busy_end > current_time:
                                busy = True
                                break

                        if busy:
                            schedule_possible = False
                            break

                        # Проверка расписания барбера
                        if not is_barber_available_in_memory(
                            barber, current_time.time(), interval_end.time(), barber_availability
                        ):
                            schedule_possible = False
                            break

                        # Проверка перекрытий в текущей проверке
                        overlap = False
                        for sched in barber_schedules[barber.id]:
                            if sched['start'] < interval_end and sched['end'] > current_time:
                                overlap = True
                                break

                        if overlap:
                            schedule_possible = False
                            break

                        # Добавляем в расписание
                        barber_schedules[barber.id].append({'start': current_time, 'end': interval_end})

                    else:
                        # Выбираем любого доступного барбера по категории
                        try:
                            service_category = ServiceCategory.objects.get(id=category_id)
                        except ServiceCategory.DoesNotExist:
                            logger.warning(f"Категория услуг с ID {category_id} не найдена.")
                            schedule_possible = False
                            break

                        candidate_barbers = service_category.barbers.filter(salon=salon)
                        busy_barbers_ids = set(appointment.barber_id for appointment in busy_appointments if appointment.barber in candidate_barbers)

                        available_barbers = [b for b in candidate_barbers if b.id not in busy_barbers_ids]

                        barber_found = False
                        for barber in available_barbers:
                            # Проверка расписания барбера
                            if not is_barber_available_in_memory(
                                barber, current_time.time(), interval_end.time(), barber_availability
                            ):
                                continue

                            # Проверка перекрытий в текущей проверке
                            overlap = False
                            for sched in barber_schedules[barber.id]:
                                if sched['start'] < interval_end and sched['end'] > current_time:
                                    overlap = True
                                    break

                            if overlap:
                                continue

                            # Назначаем барбера
                            barber_schedules[barber.id].append({'start': current_time, 'end': interval_end})
                            barber_found = True
                            break

                        if not barber_found:
                            schedule_possible = False
                            break

                    current_time = interval_end

                if schedule_possible:
                    available_minutes.add(minute)

            else:
                # Нет активных категорий
                total_service_duration = total_service_duration or salon.default_duration
                minute_end_datetime = minute_start_datetime + timedelta(minutes=total_service_duration)

                if minute_end_datetime > end_datetime:
                    continue

                # Проверяем, есть ли барбер, доступный в это время
                barber_available = False
                for barber in barbers:
                    # Проверка занятости барбера
                    busy = False
                    for busy_start, busy_end in barber_busy_times.get(barber.id, []):
                        if busy_start < minute_end_datetime and busy_end > minute_start_datetime:
                            busy = True
                            break
                    if busy:
                        continue

                    # Проверка расписания барбера
                    if is_barber_available_in_memory(
                        barber, minute_start_datetime.time(), minute_end_datetime.time(), barber_availability
                    ):
                        barber_available = True
                        break

                if barber_available:
                    available_minutes.add(minute)

        # Кешируем результат
        response = {'available_minutes': sorted(available_minutes)}
        cache.set(cache_key, response, timeout=60)  # Кешировать на 1 минуту
        logger.debug("Кеширование результатов успешно.")
        return Response(response)

    except Exception as e:
        logger.exception("Error in get_available_minutes")
        return Response({'available_minutes': [], 'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@transaction.atomic
def book_appointment(request, id):
    logger.debug("Начало обработки запроса на бронирование")

    if request.method != "POST":
        logger.warning(f"Некорректный метод запроса: {request.method}")
        return JsonResponse({'error': 'Некорректный метод запроса.'}, status=400)
    
    salon = get_object_or_404(Salon, id=id)

    # Проверяем, является ли запрос JSON
    if request.headers.get('Content-Type') == 'application/json':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {e}")
            return JsonResponse({'error': 'Некорректный формат данных.'}, status=400)

        date_str = data.get("date")
        time_str = data.get("time")
        booking_details = data.get("booking_details", [])
        total_service_duration = data.get("total_service_duration", salon.default_duration)
    else:
        # Если запрос не является JSON, возвращаем ошибку
        logger.error("Некорректный формат данных. Ожидается JSON.")
        return JsonResponse({'error': 'Некорректный формат данных.'}, status=400)

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
    start_datetime = timezone.make_aware(start_datetime_naive, pytz.UTC)
    initial_start_datetime = start_datetime  # Сохраняем начальное время

    if booking_details:
        total_service_duration = sum(category['duration'] for category in booking_details)
    else:
        total_service_duration = salon.default_duration  # Используем длительность по умолчанию

    end_datetime = start_datetime + timedelta(minutes=total_service_duration)

    # Создаем Appointment
    appointment = Appointment(
        salon=salon,
        user=request.user if request.user.is_authenticated else None,
        start_datetime=initial_start_datetime,
        end_datetime=end_datetime
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

        available_barber = Barber.objects.select_for_update().filter(
            salon=salon
        ).exclude(
            id__in=busy_barber_ids
        ).first()

        if not available_barber:
            logger.warning("Нет доступных мастеров на выбранное время.")
            return JsonResponse({'error': 'Нет доступных мастеров на выбранное время.'}, status=400)

        # Проверка доступности по расписанию
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
        for category_detail in booking_details:
            category_id = category_detail.get('categoryId')
            services = category_detail.get('services', [])
            barber_id = category_detail.get('barberId', 'any')
            duration = category_detail.get('duration')

            interval_end = start_datetime + timedelta(minutes=duration)

            if barber_id != 'any':
                try:
                    barber = Barber.objects.select_for_update().get(id=barber_id, salon=salon)
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
                    start_datetime__lt=interval_end,
                    end_datetime__gt=start_datetime
                ).values_list('barber_id', flat=True)

                available_barber = Barber.objects.select_for_update().filter(
                    salon=salon,
                    categories__id=category_id
                ).exclude(
                    id__in=busy_barber_ids
                ).first()

                if available_barber:
                    barber = available_barber
                else:
                    logger.warning(f"Нет доступных барберов для категории {category_id}")
                    return JsonResponse({'error': 'Нет доступных барберов для одной из категорий.'}, status=400)

            # Проверка доступности по расписанию
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

            for service_info in services:
                service_id = service_info.get('serviceId')
                try:
                    service = Service.objects.get(id=service_id, salon=salon)
                    appointment_barber_service.services.add(service)
                except Service.DoesNotExist:
                    logger.warning(f"Услуга с ID {service_id} не найдена в салоне {salon}")
                    return JsonResponse({'error': f"Услуга с ID {service_id} не найдена в салоне."}, status=400)

            appointments_to_create.append(appointment_barber_service)

            # Обновляем start_datetime для следующей услуги
            start_datetime = interval_end

    # Связываем созданные AppointmentBarberService с Appointment
    if appointments_to_create:
        appointment.barber_services.set(appointments_to_create)

    logger.info(f"Бронирование успешно создано для пользователя - {request.user if request.user.is_authenticated else 'Анонимный пользователь'}")
    return JsonResponse({'success': True, 'message': 'Бронирование успешно создано!'})

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
    :param request_start_time: Время начала запроса (time).
    :param request_end_time: Время окончания запроса (time).
    :param barber_availability: Словарь с расписанием барберов.
    :return: True, если барбер доступен, иначе False.
    """
    intervals = barber_availability.get(barber.id, [])

    if not intervals:
        # Нет записей на этот день: считаем день полностью выходным
        return False

    # Проверяем, есть ли недоступные интервалы, пересекающие запрошенный интервал
    for interval in intervals:
        if not interval['is_available']:
            if interval['start_time'] < request_end_time and interval['end_time'] > request_start_time:
                return False

    # Проверяем доступные интервалы, должен быть хотя бы один, покрывающий весь [request_start_time, request_end_time]
    for interval in intervals:
        if interval['is_available']:
            if interval['start_time'] <= request_start_time and interval['end_time'] >= request_end_time:
                return True

    return False
