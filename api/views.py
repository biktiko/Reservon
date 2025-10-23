# C:\Reservon\Reservon\api\views.py
from rest_framework.decorators import api_view, permission_classes
from .utils import subtract_intervals, merge_intervals
from salons.utils import get_barber_busy_times, get_barber_availability, _parse_local
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
    SalonSerializer, SalonDetailSerializer, PlatformPartnerSerializer
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
def api_platform_partners_list(request, partner_id):
    """
    Returns a list of active sub-partners for a given platform partner ID.
    Filters by reservon_partner_id and jackbot_AI_mod=True.
    """
    salons = Salon.objects.filter(
        reservon_partner_id=partner_id,
        status='active',
        jackbot_AI_mod=True
    ).prefetch_related('services') # Оптимизируем запрос для получения услуг
    
    if not salons.exists():
        return Response(
            {'error': f'No active partners found for platform ID {partner_id} or platform does not exist.'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = PlatformPartnerSerializer(salons, many=True)
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
    Returns available booking start time intervals in "HH:MM-HH:MM, ..." format.
    """
    data = request.data
    rs = _parse_local(data.get('range_start', ''))
    re = _parse_local(data.get('range_end', ''))
    if not rs or not re or rs >= re:
        return Response({'error': 'Invalid range_start/range_end'}, status=400)

    # Filter by barbers
    barber_ids = data.get('barber_ids', 'any')
    if barber_ids == 'any':
        barbers = Barber.objects.filter(salon_id=salon_id)
    else:
        if not isinstance(barber_ids, list):
            return Response({'error': 'barber_ids must be a list or "any"'}, status=400)
        barbers = Barber.objects.filter(id__in=barber_ids)

    # --- Duration Calculation Logic ---
    # Implements a priority system for determining the required appointment duration.
    svc_ids = data.get('service_ids', 'any')
    duration_param = data.get('duration')
    total_duration = 0 # Initialize to prevent UnboundLocalError

    # Priority 1: Use service_ids if it's a valid list. This has the highest precedence.
    if isinstance(svc_ids, list) and svc_ids:
        for sid in svc_ids:
            try:
                svc = Service.objects.get(id=sid)
                total_duration += int(svc.duration.total_seconds() // 60)
            except Service.DoesNotExist:
                return Response({'error': f'Service {sid} not found'}, status=400)

    # Priority 2: Use the 'duration' parameter if service_ids is not used.
    elif duration_param is not None:
        try:
            total_duration = int(duration_param)
            if total_duration <= 0:
                return Response({'error': 'duration must be a positive number'}, status=400)
        except (ValueError, TypeError):
            return Response({'error': 'duration must be a valid integer'}, status=400)

    # Priority 3: Fallback to a default value if neither of the above is provided.
    else:
        total_duration = 30 # Default to 30 minutes

    # --- End of Duration Logic ---

    # Get busy schedules and availability for the requested day
    salon = Salon.objects.get(id=salon_id)
    day_code = rs.strftime('%A').lower()
    busy_map = get_barber_busy_times(salon, rs.date())      # {barber_id: [(start, end), ...]}
    avail_map = get_barber_availability(barbers, day_code)  # {barber.id: [Availability, ...]}

    free_all = []
    for barber in barbers:
        # Build a list of available intervals within the requested range_start-range_end window
        avails = []
        for av in avail_map.get(barber.id, []):
            # av is a dict with 'start_time', 'end_time', 'is_available' keys
            if not av.get('is_available', True):
                continue

            start_time = av['start_time']
            end_time   = av['end_time']

            start = timezone.make_aware(datetime.combine(rs.date(), start_time), timezone.get_current_timezone())
            end = timezone.make_aware(datetime.combine(rs.date(), end_time), timezone.get_current_timezone())
            
            # Trim the interval to fit within the requested start/end range
            if end <= rs or start >= re:
                continue
            avails.append((max(start, rs), min(end, re)))

        # Get the busy intervals for the current barber
        busys = busy_map.get(barber.id, [])

        # Subtract busy intervals from available intervals
        free = subtract_intervals(avails, busys)

        # If a duration is set, filter out intervals that are shorter than total_duration
        if total_duration > 0:
            tmp = []
            for s, e in free:
                if (e - s).total_seconds() / 60 >= total_duration:
                    # Valid start times are from the beginning of the slot up to (end - duration)
                    tmp.append((s, e - timedelta(minutes=total_duration)))
            free = tmp

        free_all.extend(free)

    # Merge all free intervals from all barbers to find the total time range where at least one barber is free
    merged = merge_intervals(free_all)

    # Format the output string
    parts = [
        f"{interval[0].strftime('%H:%M')}-{interval[1].strftime('%H:%M')}"
        for interval in merged
    ]
    return Response({'free_ranges': ", ".join(parts)})

    # Add this new API wrapper to api/views.py

@api_view(['POST'])
def api_check_availability(request, salon_id):
    """
    API endpoint wrapper for the availability check function.
    """
    from salons.views import check_availability_and_suggest
    django_request = request._request
    django_response = check_availability_and_suggest(django_request, id=salon_id)
    
    # This logic safely returns the JSON response from our function
    if isinstance(django_response, JsonResponse):
        content_dict = json.loads(django_response.content)
        return Response(content_dict, status=django_response.status_code)
    
    return django_response

@api_view(['POST'])
@permission_classes([AllowAny])
def api_events_create_booking(request):
    """
    Proxy to events.views.create_booking (JSON in -> JSON out).
    """
    django_request = request._request
    from events.views import create_booking as events_create_booking

    django_response = events_create_booking(django_request)

    if isinstance(django_response, JsonResponse):
        try:
            data = json.loads(django_response.content)
        except Exception:
            data = json.loads(django_response.content.decode('utf-8'))
        return Response(data, status=django_response.status_code)

    return django_response