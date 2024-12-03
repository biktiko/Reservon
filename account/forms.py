# account/forms.py

from django import forms
from django.forms import ModelForm
from django.forms.models import inlineformset_factory
from salons.models import Appointment, AppointmentBarberService, Barber, Service
from django.forms.widgets import DateTimeInput, SelectMultiple

class CustomDateTimeInput(DateTimeInput):
    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'datetime-input'}
        if attrs is not None:
            final_attrs.update(attrs)
        super().__init__(attrs=final_attrs, format='%d.%m.%Y %H:%M')

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
        fields = ['start_datetime']  # Удалено поле 'barbers'
        widgets = {
            'start_datetime': CustomDateTimeInput(attrs={'id': 'id_start_datetime'}),
            # 'barbers' удалено
        }

class AppointmentBarberServiceForm(ModelForm):
    class Meta:
        model = AppointmentBarberService
        fields = ['barber', 'services', 'start_datetime', 'end_datetime']
        widgets = {
            'services': forms.SelectMultiple(attrs={'class': 'services-select'}),
            'barber': forms.Select(attrs={'class': 'barber-select'}),
            'start_datetime': CustomDateTimeInput(),
            'end_datetime': CustomDateTimeInput(),
        }

AppointmentBarberServiceFormSet = inlineformset_factory(
    Appointment,
    AppointmentBarberService,
    form=AppointmentBarberServiceForm,
    fields=['barber', 'services', 'start_datetime', 'end_datetime'],
    extra=1,
    can_delete=True
)