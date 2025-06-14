# C:\Reservon\Reservon\salons\utils.py
from datetime import timedelta
from .models import Salon, BarberAvailability, AppointmentBarberService, ServiceCategory, BarberService
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db.models import Prefetch
from collections import defaultdict
from datetime import datetime, time as dtime
from django.shortcuts import get_object_or_404
from .models import Appointment, Service
import logging
from .errors import ClientError
import json
from reservon.utils.twilio_service import send_whatsapp_message
from authentication.models import PushSubscription
from authentication.utils import get_or_create_user_by_phone
from django.conf import settings
from main.tasks import send_push_notification_task

logger = logging.getLogger('booking')

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

def round_down_to_5(dt):
    """
    Округляет datetime dt вниз до ближайшей отметки кратной 5 минутам.
    Например, 10:52:23 -> 10:50:00.
    """
    return dt - timedelta(
        minutes=dt.minute % 5,
        seconds=dt.second,
        microseconds=dt.microsecond
    )

def is_barber_busy(barber_id, start_dt, end_dt, barber_busy_times):
    """Проверяем пересечение [start_dt, end_dt) с занятыми интервалами барбера."""
    intervals = barber_busy_times.get(barber_id, [])
    for (bs, be) in intervals:
        if bs < end_dt and be > start_dt:
            return True
    return False
# test
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

def load_salon_and_barbers(salon_id):
    salon = Salon.objects.prefetch_related(
        Prefetch('barbers__availabilities', queryset=BarberAvailability.objects.all())
    ).get(id=salon_id)
    return salon, salon.barbers.all()

def get_barber_availability(barbers, day_code):
    return {
        b.id: [
            {
                'start_time': iv.start_time,
                'end_time': iv.end_time,
                'is_available': iv.is_available
            } for iv in b.availabilities.filter(day_of_week=day_code)
        ] for b in barbers
    }

def get_barber_busy_times(salon, date):
    apps = AppointmentBarberService.objects.filter(
        barber__salon=salon,
        start_datetime__date=date
    ).select_related('barber')
    busy = defaultdict(list)
    for app in apps:
        start_local = timezone.localtime(app.start_datetime)
        end_local = timezone.localtime(app.end_datetime)
        busy[app.barber_id].append((start_local, end_local))
    return busy

def compute_active_categories(booking_details, salon_id=None):
    """Return normalized booking details with calculated durations."""
    active = []
    for d in booking_details or []:
        dur_minutes = 0
        for svc in d.get('services', []):
            sid = svc.get('serviceId')
            try:
                if salon_id:
                    serv = Service.objects.get(id=sid, salon_id=salon_id)
                else:
                    serv = Service.objects.get(id=sid)
                dur_minutes += int(serv.duration.total_seconds() // 60)
            except Service.DoesNotExist:
                continue
        if dur_minutes == 0:
            try:
                dur_minutes = int(d.get('duration', 0))
            except (ValueError, TypeError):
                dur_minutes = 0
        active.append({
            'category_id': d.get('categoryId'),
            'services': d.get('services', []),
            'barber_id': d.get('barberId', 'any'),
            'duration': dur_minutes
        })
    return active


def get_candidate_slots(salon_id, date_str, booking_details, total_service_duration, selected_barber_id='any'):
    # Parse date
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return []

    # Load salon & barbers
    try:
        salon, barbers = load_salon_and_barbers(salon_id)
    except Salon.DoesNotExist:
        return []

    day_code = date.strftime('%A').lower()
    availability = get_barber_availability(barbers, day_code)
    busy_times = get_barber_busy_times(salon, date)

    active = compute_active_categories(booking_details, salon_id=salon_id)
    if active:
        duration = sum(c['duration'] for c in active)
    else:
        duration = total_service_duration or salon.default_duration or 30

    # Filter by selected_barber_id if provided
    if selected_barber_id != 'any':
        try:
            sel = int(selected_barber_id)
            barbers = barbers.filter(id=sel)
        except Exception:
            return []

    now = timezone.now()
    start_work, end_work = 9, 21
    slots = []

    # Generate every 5-min slot
    for hour in range(start_work, end_work):
        for minute in range(0, 60, 5):
            naive = datetime.combine(date, dtime(hour, minute))
            slot = timezone.make_aware(naive, timezone.get_current_timezone())
            if slot < now:
                continue

            if active:
                possible = True
                sched = defaultdict(list)
                local = slot
                for cat in active:
                    end_cat = local + timedelta(minutes=cat['duration'])
                    if cat['barber_id'] != 'any':
                        try:
                            b = barbers.get(id=int(cat['barber_id']))
                        except Exception:
                            possible = False
                            break
                        if is_barber_busy(b.id, local, end_cat, busy_times) or \
                           not is_barber_available_in_memory(b, local.time(), end_cat.time(), availability) or \
                           has_overlap(sched[b.id], local, end_cat):
                            possible = False
                            break
                        sched[b.id].append({'start': local, 'end': end_cat})
                    else:
                        if cat['category_id'] in [None, 'any']:
                            candidates = barbers
                        else:
                            try:
                                sc = ServiceCategory.objects.get(id=cat['category_id'])
                                candidates = sc.barbers.filter(salon=salon)
                            except ServiceCategory.DoesNotExist:
                                possible = False
                                break
                        found = False
                        for cb in candidates:
                            if is_barber_busy(cb.id, local, end_cat, busy_times) or \
                               not is_barber_available_in_memory(cb, local.time(), end_cat.time(), availability) or \
                               has_overlap(sched[cb.id], local, end_cat):
                                continue
                            sched[cb.id].append({'start': local, 'end': end_cat})
                            found = True
                            break
                        if not found:
                            possible = False
                            break
                    local = end_cat
                if possible:
                    slots.append(slot)
            else:
                end_slot = slot + timedelta(minutes=duration)
                works = any(
                    is_barber_available_in_memory(b, slot.time(), end_slot.time(), availability)
                    for b in barbers
                )
                conflict = any(
                    slot < be and end_slot > bs
                    for times in busy_times.values() for bs, be in times
                )
                if works and not conflict:
                    slots.append(slot)

    slots.sort()
    return slots

def format_free_ranges(slots):
    if not slots:
        return []
    ranges = []
    start = prev = slots[0]
    for s in slots[1:]:
        if (s - prev).total_seconds() <= 5 * 60:
            prev = s
        else:
            ranges.append((start, prev))
            start = prev = s
    ranges.append((start, prev))
    return ranges


# booking 

def parse_booking_request(request, salon_id):
    logger.debug("parse_booking_request: start")
    

    if request.method != 'POST' or request.headers.get('Content-Type') != 'application/json':
        logger.warning("Invalid request method or content type")
        raise ClientError('Invalid request', status=400)
    try:
        data = json.loads(request.body)
        logger.debug(f"Request data: {data}")
    except json.JSONDecodeError:
        logger.error("Invalid JSON format")
        raise ClientError('Invalid JSON', status=400)
    salon = get_object_or_404(Salon, id=salon_id)
    date, time_str = data.get('date'), data.get('time')
    try:
        dt = datetime.strptime(f"{date} {time_str}", '%Y-%m-%d %H:%M')
    except Exception:
        logger.error("Invalid date/time format")
        raise ClientError('Invalid date/time', status=400)
    start = timezone.make_aware(dt, timezone.get_current_timezone())
    details = data.get('booking_details', [])
    total=0
    if details:
        for d in details:
            for svc in d.get('services', []):
                sid = svc.get('serviceId')
                try:
                    serv = Service.objects.get(id=sid, salon=salon)
                except Service.DoesNotExist:
                    logger.warning(f"Service ID {sid} not found in salon {salon.id}")
                    raise ClientError(f"Service with ID {sid} not found in salon.", status=400)
                total += int(serv.duration.total_seconds() // 60)
    if total == 0:
        total = salon.default_duration or 30
    end = start + timedelta(minutes=total)
    comment = data.get('user_comment', '')
    phone = data.get('phone_number')
    logger.debug(f"Parsed: start={start}, end={end}, total={total}, phone={phone}")
    return salon, data.get('salonMod', 'category'), start, end, details, total, comment, phone


def choose_user(request, phone):
    logger.debug(f"choose_user: phone={phone}")
    if phone:
        user = get_or_create_user_by_phone(phone)[0]
        logger.info(f"Created/found user by phone: {user}")
        return user
    if request.user.is_authenticated:
        logger.info(f"Using authenticated user: {request.user}")
        return request.user
    logger.info("No user authenticated or phone provided")
    return None

def _extract_service_id(svc):
    # Если элемент — dict с ключом serviceId, вернём его, иначе предполагаем, что это уже int
    if isinstance(svc, dict):
        return svc.get('serviceId')
    return svc

def get_nearest_suggestion(salon_id, date_str, chosen_hour, booking_details, total_service_duration, selected_barber_id='any'):
    """
    Возвращает ближайшие слоты до и после выбранног=о часа в формате {'nearest_before': 'HH:MM', 'nearest_after': 'HH:MM'}
    """
    for detail in booking_details:
        # приводим все services к словарям {'serviceId': int}
        normalized = []
        for svc in detail.get('services', []):
            sid = _extract_service_id(svc)
            if sid is None:
                # если вдруг где-то потеряли ID — бросаем клиентскую ошибку
                raise ValueError("Service ID not provided in compute_nearest_suggestion")
            normalized.append({'serviceId': sid})
        detail['services'] = normalized

    slots = get_candidate_slots(salon_id, date_str, booking_details, total_service_duration, selected_barber_id)
    if not slots:
        return {'nearest_before': None, 'nearest_after': None}
    try:
        ref_naive = datetime.strptime(f"{date_str} {int(chosen_hour):02d}:00", '%Y-%m-%d %H:%M')
    except ValueError:
        return {'nearest_before': None, 'nearest_after': None}
    ref_time = timezone.make_aware(ref_naive, timezone.get_current_timezone())
    before = [s for s in slots if s <= ref_time]
    after = [s for s in slots if s >= ref_time]
    nb = max(before) if before else None
    na = min(after) if after else None
    if nb and na and abs((nb - na).total_seconds())/60 < 30:
        na = None
    fmt = '%H:%M'
    return { 'nearest_before': nb.strftime(fmt) if nb else None, 'nearest_after': na.strftime(fmt) if na else None }

def save_appointment(salon, user, start, end, comment, assignments, mode):
    logger.debug("save_appointment: creating appointment record")
    appt = Appointment.objects.create(salon=salon, user=user, start_datetime=start, end_datetime=end, user_comment=comment)
    logger.info(f"Appointment created: {appt.id}")
    for b, s, e, svs in assignments:
        abs_obj = AppointmentBarberService.objects.create(appointment=appt, barber=b, start_datetime=s, end_datetime=e)
        for svc in svs:
            sid = svc.get('serviceId')
            if mode == 'barber':
                bs = BarberService.objects.get(id=sid, barber=b)
                abs_obj.barberServices.add(bs)
                logger.debug(f"Added BarberService {bs.id} to ABS {abs_obj.id}")
            else:
                serv = Service.objects.get(id=sid, salon=salon)
                abs_obj.services.add(serv)
                logger.debug(f"Added Service {serv.id} to ABS {abs_obj.id}")
    return appt

def notify_barbers(appt):
    logger.debug(f"notify_barbers: start for appointment {appt.id}")
    if settings.DEBUG:
        logger.info("notify_barbers skipped in DEBUG")
        return
    notified_ids = set()
    abs_qs = appt.appointmentbarberservice_set.select_related('barber__user')
    unique_barbers = {obj.barber for obj in abs_qs}
    master_names = ", ".join(b.name for b in unique_barbers)
    try:
        user_phone = appt.user.main_profile.phone_number
    except Exception:
        user_phone = "Неизвестен"
    for obj in abs_qs:
        barber = obj.barber
        if barber.id in notified_ids:
            continue
        notified_ids.add(barber.id)
        try:
            profile = barber.user.main_profile
        except Exception:
            logger.warning(f"Profile for barber {barber.id} not found")
            continue
        # WhatsApp notification
        if profile.whatsapp:
            TEMPLATE_SID = "HXa27885cd64b14637a00e845fbbfaa326"
            datetime_str = appt.start_datetime.strftime("%d.%m %H:%M") + "-" + appt.end_datetime.strftime("%H:%M")
            data_vars = {
                "client_phoneNumber": user_phone,
                "datetime": datetime_str,
                "master_name": master_names,
                "admin_number": profile.whatsapp_phone_number
            }
            content_vars = {
                "1": data_vars["datetime"],
                "2": data_vars["master_name"],
                "3": data_vars["client_phoneNumber"]
            }
            vars_str = json.dumps(content_vars, ensure_ascii=False)
            logger.info(f"Sending WhatsApp to {profile.whatsapp_phone_number}")
            try:
                send_whatsapp_message(profile.whatsapp_phone_number, TEMPLATE_SID, vars_str)
            except Exception as e:
                logger.error(f"Error sending WhatsApp to {barber.id}: {e}")
        # Push notifications
        if profile.push_subscribe:
            subs = PushSubscription.objects.filter(user=barber.user)
            for sub in subs:
                sub_info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}
                payload = {
                    "head": "Новое бронирование",
                    "body": f"Пользователь забронировал услугу у {barber.name}.",
                    "icon": "/static/main/img/notification-icon.png",
                    "url": "/user-account/bookings/"
                }
                logger.info(f"Queue push for barber {barber.id}")
                try:
                    send_push_notification_task.delay(sub_info, json.dumps(payload))
                except Exception as e:
                    logger.error(f"Error sending push to {barber.id}: {e}")
    logger.debug("notify_barbers: done")


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
