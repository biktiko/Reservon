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
    list_display = ('id', 'salon', 'user', 'start_datetime', 'end_datetime', 'get_barbers_services', 'user_comment', 'created_at')
    list_filter = ('salon', 'user', 'start_datetime', 'created_at')
    search_fields = ('id', 'salon__name', 'user__username', 'user_comment')
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
    list_display = ('id', 'name', 'price', 'duration', 'salon', 'category', 'status')
    list_filter = ('salon', 'category', 'status')
    search_fields = ('id', 'name', 'salon__name', 'category__name', 'status')
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
    fields = ('name', 'image', 'description', 'price', 'duration', 'category', 'status')
    show_change_link = True


@admin.register(Barber)
class BarberAdmin(ImportExportModelAdmin):
    form = BarberAdminForm
    list_display = ('id', 'user', 'name', 'salon', 'get_categories', 'get_services', 'get_barber_services_names', 'status')
    list_filter = ('salon', 'categories', 'status')
    search_fields = ('id', 'user__username', 'name', 'salon__name', 'status')
    filter_horizontal = ('categories', 'services')
    autocomplete_fields = ['salon', 'categories', 'user']
    fields = ('salon', 'user', 'name', 'avatar', 'description', 'categories', 'services', 'status')
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

class ChoiceWithDescSelect(forms.Select):
    """Select, который добавляет к пункту описание и тултип."""
    def __init__(self, *args, descriptions=None, **kwargs):
        self.descriptions = descriptions or {}
        super().__init__(*args, **kwargs)

    def create_option(
        self, name, value, label, selected, index,
        subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index,
            subindex=subindex, attrs=attrs,
        )
        desc = self.descriptions.get(value)
        if desc:
            # (а) показываем описание рядом
            option["label"] = f"{label} — {desc}"
            # (б) добавляем title для ховера
            option["attrs"]["title"] = desc
        return option

# ---  Описания для status / additional_status ------------------------------

STATUS_DESCRIPTIONS = {
    'new': 'только появился лид',
    'in process': 'уже в процессе обсуждения',
    'active': 'уже сотрудничает',
    'suspend': 'мы приостановили',
    'refused': 'они отказались',
}

ADDITIONAL_DESCRIPTIONS = {
    'inbound': 'они сами обратились',
    'waiting_contact': 'ждём ответа',
    'mail': 'отправлено письмо',
    'they_think': 'думают',
    'not now': 'сказали «свяжемся, если нужно будет»',
    'not_interested': 'не заинтересованы',
    'ignored': 'не отвечают',
    'expansion_needed': 'нужно расширить',
    'former_partner': 'раньше сотрудничали',
}

class SalonAdminForm(forms.ModelForm):
    class Meta:
        model = Salon
        fields = '__all__'
        widgets = {
            "status": ChoiceWithDescSelect( 
                descriptions=STATUS_DESCRIPTIONS
            ),
            "additional_status": ChoiceWithDescSelect(
                descriptions=ADDITIONAL_DESCRIPTIONS
            ),
        }

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
    list_display = ('id', 'name', 'salon_manager','city', 'status', 'additional_status', 'address', 'mod')
    list_filter = ('status', 'additional_status', 'salon_manager', 'city', 'category')
    search_fields = ('id', 'name', 'salon_manager','city', 'status', 'additional_status', 'address', 'mod')
    inlines = [ServiceInline, SalonImageInline, BarberInline, NoteInline]
    autocomplete_fields = ['admins']

    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'salon_manager')
        }),
        ('Partnership status', {
            'fields': ('status', 'additional_status')
        }),
        ('Address', {
            'fields': ('city', 'address', 'coordinates')
        }),
        ('Salon visual', {
            # Для одного элемента в кортеже ставим запятую
            'fields': ('logo',)
        }),
        ('Salon contacts', {
            'fields': ('phone_number', 'instagram', 'facebook')
        }),
        ('Descriptions', {
            'fields': (
                'shortDescription_hy',
                'shortDescription_ru',
                'shortDescription_eng',
                'description_hy',
                'description_ru',
                'description_eng'
            )
        }),
        ('Telegram settings', {
            'fields': ('telegram_status', 'telegram_appointmentMod', 'telegram_barbersMod')
        }),
        ('Salon settings', {
            'fields': (
                'admins',
                'mod',
                'appointment_mod',
                'reservDays',
                'default_duration',
                'default_price',
                'IsCheckDays',
                'anyBarberMode'
            )
        }),
    )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'admins':
            # kwargs['queryset'] = User.objects.filter(is_staff=True, is_active=True)
            pass
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def display_admins(self, obj):
        return ", ".join([str(admin) for admin in obj.admins.all()])
    display_admins.short_description = "Admins"

    def status_display(self, obj):
        return obj.get_status_display()
    status_display.short_description = 'Status'

    def additional_status_display(self, obj):
        return obj.get_additional_status_display()
    additional_status_display.short_description = 'Additional status'

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
    list_filter = ('appointment__salon', 'barber', 'start_datetime')
    filter_horizontal = ('services',)
    autocomplete_fields = ['appointment', 'barber', 'services']
