from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class RegistrationForm(forms.Form):
    username = forms.CharField(max_length=100)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Username sudah digunakan.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email sudah digunakan.')
        return email

    def clean(self):
        data = super().clean()
        password = data.get('password')
        confirmation = data.get('password_confirm')
        if password and confirmation and password != confirmation:
            self.add_error('password_confirm', 'Konfirmasi password tidak cocok.')
        if password and data.get('username') and data.get('email'):
            candidate = User(username=data['username'], email=data['email'])
            try:
                validate_password(password, user=candidate)
            except ValidationError as error:
                self.add_error('password', error)
        return data
