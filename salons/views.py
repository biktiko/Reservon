# salons/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import Salon, Appointment, Barber, Service, ServiceCategory, SalonImage
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime, timedelta, time
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
import logging

# logger = logging.getLogger(__name__)
logger = logging.getLogger('booking')

def main(request):
    # salons_list = salons.objects.all()  # Получаем все объекты из таблицы salons    active_salons = Salons.objects.filter(status='active')
    active_salons = Salon.objects.filter(status='active')
    return render(request, 'salons/salons.html', {"salons": active_salons})

def salon_detail(request, id):
    salon = get_object_or_404(Salon, id=id)
    services = Service.objects.filter(salon=salon, status='active')
    services_with_category = services.filter(category__isnull=False)
    services_without_category = services.filter(category__isnull=True)

    # Получаем категории, связанные с услугами этого салона
    service_categories = ServiceCategory.objects.filter(services__in=services).distinct()

    image_urls = []
    if salon.logo:
        image_urls.append(salon.logo.url)
    # Добавляем URL всех дополнительных изображений
    image_urls += [image.image.url for image in salon.images.all()]


    context = {
        'salon': salon,
        'services': services,
        'service_categories': service_categories,
        'services_with_category': services_with_category,
        'services_without_category': services_without_category,
    }
    return render(request, 'salons/salon-detail.html', context)
    
def get_barber_availability(request, barber_id):
    try:
        barber = Barber.objects.get(id=barber_id)
        availability = barber.availability  # Предполагается, что availability хранит расписание в JSON
        return JsonResponse({'availability': availability})
    except Barber.DoesNotExist:
        return JsonResponse({'error': 'Barber not found'}, status=404)

@api_view(['GET'])
def get_available_minutes(request):
    salon_id = request.GET.get('salon_id')
    barber_id = request.GET.get('barber_id', 'any')
    date_str = request.GET.get('date')
    hour_str = request.GET.get('hour')
    total_service_duration = int(request.GET.get('total_service_duration', 20))  # в минутах

    salon = get_object_or_404(Salon, id=salon_id)
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    hour = int(hour_str)

    # Получение рабочих часов салона
    day_name = date.strftime('%A').lower()
    salon_hours = salon.opening_hours.get(day_name)
    if not salon_hours:
        return JsonResponse({'available_minutes': []})

    salon_open = datetime.strptime(salon_hours['open'], '%H:%M').time()
    salon_close = datetime.strptime(salon_hours['close'], '%H:%M').time()

    # Проверка, что выбранный час находится в рабочем времени
    selected_hour_time = time(hour, 0)
    if not (salon_open <= selected_hour_time < salon_close):
        return JsonResponse({'available_minutes': []})

    # Определение времени начала и конца интервала
    start_datetime = datetime.combine(date, selected_hour_time)
    end_datetime = datetime.combine(date, salon_close)

    available_minutes = set()

    if barber_id != 'any':
        # Если выбран конкретный барбер
        try:
            barber = Barber.objects.get(id=barber_id, salon=salon)
        except Barber.DoesNotExist:
            return JsonResponse({'available_minutes': []})

        overlapping_appointments = Appointment.objects.filter(
            salon=salon,
            barber=barber,
            date=date,
            start_time__lt=(datetime.combine(date, selected_hour_time) + timedelta(minutes=total_service_duration)).time(),
            end_time__gt=selected_hour_time
        )

        busy_intervals = [
            (datetime.combine(date, appt.start_time), datetime.combine(date, appt.end_time))
            for appt in overlapping_appointments
        ]

        # Проходим по каждому 5-минутному интервалу
        for minute in range(0, 60, 5):
            proposed_start = start_datetime + timedelta(minutes=minute)
            proposed_end = proposed_start + timedelta(minutes=total_service_duration)

            # Проверяем, не выходит ли время за пределы рабочего времени
            if proposed_end.time() > salon_close:
                continue

            # Проверка перекрытий
            overlap = False
            for busy_start, busy_end in busy_intervals:
                if proposed_start < busy_end and proposed_end > busy_start:
                    overlap = True
                    logger.debug(f"Minute {minute}: Overlaps with appointment {busy_start.time()} - {busy_end.time()}")
                    break

            if not overlap:
                available_minutes.add(minute)
                logger.debug(f"Minute {minute}: Available for barber {barber_id}")

    else:
        # Если выбран "любой барбер"
        barbers = Barber.objects.filter(salon=salon)
        if not barbers.exists():
            return JsonResponse({'available_minutes': []})

        for minute in range(0, 60, 5):
            proposed_start = start_datetime + timedelta(minutes=minute)
            proposed_end = proposed_start + timedelta(minutes=total_service_duration)

            if proposed_end.time() > salon_close:
                continue

            # Проверяем, есть ли хотя бы один барбер, свободный в этом интервале
            is_available = False
            for barber in barbers:
                overlapping = Appointment.objects.filter(
                    salon=salon,
                    barber=barber,
                    date=date,
                    start_time__lt=proposed_end.time(),
                    end_time__gt=proposed_start.time()
                ).exists()
                if not overlapping:
                    is_available = True
                    logger.debug(f"Minute {minute}: Available for barber {barber.id}")
                    break
                else:
                    logger.debug(f"Minute {minute}: Barber {barber.id} is busy")

            if is_available:
                available_minutes.add(minute)
                logger.debug(f"Minute {minute}: Available")

    # Сортируем и возвращаем доступные минуты
    available_minutes = sorted(list(available_minutes))
    logger.debug(f"Available minutes for date {date_str} and hour {hour_str}: {available_minutes}")
    return JsonResponse({'available_minutes': available_minutes})

@transaction.atomic
def book_appointment(request, id):
    logger.debug("Начало обработки запроса на бронирование")

    if request.method != "POST":
        logger.warning(f"Некорректный метод запроса: {request.method}")
        messages.error(request, "Некорректный метод запроса.")
        return redirect(reverse('salon_detail', args=[id]))

    date_str = request.POST.get("date")
    time_str = request.POST.get("time")
    barber_id = request.POST.get("barber_id", "any")
    selected_services = request.POST.getlist("services")

    logger.debug(f"Получены данные бронирования - date: {date_str}, time: {time_str}, barber_id: {barber_id}, services: {selected_services}")

    salon = get_object_or_404(Salon, id=id)
    logger.debug(f"Найден салон - {salon}")

    # Валидация даты
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        logger.debug(f"Отформатированная дата: {date}")
    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка форматирования даты: {e}")
        messages.error(request, "Некорректный формат даты.")
        return redirect(reverse('salon_detail', args=[id]))

    # Валидация времени
    try:
        start_time = datetime.strptime(time_str, '%H:%M').time()
        logger.debug(f"Отформатированное время: {start_time}")
    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка форматирования времени: {e}")
        messages.error(request, "Некорректный формат времени.")
        return redirect(reverse('salon_detail', args=[id]))

    # Проверка рабочего времени салона
    day_name = date.strftime('%A').lower()
    salon_hours = salon.opening_hours.get(day_name)
    logger.debug(f"Рабочие часы салона на {day_name}: {salon_hours}")

    if not salon_hours:
        logger.info(f"Салон закрыт на выбранный день: {day_name}")
        messages.error(request, "Салон закрыт в выбранный день.")
        return redirect(reverse('salon_detail', args=[id]))

    try:
        salon_open = datetime.strptime(salon_hours['open'], '%H:%M').time()
        salon_close = datetime.strptime(salon_hours['close'], '%H:%M').time()
        logger.debug(f"Салон работает с {salon_open} до {salon_close}")
    except (ValueError, KeyError) as e:
        logger.error(f"Ошибка получения рабочих часов: {e}")
        messages.error(request, "Некорректные рабочие часы салона.")
        return redirect(reverse('salon_detail', args=[id]))

    if not (salon_open <= start_time < salon_close):
        logger.info(f"Выбранное время {start_time} вне рабочего графика салона.")
        messages.error(request, "Выбранное время вне рабочего графика салона.")
        return redirect(reverse('salon_detail', args=[id]))

    # Рассчитываем общую длительность обслуживания
    if selected_services:
        total_service_duration = 5  # Запас в 5 минут
        total_services_duration = 0
        for service_id in selected_services:
            try:
                service = Service.objects.get(id=service_id, salon=salon)
                duration_minutes = service.duration.total_seconds() / 60
                total_services_duration += duration_minutes
                logger.debug(f"Добавлена услуга - {service.name}, длительность: {duration_minutes} минут")
            except Service.DoesNotExist:
                logger.warning(f"Услуга с ID {service_id} не найдена в салоне {salon}")
                messages.warning(request, f"Услуга с ID {service_id} не найдена и не была добавлена.")
        total_service_duration += total_services_duration
    else:
        total_service_duration = salon.default_duration  # Используем дефолтное время
        logger.debug(f"Базовая длительность обслуживания: {total_service_duration} минут")

    logger.debug(f"Общая длительность обслуживания: {total_service_duration} минут")

    # Рассчитываем end_time **здесь**, перед выбором барбера
    start_datetime = datetime.combine(date, start_time)
    end_datetime = start_datetime + timedelta(minutes=total_service_duration)
    end_time = end_datetime.time()
    logger.debug(f"Время бронирования: {start_time} - {end_time}")

    # Обработка выбранного барбера
    if barber_id == 'any':
        # Используем select_for_update для блокировки выбранных барберов на время транзакции
        available_barber = Barber.objects.select_for_update().filter(salon=salon).exclude(
            appointments__date=date,
            appointments__start_time__lt=end_time,
            appointments__end_time__gt=start_time
        ).first()
        if available_barber:
            barber = available_barber
            logger.debug(f"Выбран любой мастер: {barber}")
        else:
            messages.error(request, "Нет доступных барберов на выбранное время.")
            return redirect(reverse('salon_detail', args=[id]))
    else:
        try:
            barber = Barber.objects.select_for_update().get(id=barber_id, salon=salon)
            logger.debug(f"Выбран барбер - {barber}")
        except Barber.DoesNotExist:
            logger.warning(f"Барбер с ID {barber_id} не найден в салоне {salon}")
            messages.error(request, "Выбранный барбер не найден.")
            return redirect(reverse('salon_detail', args=[id]))


    # Проверка перекрывающихся бронирований уже после выбора барбера
    overlapping_appointments = Appointment.objects.filter(
        salon=salon,
        date=date,
        start_time__lt=end_time,
        end_time__gt=start_time
    )

    if barber:
        overlapping_appointments = overlapping_appointments.filter(barber=barber)
        logger.debug(f"Фильтр по барберу: {barber}")
    else:
        overlapping_appointments = overlapping_appointments.filter(barber__isnull=True)
        logger.debug("Фильтр по любому барберу")

    overlapping_count = overlapping_appointments.count()
    logger.debug(f"Найдено перекрывающихся бронирований: {overlapping_count}")

    if overlapping_appointments.exists():
        logger.info("Выбранный временной слот уже занят.")
        messages.error(request, "Выбранный временной слот уже занят.")
        return redirect(reverse('salon_detail', args=[id]))

    # Создание записи о бронировании
    try:
        appointment = Appointment.objects.create(
            salon=salon,
            user=request.user if request.user.is_authenticated else None,
            barber=barber,
            date=date,
            start_time=start_time,
            end_time=end_time
        )
        logger.debug(f"Создано бронирование - {appointment}")

        # Добавляем выбранные услуги к записи
        for service_id in selected_services:
            try:
                service = Service.objects.get(id=service_id, salon=salon)
                appointment.services.add(service)
                logger.debug(f"Услуга добавлена к бронированию - {service.name}")
            except Service.DoesNotExist:
                logger.warning(f"Услуга с ID {service_id} не найдена при добавлении к бронированию")

        messages.success(request, "Бронирование успешно создано!")
        logger.info(f"Бронирование успешно создано для пользователя - {appointment.user}")
    except Exception as e:
        logger.error(f"Ошибка при создании бронирования: {e}")
        messages.error(request, f"Ошибка при создании бронирования: {e}")
        return redirect(reverse('salon_detail', args=[id]))

    logger.debug("Завершение обработки запроса на бронирование")
    return redirect(reverse('salon_detail', args=[id]))