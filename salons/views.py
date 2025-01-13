# salons/views.py
from django.shortcuts import render, get_object_or_404
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
        # barbers = Barber.objects.filter(
        #     categories=category,
        #     salon=salon,
        #     barber_services__service__category=category
        # ).distinct()

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
        'categories_with_services': categories_with_services,
        'barbers_by_category': barbers_by_category,
        'barbers_by_category_json': barbers_by_category_json,
    }

    return render(request, 'salons/salon-detail.html', context)

def get_barber_availability(request, barber_id):
    try:
        barber = Barber.objects.get(id=barber_id)
        availability = barber.availability
        return JsonResponse({'availability': availability})
    except Barber.DoesNotExist:
        return JsonResponse({'error': 'Barber not found'}, status=404)
    
@api_view(['POST'])
def get_available_minutes(request):
    data = request.data
    salon_id = data.get('salon_id')
    booking_details = data.get('booking_details', [])
    date_str = data.get('date')
    # Это список часов, которые фронтенд хочет проверить. 
    # (Например, [10, 11, 12], если пользователь смотрит слот между 10:00 и 13:00)
    hours = data.get('hours', [])  
    selected_barber_id = data.get('selected_barber_id', 'any')  
    total_service_duration = int(data.get('total_service_duration', 0))

    # Валидация обязательных полей
    if not all([salon_id, date_str, hours]):
        logger.error("Отсутствуют обязательные поля в запросе.")
        return Response(
            {'available_minutes': {}, 'error': 'Отсутствуют обязательные поля.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Проверяем, что hours — список целых чисел
    if not isinstance(hours, list) or not all(isinstance(hour, int) for hour in hours):
        logger.error("Поле 'hours' должно быть списком целых чисел.")
        return Response(
            {'available_minutes': {}, 'error': "Поле 'hours' должно быть списком целых чисел."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Загружаем салон (и расписания барберов)    
    try:
        salon = Salon.objects.prefetch_related(
            Prefetch('barbers__availabilities', queryset=BarberAvailability.objects.all())
        ).get(id=salon_id)
    except Salon.DoesNotExist:
        logger.error(f"Салон с ID {salon_id} не найден.")
        return Response(
            {'available_minutes': {}, 'error': 'Салон не найден.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Парсим дату
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError as e:
        logger.error(f"Ошибка форматирования даты: {e}")
        return Response(
            {'available_minutes': {}, 'error': 'Некорректный формат даты.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    day_code = date.strftime('%A').lower()

    # Предзагружаем барберов и их расписание
    barbers = salon.barbers.all()
    barber_availability = {}
    for barber in barbers:
        availability = []
        for interval in barber.availabilities.filter(day_of_week=day_code):
            availability.append({
                'start_time': interval.start_time,
                'end_time': interval.end_time,
                'is_available': interval.is_available
            })
        barber_availability[barber.id] = availability

    # Подгружаем занятость барберов **за весь день** (убираем фильтр по часам!)
    busy_appointments = AppointmentBarberService.objects.filter(
        barber__salon=salon,
        start_datetime__date=date
    ).select_related('barber')

    barber_busy_times = defaultdict(list)
    for appointment in busy_appointments:
        barber_busy_times[appointment.barber_id].append(
            (appointment.start_datetime, appointment.end_datetime)
        )

    # Обработка booking_details
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

    available_minutes = defaultdict(set)  # hour -> set of minutes
    
    from django.utils import timezone
    now = timezone.now()  # Текущее время (aware)

    for hour in hours:
        try:
            start_datetime_naive = datetime.combine(date, time(hour, 0))
            start_datetime = timezone.make_aware(start_datetime_naive, timezone.get_current_timezone())
            # Конец этого часа — раньше вы делали end_datetime, 
            # но теперь не будем запрещать выход за пределы end_datetime
        except Exception as e:
            logger.error(f"Ошибка при создании datetime: {e}")
            available_minutes[hour] = []
            continue

        if booking_details:
            # Общая длительность всех категорий (либо total_service_duration?)
            total_duration = sum(cat['duration'] for cat in active_categories)

            for minute in range(0, 60, 5):
                minute_start_datetime = start_datetime + timedelta(minutes=minute)
                minute_end_datetime = minute_start_datetime + timedelta(minutes=total_duration)

                # 1) Пропускаем, если это время уже в прошлом
                if minute_start_datetime < now:
                    continue

                # (В старом коде было: if minute_end_datetime > end_datetime: continue — УДАЛЯЕМ!)

                schedule_possible = True
                barber_schedules = defaultdict(list)

                for category in active_categories:
                    category_id = category['category_id']
                    duration = category['duration']
                    barber_id = category['barber_id']
                    interval_end = minute_start_datetime + timedelta(minutes=duration)

                    if barber_id != 'any':
                        # Конкретный барбер
                        try:
                            barber_id_int = int(barber_id)
                            barber = barbers.filter(id=barber_id_int).first()
                            if not barber:
                                raise ValueError
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Барбер с ID {barber_id} не найден в салоне {salon}"
                            )
                            schedule_possible = False
                            break

                        # Проверяем занятость
                        if is_barber_busy(
                            barber.id,
                            minute_start_datetime,
                            interval_end,
                            barber_busy_times
                        ):
                            schedule_possible = False
                            break

                        # Проверяем расписание барбера
                        if not is_barber_available_in_memory(
                            barber,
                            minute_start_datetime.time(),
                            interval_end.time(),
                            barber_availability
                        ):
                            schedule_possible = False
                            break

                        # Проверяем перекрытия внутри текущей проверки
                        if has_overlap(barber_schedules[barber.id], minute_start_datetime, interval_end):
                            schedule_possible = False
                            break

                        barber_schedules[barber.id].append({
                            'start': minute_start_datetime,
                            'end': interval_end
                        })

                    else:
                        # barber_id == 'any': найти любого барбера из категории
                        try:
                            service_category = ServiceCategory.objects.get(id=category_id)
                        except ServiceCategory.DoesNotExist:
                            logger.warning(f"Категория услуг с ID {category_id} не найдена.")
                            schedule_possible = False
                            break

                        # Барберы, обслуживающие эту категорию
                        candidate_barbers = service_category.barbers.filter(salon=salon)

                        barber_found = False
                        for candidate_barber in candidate_barbers:
                            # Проверка занятости
                            if is_barber_busy(
                                candidate_barber.id,
                                minute_start_datetime,
                                interval_end,
                                barber_busy_times
                            ):
                                continue

                            # Проверка расписания
                            if not is_barber_available_in_memory(
                                candidate_barber,
                                minute_start_datetime.time(),
                                interval_end.time(),
                                barber_availability
                            ):
                                continue

                            # Проверка перекрытий
                            if has_overlap(barber_schedules[candidate_barber.id], minute_start_datetime, interval_end):
                                continue

                            # Если дошли сюда — значит барбер свободен, назначаем
                            barber_schedules[candidate_barber.id].append({
                                'start': minute_start_datetime,
                                'end': interval_end
                            })
                            barber_found = True
                            break

                        if not barber_found:
                            schedule_possible = False
                            break

                    # Сдвигаем начало для следующей категории
                    minute_start_datetime = interval_end

                if schedule_possible:
                    available_minutes[hour].add(minute)

        else:
            # Если нет booking_details: общий duration = total_service_duration или salon.default_duration
            duration = total_service_duration or salon.default_duration
            for minute in range(0, 60, 5):
                minute_start_datetime = start_datetime + timedelta(minutes=minute)
                minute_end_datetime = minute_start_datetime + timedelta(minutes=duration)

                if minute_start_datetime < now:
                    continue
                # Не проверяем > end_datetime

                # Проверяем, есть ли хоть один свободный барбер
                barber_available = False
                for barber in barbers:
                    if is_barber_busy(barber.id, minute_start_datetime, minute_end_datetime, barber_busy_times):
                        continue

                    if is_barber_available_in_memory(
                        barber,
                        minute_start_datetime.time(),
                        minute_end_datetime.time(),
                        barber_availability
                    ):
                        barber_available = True
                        break

                if barber_available:
                    available_minutes[hour].add(minute)

    # Преобразуем set -> отсортированный список
    available_minutes_response = {hour: sorted(list(minutes)) for hour, minutes in available_minutes.items()}

    # Кэширование (не меняем логику)
    from django.utils import timezone
    current_time = timezone.now()
    cache_time_str = f"{(current_time.minute // 5) * 5}"

    cache_key = generate_safe_cache_key(
        salon_id,
        date_str,
        hours,
        booking_details,
        cache_time_str,
        selected_barber_id=selected_barber_id
    )

    cached_response = cache.get(cache_key)
    if cached_response:
        logger.debug(f"Данные получены из кэша. Ключ: {cache_key}")
        return Response(cached_response)

    response = {'available_minutes': available_minutes_response}
    cache.set(cache_key, response, timeout=30)
    logger.debug(f"Кеширование результатов успешно. Ключ: {cache_key}")
    return Response(response)


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


    # Преобразуем set в отсортированные списки
    available_minutes_response = {hour: sorted(list(minutes)) for hour, minutes in available_minutes.items()}

    # Генерация безопасного ключа кэша с использованием хеширования
    current_time = timezone.now()
    cache_time_str = f"{(current_time.minute // 5) * 5}"  # Округление до ближайших 5 минут

    cache_key = generate_safe_cache_key(
        salon_id,
        date_str,
        hours,
        booking_details,
        cache_time_str,
        selected_barber_id=selected_barber_id  # Включаем выбранного мастера
    )

    # Попытка получить данные из кэша
    cached_response = cache.get(cache_key)
    if cached_response:
        logger.debug(f"Данные получены из кэша. Ключ: {cache_key}")
        return Response(cached_response)

    # Кешируем результат с учётом безопасного ключа
    response = {'available_minutes': available_minutes_response}
    cache.set(cache_key, response, timeout=30)  # Уменьшаем время кэша до 30 секунд
    logger.debug(f"Кеширование результатов успешно. Ключ: {cache_key}")
    return Response(response)

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
                    try:
                        service = Service.objects.get(id=service_id, salon=salon)
                        appointment_barber_service.services.add(service)
                        logger.debug(f"Добавлена услуга {service.name} (ID: {service.id}) к AppointmentBarberService")
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
                        "client_phoneNumber": profile.phone_number,
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

def generate_safe_cache_key(salon_id, date_str, hours, booking_details, cache_time_str, selected_barber_id='any'):
    """
    Генерирует безопасный ключ кэша, используя хеширование параметров запроса.

    :param salon_id: ID салона
    :param date_str: Дата бронирования в формате 'YYYY-MM-DD'
    :param hours: Список часов (целые числа)
    :param booking_details: Список деталей бронирования (словари)
    :param cache_time_str: Строка округленного времени кэша (например, '45' для минут)
    :param selected_barber_id: ID выбранного барбера или 'any' для любого
    :return: Строка безопасного ключа кэша
    """
    key_string = (
        f"available_minutes_{salon_id}_v{get_cache_version(salon_id)}_"
        f"{date_str}_{json.dumps(hours, sort_keys=True)}_"
        f"{json.dumps(booking_details, sort_keys=True)}_"
        f"{selected_barber_id}_{cache_time_str}"
    )
    key_hash = hashlib.md5(key_string.encode('utf-8')).hexdigest()
    return f"available_minutes_{salon_id}_v{get_cache_version(salon_id)}_{key_hash}"


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