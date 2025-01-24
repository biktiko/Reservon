# api/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from django.db.models import Q, Prefetch
from django.http import JsonResponse
from django.core.cache import cache
from collections import defaultdict
from datetime import datetime, timedelta, time as dt_time
from salons.models import (
    Salon, Service, ServiceCategory, Barber,
    Appointment, AppointmentBarberService, BarberAvailability
)
from .serializers import (
    SalonSerializer, SalonDetailSerializer,
    CreateBookingSerializer
)
import logging
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger('booking')


from salons.views import (
    is_barber_available_in_memory,
    generate_safe_cache_key
)

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
    # Просто вызываем вашу существующую логику
    from salons.views import book_appointment
    response = book_appointment(request, id=salon_id)
    
    # Если возвращается JsonResponse, можно сконвертировать в DRF Response
    if isinstance(response, JsonResponse):
        return Response(response.json(), status=response.status_code)
    
    return response

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

