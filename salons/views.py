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

# logger = logging.getLogger(__name__)
logger = logging.getLogger('booking')

def main(request):
    query = request.GET.get('q')
    if query:
        salons = Salon.objects.filter(
            Q(name__icontains=query) | Q(address__icontains=query)
        )
    else:
        salons = Salon.objects.filter(status='active')
    return render(request, 'salons/salons.html', {'salons': salons})

def salon_detail(request, id):
    salon = get_object_or_404(Salon, id=id)
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

        salon = Salon.objects.get(id=salon_id)
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        hour = int(hour_str)
        start_datetime_naive = datetime.combine(date, time(hour, 0))
        start_datetime = timezone.make_aware(start_datetime_naive, pytz.UTC)
        end_datetime = start_datetime + timedelta(hours=1)

        active_categories = []
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

        if not active_categories:
            # Нет активных категорий
            total_service_duration = total_service_duration or salon.default_duration
            available_minutes = []
            for minute in range(0, 60, 5):
                minute_start_datetime = start_datetime + timedelta(minutes=minute)
                minute_end_datetime = minute_start_datetime + timedelta(minutes=total_service_duration)

                if minute_end_datetime > end_datetime:
                    continue

                # Определяем занятых мастеров
                busy_barbers = Barber.objects.filter(
                    salon=salon,
                    appointmentbarberservice__start_datetime__lt=minute_end_datetime,
                    appointmentbarberservice__end_datetime__gt=minute_start_datetime,
                ).values_list('id', flat=True).distinct()

                available_barbers = Barber.objects.filter(salon=salon).exclude(id__in=busy_barbers)

                logger.debug(f"Minute {minute}: Busy barbers IDs: {list(busy_barbers)}, Available barbers IDs: {list(available_barbers.values_list('id', flat=True))}")

                if available_barbers.exists():
                    # Проверяем расписание хотя бы одного мастера
                    schedule_ok = False
                    for barber in available_barbers:
                        if is_barber_available(barber, minute_start_datetime, minute_end_datetime):
                            schedule_ok = True
                            break
                    if schedule_ok:
                        available_minutes.append(minute)

            return Response({'available_minutes': sorted(set(available_minutes))})

        else:
            # Есть активные категории
            available_minutes = []
            total_duration = sum(category['duration'] for category in active_categories)

            for minute in range(0, 60, 5):
                minute_start_datetime = start_datetime + timedelta(minutes=minute)
                minute_end_datetime = minute_start_datetime + timedelta(minutes=total_duration)

                now = timezone.now()
                if minute_start_datetime < now:
                    continue

                if minute_end_datetime > end_datetime:
                    continue

                schedule_possible = True
                current_time = minute_start_datetime
                barber_schedules = {}

                for category in active_categories:
                    category_id = category['category_id']
                    duration = category['duration']
                    barber_id = category['barber_id']

                    barber_assigned = False
                    interval_end = current_time + timedelta(minutes=duration)

                    if barber_id != 'any':
                        try:
                            barber = Barber.objects.get(id=barber_id, salon=salon)
                        except Barber.DoesNotExist:
                            return Response({'available_minutes': [], 'error': f"Barber with ID {barber_id} not found."}, status=status.HTTP_400_BAD_REQUEST)
                        # Проверка занятости этим мастером
                        overlapping = AppointmentBarberService.objects.filter(
                            barber=barber,
                            start_datetime__lt=interval_end,
                            end_datetime__gt=current_time
                        ).exists()

                        if overlapping:
                            # Этот мастер занят
                            pass
                        else:
                            # Проверяем есть ли конфликт с barber_schedules
                            overlapping_in_schedule = False
                            if barber.id in barber_schedules:
                                for scheduled_time in barber_schedules[barber.id]:
                                    if scheduled_time['start'] < interval_end and scheduled_time['end'] > current_time:
                                        overlapping_in_schedule = True
                                        break

                            if not overlapping and not overlapping_in_schedule:
                                # Дополнительная проверка расписания
                                if is_barber_available(barber, current_time, interval_end):
                                    barber_schedules.setdefault(barber.id, []).append({
                                        'start': current_time,
                                        'end': interval_end
                                    })
                                    barber_assigned = True
                    else:
                        # barber_id = any
                        # Выбираем любого подходящего барбера по категории
                        busy_barbers = AppointmentBarberService.objects.filter(
                            start_datetime__lt=interval_end,
                            end_datetime__gt=current_time
                        ).values_list('barber_id', flat=True)

                        service_category = ServiceCategory.objects.get(id=category_id)
                        candidate_barbers = service_category.barbers.filter(salon=salon).exclude(id__in=busy_barbers)

                        for barber in candidate_barbers:
                            overlapping_in_schedule = False
                            if barber.id in barber_schedules:
                                for scheduled_time in barber_schedules[barber.id]:
                                    if scheduled_time['start'] < interval_end and scheduled_time['end'] > current_time:
                                        overlapping_in_schedule = True
                                        break

                            if not overlapping_in_schedule:
                                # Проверка расписания
                                if is_barber_available(barber, current_time, interval_end):
                                    barber_schedules.setdefault(barber.id, []).append({
                                        'start': current_time,
                                        'end': interval_end
                                    })
                                    barber_assigned = True
                                    break

                    if not barber_assigned:
                        schedule_possible = False
                        break

                    current_time = interval_end

                    if current_time > end_datetime:
                        schedule_possible = False
                        break

                if schedule_possible:
                    available_minutes.append(minute)

            return Response({'available_minutes': sorted(set(available_minutes))})

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
            logger.debug(data)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {e}")
            return JsonResponse({'error': 'Некорректный формат данных.'}, status=400)

        date_str = data.get("date")
        time_str = data.get("time")
        booking_details = data.get("booking_details", [])
        total_service_duration = data.get("total_service_duration", salon.default_duration)
        logger.debug(f"Получены данные бронирования - date: {date_str}, time: {time_str}, booking_details: {booking_details}")
    else:
        # Если запрос не является JSON, возвращаем ошибку
        logger.error("Некорректный формат данных. Ожидается JSON.")
        return JsonResponse({'error': 'Некорректный формат данных.'}, status=400)

    # Валидация даты
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        logger.debug(f"Отформатированная дата: {date}")
    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка форматирования даты: {e}")
        return JsonResponse({'error': 'Некорректный формат даты.'}, status=400)

    # Валидация времени
    try:
        start_time = datetime.strptime(time_str, '%H:%M').time()
        logger.debug(f"Отформатированное время: {start_time}")
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
    logger.debug(f"Время бронирования: {start_datetime} - {end_datetime}")

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
        logger.debug(f"Создано AppointmentBarberService: {appointment_barber_service}")

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
            logger.debug(f"Создано AppointmentBarberService: {appointment_barber_service}")

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