# salons/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='salons_main'),  # Маршрут со списком салонов
    path('<int:id>/', views.salon_detail, name='salon_detail'),
    path('<int:salon_id>/services/', views.salon_services, name='salon_services'),
    path('<int:id>/book/', views.book_appointment, name='book_appointment'),
]
