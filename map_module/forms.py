from django import forms

from .models import Location
from .permissions import allowed_kinds


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = (
            'kind',
            'name',
            'managed_by',
            'area',
            'commodities',
            'schedule',
            'description',
            'photo_url',
            'latitude',
            'longitude',
            'address',
            'contact_info',
            'detail_visibility',
            'is_active',
        )
        widgets = {  # noqa: RUF012
            'latitude': forms.NumberInput(attrs={'step': 'any', 'inputmode': 'decimal'}),
            'longitude': forms.NumberInput(attrs={'step': 'any', 'inputmode': 'decimal'}),
            'description': forms.Textarea(attrs={'rows': 3, 'maxlength': 300}),
            'area': forms.TextInput(attrs={'placeholder': 'Contoh: Beji, Depok'}),
            'commodities': forms.TextInput(attrs={'placeholder': 'Contoh: Selada, kangkung, cabai'}),
            'schedule': forms.TextInput(attrs={'placeholder': 'Contoh: Sabtu 08.00–11.00'}),
        }
        labels = {  # noqa: RUF012
            'kind': 'Jenis lokasi',
            'name': 'Nama lokasi',
            'managed_by': 'Nama pemilik atau komunitas',
            'area': 'Wilayah',
            'commodities': 'Komoditas yang tersedia',
            'schedule': 'Jadwal buka / pengambilan',
            'description': 'Deskripsi singkat',
            'photo_url': 'Tautan foto',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'address': 'Alamat lengkap',
            'contact_info': 'Kontak',
            'detail_visibility': 'Siapa yang boleh melihat alamat lengkap dan kontak',
            'is_active': 'Tampilkan di peta',
        }

    def __init__(self, *args, user, **kwargs):
        kwargs.setdefault('label_suffix', '')  # seragam dengan form modul lain (tanpa titik dua)
        super().__init__(*args, **kwargs)
        allowed = set(allowed_kinds(user))
        # Pada edit, jenis yang sudah ada tetap muncul agar form tidak rusak.
        if self.instance.pk:
            allowed.add(self.instance.kind)
        self.fields['kind'].choices = [
            (value, label) for value, label in Location.Kind.choices if value in allowed
        ]
        self.fields['latitude'].help_text = 'Klik peta di bawah untuk mengisi otomatis.'

    def clean_name(self):
        return self.cleaned_data['name'].strip()

    def clean_commodities(self):
        # Rapikan "selada,  kangkung ,,cabai" menjadi "selada, kangkung, cabai".
        items = [item.strip() for item in self.cleaned_data['commodities'].split(',')]
        return ', '.join(item for item in items if item)

    def clean_kind(self):
        kind = self.cleaned_data['kind']
        # Pertahankan jenis lama saat edit; jenis baru harus dalam hak user.
        if self.instance.pk and kind == self.instance.kind:
            return kind
        if kind not in {value for value, _ in self.fields['kind'].choices}:
            raise forms.ValidationError('Anda tidak berhak membuat lokasi dengan jenis ini.')
        return kind
