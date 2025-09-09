# C:\Reservon\Reservon\api\views.py
from rest_framework.decorators import api_view, permission_classes
from .utils import _parse_local, subtract_intervals, merge_intervals
from salons.utils import get_barber_busy_times, get_barber_availability
from salons.models import Barber, Service
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from salons.models import Salon
from django.utils import timezone
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from .serializers import (
    SalonSerializer, SalonDetailSerializer,
)
import json
import logging


logger = logging.getLogger('booking')

# Get the custom User model
User = get_user_model()

@api_view(['GET'])
@permission_classes([AllowAny])
def api_salons_list(request):
    """
    Returns list of active salons or filtered by 'q'.
    """
    query = request.GET.get('q', '')
    if query:
        # Ensure we filter only active salons
        salons = Salon.objects.filter(
            (Q(name__icontains=query) | Q(address__icontains=query)) & Q(status='active')
        )
    else:
        salons = Salon.objects.filter(status='active')
    serializer = SalonSerializer(salons, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_salon_detail(request, salon_id):
    """
    Returns detailed info about a salon (categories, services, barbers).
    """
    salon = get_object_or_404(Salon, id=salon_id, status='active')
    serializer = SalonDetailSerializer(salon)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
def api_create_booking(request, salon_id):
    django_request = request._request

    from salons.views import book_appointment
    django_response = book_appointment(django_request, id=salon_id)
    
    if isinstance(django_response, JsonResponse):
        # Django JsonResponse => content is a bytes with JSON
        content_dict = json.loads(django_response.content)
        return Response(content_dict, status=django_response.status_code)
    # Иначе return django_response
    return django_response


@api_view(['POST'])
def api_get_available_minutes(request):
    # DRF Request -> Django HttpRequest
    django_request = request._request  

    # Возможные случаи, если старая вьюшка ожидает request.POST:
    # нужно подложить в django_request.POST нужные данные (не всегда обязательно).
    # django_request.POST = request.data  # иногда может помочь, если в старой вьюшке используется request.POST[...]
    from salons.views import get_available_minutes as get_available_minutes_view
    response = get_available_minutes_view(django_request)

    if isinstance(response, JsonResponse):
        return Response(response.json(), status=response.status_code)
    return response

@api_view(['POST'])
def api_get_nearest_available_time(request):
    # DRF Request -> Django HttpRequest
    django_request = request._request  

    # Возможные случаи, если старая вьюшка ожидает request.POST:
    # нужно подложить в django_request.POST нужные данные (не всегда обязательно).
    # django_request.POST = request.data  # иногда может помочь, если в старой вьюшке используется request.POST[...]
    from salons.views import get_nearest_suggestion as get_nearest_available_time_view
    response = get_nearest_available_time_view(django_request)

    if isinstance(response, JsonResponse):
        return Response(response.json(), status=response.status_code)
    return response

@csrf_exempt
@api_view(['POST'])
def admin_verify(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Метод не поддерживается'}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Некорректный JSON'}, status=400)

    phone_number = data.get('phone_number')
    if not phone_number:
        return JsonResponse({'success': False, 'error': 'Телефон не указан'}, status=400)
    
    phone_number = phone_number.strip()
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    try:
        # Поиск пользователя по полю phone_number в связанном профиле main_profile
        user = User.objects.get(main_profile__phone_number=phone_number)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Пользователь не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    salons = user.administered_salons.all()
    salons_list = [{'id': salon.id, 'name': salon.name} for salon in salons]
    
    if not salons_list:
        return JsonResponse({'success': False, 'error': 'Пользователь не является администратором ни одного салона'}, status=403)
    
    return JsonResponse({'success': True, 'salons': salons_list})

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def api_reschedule_appointments(request, salon_id):
    """
    Вызов стандартного salons.views.reschedule_appointments
    и адаптация JsonResponse → DRF Response.
    """
    # конвертируем DRF Request → Django HttpRequest
    django_request = request._request

    # импортируем оригинальную функцию
    from salons.views import reschedule_appointments as drf_view

    # вызываем её
    django_response = drf_view(django_request, salon_id)

    # если возвратили JsonResponse — оборачиваем в DRF Response
    if isinstance(django_response, JsonResponse):
        data = json.loads(django_response.content)
        return Response(data, status=django_response.status_code)

    # иначе отдаём «как есть» (HttpResponse, Redirect и т.п.)
    return django_response

@api_view(['POST'])
@permission_classes([AllowAny])
def api_free_ranges(request, salon_id):
    """
    Возвращает свободные интервалы стартов записи в формате "HH:MM-HH:MM, ...".
    """
    data = request.data
    rs = _parse_local(data.get('range_start', ''))
    re = _parse_local(data.get('range_end', ''))
    if not rs or not re or rs >= re:
        return Response({'error': 'Invalid range_start/range_end'}, status=400)

    # фильтр по мастерам
    barber_ids = data.get('barber_ids', 'any')
    if barber_ids == 'any':
        barbers = Barber.objects.filter(salon_id=salon_id)
    else:
        if not isinstance(barber_ids, list):
            return Response({'error': 'barber_ids must be list or "any"'}, status=400)
        barbers = Barber.objects.filter(id__in=barber_ids)

    # вычисляем общую длительность услуг (в минутах)
    svc_ids = data.get('service_ids', 'any')
    total_duration = 0
    if svc_ids != 'any':
        if not isinstance(svc_ids, list):
            return Response({'error': 'service_ids must be list or "any"'}, status=400)
        total_duration = 0
        for sid in svc_ids:
            try:
                svc = Service.objects.get(id=sid)
                total_duration += int(svc.duration.total_seconds() // 60)
            except Service.DoesNotExist:
                return Response({'error': f'Service {sid} not found'}, status=400)
    else:
        # Устанавливаем минимальную длительность по умолчанию, если услуги не указаны
        total_duration = 30

    # получаем занятости и доступности на этот день
    salon = Salon.objects.get(id=salon_id)
    day_code = rs.strftime('%A').lower()
    busy_map = get_barber_busy_times(salon, rs.date())       # { barber_id: [(s,e),...] }
    avail_map = get_barber_availability(barbers, day_code)   # { barber.id: [Availability,...] }

    free_all = []
    for barber in barbers:
        # строим список доступных интервалов в рамках range_start-range_end
        avails = []
        for av in avail_map.get(barber.id, []):
            # av — это dict с ключами 'start_time', 'end_time', 'is_available'
            if not av.get('is_available', True):
                continue

            start_time = av['start_time']
            end_time   = av['end_time']

            start = timezone.make_aware(
                datetime.combine(rs.date(), start_time),
                timezone.get_current_timezone()
            )
            end = timezone.make_aware(
                datetime.combine(rs.date(), end_time),
                timezone.get_current_timezone()
            )
            # обрезаем по rs/re
            if end <= rs or start >= re:
                continue
            avails.append((max(start, rs), min(end, re)))

        # busy-интервалы
        busys = busy_map.get(barber.id, [])

        # вычитаем занятости из доступности
        free = subtract_intervals(avails, busys)

        # если заданы услуги — оставляем только интервалы >= total_duration
        if total_duration > 0:
            tmp = []
            for s, e in free:
                if (e - s).total_seconds() / 60 >= total_duration:
                    # допустимые старты: [s ... e - duration]
                    tmp.append((s, e - timedelta(minutes=total_duration)))
            free = tmp

        free_all.extend(free)

    # сливаем интервалы по всем мастерам (объединённая зона, где хотя бы один свободен)
    merged = merge_intervals(free_all)

    # форматируем
    parts = [
        f"{interval[0].strftime('%H:%M')}-{interval[1].strftime('%H:%M')}"
        for interval in merged
    ]
    return Response({'free_ranges': ", ".join(parts)})