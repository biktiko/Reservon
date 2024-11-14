# authentication/forms.py

from django import forms

class PhoneNumberForm(forms.Form):
    phone_number = forms.CharField(max_length=15, required=True)

class VerificationCodeForm(forms.Form):
    code = forms.CharField(max_length=4, required=True)

class SetNamePasswordForm(forms.Form):
    first_name = forms.CharField(max_length=30, required=True)
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=6, required=True)
    password2 = forms.CharField(widget=forms.PasswordInput, min_length=6, required=True)

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Пароли не совпадают.')
