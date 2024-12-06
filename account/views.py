# account/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import models
from salons.models import Salon, Appointment, Barber, Service, AppointmentBarberService, BarberAvailability
from django.core.paginator import Paginator
from .forms import  AppointmentBarberServiceFormSet, AdminBookingForm
from django.utils import timezone
from django.contrib import messages
from collections import defaultdict
from django.db import transaction
from django.http import JsonResponse
import logging
from .utils import get_random_available_barber
from django.forms import modelform_factory, modelformset_factory, ModelForm
from django.template.loader import render_to_string
from django import forms


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


@login_required
def salon_masters(request):
    user = request.user
    salons = user.administered_salons.all()

    salon_id = request.GET.get('salon_id')
    if salon_id:
        salon = get_object_or_404(Salon, id=salon_id, admins=user)
    else:
        salon = salons.first()

    if salon:
        barbers = Barber.objects.filter(salon=salon).prefetch_related('categories')
        # Определяем активного мастера
        active_barber_id = request.GET.get('active_barber_id')
        if active_barber_id:
            active_barber = get_object_or_404(Barber, id=active_barber_id, salon=salon)
        else:
            active_barber = barbers.first() if barbers.exists() else None
    else:
        barbers = []
        active_barber = None
        active_barber_id = None

    # Подготовка расписания для каждого мастера уже была описана ранее
    # Предположим, мы уже добавили day_schedules для active_barber
    if active_barber:
        # Аналогичный код получения расписания для active_barber
        day_schedules = []
        for day_code, day_name in BarberAvailability.DAY_OF_WEEK_CHOICES:
            availabilities = BarberAvailability.objects.filter(barber=active_barber, day_of_week=day_code)
            if availabilities.exists():
                intervals = []
                for availability in availabilities:
                    status = 'Работает' if availability.is_available else 'Недоступен'
                    intervals.append(f"{availability.start_time.strftime('%H:%M')}-{availability.end_time.strftime('%H:%M')} ({status})")
                day_schedules.append({
                    'day': day_code,
                    'day_display': day_name,
                    'intervals': intervals
                })
            else:
                day_schedules.append({
                    'day': day_code,
                    'day_display': day_name,
                    'intervals': ['Выходной']
                })
        active_barber.day_schedules = day_schedules

    context = {
        'barbers': barbers,
        'salon': salon,
        'active_menu': 'salon_masters',
        'active_barber': active_barber,
        'active_barber_id': active_barber_id,
    }
    return render(request, 'account/salon_masters.html', context)

@login_required
def barber_detail(request, barber_id):
    barber = get_object_or_404(Barber, id=barber_id, salon__admins=request.user)
    context = {
        'barber': barber,
    }
    return render(request, 'account/barber_detail.html', context)


@login_required
def add_availability(request, barber_id):
    barber = get_object_or_404(Barber, id=barber_id)
    AvailabilityForm = modelform_factory(BarberAvailability, fields=('day_of_week', 'start_time', 'end_time', 'is_available'))

    if request.method == 'POST':
        form = AvailabilityForm(request.POST)
        if form.is_valid():
            availability = form.save(commit=False)
            availability.barber = barber
            availability.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        day = request.GET.get('day')
        form = AvailabilityForm(initial={'day_of_week': day})
        return render(request, 'account/availability_form.html', {'form': form, 'barber': barber})


class BarberEditForm(ModelForm):
    class Meta:
        model = Barber
        fields = ['name', 'description', 'categories']

@login_required
def edit_barber_field(request, barber_id):
    barber = get_object_or_404(Barber, id=barber_id, salon__admins=request.user)
    field = request.GET.get('field')

    # Создаем форму только с нужным полем
    class SingleFieldForm(forms.ModelForm):
        class Meta:
            model = Barber
            fields = [field]

    if request.method == 'POST':
        form = SingleFieldForm(request.POST, instance=barber)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = SingleFieldForm(instance=barber)
        html = render_to_string('account/edit_barber_field.html', {'form': form, 'barber': barber, 'field': field}, request=request)
        return JsonResponse({'success': True, 'html': html})

@login_required
def edit_barber_schedule(request, barber_id):
    barber = get_object_or_404(Barber, id=barber_id, salon__admins=request.user)
    day = request.GET.get('day')

    BarberAvailabilityFormSet = modelformset_factory(
        BarberAvailability,
        fields=('start_time', 'end_time', 'is_available'),
        extra=1,
        can_delete=True
    )

    queryset = BarberAvailability.objects.filter(barber=barber, day_of_week=day)

    if request.method == 'POST':
        formset = BarberAvailabilityFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            instances = formset.save(commit=False)
            # Удаляем старые записи
            queryset.delete()
            for instance in instances:
                instance.barber = barber
                instance.day_of_week = day
                instance.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': formset.errors})
    else:
        formset = BarberAvailabilityFormSet(queryset=queryset)


        html = render_to_string('account/edit_barber_schedule.html', {
        'formset': formset,
        'barber': barber,
        'day': day
    }, request=request)
    return JsonResponse({'success': True, 'html': html})


class BarberPhotoForm(ModelForm):
    class Meta:
        model = Barber
        fields = ['avatar']

@login_required
def edit_barber_photo(request, barber_id):
    barber = get_object_or_404(Barber, id=barber_id, salon__admins=request.user)

    if request.method == 'POST':
        form = BarberPhotoForm(request.POST, request.FILES, instance=barber)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = BarberPhotoForm(instance=barber)
        html = render_to_string('account/edit_barber_photo.html', {'form': form, 'barber': barber}, request=request)
        return JsonResponse({'success': True, 'html': html})
