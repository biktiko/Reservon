# C:\Reservon\Reservon\main\urls.py
from django.urls import path
from . import views


urlpatterns = [
    path('', views.main),
    path('about/', views.about),
    path('contact/', views.contacts),
]