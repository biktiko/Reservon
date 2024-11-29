# C:\Reservon\Reservon\salons\models.py
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta

class Salon(models.Model):
    admins = models.ManyToManyField(User, related_name='administered_salons', blank=True)

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
    default_duration = models.IntegerField('Default duration (minutes)', default=15)

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
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    availability = models.JSONField("Barber's Working Hours", default=dict)
    avatar = models.ImageField(upload_to='salons/barbers', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    categories = models.ManyToManyField(ServiceCategory, related_name='barbers')  # Add this line

    def __str__(self):
        return f"{self.name} ({self.salon.name})"

    def get_avatar_url(self):
        if self.avatar and self.avatar.url:
            return self.avatar.url
        return '/static/salons/img/default-avatar.png'


class Appointment(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    barbers = models.ManyToManyField(
        Barber,
        through='AppointmentBarberService',
        related_name='appointments'
    )

    def __str__(self):
        return f"{self.salon.name} - {self.start_datetime} - {self.end_datetime}"

    def get_total_duration(self):
        total_duration = sum(item.get_total_duration() for item in self.barber_services.all())
        return total_duration


class AppointmentBarberService(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='barber_services')
    barber = models.ForeignKey(Barber, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointmentbarberservice')
    services = models.ManyToManyField(Service)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()


    def get_total_duration(self):
        return (self.end_datetime - self.start_datetime).total_seconds() / 60  # Возвращает в минутах

    def __str__(self):
        return f"{self.appointment} - {self.barber.name if self.barber else 'Любой мастер'}"



