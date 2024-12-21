# C:\Reservon\Reservon\main\urls.py
from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.main, name='main'),
    path('about/', views.about, name='about'),
    path('contact/', views.contacts, name='contacts'),
    path('search/', views.search_salons, name='search_salons'),
    path('subscribe_push/', views.subscribe_push, name='subscribe_push'),
    path('unsubscribe_push/', views.unsubscribe_push, name='unsubscribe_push'),
    # path('subscribe_push/', views.send_push_notification, name='subscribe_push'),
    
]