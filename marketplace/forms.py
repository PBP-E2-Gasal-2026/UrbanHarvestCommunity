from django import forms
from django.utils import timezone

from .models import Product, ProductImage

MAX_IMAGE_SIZE = 2 * 1024 * 1024
ALLOWED_IMAGE_TYPES = ('image/jpeg', 'image/png', 'image/webp')

NAME_MIN, NAME_MAX = 5, 100
DESCRIPTION_MIN = 20
PRICE_MIN, PRICE_MAX = 100, 100_000_000
STOCK_MAX = 99_999

# Batas kasar wilayah Indonesia, untuk menolak titik yang jelas salah.
INDONESIA_LAT = (-11.5, 6.5)
INDONESIA_LNG = (94.5, 141.5)


def validate_image(image):
    if image.size > MAX_IMAGE_SIZE:
        raise forms.ValidationError('Ukuran foto maksimal 2 MB.')
    if getattr(image, 'content_type', None) not in ALLOWED_IMAGE_TYPES:
        raise forms.ValidationError('Format foto harus JPG, PNG, atau WebP.')


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        return [super(MultipleImageField, self).clean(file, initial) for file in files]


class ProductForm(forms.ModelForm):
    extra_images = MultipleImageField(
        required=False, label='Foto tambahan',
        widget=MultipleFileInput(attrs={'accept': ','.join(ALLOWED_IMAGE_TYPES)}),
    )
    remove_images = forms.ModelMultipleChoiceField(
        queryset=ProductImage.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple, label='Hapus foto tambahan',
    )

    class Meta:
        model = Product
        fields = [  # noqa: RUF012
            'image', 'image_url', 'name', 'category', 'description',
            'price', 'unit', 'stock', 'min_order', 'harvested_at',
            'location', 'pickup_address', 'latitude', 'longitude', 'pickup_notes', 'is_active',
        ]
        labels = {  # noqa: RUF012
            'image': 'Foto utama',
            'image_url': 'Atau URL foto utama',
            'name': 'Nama produk',
            'category': 'Kategori',
            'description': 'Deskripsi',
            'price': 'Harga (Rp)',
            'unit': 'Per satuan',
            'stock': 'Stok',
            'min_order': 'Minimal pembelian',
            'harvested_at': 'Tanggal panen (opsional)',
            'location': 'Kota / kecamatan',
            'pickup_address': 'Alamat lengkap titik pengambilan',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'pickup_notes': 'Catatan pengambilan (opsional)',
            'is_active': 'Tampilkan di katalog',
        }
        widgets = {  # noqa: RUF012
            'name': forms.TextInput(attrs={'maxlength': NAME_MAX, 'placeholder': 'Contoh: Tomat Cherry Organik 500 gr'}),
            'description': forms.Textarea(attrs={
                'rows': 5, 'placeholder': 'Ceritakan kondisi, cara tanam, dan keunggulan produk.',
            }),
            'image': forms.ClearableFileInput(attrs={'accept': ','.join(ALLOWED_IMAGE_TYPES)}),
            'price': forms.NumberInput(attrs={'min': PRICE_MIN, 'placeholder': '25000'}),
            'stock': forms.NumberInput(attrs={'min': 0, 'max': STOCK_MAX}),
            'min_order': forms.NumberInput(attrs={'min': 1}),
            'harvested_at': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'location': forms.TextInput(attrs={'placeholder': 'Contoh: Beji, Depok'}),
            'pickup_address': forms.TextInput(attrs={'placeholder': 'Nama jalan, nomor, RT/RW, patokan'}),
            'pickup_notes': forms.TextInput(attrs={'placeholder': 'Contoh: Senin–Sabtu 07.00–11.00, hubungi dulu'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Field yang wajib menurut standar listing marketplace.
        for name in ('description', 'pickup_address', 'latitude', 'longitude'):
            self.fields[name].required = True
        for field in self.fields.values():
            field.error_messages['required'] = 'Wajib diisi.'
            field.error_messages['invalid'] = 'Format tidak valid.'
        self.fields['category'].error_messages['invalid_choice'] = 'Pilih kategori yang tersedia.'
        self.fields['latitude'].error_messages['required'] = 'Tandai titik pengambilan di peta.'
        self.fields['longitude'].error_messages['required'] = 'Tandai titik pengambilan di peta.'
        if self.instance.pk:
            self.fields['remove_images'].queryset = self.instance.images.all()

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'content_type'):
            validate_image(image)
        return image

    def clean_extra_images(self):
        images = self.cleaned_data.get('extra_images') or []
        for image in images:
            validate_image(image)
        return images

    def clean_name(self):
        name = ' '.join(self.cleaned_data['name'].split())
        if not NAME_MIN <= len(name) <= NAME_MAX:
            raise forms.ValidationError(f'Nama produk {NAME_MIN}–{NAME_MAX} karakter.')
        return name

    def clean_description(self):
        description = self.cleaned_data['description'].strip()
        if len(description) < DESCRIPTION_MIN:
            raise forms.ValidationError(f'Deskripsi minimal {DESCRIPTION_MIN} karakter.')
        return description

    def clean_price(self):
        price = self.cleaned_data['price']
        if not PRICE_MIN <= price <= PRICE_MAX:
            raise forms.ValidationError('Harga harus antara Rp100 dan Rp100.000.000.')
        return price

    def clean_stock(self):
        stock = self.cleaned_data['stock']
        if stock > STOCK_MAX:
            raise forms.ValidationError(f'Stok maksimal {STOCK_MAX}.')
        return stock

    def clean_harvested_at(self):
        harvested_at = self.cleaned_data.get('harvested_at')
        if harvested_at and harvested_at > timezone.localdate():
            raise forms.ValidationError('Tanggal panen tidak boleh di masa depan.')
        return harvested_at

    def clean(self):
        cleaned = super().clean()

        stock, min_order = cleaned.get('stock'), cleaned.get('min_order')
        if stock and min_order and min_order > stock:
            self.add_error('min_order', 'Minimal pembelian tidak boleh melebihi stok.')

        lat, lng = cleaned.get('latitude'), cleaned.get('longitude')
        if lat is not None and lng is not None and not (
            INDONESIA_LAT[0] <= lat <= INDONESIA_LAT[1] and INDONESIA_LNG[0] <= lng <= INDONESIA_LNG[1]
        ):
            self.add_error('latitude', 'Titik pengambilan harus berada di Indonesia.')

        # Foto lama yang tidak diubah tetap terbaca di cleaned_data['image'].
        if not (cleaned.get('image') or cleaned.get('image_url')):
            self.add_error('image', 'Tambahkan minimal satu foto utama.')

        kept = self.instance.images.count() - len(cleaned.get('remove_images') or []) if self.instance.pk else 0
        if kept + len(cleaned.get('extra_images') or []) > ProductImage.MAX_PER_PRODUCT:
            self.add_error('extra_images', f'Maksimal {ProductImage.MAX_PER_PRODUCT} foto tambahan.')
        return cleaned

    def save(self, commit=True):
        product = super().save(commit=commit)
        if commit:
            self.save_images(product)
        return product

    def save_images(self, product):
        for image in self.cleaned_data.get('remove_images') or []:
            image.image.delete(save=False)
            image.delete()
        start = product.images.count()
        for offset, image in enumerate(self.cleaned_data.get('extra_images') or []):
            ProductImage.objects.create(product=product, image=image, position=start + offset)
