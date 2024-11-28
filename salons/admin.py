# salons/admin.py

from django.contrib import admin
from django import forms
from django_json_widget.widgets import JSONEditorWidget
from .models import (
    Salon,
    Service,
    SalonImage,
    Barber,
    ServiceCategory,
    Appointment,
    AppointmentBarberService,
)

from import_export import resources
from import_export.admin import ImportExportModelAdmin

# --- Настройка админки для AppointmentBarberService ---

class AppointmentBarberServiceInline(admin.TabularInline):
    model = AppointmentBarberService
    extra = 1
    fields = ('barber', 'services', 'start_datetime', 'end_datetime')
    filter_horizontal = ('services',)

# Настройка админки для модели Appointment
@admin.register(Appointment)
class AppointmentAdmin(ImportExportModelAdmin):
    list_display = ('salon', 'user', 'start_datetime', 'end_datetime', 'get_barbers_services')
    list_filter = ('salon', 'user')
    search_fields = ('salon__name', 'user__username')
    inlines = [AppointmentBarberServiceInline]

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

# Форма для модели Barber с JSONEditorWidget
class BarberAdminForm(forms.ModelForm):
    class Meta:
        model = Barber
        fields = '__all__'
        widgets = {
            'availability': JSONEditorWidget(),
        }

@admin.register(Barber)
class BarberAdmin(ImportExportModelAdmin):
    form = BarberAdminForm  # Используем форму с JSONEditorWidget
    list_display = ('name', 'salon', 'get_categories')
    list_filter = ('salon', 'categories')
    search_fields = ('name', 'salon__name')
    filter_horizontal = ('categories',)
    autocomplete_fields = ['salon', 'categories']
    fields = ('salon', 'name', 'avatar', 'description', 'availability', 'categories')

    def get_categories(self, obj):
        return ", ".join([category.name for category in obj.categories.all()])
    get_categories.short_description = 'Категории'

# --- Настройка админки для Salon ---

# Форма для модели Salon с JSONEditorWidget
class SalonAdminForm(forms.ModelForm):
    class Meta:
        model = Salon
        fields = '__all__'
        widgets = {
            'opening_hours': JSONEditorWidget(),  # Поле opening_hours
        }

# Inline для Barber внутри Salon
class BarberInline(admin.StackedInline):
    model = Barber
    extra = 1
    form = BarberAdminForm  # Используем форму с JSONEditorWidget
    fields = ('name', 'avatar', 'description', 'availability', 'categories')
    filter_horizontal = ('categories',)
    autocomplete_fields = ['categories']

@admin.register(Salon)
class SalonAdmin(ImportExportModelAdmin):
    form = SalonAdminForm
    list_display = ('name', 'status', 'default_price', 'default_duration', 'reservDays', 'coordinates')
    list_filter = ('status',)
    search_fields = ('name', 'address')
    inlines = [ServiceInline, SalonImageInline, BarberInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'logo', 'address', 'coordinates', 'opening_hours', 'reservDays', 'status')
        }),
        ('Описание', {
            'fields': (
                'shortDescription_hy', 'shortDescription_ru', 'shortDescription_eng',
                'description_hy', 'description_ru', 'description_eng'
            )
        }),
        ('Настройки по умолчанию', {
            'fields': ('default_duration', 'default_price')
        }),
    )

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
