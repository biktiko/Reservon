# api/urls.py
from django.urls import path
from .views import (
    api_salons_list,
    api_salon_detail,
    api_create_booking,
    api_get_available_minutes,
    api_get_nearest_available_time,
    admin_verify,
    api_reschedule_appointments,
    api_free_ranges,
    api_check_slot_availability
)

urlpatterns = [
    path('salons/', api_salons_list, name='api_salons_list'),
    path('salons/<int:salon_id>/', api_salon_detail, name='api_salon_detail'),
    path('salons/<int:salon_id>/book/', api_create_booking, name='api_create_booking'),
    path('salons/<int:salon_id>/check_slot/', api_check_slot_availability, name='api_check_slot_availability'),
    path('salons/availability/', api_get_available_minutes, name='api_salon_availability'),
    path('salons/get_nearest_available_time/', api_get_nearest_available_time, name='api_salon_availability'),
    path('salons/<int:salon_id>/reschedule/', api_reschedule_appointments, name='api_reschedule'),
    path('salons/<int:salon_id>/free_ranges/', api_free_ranges ,name='api_free_ranges'),
    path('admin/verify/', admin_verify, name='admin_verify'),
]