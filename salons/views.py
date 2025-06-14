# salons/views.py
from django.shortcuts import render, get_object_or_404
from .models import Salon, Barber, Service, ServiceCategory, AppointmentBarberService, BarberAvailability, BarberService
from .utils import get_nearest_suggestion, is_barber_available, send_whatsapp_message, get_or_create_user_by_phone, send_push_notification_task, _extract_service_id, normalize_phone
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
from .utils import get_candidate_slots, format_free_ranges
from django.views.decorators.csrf import csrf_exempt
import logging
from .errors import BookingError, ClientError
from datetime import timedelta
from .models import Appointment
from django.conf import settings
from authentication.models import PushSubscription
from django.http import HttpResponse
from django.utils.dateparse import parse_datetime

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
        # total_service_duration = data.get("total_service_duration", salon.default_duration)
        user_comment = data.get("user_comment", "")

        #  нормализуем оба формата services: int → {'serviceId': int}
        for detail in booking_details:
            raw_svcs = detail.get('services')
           # если services не список, сбрасываем его в пустой
            if not isinstance(raw_svcs, list):
               raw_svcs = []
            normalized = []
            for svc in raw_svcs:
                sid = _extract_service_id(svc)
                if sid is None:
                    raise ClientError("Service ID not provided", status=400)
                normalized.append({'serviceId': sid})
            detail['services'] = normalized

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
        # 4) Считаем общую длительность по моделям, игнорируем любые duration из запроса
        # -----------------------------------
        total_service_duration = 0
        if total_service_duration is None:
            total_service_duration = sum(
                Service.objects.get(id=_extract_service_id(svc), salon=salon)
                .duration.total_seconds() // 60
                for detail in booking_details
                for svc in detail['services']
            ) or salon.default_duration or 30

        if total_service_duration == 0:
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

            logger.info(f"start_datetime: {start_datetime}")
            logger.info(f"end_datetime: {end_datetime}")

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

                # игнорируем cat_detail['duration'], считаем сумму длительностей из Service
                dur_minutes = 0
                for svc in services:
                    sid = _extract_service_id(svc)
                    if sid is None:
                        raise ClientError("Service ID not provided", status=400)
                    serv = Service.objects.get(id=sid, salon=salon)
                    dur_minutes += int(serv.duration.total_seconds() // 60)

                interval_end = local_start + timedelta(minutes=dur_minutes)

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
            for svc in services_list:
                sid = _extract_service_id(svc)
                if salonMod == 'barber':
                    barber_service = BarberService.objects.get(id=sid, barber=barber)
                    abs_obj.barberServices.add(barber_service)
                else:
                    serv = Service.objects.get(id=sid, salon=salon)
                    abs_obj.services.add(serv)

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

def _parse_local(dt_str: str):
    """
    Парсим строку:
    - сначала пытаемся parse_datetime (ISO +зона),
    - иначе strptime('%d.%m.%Y %H:%M') и локализуем к текущей TZ (+04:00).
    """
    if not dt_str:
        return None
    # 1) ISO
    dt = parse_datetime(dt_str)
    if dt and dt.tzinfo:
        return dt
    # 2) формат DD.MM.YYYY HH:MM
    try:
        naive = datetime.strptime(dt_str, '%d.%m.%Y %H:%M')
    except ValueError:
        return None
    # делаем aware с вашей TZ (+04:00)
    return timezone.make_aware(naive, timezone.get_current_timezone())


@csrf_exempt
@transaction.atomic
def reschedule_appointments(request, salon_id):
    TEMPLATE_SID = "HXb2f720ab353ffcce7849e3aede8348ca"

    if request.method != "POST":
        return HttpResponse("Invalid method", status=405)

    # 1) Парсим JSON
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # 2) Извлекаем и валидируем range_start / range_end
    range_start = _parse_local(body.get("range_start", ""))
    range_end   = _parse_local(body.get("range_end", ""))
    if not (range_start and range_end):
        return JsonResponse({
            "error": "Invalid or missing range_start/range_end. "
                     "Use DD.MM.YYYY HH:MM or full ISO+offset."
        }, status=400)

    # 3) Прочие параметры
    barber_ids    = body.get("barber_ids", "any")
    service_ids   = body.get("service_ids", "any")
    try:
        move_minutes = int(body.get("move_minutes", 0))
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid move_minutes"}, status=400)
    notify = bool(body.get("notify_whatsapp", False))
    delta  = timedelta(minutes=move_minutes)

    # 4) Исходный queryset сегментов в окне
    abs_qs = AppointmentBarberService.objects.select_for_update().filter(
        appointment__salon_id=salon_id,
        start_datetime__gte=range_start,
        end_datetime__lte=range_end,
    )
    if barber_ids != "any":
        abs_qs = abs_qs.filter(barber_id__in=barber_ids)
    if service_ids != "any":
        abs_qs = abs_qs.filter(
            Q(services__id__in=service_ids) |
            Q(barberServices__id__in=service_ids)
        ).distinct()

    # 5) Все сегменты тех же Appointment
    initial_appts = set(abs_qs.values_list('appointment_id', flat=True))
    all_abs = AppointmentBarberService.objects.select_for_update().filter(
        appointment__salon_id=salon_id
    )
    to_move = set(all_abs.filter(appointment_id__in=initial_appts))

    # 6) Добавляем конфликтующие сегменты каскадом
    changed = True
    while changed:
        changed = False
        for seg in list(to_move):
            new_s = seg.start_datetime + delta
            new_e = seg.end_datetime   + delta
            conflicts = all_abs.filter(
                start_datetime__lt=new_e,
                end_datetime__gt=new_s
            ).exclude(id__in=[s.id for s in to_move])
            for c in conflicts:
                to_move.add(c)
                changed = True

    # 7) Сдвигаем все накопленные сегменты
    touched_appts = set()
    for seg in to_move:
        seg.start_datetime += delta
        seg.end_datetime   += delta
        seg.save()
        touched_appts.add(seg.appointment_id)

    # 8) Пересчитываем время у Appointment и шлём WhatsApp
    for appt in Appointment.objects.filter(id__in=touched_appts):
        segments = list(appt.barber_services.all())
        if not segments:
            continue

        new_start = min(s.start_datetime for s in segments)
        new_end   = max(s.end_datetime   for s in segments)

        appt.start_datetime = new_start
        appt.end_datetime   = new_end
        appt.save(update_fields=['start_datetime', 'end_datetime'])

        if notify and appt.user and hasattr(appt.user, 'main_profile'):
            phone = appt.user.main_profile.phone_number
            if phone:
                vars = {
                    "1": appt.salon.name,
                    # здесь игнорируем TZ, выводим локальное время
                    "2": new_start.strftime("%d.%m %H:%M")
                }
                send_whatsapp_message(
                    phone,
                    TEMPLATE_SID,
                    json.dumps(vars, ensure_ascii=False)
                )

    return JsonResponse({
        "success": True,
        "moved_segments_count": len(to_move),
        "appointments_updated": list(touched_appts)
    })