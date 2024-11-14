# C:\Reservon\Reservon\salons\models.py
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta

class Salon(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('active', 'Active'),
        ('suspend', 'Suspend'),
        ('disable', 'Disable'),
    ]

    name = models.CharField('Salon name', max_length=50)
    logo = models.ImageField('Logo', upload_to='salon_logos/', blank=True, null=True)
    address = models.CharField('Address', max_length=100)
    coordinates = models.CharField('Coordinates', max_length=50, blank=True, null=True)
    opening_hours = models.JSONField(
        "Working Hours", 
        default=dict,
        help_text="JSON format: {'monday': {'open': '09:00', 'close': '18:00'}, ... }"
    )
    default_duration = models.IntegerField('Default duration (minutes)', default=20)
    default_price = models.DecimalField('Default price', max_digits=15, decimal_places=0, default=2000)
    services_hy = models.CharField('Services_hy', max_length=100, blank=True, null=True)
    services_ru = models.CharField('Services_ru', max_length=100, blank=True, null=True)
    services_eng = models.CharField('Services_eng', max_length=100, blank=True, null=True)
    shortDescription_hy = models.CharField('Short description_hy', max_length=100, blank=True, null=True)
    shortDescription_ru = models.CharField('Short description_ru', max_length=100, blank=True, null=True)
    shortDescription_eng = models.CharField('Short description_eng', max_length=100, blank=True, null=True)
    description_hy = models.TextField('description_hy', blank=True)
    description_ru = models.TextField('description_ru', blank=True)
    description_eng = models.TextField('description_eng', blank=True)
    reservDays = models.IntegerField('Reserv days', default=9)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name="Status"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Salon'
        verbose_name_plural = 'Salons'

class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)  # Название категории

    def __str__(self):
        return self.name


class Service(models.Model):

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspend', 'Suspend'),
    ]

    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='salons/services', blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration = models.DurationField()
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='services')
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='services')
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Status"
    )

    def __str__(self):
        return self.name
class SalonImage(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='salons/salons')
    upload_date = models.DateTimeField(auto_now_add=True)

class Barber(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='barbers')
    name = models.CharField(max_length=100)
    availability = models.JSONField("Barber's Working Hours", default=dict)
    avatar = models.ImageField(upload_to='salons/barbers', blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.salon.name})"
    
    def get_avatar_url(self):
        if self.avatar and self.avatar.url:
            return self.avatar.url
        return '/static/salons/img/default-avatar.png'

class Appointment(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    barber = models.ForeignKey(Barber, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    services = models.ManyToManyField(Service, related_name='appointments')  # Связь с услугами
    start_datetime = models.DateTimeField()  # Сделать поле обязательным
    end_datetime = models.DateTimeField(null=True, blank=True)    # Осталось как есть

    def save(self, *args, **kwargs):
        if not self.end_datetime and self.start_datetime:
            # Установите end_datetime как start_datetime плюс 20 минут
            self.end_datetime = self.start_datetime + timedelta(minutes=20)
        super().save(*args, **kwargs)

    def __str__(self):
        barber_name = self.barber.name if self.barber else "Любой мастер"
        return f"{self.salon.name} - {barber_name} - {self.start_datetime} - {self.end_datetime}"

    def get_total_duration(self):
        total_duration = sum(service.duration.total_seconds() for service in self.services.all())
        total_duration += self.salon.default_duration * 60  # Добавляем default_duration салона (в секундах)
        return total_duration / 60  # Возвращаем длительность в минутах

    class Meta:
        indexes = [
            models.Index(fields=['salon', 'start_datetime', 'end_datetime']),
        ]
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'

