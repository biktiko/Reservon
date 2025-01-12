from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User
from .models import Profile
from main.admin import NoteInline
from .forms import CustomUserCreationForm, CustomUserChangeForm

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
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm

    list_display = DefaultUserAdmin.list_display + ('has_password', 'profile_status')
    list_filter = DefaultUserAdmin.list_filter + ('main_profile__status',)
    search_fields = DefaultUserAdmin.search_fields + ('main_profile__phone_number',)
    inlines = (ProfileInline, NoteInline, )

    # Поля при создании (add_view)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'first_name',
                'last_name',
                'password1',
                'password2',   # <-- Нужно чтобы задавать пароль
                'is_staff',
                'is_active'
            ),
        }),
    )

    # Поля при редактировании (change_view) Django берёт из form = CustomUserChangeForm
    fieldsets = (
        (None, {
            'fields': (
                'username',
                'password',   # поле пароль всё равно нужно, даже если хэш
                'email',
                'first_name',
                'last_name',
            )
        }),
        ('Права', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            ),
        }),
    )

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
admin.site.register(Profile)