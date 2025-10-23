# api/serializers.py

from rest_framework import serializers
from salons.models import (
    Salon, Service, ServiceCategory, Barber, BarberService,
    Appointment, AppointmentBarberService, BarberAvailability
)
from django.contrib.auth.models import User
from events.models import Event, EventTariff  # add

# --- move these to module level to avoid NameError ---
class EventTariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventTariff
        fields = [
            'id', 'title', 'price', 'currency', 'status',
            'availability_type', 'days_of_week', 'specific_dates', 'months',
            'max_people', 'parallel_events', 'requires_time', 'time_slots',
            'duration', 'requires_confirmation'
        ]

class EventSerializer(serializers.ModelSerializer):
    tariffs = EventTariffSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'status', 'short_description', 'details', 'photo',
            'type', 'link', 'organizer_name', 'organizer_phone',
            'location_address', 'location_coordinates', 'language',
            'min_age', 'has_multiple_tariffs', 'tariffs'
        ]
# --- end module-level serializers ---

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'duration', 'category', 'status']

class SimpleServiceSerializer(serializers.ModelSerializer):
    """
    Облегченный сериализатор услуг только с необходимой для AI информацией.
    """
    class Meta:
        model = Service
        fields = ['name', 'description', 'price', 'duration']


class PlatformPartnerSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка партнеров на платформе.
    Включает основную информацию о салоне и список его услуг.
    """
    services = SimpleServiceSerializer(many=True, read_only=True)
    category = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Salon
        fields = [
            'id', 'name', 'address', 'category', 'status',
            'shortDescription_ru',
            'services'
        ]
class BarberServiceSerializer(serializers.ModelSerializer):
    """
    Сериализатор для BarberService (услуг мастера),
    используется внутри BarberSerializer.
    """
    category = serializers.StringRelatedField()

    class Meta:
        model = BarberService
        fields = ['id', 'name', 'description', 'image', 'price', 'duration', 'category', 'status']


class BarberSerializer(serializers.ModelSerializer):
    """
    Сериализатор мастера, включает:
      - services (обычные услуги из модели Service, связанные ManyToMany)
      - barber_services (персональные услуги мастера из модели BarberService)
    """
    services = ServiceSerializer(many=True, read_only=True)
    barber_services = BarberServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Barber
        fields = [
            'id',
            'name',
            'avatar',
            'description',
            'categories',
            'services',
            'barber_services'
        ]
class SalonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Salon
        fields = [
            'id', 'name', 'logo', 'address', 'status', 'mod',
            'IsCheckDays', 'reservDays',
            'shortDescription_hy', 'shortDescription_ru', 'shortDescription_eng',
            'description_hy', 'description_ru', 'description_eng'
        ]

# Поля салона, которые не хотим возвращать по умолчанию
SALON_FIELDS_BLACKLIST = (
    'telegram_status', 'telegram_appointmentMod', 'telegram_barbersMod'
    'shortDescription_hy', 'shortDescription_ru',
    'description_hy', 'description_ru',
    'reservDays',
    'mod',
    'appointment_mod',
    'IsCheckDays',
    'additional_status',
    'salon_manager',
    'is_visible',
    'logo'
)

class SalonDetailSerializer(serializers.ModelSerializer):
    """
    Детальный сериализатор салона:
    - services
    - barbers
    - events (с тарифами)
    """
    services = ServiceSerializer(many=True, read_only=True)
    barbers = BarberSerializer(many=True, read_only=True)
    events = EventSerializer(many=True, read_only=True)

    class Meta:
        model = Salon
        fields = '__all__'  # берем все, потом вычитаем blacklist

    def get_fields(self):
        fields = super().get_fields()
        # Объединяем дефолтный blacklist и динамический из контекста
        extra_exclude = self.context.get('exclude_fields', []) or []
        blacklist = set(SALON_FIELDS_BLACKLIST) | set(extra_exclude)
        for name in blacklist:
            fields.pop(name, None)
        return fields

class BookingServiceSerializer(serializers.Serializer):
    serviceId = serializers.IntegerField()
    duration = serializers.IntegerField()
class BookingDetailSerializer(serializers.Serializer):
    categoryId = serializers.IntegerField()
    services = BookingServiceSerializer(many=True)
    barberId = serializers.CharField()

class CreateBookingSerializer(serializers.Serializer):
    salon_id = serializers.IntegerField(required=True)
    date = serializers.DateField()
    time = serializers.TimeField()
    booking_details = BookingDetailSerializer(many=True, required=False)
    total_service_duration = serializers.IntegerField(required=False)
    endTime = serializers.CharField(required=False)
    user_comment = serializers.CharField(required=False, allow_blank=True)

    def validate_salon_id(self, value):
        if not Salon.objects.filter(id=value, status='active').exists():
            raise serializers.ValidationError("Салон не найден или не активен.")
        return value

    def validate_booking_details(self, value):
        return value

    def create(self, validated_data):
        return validated_data
