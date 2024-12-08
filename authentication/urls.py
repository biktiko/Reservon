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
    path('verify_code/', views.verify_code, name='verify_code'),  # Добавлено
    path('set_password/', views.set_password, name='set_password'),  # Добавлено
    path('enter_password/', views.enter_password, name='enter_password'),  # Добавлено
    path('resend_verification_code/', views.resend_verification_code, name='resend_verification_code'),  # Добавлено
    path('logout/', views.custom_logout_view, name='logout'),  # Используем кастомное представление
    # path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # path('logout/', LogoutView.as_view(next_page='/'), name='logout'),

]
