from django.db import models
from salons.models import Salon
from django.contrib.auth.models import User

class Event(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    TYPE_CHOICES = [
        ('tour', 'Tour'),
        ('event', 'Event'),
        ('training', 'Training'),
        ('other', 'Other'),
    ]

    business = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    short_description = models.TextField(blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='events/photos/', blank=True, null=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='event')
    link = models.URLField(blank=True, null=True)
    organizer_name = models.CharField(max_length=100, blank=True, null=True)
    organizer_phone = models.CharField(max_length=20, blank=True, null=True)
    location_address = models.CharField(max_length=255, blank=True, null=True)
    location_coordinates = models.CharField(max_length=50, blank=True, null=True)
    language = models.CharField(max_length=50)
    min_age = models.PositiveIntegerField(default=0)
    has_multiple_tariffs = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.has_multiple_tariffs:
            EventTariff.objects.create(
                event=self,
                title='Default Tariff',
                price={'default': 0},
                currency='USD'
            )

class EventTariff(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('hidden', 'Hidden'),
    ]
    AVAILABILITY_CHOICES = [
        ('weekly', 'Weekly'),
        ('specific_dates', 'Specific Dates'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tariffs')
    photo = models.ImageField(upload_to='events/tariffs/', blank=True, null=True)
    title = models.CharField(max_length=255)
    short_description = models.TextField(blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    price = models.JSONField(default=dict)
    currency = models.CharField(max_length=10, default='USD')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    
    availability_type = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='weekly')
    days_of_week = models.JSONField(default=list, blank=True) # ["mon", "tue"] or "any"
    specific_dates = models.JSONField(default=list, blank=True) # ["2025-10-19", "2025-10-22"]
    months = models.JSONField(default=list, blank=True) # ["may", "jun"] or "any"

    max_people = models.IntegerField(default=0)
    parallel_events = models.IntegerField(default=0)
    requires_time = models.BooleanField(default=False)
    time_slots = models.JSONField(default=list, blank=True) # ["10:00", "12:00"]

    duration = models.CharField(max_length=50, blank=True, null=True) # "2 hours", "3 days"

    requires_confirmation = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.event.title} - {self.title}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    SOURCE_CHOICES = [
        ('website', 'Website'),
        ('telegram', 'Telegram'),
        ('partner_api', 'Partner API'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bookings')
    tariff = models.ForeignKey(EventTariff, on_delete=models.CASCADE, related_name='bookings')
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    comment = models.TextField(blank=True, null=True)
    
    booking_date = models.DateField()
    booking_time = models.TimeField(blank=True, null=True) # or "any"
    
    participants_count = models.PositiveIntegerField(default=1)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='website')
    
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f"Booking for {self.event.title} by {self.user} on {self.booking_date}"

    def save(self, *args, **kwargs):
        if self._state.adding and self.tariff and not self.tariff.requires_confirmation:
            self.confirmed = True
        super().save(*args, **kwargs)
