from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class Location(models.Model):
    """Satu titik di peta: kebun, merchant, atau titik pengambilan.

    Lokasi dikelola di database modul ini sendiri (PRD §5.5 butir 6). Modul lain
    cukup menautkan lewat ID lokasi atau ``owner`` (= merchant/penjual), tanpa
    foreign key ke model modul lain.
    """

    class Kind(models.TextChoices):
        COMMUNITY_GARDEN = 'community_garden', 'Kebun komunitas'
        FARMER_GARDEN = 'farmer_garden', 'Kebun petani'
        MERCHANT = 'merchant', 'Merchant'
        PICKUP_POINT = 'pickup_point', 'Titik pengambilan'

    class DetailVisibility(models.TextChoices):
        PRIVATE = 'private', 'Hanya saya'
        MEMBERS = 'members', 'Pengguna yang sudah masuk'
        PUBLIC = 'public', 'Semua orang'

    # Jenis yang hanya boleh dibuat Petani–Penjual (terkait etalase/produk).
    SELLER_KINDS = (Kind.MERCHANT, Kind.PICKUP_POINT)
    GARDEN_KINDS = (Kind.COMMUNITY_GARDEN, Kind.FARMER_GARDEN)

    # --- Ringkasan publik (selalu tampil, juga untuk Guest) ---
    kind = models.CharField(max_length=20, choices=Kind.choices)
    name = models.CharField(max_length=120)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    area = models.CharField(
        max_length=120,
        blank=True,
        help_text='Kelurahan/kecamatan/kota, mis. "Beji, Depok". Selalu tampil publik.',
    )
    description = models.CharField(
        max_length=300, blank=True, help_text='Deskripsi singkat, maksimal 300 karakter.'
    )
    commodities = models.CharField(
        max_length=200,
        blank=True,
        help_text='Komoditas yang tersedia, pisahkan dengan koma. Mis. "Selada, kangkung, cabai".',
    )
    schedule = models.CharField(
        max_length=120,
        blank=True,
        help_text='Jadwal buka/pengambilan, mis. "Sabtu 08.00–11.00".',
    )
    managed_by = models.CharField(
        max_length=120,
        blank=True,
        help_text='Nama pemilik atau komunitas yang ditampilkan. Kosong = nama pengguna Anda.',
    )
    photo_url = models.URLField(blank=True, help_text='Tautan foto (opsional).')

    # --- Detail (alamat lengkap + kontak) mengikuti pilihan pemilik, PRD §5.5 butir 3 ---
    address = models.CharField(
        max_length=255, blank=True, help_text='Alamat lengkap (nama jalan, nomor, patokan).'
    )
    contact_info = models.CharField(
        max_length=150, blank=True, help_text='Nomor telepon/WhatsApp atau email (opsional).'
    )
    detail_visibility = models.CharField(
        max_length=10,
        choices=DetailVisibility.choices,
        default=DetailVisibility.MEMBERS,
        help_text='Siapa yang boleh melihat alamat lengkap dan kontak.',
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='map_locations',
        help_text='Pemilik/merchant. Kosong untuk lokasi yang dikelola Admin.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        indexes = (models.Index(fields=['is_active', 'kind']),)

    def __str__(self):
        return f'{self.name} ({self.get_kind_display()})'

    def clean(self):
        super().clean()
        # (0, 0) hampir pasti berarti koordinat belum diisi, bukan kebun di Samudra Atlantik.
        if (
            self.latitude is not None
            and self.longitude is not None
            and self.latitude == 0
            and self.longitude == 0
        ):
            raise ValidationError('Koordinat (0, 0) tidak valid. Pilih titik di peta.')

    # Label pendek untuk chip/badge/legenda, mengikuti draf Figma "peta-kebun-desktop".
    SHORT_LABELS = {  # noqa: RUF012
        Kind.COMMUNITY_GARDEN: 'Komunitas',
        Kind.FARMER_GARDEN: 'Kebun petani',
        Kind.MERCHANT: 'Merchant',
        Kind.PICKUP_POINT: 'Titik ambil',
    }

    @property
    def short_label(self):
        return self.SHORT_LABELS.get(self.kind, self.get_kind_display())

    @property
    def badge_tone(self):
        """Tone komponen Figma "Badge": titik ambil = Warning, lainnya = Brand."""
        return 'warning' if self.kind == self.Kind.PICKUP_POINT else 'brand'

    @property
    def manager_name(self):
        """Nama pemilik/komunitas yang ditampilkan (README §2.3)."""
        if self.managed_by:
            return self.managed_by
        return self.owner.username if self.owner_id else ''

    @property
    def commodity_list(self):
        return [item.strip() for item in self.commodities.split(',') if item.strip()]

    def get_absolute_url(self):
        return reverse('map_module:location_detail', args=[self.pk])

    def get_map_url(self):
        """Tautan yang membuka peta dan langsung memfokuskan lokasi ini."""
        return f"{reverse('map_module:map')}?focus={self.pk}"
