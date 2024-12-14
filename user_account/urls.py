# user_account/urls.py

from django.urls import path
from . import views

app_name = 'user_account'

urlpatterns = [
    path('', views.account_dashboard, name='account_dashboard'),
    path('bookings/', views.manage_bookings, name='manage_bookings'),
    path('bookings/add/', views.add_booking, name='add_booking'),
    path('bookings/salon_masters', views.salon_masters, name='salon_masters'),
    path('barbers/<int:barber_id>/', views.barber_detail, name='barber_detail'),
    path('barbers/<int:barber_id>/edit_field/', views.edit_barber_field, name='edit_barber_field'),
    path('barbers/<int:barber_id>/edit_photo/', views.edit_barber_photo, name='edit_barber_photo'),
    path('barbers/<int:barber_id>/edit_schedule/', views.edit_barber_schedule, name='edit_barber_schedule'),
    path('bookings/edit/<int:booking_id>/', views.edit_booking, name='edit_booking'),
    path('bookings/delete/<int:booking_id>/', views.delete_booking, name='delete_booking'),
    path('get_services_duration_and_price/', views.get_services_duration_and_price, name='get_services_duration_and_price'),
    path('my_account/', views.my_account_view, name='my_account'),

]
