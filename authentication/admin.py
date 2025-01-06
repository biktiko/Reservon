from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User
from .models import Profile
from main.admin import NoteInline
# Отмена регистрации стандартного UserAdmin
admin.site.unregister(User)

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fk_name = 'user'
    fields = ('phone_number', 'status','login_method', 'google_uid', 'whatsapp', 'push_subscribe', 'whatsapp_phone_number', 'avatar') 
    extra = 0

class CustomUserAdmin(DefaultUserAdmin):
    list_display = DefaultUserAdmin.list_display + ('has_password', 'profile_status')
    list_filter = DefaultUserAdmin.list_filter + ('main_profile__status',)
    search_fields = DefaultUserAdmin.search_fields + ('main_profile__phone_number',)
    inlines = (ProfileInline, NoteInline)

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Если это новый объект
            obj.set_unusable_password()  # Устанавливает, что у пользователя нет пароля
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        if formset.model == Profile:
            instances = formset.save(commit=False)
            for instance in instances:
                instance.save()
            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)

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

admin.site.register(User, CustomUserAdmin)
