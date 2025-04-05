from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
# from simple_history.models import HistoricalRecords

class Salon(models.Model):
    
    admins = models.ManyToManyField(User, related_name='administered_salons', blank=True)

    STATUS_CHOICES = [
        ('new', 'New'),
        ('active', 'Active'),
        ('in process', 'In process'),
        ('refused', 'Refused'),
        ('suspend', 'Suspend'),
    ]

    ADDITIONAL_STATUS_CHOICES = [
        ('waiting_contact', 'Waiting for a contact'),
        ('they_think', 'They think'),
        ('mail', 'Mail'),
        ('ignored', 'Ignored'),
        ('inbound', 'Inbound'),
        ('former_partner', 'Former Partner'),
        ('expansion_needed', 'Expansion needed'),
    ]

    MOD_CHOICES = [
        ('category', 'Category'),  # Режим, где услуги берутся из модели Service
        ('barber', 'Barber'),      # Режим, где услуги берутся из BarberService
    ]

    APPOINTMENT_MOD_CHOICES = [
        ('handle', 'Handle'),
        ('auto', 'Auto'),
    ]

    TELEGRAM_APPOINTMENT_MOD_CHOICES = [
        ('services', 'Services'),  # Режим в телеграме, где в начале услуги, потом мастера
        ('barbers', 'Barbers'),    # Режим в телеграме, где в начале мастера, потом услуги
    ]

    BARBERS_MOD_CHOICES = [
        ('without_images', 'Without images'),  # Мастера без изображений
        ('with_images', 'With images'),        # Мастера с изображениями
    ]

    name = models.CharField('Salon name', max_length=50)
    logo = models.ImageField('Logo', upload_to='salon_logos/', blank=True, null=True)
    city = models.CharField('City', max_length=20, default='Yerevan', blank=False)
    address = models.CharField('Address', max_length=100, blank=True, null=True)
    coordinates = models.CharField('Coordinates', max_length=50, blank=True, null=True)
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
    phone_number = models.CharField('Phone number', max_length=20, blank=True, null=True)
    instagram = models.CharField('Instagram', max_length=100, blank=True, null=True)
    facebook = models.CharField('Facebook', max_length=100, blank=True, null=True)
    reservDays = models.IntegerField('Reserv days', default=9)
    mod = models.CharField(choices=MOD_CHOICES, max_length=10, default='category')
    appointment_mod = models.CharField(choices=APPOINTMENT_MOD_CHOICES, max_length=10, default='auto')
    IsCheckDays = models.BooleanField('Is Check Days', default=True)
    salon_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_salons')

    # telegram
    telegram_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    telegram_appointmentMod = models.CharField(max_length=10, choices=TELEGRAM_APPOINTMENT_MOD_CHOICES, default='services', verbose_name="Telegram Appointment Mod")
    telegram_barbersMod = models.CharField(max_length=15, choices=BARBERS_MOD_CHOICES, default='without_images', verbose_name="Telegram Barbers Bod")

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='new', verbose_name="Status")
    additional_status = models.CharField(max_length=20, choices=ADDITIONAL_STATUS_CHOICES, verbose_name="Additional Status", blank=True, null=True)

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
    description = models.TextField(blank=True, null=True)

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

    def __str__(self):
        return f"Image of {self.salon.name} ({self.upload_date.date()})"


class Barber(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='barbers')
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    avatar = models.ImageField(upload_to='salons/barbers', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    categories = models.ManyToManyField(ServiceCategory, related_name='barbers')
    default_duration = models.IntegerField('Default duration (minutes)', default=20)

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspend', 'Suspend'),
        ('disable', 'Disable'),
    ]

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Status"
    )
    
    services = models.ManyToManyField(
        Service,
        related_name='barbers',
        blank=True
    )

    def __str__(self):
        return self.name  

    def get_avatar_url(self):
        if self.avatar and self.avatar.url:
            return self.avatar.url
        return '/static/salons/img/default-avatar.png'


class BarberService(models.Model):
    """Отдельная модель для режима 'barber': каждая услуга хранится отдельно
    и привязана к конкретному барберу, имеет собственные поля."""
    barber = models.ForeignKey(
        Barber, 
        on_delete=models.CASCADE, 
        related_name='barber_services'
    )

    name = models.CharField(max_length=100, default='Service name')
    image = models.ImageField(upload_to='salons/barberservices', blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    duration = models.DurationField(blank=True, null=True, default=20)
    description = models.TextField(blank=True, null=True)

    category = models.ForeignKey(
        ServiceCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='barber_services'
    )

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspend', 'Suspend'),
    ]

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Status"
    )

    def __str__(self):
        return f"{self.barber.name} - {self.name}"


class BarberAvailability(models.Model):
    DAY_OF_WEEK_CHOICES = [
        ('monday', 'Понедельник'),
        ('tuesday', 'Вторник'),
        ('wednesday', 'Среда'),
        ('thursday', 'Четверг'),
        ('friday', 'Пятница'),
        ('saturday', 'Суббота'),
        ('sunday', 'Воскресенье'),
    ]

    barber = models.ForeignKey(Barber, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.CharField(max_length=9, choices=DAY_OF_WEEK_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    def __str__(self):
        status = 'Доступен' if self.is_available else 'Недоступен'
        return f"{self.barber.name} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time} ({status})"


class Appointment(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user_comment = models.TextField('Комментарий клиента', null=True, blank=True)

    barbers = models.ManyToManyField(
        Barber,
        through='AppointmentBarberService',
        related_name='appointments'
    )

    def __str__(self):
        return f"{self.salon.name} - {self.start_datetime} - {self.end_datetime}"

    def get_total_duration(self):
        total_duration = sum(
            item.get_total_duration() for item in self.barber_services.all()
        )
        return total_duration
class AppointmentBarberService(models.Model):
    """Таблица для хранения связки Appointment - Barber - [Services].
    Предполагается, что здесь services - это обычные 'Service' (режим category)."""
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='barber_services')
    barber = models.ForeignKey(Barber, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointmentbarberservice')
    
    # services - это FK к модели Service, а не BarberService
    services = models.ManyToManyField(Service, blank=True)
    barberServices = models.ManyToManyField(BarberService, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    def get_total_duration(self):
        return (self.end_datetime - self.start_datetime).total_seconds() / 60  # Возвращает в минутах

    def __str__(self):
        return f"{self.appointment} - {self.barber.name if self.barber else 'Любой мастер'}"

