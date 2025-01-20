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
        fields = [
            'id', 'name', 'logo', 'address', 'status', 'mod',
            'IsCheckDays', 'reservDays',
            'shortDescription_hy', 'shortDescription_ru', 'shortDescription_eng',
            'description_hy', 'description_ru', 'description_eng'
        ]


class SalonDetailSerializer(serializers.ModelSerializer):
    # Убираем поле 'salon', так как оно дублирует сам Salon
    barbers = BarberSerializer(many=True, read_only=True)
    services = ServiceSerializer(many=True, read_only=True)
    # Если нужно, добавьте корректный метод для service_categories
    # service_categories = serializers.SerializerMethodField()

    class Meta:
        model = Salon
        fields = [
            'id', 'name', 'logo', 'address', 'status', 'mod',
            'IsCheckDays', 'reservDays',
            'shortDescription_hy', 'shortDescription_ru', 'shortDescription_eng',
            'description_hy', 'description_ru', 'description_eng',
            'services',        # Добавляем services
            'barbers'          # Удаляем service_categories, если не используем
            # 'service_categories',  # Удалите или раскомментируйте при необходимости
        ]

    # Если хотите добавить service_categories:
    # def get_service_categories(self, obj):
    #     categories = ServiceCategory.objects.filter(services__salon=obj).distinct()
    #     return ServiceCategorySerializer(categories, many=True).data


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
