# salons/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='salons_main'), 
    path('<int:id>/', views.salon_detail, name='salon_detail'),
    path('get_barber_availability/<int:barber_id>/', views.get_barber_availability, name='get_barber_availability'),
    path('<int:id>/book/', views.book_appointment, name='book_appointment'),
    path('get_available_minutes/', views.get_available_minutes, name='get_available_minutes'),
]
