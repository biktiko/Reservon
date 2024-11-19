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
    last_verification_sent_at = models.DateTimeField(null=True, blank=True)  # Новое поле


    def __str__(self):
        return f"{self.user.first_name} ({self.phone_number})"

    
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

        
# Форма для модели Profile (если требуется)
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fk_name = 'user'

# Кастомный UserAdmin с дополнительными колонками
class CustomUserAdmin(DefaultUserAdmin):
    inlines = (ProfileInline,)
    list_display = DefaultUserAdmin.list_display + ('has_password', 'profile_status')
    list_filter = DefaultUserAdmin.list_filter + ('profile__status',)
    search_fields = DefaultUserAdmin.search_fields + ('profile__phone_number',)

    def has_password(self, obj):
        return obj.has_usable_password()
    has_password.boolean = True
    has_password.short_description = 'Has Password'

    def profile_status(self, obj):
        try:
            return obj.profile.status
        except Profile.DoesNotExist:
            return 'No Profile'
    profile_status.short_description = 'Profile Status'
    profile_status.admin_order_field = 'profile__status'

# Отмена регистрации стандартного UserAdmin
admin.site.unregister(User)

# Регистрация кастомного UserAdmin
admin.site.register(User, CustomUserAdmin)