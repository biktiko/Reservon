from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Event, EventTariff, Booking

import json
from django.utils.html import format_html
import json
from django import forms
from django.db import models as dj_models
from salons.forms import FriendlyJSONField

def pretty_json(obj):
    """Отображает JSON красиво в админке"""
    if isinstance(obj, dict):
        formatted = json.dumps(obj, indent=2, ensure_ascii=False)
    else:
        formatted = str(obj)
    return format_html("<pre>{}</pre>", formatted)

pretty_json.short_description = "Price (formatted)"


class EventResource(resources.ModelResource):
    class Meta:
        model = Event
        fields = ('id', 'title', 'business__name', 'status', 'type', 'language', 'has_multiple_tariffs')

class EventTariffResource(resources.ModelResource):
    class Meta:
        model = EventTariff
        fields = ('id', 'title', 'event__title', 'price', 'currency', 'status', 'availability_type')

class BookingResource(resources.ModelResource):
    class Meta:
        model = Booking
        fields = ('id', 'user__username', 'event__title', 'tariff__title', 'status', 'booking_date', 'booking_time', 'source')

# --- Inlines ---

class BookingInlineForEvent(admin.TabularInline):
    model = Booking
    extra = 0
    autocomplete_fields = ('user', 'tariff')
    fields = ('user', 'tariff', 'booking_date', 'status', 'confirmed')

class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    show_change_link = True
    autocomplete_fields = ('user', 'event', 'tariff')
    fields = ('user', 'tariff', 'booking_date', 'booking_time', 'status', 'participants_count', 'confirmed')

# --- Формы ---

class EventTariffAdminForm(forms.ModelForm):
    DAYS_OF_WEEK_CHOICES = [
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ]
    MONTHS_CHOICES = [
        ('jan', 'January'), ('feb', 'February'), ('mar', 'March'),
        ('apr', 'April'), ('may', 'May'), ('jun', 'June'),
        ('jul', 'July'), ('aug', 'August'), ('sep', 'September'),
        ('oct', 'October'), ('nov', 'November'), ('dec', 'December'),
    ]

    days_of_week = forms.MultipleChoiceField(
        choices=DAYS_OF_WEEK_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Days of week"
    )
    months = forms.MultipleChoiceField(
        choices=MONTHS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Months"
    )
    specific_dates = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        label="Specific dates",
        help_text="Enter dates in YYYY-MM-DD format, separated by commas. E.g.: 2025-10-19, 2025-10-22"
    )

    class Meta:
        model = EventTariff
        fields = '__all__'

    # Use friendly JSON editor specifically for price
    price = FriendlyJSONField(required=False, label='Price')

    class Media:
        js = ('salons/js/friendly_json.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Преобразуем строку дат в список для текстового поля
            if isinstance(self.instance.specific_dates, list):
                self.initial['specific_dates'] = ', '.join(self.instance.specific_dates)

    def clean_specific_dates(self):
        # Преобразуем строку с датами обратно в список
        dates_str = self.cleaned_data.get('specific_dates', '')
        if not dates_str:
            return []
        return [date.strip() for date in dates_str.split(',') if date.strip()]

# --- Админ-классы ---

class EventTariffInline(admin.StackedInline):
    model = EventTariff
    form = EventTariffAdminForm
    extra = 0
    show_change_link = True
    autocomplete_fields = ('event',)
    fieldsets = (
        (None, {
            'fields': ('title', 'status', 'photo', 'short_description', 'details', 'requires_confirmation')
        }),
        ('Price', {
            'fields': ('price', 'currency')
        }),
        ('Availability', {
            'fields': ('availability_type', 'days_of_week', 'specific_dates', 'months', 'max_people', 'parallel_events', 'requires_time', 'time_slots', 'duration')
        }),
    )

@admin.register(Event)
class EventAdmin(ImportExportModelAdmin):
    resource_class = EventResource
    list_display = ('id', 'title', 'business', 'status', 'type', 'language', 'has_multiple_tariffs')
    list_filter = ('status', 'type', 'business', 'language', 'has_multiple_tariffs')
    search_fields = ('id', 'title', 'business__name', 'short_description')
    autocomplete_fields = ('business',)
    inlines = [EventTariffInline, BookingInlineForEvent]

    fieldsets = (
        (None, {
            'fields': ('title', 'business', 'status', 'type')
        }),
        ('Details', {
            'fields': ('short_description', 'details', 'photo', 'link')
        }),
        ('Organizer & Location', {
            'fields': ('organizer_name', 'organizer_phone', 'location_address', 'location_coordinates')
        }),
        ('Settings', {
            'fields': ('language', 'min_age', 'has_multiple_tariffs')
        }),
    )

@admin.register(EventTariff)
class EventTariffAdmin(ImportExportModelAdmin):
    form = EventTariffAdminForm
    resource_class = EventTariffResource
    list_display = ('id', 'title', 'event', 'status', 'availability_type', 'currency')
    list_filter = ('status', 'availability_type', 'event', 'currency')
    search_fields = ('id', 'title', 'event__title')
    autocomplete_fields = ('event',)
    inlines = [BookingInline]
    list_select_related = ('event',)

    def formatted_price(self, obj):
        return pretty_json(obj.price)
    formatted_price.allow_tags = True
    formatted_price.short_description = "Price"

    fieldsets = (
        (None, {
            'fields': ('event', 'title', 'status', 'photo', 'requires_confirmation')
        }),
        ('Description', {
            'fields': ('short_description', 'details')
        }),
        ('Price', {
            'fields': ('price', 'currency')
        }),
        ('Availability', {
            'classes': ('collapse',),
            'fields': (
                'availability_type',
                'days_of_week',
                'specific_dates',
                'months',
                'max_people',
                'parallel_events',
                'requires_time',
                'time_slots',
                'duration'
            )
        }),
    )

@admin.register(Booking)
class BookingAdmin(ImportExportModelAdmin):
    resource_class = BookingResource
    list_display = ('id', 'user', 'event', 'tariff', 'booking_date', 'booking_time', 'status', 'confirmed', 'source', 'created_at')
    list_filter = ('status', 'confirmed', 'source', 'booking_date', 'event')
    search_fields = ('id', 'user__username', 'event__title', 'tariff__title')
    autocomplete_fields = ('user', 'event', 'tariff')
    readonly_fields = ('created_at',)
    list_select_related = ('user', 'event', 'tariff')
    date_hierarchy = 'booking_date'

    fieldsets = (
        (None, {
            'fields': ('user', 'event', 'tariff')
        }),
        ('Booking Details', {
            'fields': ('status', 'confirmed', 'booking_date', 'booking_time', 'participants_count', 'comment')
        }),
        ('Meta', {
            'fields': ('source', 'created_at')
        }),

)
