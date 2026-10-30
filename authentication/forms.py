from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Profile, User, SellerApplication, Merchant

MAX_PHOTO_SIZE = 2 * 1024 * 1024

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['photo','bio', 'location', 'community']
        labels = {
            'photo': 'Foto profil',
            'bio': 'Bio',
            'location': 'Lokasi',
            'community': 'Komunitas',
        }
        help_texts = {
            'photo': 'Foto berupa gambar, maksimal 2 MB.',
        }
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo and photo.size > MAX_PHOTO_SIZE:
            raise forms.ValidationError('Ukuran foto maksimal 2 MB')
        return photo

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100, label='Username')
    password = forms.CharField(widget=forms.PasswordInput, label='Password')

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        data = super().clean()
        username = data.get('username')
        password = data.get('password')
        if username and password:
            user = authenticate(self.request, username=username, password=password)
            if user is None or not (user.is_superuser or user.roles.exists()):
                raise forms.ValidationError('Username atau password tidak valid.')
            self.user = user
        return data

    def get_user(self):
        return self.user


class RegistrationForm(forms.Form):
    username = forms.CharField(max_length=100)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if username.lower() in {'edit'}:
            raise forms.ValidationError('Username ini tidak dapat digunakan.')
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

class SellerReviewForm(forms.Form):
    decision = forms.ChoiceField(choices=[
        (SellerApplication.Status.APPROVED, 'Setujui'),
        (SellerApplication.Status.REJECTED, 'Tolak'),
    ])
    admin_note = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)


class MerchantForm(forms.ModelForm):
    class Meta:
        model = Merchant
        fields = ['name', 'description', 'location', 'show_location', 'contact', 'show_contact']
        labels = {
            'name': 'Nama merchant',
            'description': 'Deskripsi',
            'location': 'Lokasi',
            'show_location': 'Tampilkan lokasi ke publik',
            'contact': 'Kontak',
            'show_contact': 'Tampilkan kontak ke publik',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'show_location': forms.CheckboxInput(attrs={'class': 'control'}),
            'show_contact': forms.CheckboxInput(attrs={'class': 'control'}),
        }