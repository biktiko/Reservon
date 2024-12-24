# C:\Reservon\Reservon\authentication\models.py
from django.db import models
from django.contrib.auth.models import User
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
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    login_method = models.CharField(max_length=20, choices=[('password', 'Password'), ('google', 'Google')])
    google_uid = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} ({self.phone_number})"

class PushSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions', null=True, blank=True)
    endpoint = models.URLField(unique=True, max_length=1000)  # Увеличьте длину поля
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.endpoint
