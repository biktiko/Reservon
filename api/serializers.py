# api/serializers.py

from rest_framework import serializers
from salons.models import (
    Salon, Service, ServiceCategory, Barber, BarberService,
    Appointment, AppointmentBarberService, BarberAvailability
)
from django.contrib.auth.models import User


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'duration', 'category', 'status']

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
class SalonDetailSerializer(serializers.ModelSerializer):
    """
    Детальный сериализатор салона:
    - services (обычные услуги, связанные через related_name='services')
    - barbers (список мастеров, у каждого - barber_services, если есть)
    """
    services = ServiceSerializer(many=True, read_only=True)
    barbers = BarberSerializer(many=True, read_only=True)
    
    # Если понадобится список категорий, раскомментируйте и реализуйте метод
    # service_categories = serializers.SerializerMethodField()

    class Meta:
        model = Salon
        # fields = [
        #     'id', 'name', 'logo', 'address', 'status', 'mod',
        #     'IsCheckDays', 'reservDays',
        #     'shortDescription_hy', 'shortDescription_ru', 'shortDescription_eng',
        #     'description_hy', 'description_ru', 'description_eng',
        #     'services',
        #     'barbers',
        #     'appointment_mod',
        #     'telegram_status', 'telegram_appointmentMod', 'telegram_barbersMod',
        # ]

        fields = '__all__'
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
