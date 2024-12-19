# C:\Reservon\Reservon\main\models.py
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
# from webpush.models import WebPushDevice

class VerificationCode(models.Model):
    phone_number = models.CharField(max_length=20)
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        from django.utils import timezone
        expiration_time = self.created_at + timezone.timedelta(minutes=10)  # Код действует 10 минут
        return timezone.now() > expiration_time

    def __str__(self):
        return f"{self.phone_number} - {self.code}"

# class User(AbstractUser):
#     # Дополнительные поля, если необходимо
#     pass

# Необходимо также убедиться, что WebPushDevice связан с правильной моделью пользователя
# WebPushDevice._meta.get_field('user').related_model = User