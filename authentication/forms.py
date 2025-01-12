# authentication/forms.py

from django import forms
from .models import User, Profile
from django.forms.widgets import FileInput
from django.core.files.uploadedfile import UploadedFile
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name',)

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password', 'is_staff', 'is_active')
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
        
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar']
        widgets = {
            'avatar': FileInput(attrs={
                'class': 'avatar-input',
                'id': 'id_avatar',
                'accept': 'image/*'
            }),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar', False)
        if avatar and isinstance(avatar, UploadedFile):
            if avatar.size > 4 * 1024 * 1024:
                raise forms.ValidationError("Размер аватара не должен превышать 4 МБ.")
            if avatar.content_type not in ["image/jpeg", "image/png", "image/gif"]:
                raise forms.ValidationError("Только JPEG, PNG и GIF форматы поддерживаются.")
        return avatar