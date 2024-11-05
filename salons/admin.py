from django.contrib import admin
from .models import Salon, Service, Appointment, SalonImage, Barber, ServiceCategory

# Inline для услуг
class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1

# Inline для категорий услуг
class ServiceCategoryInline(admin.TabularInline):
    model = ServiceCategory
    extra = 1

# Inline для изображений салона
class SalonImageInline(admin.TabularInline):
    model = SalonImage
    extra = 1

# Inline для барберов салона
class BarberInline(admin.TabularInline):
    model = Barber
    extra = 1

# Настройка админки для модели Salon
@admin.register(Salon)
class SalonAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'default_price', 'default_duration', 'reservDays', 'coordinates')
    list_filter = ('status',)
    search_fields = ('name', 'address')
    inlines = [ServiceInline, SalonImageInline, BarberInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'logo', 'address', 'coordinates', 'opening_hours', 'reservDays', 'status')
        }),
        ('Описание', {
            'fields': ('shortDescription_hy', 'shortDescription_ru', 'shortDescription_eng',
                       'description_hy', 'description_ru', 'description_eng')
        }),
        ('Настройки по умолчанию', {
            'fields': ('default_duration', 'default_price')
        }),
    )

# Настройка админки для модели Service
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration', 'salon', 'category')
    list_filter = ('salon', 'category')
    search_fields = ('name',)

    # Удаляем инлайн, так как он не нужен здесь

# Настройка админки для модели ServiceCategory
@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [ServiceInline]  # Если хотите редактировать услуги из категории

# Остальные настройки админки остаются без изменений
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('salon', 'user', 'date', 'start_time', 'end_time')
    list_filter = ('salon', 'date')
    search_fields = ('salon__name', 'user__username')

@admin.register(SalonImage)
class SalonImageAdmin(admin.ModelAdmin):
    list_display = ('salon', 'upload_date')
    list_filter = ('salon',)
    search_fields = ('salon__name',)

@admin.register(Barber)
class BarberAdmin(admin.ModelAdmin):
    list_display = ('name', 'salon')
    list_filter = ('salon',)
    search_fields = ('name', 'salon__name')
    fieldsets = (
        (None, {
            'fields': ('salon', 'name', 'avatar', 'description', 'availability')
        }),
    )
