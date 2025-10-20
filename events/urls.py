
from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('api/create_booking/', views.create_booking, name='create_booking'),
]
