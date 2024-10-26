from django.db import models
from django.contrib.auth.models import User

class salons(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('active', 'Active'),
        ('suspend', 'Suspend'),
        ('disable', 'Disable'),
    ]

    name = models.CharField('Salon name', max_length=50)
    logo = models.ImageField('Logo', upload_to='salon_logos/', blank=True, null=True)
    images = models.ImageField('Images', upload_to='salon_images/', blank=True, null=True)
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
    services_ru = models.CharField('Services_hy', max_length=100, blank=True, null=True)
    services_eng =models.CharField('Services_hy', max_length=100, blank=True, null=True)
    shortDescription_hy = models.CharField('Short description_hy', max_length=100, blank=True, null=True)
    shortDescription_ru = models.CharField('Short description_ru', max_length=100, blank=True, null=True)
    shortDescription_eng = models.CharField('Short description_eng', max_length=100, blank=True, null=True)
    description_hy = models.TextField('description_hy', blank=True)
    description_ru = models.TextField('description_ru', blank=True)
    description_eng = models.TextField('description_eng', blank=True)
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

class Service(models.Model):
    salon = models.ForeignKey(salons, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=100, verbose_name='Service Name')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Price')
    duration = models.DurationField(verbose_name='Duration')  # Длительность услуги

    def __str__(self):
        return f"{self.name} - {self.price} ֏ ({self.salon.name})"

class Appointment(models.Model):
    salon = models.ForeignKey(salons, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()

    def __str__(self):
        return f"{self.salon.salon_name} - {self.date} {self.time}"
