# salons/admin.py

from django.contrib import admin
from django import forms
from .models import (
    Salon,
    Service,
    SalonImage,
    Barber,
    BarberService,
    BarberAvailability,
    ServiceCategory,
    Appointment,
    AppointmentBarberService,
)
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from main.admin import NoteInline

# --- Настройка админки для AppointmentBarberService ---

class AppointmentBarberServiceInline(admin.TabularInline):
    model = AppointmentBarberService
    extra = 1
    fields = ('barber', 'services', 'barberServices', 'start_datetime', 'end_datetime')
    filter_horizontal = ('services',)

# Настройка админки для модели Appointment
@admin.register(Appointment)
class AppointmentAdmin(ImportExportModelAdmin):
    list_display = ('salon', 'user', 'start_datetime', 'end_datetime', 'get_barbers_services', 'user_comment', 'created_at')
    list_filter = ('salon', 'user')
    search_fields = ('salon__name', 'user__username')
    inlines = [AppointmentBarberServiceInline, NoteInline]

    def get_barbers_services(self, obj):
        result = []
        for item in obj.barber_services.all():
            barber_name = item.barber.name if item.barber else 'Любой мастер'
            services = ", ".join([service.name for service in item.services.all()])
            result.append(f"{barber_name}: {services}")
        return "; ".join(result)
    get_barbers_services.short_description = 'Мастер и услуги'

# --- Настройка админки для SalonImage ---

class SalonImageInline(admin.TabularInline):
    model = SalonImage
    extra = 1

# --- Настройка админки для Service ---

class ServiceResource(resources.ModelResource):
    class Meta:
        model = Service
        fields = ('id', 'name', 'price', 'duration', 'salon__name', 'category__name', 'status')

@admin.register(Service)
class ServiceAdmin(ImportExportModelAdmin):
    resource_class = ServiceResource
    list_display = ('name', 'price', 'duration', 'salon', 'category', 'status')
    list_filter = ('salon', 'category', 'status')
    search_fields = ('name',)
    autocomplete_fields = ['salon', 'category']
    actions = ['make_active', 'make_suspend']

    def make_active(self, request, queryset):
        queryset.update(status='active')
    make_active.short_description = 'Пометить выбранные услуги как активные'

    def make_suspend(self, request, queryset):
        queryset.update(status='suspend')
    make_suspend.short_description = 'Пометить выбранные услуги как приостановленные'

class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1
    autocomplete_fields = ['category']
    show_change_link = True


# --- Настройка админки для ServiceCategory ---

class ServiceCategoryServiceInline(admin.TabularInline):
    model = Service
    extra = 1
    autocomplete_fields = ['salon']
    show_change_link = True

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_duration')
    search_fields = ('name',)
    inlines = [ServiceCategoryServiceInline]

# --- Настройка админки для Barber ---

# Форма для модели Barber с использованием стандартного виджета Textarea
from authentication.models import Profile  # Ensure correct import path
class BarberAdminForm(forms.ModelForm):
    # Fields from the Profile model
    profile_phone_number = forms.CharField(
        label='Phone Number',
        max_length=15,
        required=False
    )
    profile_avatar = forms.ImageField(
        label='Profile Avatar',
        required=False
    )
    profile_status = forms.ChoiceField(
        label='Profile Status',
        choices=Profile.STATUS_CHOICES,
        required=False
    )
    # Add more Profile fields as needed

    class Meta:
        model = Barber
        fields = '__all__'  # Include all Barber fields

    def __init__(self, *args, **kwargs):
        super(BarberAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.user and hasattr(self.instance.user, 'main_profile'):
            profile = self.instance.user.main_profile
            self.fields['profile_phone_number'].initial = profile.phone_number
            self.fields['profile_avatar'].initial = profile.avatar
            self.fields['profile_status'].initial = profile.status
            # Initialize other Profile fields as needed

    def save(self, commit=True):
        barber = super(BarberAdminForm, self).save(commit=False)
        user = barber.user

        # Save Barber first
        if commit:
            barber.save()

        # Handle Profile
        profile_phone_number = self.cleaned_data.get('profile_phone_number')
        profile_avatar = self.cleaned_data.get('profile_avatar')
        profile_status = self.cleaned_data.get('profile_status')
        # Retrieve or create Profile
        if user:
            profile, created = Profile.objects.get_or_create(user=user)
            if profile_phone_number:
                profile.phone_number = profile_phone_number
            if profile_avatar:
                profile.avatar = profile_avatar
            if profile_status:
                profile.status = profile_status
            # Update other Profile fields as needed
            profile.save()

        return barber
class BarberAvailabilityInline(admin.TabularInline):
    model = BarberAvailability
    extra = 1
    fields = ('day_of_week', 'start_time', 'end_time', 'is_available')

class BarberServiceInline(admin.TabularInline):
    model = BarberService
    extra = 1
    fields = ('name', 'image', 'price', 'duration', 'category', 'status')
    show_change_link = True


@admin.register(Barber)
class BarberAdmin(ImportExportModelAdmin):
    form = BarberAdminForm
    list_display = ('user', 'name', 'salon', 'get_categories', 'get_services', 'get_barber_services_names')
    list_filter = ('salon', 'categories')
    search_fields = ('name', 'salon__name')
    filter_horizontal = ('categories', 'services')
    autocomplete_fields = ['salon', 'categories', 'user']
    fields = ('salon', 'user', 'name', 'avatar', 'description', 'categories', 'services')
    inlines = [BarberAvailabilityInline, BarberServiceInline]

    def get_categories(self, obj):
        return ", ".join([category.name for category in obj.categories.all()])
    get_categories.short_description = 'Категории'

    def get_services(self, obj):
        """Услуги из модели Service, которые привязаны к барберу в режиме category."""
        return ", ".join([service.name for service in obj.services.all()])
    get_services.short_description = 'Услуги (category)'

    def get_barber_services_names(self, obj):
        """Услуги из модели BarberService, которые используются в режиме barber."""
        names = [bs.name for bs in obj.barber_services.all()]
        return ", ".join(names)
    get_barber_services_names.short_description = 'Услуги барбера (barber)'


@admin.register(BarberAvailability)
class BarberAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('barber', 'day_of_week', 'start_time', 'end_time', 'is_available')
    list_filter = ('barber', 'day_of_week', 'is_available')
    search_fields = ('barber__name',)    

# --- Настройка админки для Salon ---

# Форма для модели Salon с использованием стандартного виджета Textarea
class SalonAdminForm(forms.ModelForm):
    class Meta:
        model = Salon
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(SalonAdminForm, self).__init__(*args, **kwargs)
        # Опционально: Ограничьте доступных администраторов, например, только активные пользователи
        # self.fields['admins'].queryset = User.objects.filter(is_active=True)

class BarberInline(admin.StackedInline):
    model = Barber
    extra = 1
    fields = ('name', 'avatar', 'description', 'categories')
    filter_horizontal = ('categories',)
    autocomplete_fields = ['categories']

@admin.register(Salon)
class SalonAdmin(ImportExportModelAdmin):
    form = SalonAdminForm
    # Используем метод display_admins вместо поля admins
    list_display = ('name', 'status', 'address', 'telegram_status', 'mod')
    list_filter = ('status', 'mod')
    search_fields = ('name', 'address')
    inlines = [ServiceInline, SalonImageInline, BarberInline, NoteInline]
    autocomplete_fields = ['admins']
    fieldsets = (
        (None, {
            'fields': ('name', 'logo', 'address', 'coordinates')
        }),
        ('Descriptions', {
            'fields': (
                'shortDescription_hy', 'shortDescription_ru', 'shortDescription_eng',
                'description_hy', 'description_ru', 'description_eng'
            )
        }),
        ('Telegram settings', {
            'fields': ('telegram_status', 'telegram_appointmentMod', 'telegram_barbersMod')
        }),
        ('Salon settings', {
            'fields': ('appointment_mod', 'reservDays', 'admins', 'IsCheckDays', 'mod', 'default_duration', 'default_price', 'status')
        })
    )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'admins':
            # Uncomment the next line to restrict the queryset:
            # kwargs['queryset'] = User.objects.filter(is_staff=True, is_active=True)
            pass
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def display_admins(self, obj):
        # Return a comma-separated list of admins
        return ", ".join([str(admin) for admin in obj.admins.all()])
    display_admins.short_description = "Admins"

# --- Настройка админки для SalonImage ---

@admin.register(SalonImage)
class SalonImageAdmin(admin.ModelAdmin):
    list_display = ('salon', 'upload_date')
    list_filter = ('salon',)
    search_fields = ('salon__name',)

# --- Регистрация модели AppointmentBarberService ---

@admin.register(AppointmentBarberService)
class AppointmentBarberServiceAdmin(ImportExportModelAdmin):
    list_display = ('appointment', 'barber', 'start_datetime', 'end_datetime')
    search_fields = ('appointment__salon__name', 'barber__name')
    filter_horizontal = ('services',)
    autocomplete_fields = ['appointment', 'barber', 'services']
