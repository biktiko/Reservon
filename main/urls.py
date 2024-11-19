# C:\Reservon\Reservon\main\urls.py
from django.urls import path
from . import views


urlpatterns = [
    path('', views.main, name='main'),
    path('about/', views.about, name='about'),
    path('contact/', views.contacts, name='contacts'),
    path('search/', views.search_salons, name='search_salons'),
]