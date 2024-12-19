# authentication/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView

app_name = 'authentication'

urlpatterns = [
    path('login/', views.login_view, name='login_ajax'),
    path('load_modal/', views.load_modal, name='load_modal'),
    path('get_form/', views.get_form, name='get_form'),
    path('verify_code/', views.verify_code, name='verify_code'),
    path('set_password/', views.set_password, name='set_password'),
    path('enter_password/', views.enter_password, name='enter_password'),
    path('resend_verification_code/', views.resend_verification_code, name='resend_verification_code'),
    path('logout/', views.custom_logout_view, name='logout'),
    path('clear-cache/', views.clear_cache_view, name='clear_cache'),
]
