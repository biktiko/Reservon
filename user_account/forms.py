# account/forms.py

from django import forms
from django.forms import ModelForm
from django.forms.models import inlineformset_factory
from salons.models import Appointment, AppointmentBarberService, Barber, Service, BarberService, BarberAvailability
from datetime import timedelta

class CustomDateTimeInput(forms.DateTimeInput):
    input_type = 'text'  # Используем текстовый ввод для совместимости с Flatpickr

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'datetime-input'}
        if attrs is not None:
            final_attrs.update(attrs)
        # Используем формат, соответствующий настройкам Flatpickr
        super().__init__(attrs=final_attrs, format='%d.%m.%Y %H:%M')
class AdminBookingForm(forms.ModelForm):
    barber = forms.ModelChoiceField(
        queryset=Barber.objects.none(),  # Изначально пустой
        required=False,
        label='Мастер'
    )
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.none(),  # Изначально пустой
        required=False,
        label='Услуги'
    )
    DURATION_CHOICES = [(i, f'{i} мин') for i in range(10, 100, 10)]  # 10,20..90
    duration = forms.ChoiceField(
        choices=DURATION_CHOICES,
        initial=40,
        label='Длительность'
    )

    class Meta:
        model = Appointment
        fields = ['start_datetime', 'duration', 'barber', 'services', 'user_comment']
        labels = {
            'start_datetime': 'Начало бронирования',
        }
        widgets = {
            'start_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        print(kwargs)
        salon = kwargs.pop('salon', None)
        super(AdminBookingForm, self).__init__(*args, **kwargs)
        if salon:
            print(f"Форма инициализирована для салона: {salon.name}")
            self.fields['barber'].queryset = salon.barbers.all()
            self.fields['services'].queryset = salon.services.all()
        else:
            print("Салон не передан в форму.")
            self.fields['barber'].queryset = Barber.objects.none()
            self.fields['services'].queryset = Service.objects.none()

    def save(self, commit=True):
        instance = super().save(commit=False)
        start_dt = self.cleaned_data['start_datetime']
        duration_minutes = int(self.cleaned_data['duration'])
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        instance.end_datetime = end_dt

        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def save(self, commit=True):
        # Переопределяем логику сохранения
        instance = super().save(commit=False)
        # Считываем start_datetime и duration
        start_dt = self.cleaned_data['start_datetime']
        duration_minutes = int(self.cleaned_data['duration'])  # строка -> int
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        instance.end_datetime = end_dt

        if commit:
            instance.save()
            # many-to-many
            self.save_m2m()
        return instance
class BarberSelectMultiple(forms.SelectMultiple):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        try:
            barber = Barber.objects.get(pk=value)
            option['attrs']['data-avatar-url'] = barber.get_avatar_url()
        except Barber.DoesNotExist:
            option['attrs']['data-avatar-url'] = '/static/salons/img/default-avatar.png'
        return option

class AppointmentForm(ModelForm):
    class Meta:
        model = Appointment
        fields= []
        
from django.forms.models import inlineformset_factory, BaseInlineFormSet

class CustomAppointmentBarberServiceFormSet(BaseInlineFormSet):
    """
    Кастомный FormSet, который принимает salonMod как параметр
    и передаёт его в каждую форму.
    """
    def __init__(self, *args, salonMod='category', **kwargs):
        # Сохраняем salonMod, чтобы потом передавать в формы
        self.salonMod = salonMod
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        # Берём стандартные kwargs формы
        kwargs = super().get_form_kwargs(index)
        # Добавляем наш параметр salonMod
        kwargs['salonMod'] = self.salonMod
        return kwargs
class AppointmentBarberServiceForm(ModelForm):
    class Meta:
        model = AppointmentBarberService
        fields = ['barber', 'services', 'barberServices', 'start_datetime', 'end_datetime']
        widgets = {
            'services': forms.SelectMultiple(attrs={'class': 'services-select'}),
            'barberServices': forms.SelectMultiple(attrs={'class': 'barberServices-select'}),
            'barber': forms.Select(attrs={'class': 'barber-select'}),
            'start_datetime': CustomDateTimeInput(attrs={'class': 'datetime-input start-datetime'}),
            'end_datetime': CustomDateTimeInput(attrs={'class': 'datetime-input end-datetime'}),
        }
    
    def __init__(self, *args, **kwargs):
        salonMod = kwargs.pop('salonMod', 'category')
        super().__init__(*args, **kwargs)

        if salonMod == "barber":
            # Скрываем services
            self.fields['services'].widget = forms.HiddenInput()

            # Просто все BarberService по текущему салону
            qs = BarberService.objects.filter(barber__salon=self.instance.appointment.salon)
            self.fields['barberServices'].queryset = qs

        else:
            # Скрываем barberServices
            self.fields['barberServices'].widget = forms.HiddenInput()

            # Все обычные Service в салоне
            qs = Service.objects.filter(salon=self.instance.appointment.salon)
            self.fields['services'].queryset = qs

AppointmentBarberServiceFormSet = inlineformset_factory(
    Appointment,
    AppointmentBarberService,
    form=AppointmentBarberServiceForm,
    formset=CustomAppointmentBarberServiceFormSet,  # <-- важно
    fields=['barber', 'services', 'barberServices', 'start_datetime', 'end_datetime'],
    extra=0,
    can_delete=True
)



class BarberFieldForm(forms.ModelForm):
    class Meta:
        model = Barber
        fields = ['name', 'categories', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'categories': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        field = kwargs.pop('field', None)
        super(BarberFieldForm, self).__init__(*args, **kwargs)
        if field:
            # Ограничиваем поля для редактирования в зависимости от 'field'
            for f in self.fields:
                if f != field:
                    self.fields[f].widget = forms.HiddenInput()


class BarberScheduleForm(forms.ModelForm):
    class Meta:
        model = BarberAvailability
        fields = ['start_time', 'end_time', 'is_available']
        widgets = {
            'start_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control'}),
        }
