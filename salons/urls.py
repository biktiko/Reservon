# salons/urls.py
from django.urls import path
from . import views

app_name = 'salons'

urlpatterns = [
    path('', views.main, name='salons_main'), 
    path('<int:id>/', views.salon_detail, name='salon_detail'),
    path('get_barber_availability/<int:barber_id>/', views.get_barber_availability, name='get_barber_availability'),
    path('<int:id>/book/', views.book_appointment, name='book_appointment'),
    path('get_available_minutes/', views.get_available_minutes, name='get_available_minutes'),
    path('get_nearest_available_time/', views.get_nearest_available_time, name='get_nearest_available_time'),
    path('reschedule_appointments/<int:salon_id>/', views.reschedule_appointments, name='reschedule_appointments'),

    path(
        'whatsapp/callback/',
        views.whatsapp_callback,
        name='whatsapp_callback'
    ),
]
