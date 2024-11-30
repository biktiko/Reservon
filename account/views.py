# account/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from salons.models import Salon, Appointment, Barber
from django.db.models import Q
from django.core.paginator import Paginator
from .forms import AppointmentForm, AppointmentBarberServiceFormSet
from django.utils import timezone
from django.contrib import messages
from collections import defaultdict


@login_required
def add_booking(request):
    user = request.user
    salons = user.administered_salons.all()

    if not salons.exists():
        messages.error(request, 'Вы не являетесь администратором ни одного салона.')
        return redirect('account_dashboard')

    if request.method == 'POST':
        salon_id = request.POST.get('salon')
        salon = get_object_or_404(Salon, id=salon_id, admins=user)
        form = AppointmentForm(request.POST, salon=salon)
        formset = AppointmentBarberServiceFormSet(request.POST, salon=salon)
        if form.is_valid() and formset.is_valid():
            appointment = form.save(commit=False)
            appointment.salon = salon
            appointment.save()
            formset.instance = appointment
            formset.save()
            messages.success(request, 'Бронирование успешно создано.')
            return redirect('manage_bookings')
    else:
        salon = salons.first()  # Выбираем первый салон по умолчанию
        form = AppointmentForm(salon=salon)
        formset = AppointmentBarberServiceFormSet(salon=salon)

    context = {
        'form': form,
        'formset': formset,
        'salons': salons,
    }
    return render(request, 'account/add_booking.html', context)

@login_required
def edit_booking(request, booking_id):
    user = request.user
    appointment = get_object_or_404(Appointment, id=booking_id, salon__in=user.administered_salons.all())
    salon = appointment.salon  # Получаем салон из бронирования

    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment, salon=salon)
        formset = AppointmentBarberServiceFormSet(request.POST, instance=appointment, salon=salon)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Бронирование успешно обновлено.')
            return redirect('manage_bookings')
    else:
        form = AppointmentForm(instance=appointment, salon=salon)
        formset = AppointmentBarberServiceFormSet(instance=appointment, salon=salon)

    context = {
        'form': form,
        'formset': formset,
        'appointment': appointment,
    }
    return render(request, 'account/edit_booking.html', context)

# account/views.py

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

    context = {
        'appointments': page_obj,
        'barbers': barbers,
        'selected_salon': selected_salon,
        'salons': salons,
        'active_menu': 'bookings',
        'active_sidebar': 'salons',
        'now': timezone.now(),
    }
    return render(request, 'account/manage_bookings.html', context)

@login_required
def view_booking(request, booking_id):
    user = request.user
    appointment = get_object_or_404(Appointment, id=booking_id, salon__in=user.administered_salons.all())

    context = {
        'appointment': appointment,
        'selected_salon': appointment.salon,
        'salons': user.administered_salons.all(),
    }
    return render(request, 'account/view_booking.html', context)