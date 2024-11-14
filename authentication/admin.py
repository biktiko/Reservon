from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User
from .models import Profile

# Отмена регистрации стандартного UserAdmin
admin.site.unregister(User)

# Создание кастомного UserAdmin с дополнительными колонками
class CustomUserAdmin(DefaultUserAdmin):
    list_display = DefaultUserAdmin.list_display + ('has_password', 'profile_status')
    list_filter = DefaultUserAdmin.list_filter + ('main_profile__status',)
    search_fields = DefaultUserAdmin.search_fields + ('main_profile__phone_number',)

    def has_password(self, obj):
        return obj.has_usable_password()
    has_password.boolean = True
    has_password.short_description = 'Has Password'

    def profile_status(self, obj):
        try:
            return obj.main_profile.status
        except Profile.DoesNotExist:
            return 'No Profile'
    profile_status.short_description = 'Profile Status'
    profile_status.admin_order_field = 'main_profile__status'


# Регистрация кастомного UserAdmin
admin.site.register(User, CustomUserAdmin)
