# C:\Reservon\Reservon\authentication\models.py
from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

class Profile(models.Model):
    STATUS_CHOICES = [
        ('unverified', 'Unverified'),
        ('verified', 'Verified'),
        ('suspended', 'Suspended'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='main_profile')
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unverified')
    last_verification_sent_at = models.DateTimeField(null=True, blank=True) 
    notes = models.TextField('Notes', blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name} ({self.phone_number})"
        
# Кастомный UserAdmin с дополнительными колонками


# class VerificationCode(models.Model):
#     phone_number = models.CharField(max_length=20)
#     code = models.CharField(max_length=4)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def is_expired(self):
#         from django.utils import timezone
#         expiration_time = self.created_at + timezone.timedelta(minutes=10)  # Код действует 10 минут
#         return timezone.now() > expiration_time

#     def __str__(self):
#         return f"{self.phone_number} - {self.code}"
