# account/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.account_dashboard, name='account_dashboard'),
    path('bookings/', views.manage_bookings, name='manage_bookings'),
    path('bookings/add/', views.add_booking, name='add_booking'),  # Новый маршрут для добавления бронирования
    path('bookings/edit/<int:booking_id>/', views.edit_booking, name='edit_booking'),
    path('bookings/delete/<int:booking_id>/', views.delete_booking, name='delete_booking'),
]
