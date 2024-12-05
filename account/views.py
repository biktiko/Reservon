# account/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.db import models
from salons.models import Salon, Appointment, Barber, Service, AppointmentBarberService
from django.db.models import Q
from django.core.paginator import Paginator
from .forms import AppointmentForm, AppointmentBarberServiceFormSet, AdminBookingForm
from django.utils import timezone
from django.contrib import messages
from collections import defaultdict
from django.db import transaction
from django.http import JsonResponse
import logging
from .utils import get_random_available_barber

# logger = logging.getLogger(__name__)
logger = logging.getLogger('booking')

@login_required
@transaction.atomic
def add_booking(request):
    if request.method == 'POST':
        form = AdminBookingForm(request.POST)
        salon_id = request.POST.get('salon_id')
        salon = get_object_or_404(Salon, id=salon_id, admins=request.user)
        
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.salon = salon
            appointment.user = None
            appointment.save()

            barber = form.cleaned_data['barber']
            services = form.cleaned_data['services']

            if not barber:
                barber = get_random_available_barber(
                    appointment.start_datetime, 
                    appointment.end_datetime, 
                    appointment.salon
                )
                if not barber:
                    form.add_error('barber', 'Нет доступных мастеров на выбранное время')
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)
                    return render(request, 'account/add_booking.html', {'form': form, 'selected_salon': salon})

            appointment_barber_service = AppointmentBarberService.objects.create(
                appointment=appointment,
                barber=barber,
                start_datetime=appointment.start_datetime,
                end_datetime=appointment.end_datetime,
            )
            if services:
                appointment_barber_service.services.set(services)

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Бронирование успешно создано!'})
            return redirect('booking_success')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)
    else:
        form = AdminBookingForm()
    return render(request, 'account/add_booking.html', {'form': form})

@login_required
def edit_booking(request, booking_id):
    user = request.user
    appointment = get_object_or_404(
        Appointment.objects.select_related('user__main_profile').prefetch_related('barbers', 'barber_services'),
        id=booking_id,
        salon__in=user.administered_salons.all()
    )
    salon = appointment.salon

    # Получаем имя клиента
    if appointment.user:
        customer_name = appointment.user.get_full_name() or 'Гость'
    else:
        customer_name = 'Гость'

    # Получаем телефон клиента
    if appointment.user and hasattr(appointment.user, 'main_profile'):
        customer_phone = appointment.user.main_profile.phone_number or 'Не указан'
    else:
        customer_phone = 'Не указан'

    if request.method == 'POST':
        formset = AppointmentBarberServiceFormSet(request.POST, instance=appointment)
        if formset.is_valid():
            with transaction.atomic():
                formset.instance = appointment  # Устанавливаем связь формсета с appointment

                # Сохраняем формы по отдельности
                instances = formset.save(commit=False)
                for obj in formset.deleted_objects:
                    obj.delete()
                for instance in instances:
                    instance.appointment = appointment
                    instance.save()
                formset.save_m2m()

                # После сохранения формсета обновляем start_datetime и end_datetime в Appointment
                appointment.start_datetime = appointment.barber_services.aggregate(models.Min('start_datetime'))['start_datetime__min']
                appointment.end_datetime = appointment.barber_services.aggregate(models.Max('end_datetime'))['end_datetime__max']
                appointment.save(update_fields=['start_datetime', 'end_datetime'])

                messages.success(request, 'Бронирование успешно обновлено.')
                return redirect('manage_bookings')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки ниже.')
    else:
        formset = AppointmentBarberServiceFormSet(instance=appointment)

    # Вычисляем длительность и цену для каждой категории
    category_forms = []
    total_duration = 0
    total_price = 0
    for form_instance in formset.forms:
        barber_service = form_instance.instance
        if barber_service.pk:
            services = barber_service.services.all()
        else:
            # Используем данные из формы
            service_ids = form_instance['services'].value()
            services = Service.objects.filter(id__in=service_ids)
        # Вычисляем длительность и цену категории
        total_duration_category = sum(service.duration.total_seconds() / 60 for service in services)
        total_price_category = sum(service.price for service in services)
        total_duration += total_duration_category
        total_price += total_price_category
        categories = set(service.category.name for service in services if service.category)
        category_name = ', '.join(categories) if categories else 'Без категории'
        category_forms.append({
            'form': form_instance,
            'duration': total_duration_category,
            'price': total_price_category,
            'category_name': category_name,
        })

    # Получаем количество категорий
    category_count = len(category_forms)

    context = {
        'formset': formset,
        'appointment': appointment,
        'total_duration': total_duration,
        'total_price': total_price,
        'category_count': category_count,
        'customer_name': customer_name,
        'customer_phone': customer_phone,
        'category_forms': category_forms,
        'active_menu': 'bookings',
        'active_sidebar': 'salons',
        'LANGUAGE_CODE': request.LANGUAGE_CODE,
    }
    return render(request, 'account/edit_booking.html', context)

@login_required
def account_dashboard(request):
    user = request.user
    salons = user.administered_salons.all()

    # Получаем выбранный салон из параметров запроса или берем первый по умолчанию
    salon_id = request.GET.get('salon_id')
    if salon_id:
        selected_salon = get_object_or_404(Salon, id=salon_id, admins=user)
    else:
        selected_salon = salons.first() if salons.exists() else None

    categories_with_services = []
    if selected_salon:
        # Получаем все услуги салона с предзагрузкой категорий
        services = selected_salon.services.select_related('category').all()

        # Группируем услуги по категориям
        category_services = defaultdict(list)
        for service in services:
            category_name = service.category.name if service.category else 'Без категории'
            category_services[category_name].append(service)

        # Преобразуем в список кортежей для удобной итерации в шаблоне
        categories_with_services = sorted(category_services.items())

    context = {
        'salons': salons,
        'selected_salon': selected_salon,
        'categories_with_services': categories_with_services,
        'currency_symbol': '֏', 
        'active_menu': 'salon',
        'active_sidebar': 'salons',
    }
    return render(request, 'account/dashboard.html', context)
# account/views.py

@login_required
def manage_bookings(request):
    user = request.user
    salons = user.administered_salons.all()

    if not salons.exists():
        return render(request, 'account/no_salons.html')

    # Получаем выбранный салон
    salon_id = request.GET.get('salon_id')
    if salon_id:
        selected_salon = get_object_or_404(Salon, id=salon_id, admins=user)
    else:
        selected_salon = salons.first()

    # Получаем бронирования для выбранного салона
    appointments = Appointment.objects.filter(salon=selected_salon)

    # Применяем фильтры
    barber_id = request.GET.get('barber')
    status = request.GET.get('status', 'upcoming')  # По умолчанию 'upcoming'

    if barber_id:
        appointments = appointments.filter(barber_services__barber_id=barber_id)

    if status == 'past':
        appointments = appointments.filter(end_datetime__lt=timezone.now())
    elif status == 'upcoming':
        appointments = appointments.filter(start_datetime__gte=timezone.now())

    # Убираем дубликаты из-за объединений
    appointments = appointments.distinct()

    # Сортируем от ближайшего к дальнему
    appointments = appointments.order_by('start_datetime')

    # Пагинация
    paginator = Paginator(appointments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Получаем мастеров для фильтрации
    barbers = Barber.objects.filter(salon=selected_salon)

    booking_form = AdminBookingForm()

    context = {
        'appointments': page_obj,
        'barbers': barbers,
        'selected_salon': selected_salon,
        'salons': salons,
        'active_menu': 'bookings',
        'active_sidebar': 'salons',
        'now': timezone.now(),
        'booking_form': booking_form,
    }
    return render(request, 'account/manage_bookings.html', context)

@login_required
def get_services_duration_and_price(request):
    service_ids = request.GET.get('service_ids', '')
    service_ids = service_ids.split(',')

    services = Service.objects.filter(id__in=service_ids)
    total_duration = sum(service.duration.total_seconds() / 60 for service in services)
    total_price = sum(service.price for service in services)

    return JsonResponse({
        'total_duration': total_duration,
        'total_price': total_price,
    })

@login_required
def delete_booking(request, booking_id):
    user = request.user
    appointment = get_object_or_404(Appointment, id=booking_id, salon__in=user.administered_salons.all())

    if request.method == 'POST':
        appointment.delete()
        return redirect('manage_bookings')

    context = {
        'appointment': appointment,
    }
    return render(request, 'account/delete_booking.html', context)
