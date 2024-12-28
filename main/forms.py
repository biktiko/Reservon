# main/forms.py

from django import forms
import re
from .models import User

class RegistrationForm(forms.Form):
    phone_number = forms.CharField(max_length=15, required=True, label='Номер телефона')
    first_name = forms.CharField(max_length=30, required=True, label='Имя')
    password1 = forms.CharField(widget=forms.PasswordInput, label='Пароль')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Повторите пароль')

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not re.match(r'^\+374\d{8}$', phone_number) or not phone_number=="+15005550007":
            raise forms.ValidationError('Неверный формат армянского номера телефона.')
        if User.objects.filter(username=phone_number).exists():
            raise forms.ValidationError('Пользователь с таким номером уже существует.')
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 != password2:
            self.add_error('password2', 'Пароли не совпадают.')
        elif len(password1) < 6:
            self.add_error('password1', 'Пароль должен быть не менее 6 символов.')

class SetPasswordForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput, label='Новый пароль')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Повторите пароль')

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 != password2:
            self.add_error('password2', 'Пароли не совпадают.')
        elif len(password1) < 6:
            self.add_error('password1', 'Пароль должен быть не менее 6 символов.')