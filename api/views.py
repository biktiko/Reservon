# api/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta, time as dt_time
from salons.models import Salon
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