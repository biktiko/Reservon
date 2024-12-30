# account/forms.py

from django import forms
from django.forms import ModelForm
from django.forms.models import inlineformset_factory
from salons.models import Appointment, AppointmentBarberService, Barber, Service, BarberAvailability
from django.forms.widgets import DateTimeInput
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
        queryset=Barber.objects.all(),
        required=False,
        label='Мастер'
    )
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.all(),
        required=False,
        label='Услуги'
    )
    # Вместо end_datetime:
    DURATION_CHOICES = [(i, f'{i} мин') for i in range(10, 100, 10)]  # 10,20..90
    duration = forms.ChoiceField(
        choices=DURATION_CHOICES,
        initial=20,          # дефолт 20
        label='Длительность'
    )

    class Meta:
        model = Appointment
        fields = ['start_datetime', 'duration', 'barber', 'services']
        # end_datetime выпилили из fields
        labels = {
            'start_datetime': 'Начало бронирования',
        }
        widgets = {
            'start_datetime': DateTimeInput(attrs={'type': 'datetime-local'}),
        }

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
        
class AppointmentBarberServiceForm(ModelForm):
    class Meta:
        model = AppointmentBarberService
        fields = ['barber', 'services', 'start_datetime', 'end_datetime']
        widgets = {
            'services': forms.SelectMultiple(attrs={'class': 'services-select'}),
            'barber': forms.Select(attrs={'class': 'barber-select'}),
            'start_datetime': CustomDateTimeInput(attrs={'class': 'datetime-input start-datetime'}),
            'end_datetime': CustomDateTimeInput(attrs={'class': 'datetime-input end-datetime'}),
        }

AppointmentBarberServiceFormSet = inlineformset_factory(
    Appointment,
    AppointmentBarberService,
    form=AppointmentBarberServiceForm,
    fields=['barber', 'services', 'start_datetime', 'end_datetime'],
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
