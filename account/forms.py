# account/forms.py

from django import forms
from salons.models import Appointment, AppointmentBarberService, Barber, Service
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.contrib.auth.models import User

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['user', 'start_datetime', 'end_datetime']
        widgets = {
            'start_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        salon = kwargs.pop('salon', None)
        super().__init__(*args, **kwargs)
        if salon:
            self.fields['user'].queryset = User.objects.filter(is_active=True)
            # Если нужно ограничить выбор пользователей, вы можете это сделать здесь

class AppointmentBarberServiceForm(forms.ModelForm):
    class Meta:
        model = AppointmentBarberService
        fields = ['barber', 'services', 'start_datetime', 'end_datetime']
        widgets = {
            'start_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        
class BaseAppointmentBarberServiceFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.salon = kwargs.pop('salon', None)
        super().__init__(*args, **kwargs)
        for form in self.forms:
            form.fields['barber'].queryset = Barber.objects.filter(salon=self.salon)
            form.fields['services'].queryset = Service.objects.filter(salon=self.salon)

AppointmentBarberServiceFormSet = inlineformset_factory(
    Appointment,
    AppointmentBarberService,
    form=AppointmentBarberServiceForm,
    formset=BaseAppointmentBarberServiceFormSet,  # Указываем кастомный класс
    extra=1,
    can_delete=True
)