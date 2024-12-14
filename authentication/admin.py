from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User
from .models import Profile

# Отмена регистрации стандартного UserAdmin
admin.site.unregister(User)

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fk_name = 'user'
    fields = ('phone_number', 'status', 'notes', 'login_method', 'google_uid') 
    extra = 0

class CustomUserAdmin(DefaultUserAdmin):
    inlines = (ProfileInline,)
    list_display = DefaultUserAdmin.list_display + ('has_password', 'profile_status', 'get_notes')
    list_filter = DefaultUserAdmin.list_filter + ('main_profile__status',)
    search_fields = DefaultUserAdmin.search_fields + ('main_profile__phone_number',)

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

    def get_notes(self, obj):
        try:
            return obj.main_profile.notes
        except Profile.DoesNotExist:
            return 'No Notes'
    get_notes.short_description = 'Notes'

admin.site.register(User, CustomUserAdmin)
