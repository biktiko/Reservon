# C:\Reservon\Reservon\main\models.py
from django.db import models

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
