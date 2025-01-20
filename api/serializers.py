# api/serializers.py

from rest_framework import serializers
from salons.models import (
    Salon, Service, ServiceCategory, Barber,
    Appointment, AppointmentBarberService, BarberAvailability
)
from django.contrib.auth.models import User


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'price', 'duration', 'category', 'status']


class ServiceCategorySerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'default_duration', 'services']


class BarberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barber
        fields = ['id', 'name', 'avatar', 'description', 'categories']


class SalonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Salon
        fields = ['id', 'name', 'logo', 'address', 'status']


class SalonDetailSerializer(serializers.ModelSerializer):
    service_categories = ServiceCategorySerializer(many=True, source='servicecategory_set', read_only=True)
    barbers = BarberSerializer(many=True, read_only=True)
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Salon
        fields = [
            'id', 'name', 'logo', 'address', 'status',
            'service_categories', 'barbers'
        ]


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
        # Дополнительная валидация, если требуется
        return value

    def create(self, validated_data):
        # Логика создания бронирования
        # Здесь можно интегрировать вашу существующую функцию `book_appointment`
        # Однако для чистоты API лучше перенести логику сюда или адаптировать существующую
        # Для простоты мы вернем данные без сохранения
        return validated_data
