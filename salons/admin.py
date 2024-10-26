from django.contrib import admin
from .models import salons, Service

class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1

@admin.register(salons)
class SalonAdmin(admin.ModelAdmin):
    inlines = [ServiceInline]

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration', 'salon')
