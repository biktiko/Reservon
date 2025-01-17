# user_account/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import models
from salons.models import Salon, Appointment, Barber, Service, AppointmentBarberService, BarberAvailability, BarberService
from authentication.models import Profile
from django.core.paginator import Paginator
from .forms import  AppointmentBarberServiceFormSet, AdminBookingForm, BarberScheduleForm
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
from authentication.forms import UserProfileForm, ProfileForm

logger = logging.getLogger('booking')

@login_required
@transaction.atomic
def add_booking(request):
    if request.method == 'POST':
        salon_id = request.POST.get('salon_id')
        salon = get_object_or_404(Salon, id=salon_id, admins=request.user)
        form = AdminBookingForm(request.POST, salon=salon)
        
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
                    return render(request, 'user_account/add_booking.html', {'form': form, 'selected_salon': salon})

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
            # Если форма не валидна, повторно передаём объект salon в форму
            salon = get_object_or_404(Salon, id=request.POST.get('salon_id'), admins=request.user)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors.as_json()}, status=400)
            return render(request, 'user_account/add_booking.html', {'form': form, 'selected_salon': salon})
    else:
        salon_id = request.GET.get('salon_id')  # Предполагаем, что salon_id передаётся через GET-параметр
        print('salon_id', salon_id)
        salon = get_object_or_404(Salon, id=salon_id, admins=request.user)
        form = AdminBookingForm(salon=salon)
    return render(request, 'user_account/add_booking.html', {'form': form, 'selected_salon': salon})
    
@login_required
def edit_booking(request, booking_id):
    user = request.user
    appointment = get_object_or_404(
        Appointment.objects.select_related('user__main_profile').prefetch_related('barbers', 'barber_services'),
        id=booking_id,
        salon__in=user.administered_salons.all()
    )
    salon = appointment.salon
    salonMod = salon.mod  # "barber" или "category"

    if appointment.user:
        customer_name = appointment.user.get_full_name() or 'Гость'
        customer_phone = getattr(appointment.user.main_profile, 'phone_number', 'Не указан')
    else:
        customer_name = 'Гость'

    # Получаем телефон клиента
    if appointment.user and hasattr(appointment.user, 'main_profile'):
        customer_phone = appointment.user.main_profile.phone_number or 'Не указан'
    else:
        customer_phone = 'Не указан'

    if request.method == 'POST':
        formset = AppointmentBarberServiceFormSet(
            request.POST,
            instance=appointment,
            form_kwargs={'salonMod': salonMod}
        )
        if formset.is_valid():
            with transaction.atomic():
                instances = formset.save(commit=False)
                for obj in formset.deleted_objects:
                    obj.delete()
                for instance_obj in instances:
                    instance_obj.appointment = appointment
                    instance_obj.save()
                formset.save_m2m()

                # Обновляем дату/время начала и окончания в Appointment
                appointment.start_datetime = appointment.barber_services.aggregate(
                    models.Min('start_datetime')
                )['start_datetime__min']
                appointment.end_datetime = appointment.barber_services.aggregate(
                    models.Max('end_datetime')
                )['end_datetime__max']
                appointment.save(update_fields=['start_datetime', 'end_datetime'])

                messages.success(request, 'Бронирование успешно обновлено.')
                return redirect('user_account:manage_bookings')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки ниже.')
    else:
        formset = AppointmentBarberServiceFormSet(
            instance=appointment,
            form_kwargs={'salonMod': salonMod}
        )
    # Собираем данные для рендера шаблона
    category_forms = []
    total_duration = 0
    total_price = 0

    for form_instance in formset.forms:
        barber_service = form_instance.instance

        # 1) Получаем список услуг (или barberServices) в зависимости от pk и режима
        if salonMod == "barber":
            if barber_service.pk:
                services = barber_service.barberServices.all()  # уже сохранённые barberServices
            else:
                service_ids = form_instance['barberServices'].value()  # данные из формы
                services = BarberService.objects.filter(id__in=service_ids)

            # 2) Считаем длительность и цену
            #    у BarberService duration хранится в поле .duration (timedelta),
            #    price — в .price
            total_duration_category = sum(
                s.duration.total_seconds() / 60 for s in services if s.duration
            )
            total_price_category = sum(
                s.price for s in services if s.price
            )
            
            # 3) Название «категории» (можно вывести barber_service.barber.name
            #    или barber_service.category — зависит от вашей логики)
            #    Пока сделаем так же, как в "category" — берём category.name:
            categories = set(s.category.name for s in services if s.category)
            category_name = ', '.join(categories) if categories else 'Без категории'

        else:
            # "category" режим
            if barber_service.pk:
                services = barber_service.services.all()
            else:
                service_ids = form_instance['services'].value()
                services = Service.objects.filter(id__in=service_ids)

            total_duration_category = sum(
                s.duration.total_seconds() / 60 for s in services if s.duration
            )
            total_price_category = sum(
                s.price for s in services if s.price
            )
            categories = set(s.category.name for s in services if s.category)
            category_name = ', '.join(categories) if categories else 'Без категории'

        # 4) Общий total
        total_duration += total_duration_category
        total_price += total_price_category

        # 5) Добавляем словарь в category_forms, чтобы шаблон отобразил
        category_forms.append({
            'form': form_instance,
            'duration': total_duration_category,
            'price': total_price_category,
            'category_name': category_name,
        })

    context = {
        'formset': formset,
        'appointment': appointment,
        'total_duration': total_duration,
        'total_price': total_price,
        'category_forms': category_forms,
        'customer_name': customer_name,
        'customer_phone': customer_phone,
        'category_forms': category_forms,
        'active_menu': 'bookings',
        'active_sidebar': 'salons',
        'LANGUAGE_CODE': request.LANGUAGE_CODE,
        'salonMod': salonMod
    }
    return render(request, 'user_account/edit_booking.html', context)


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
    return render(request, 'user_account/dashboard.html', context)
# account/views.py

@login_required
def manage_bookings(request):
    user = request.user
    salons = user.administered_salons.all()

    if not salons.exists():
        return render(request, 'user_account/no_salons.html')

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

    booking_form = AdminBookingForm(salon=selected_salon)

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
    return render(request, 'user_account/manage_bookings.html', context)

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
        return redirect('user_account:manage_bookings')
    context = {
        'appointment': appointment,
    }
    return render(request, 'user_account/delete_booking.html', context)


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
        day_schedules = []
        for day_code, day_name in BarberAvailability.DAY_OF_WEEK_CHOICES:
            availabilities = BarberAvailability.objects.filter(barber=active_barber, day_of_week=day_code)

            if availabilities.exists():
                # Проверяем доступные интервалы
                if all(not a.is_available for a in availabilities):
                    # Все интервалы недоступны → "Выходной"
                    day_schedules.append({
                        'day': day_code,
                        'day_display': day_name,
                        'intervals': ['Выходной']
                    })
                else:
                    intervals = []
                    for availability in availabilities:
                        if availability.is_available:
                            intervals.append(f"{availability.start_time.strftime('%H:%M')}-{availability.end_time.strftime('%H:%M')}")
                        # Недоступные интервалы игнорируем

                    # Если intervals пуст — значит не было доступных интервалов,
                    # но мы уже проверили этот случай через all(not a.is_available),
                    # значит intervals точно не пуст.
                    day_schedules.append({
                        'day': day_code,
                        'day_display': day_name,
                        'intervals': intervals
                    })
            else:
                # Нет записей → Выходной
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
    return render(request, 'user_account/salon_masters.html', context)

@login_required
def barber_detail(request, barber_id):
    barber = get_object_or_404(Barber, id=barber_id, salon__admins=request.user)
    context = {
        'barber': barber,
    }
    return render(request, 'user_account/barber_detail.html', context)


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
        return render(request, 'user_account/availability_form.html', {'form': form, 'barber': barber})


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

    field_display_map = {
        'name': 'Имя',
        'description': 'Описание',
        'categories': 'Категории'
        }
    field_display_name = field_display_map.get(field, 'Параметр')

    if request.method == 'POST':
        form = SingleFieldForm(request.POST, instance=barber)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = SingleFieldForm(instance=barber)
        html = render_to_string('user_account/edit_barber_field.html', {
            'form': form, 
            'barber': barber, 
            'field': field,  
            'field_display_name': field_display_name
        }, request=request)
        
        return JsonResponse({'success': True, 'html': html})

@login_required
def edit_barber_schedule(request, barber_id):
    barber = get_object_or_404(Barber, id=barber_id, salon__admins=request.user)
    day = request.GET.get('day')

    # Определяем есть ли записи в БД
    queryset = BarberAvailability.objects.filter(barber=barber, day_of_week=day).order_by('start_time')

    # Если день пуст - показываем 2 формы с дефолтными значениями
    if queryset.exists():
        extra = 0
        initial = []
    else:
        extra = 2
        initial = [
            {'start_time': '09:00', 'end_time': '18:00', 'is_available': True},
            {'start_time': '13:00', 'end_time': '14:00', 'is_available': False}
        ]

    BarberAvailabilityFormSet = modelformset_factory(
        BarberAvailability,
        fields=('start_time', 'end_time', 'is_available'),
        form=BarberScheduleForm,
        extra=extra,
        can_delete=True
    )

    if request.method == 'POST':
        day = request.GET.get('day') or request.POST.get('day')  # Убедитесь, что day не пуст
        formset = BarberAvailabilityFormSet(request.POST, queryset=queryset)
        total_forms = int(request.POST.get('form-TOTAL_FORMS', 0))

        if total_forms == 0:
            # Нет форм → день выходной, удаляем все интервалы
            queryset.delete()
            return JsonResponse({'success': True})

        if formset.is_valid():
            if not formset.has_changed():
                return JsonResponse({'success': True})
            
            queryset.delete()
            instances = formset.save(commit=False)
            for form in formset.forms:
                start = form.cleaned_data.get('start_time')
                end = form.cleaned_data.get('end_time')
                if not start and not end:
                    continue
                instance = form.save(commit=False)
                instance.barber = barber
                instance.day_of_week = day
                instance.save()

            return JsonResponse({'success': True})
        else:
            # Обработка ошибок
            errors_data = []
            for f in formset.forms:
                if f.errors:
                    errors_data.append(f.errors)
                else:
                    errors_data.append({})
            return JsonResponse({'success': False, 'errors': errors_data})
    else:
        formset = BarberAvailabilityFormSet(queryset=queryset, initial=initial)
        html = render_to_string('user_account/edit_barber_schedule.html', {
            'formset': formset,
            'barber': barber,
            'day': day,
            'day_display': day
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
        html = render_to_string('user_account/edit_barber_photo.html', {'form': form, 'barber': barber}, request=request)
        return JsonResponse({'success': True, 'html': html})

@login_required
def my_account_view(request):
    user = request.user
    try:
        profile = user.main_profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=user)

    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('user_account:my_account') 
    else:
        user_form = UserProfileForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'phone_number': profile.phone_number,
        'email': user.email,
        'active_sidebar': 'account'
    }
    return render(request, 'user_account/my_account.html', context)