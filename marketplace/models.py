from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import (
    Avg,
    Case,
    Count,
    FloatField,
    IntegerField,
    OuterRef,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']  # noqa: RUF012
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def available(self):
        return self.active().filter(stock__gt=0)

    def with_stock_rank(self):
        return self.annotate(
            in_stock_rank=Case(When(stock__gt=0, then=Value(1)), default=Value(0),
                               output_field=IntegerField()),
        )

    def with_stats(self):
        """Tambah jumlah terjual (pesanan selesai) dan rating rata-rata.

        Memakai subquery terpisah agar join ke pesanan tidak menggandakan hitungan ulasan.
        """
        sold = (OrderItem.objects.filter(product=OuterRef('pk'), order__status='completed')
                .values('product').annotate(total=Sum('quantity')).values('total'))
        ratings = Review.objects.filter(product=OuterRef('pk')).values('product')
        return self.annotate(
            sold_count=Coalesce(Subquery(sold, output_field=IntegerField()), 0),
            rating_avg=Subquery(ratings.annotate(avg=Avg('rating')).values('avg'),
                                output_field=FloatField()),
            rating_count=Coalesce(Subquery(ratings.annotate(n=Count('pk')).values('n'),
                                           output_field=IntegerField()), 0),
        )

    def in_stock_first(self, *ordering):
        """Produk yang masih ada stoknya selalu ditampilkan lebih dulu."""
        return self.with_stock_rank().order_by('-in_stock_rank', *ordering)


class Product(models.Model):
    UNIT_CHOICES = (
        ('kg', 'kg'),
        ('gram', 'gram'),
        ('ikat', 'ikat'),
        ('pcs', 'pcs'),
        ('pack', 'pack'),
        ('pot', 'pot'),
        ('karung', 'karung'),
        ('liter', 'liter'),
    )

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products'
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='products/%Y/%m/', blank=True)
    image_url = models.URLField(blank=True, help_text='Dipakai jika tidak ada foto yang diunggah')
    price = models.PositiveIntegerField(help_text='Harga dalam Rupiah per satuan')
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='kg')
    stock = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    min_order = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    harvested_at = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=150, help_text='Kota/kecamatan titik pengambilan')
    pickup_address = models.CharField(max_length=255, blank=True)
    pickup_notes = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']  # noqa: RUF012
        indexes = [  # noqa: RUF012
            models.Index(fields=['is_active', 'stock']),
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return self.name

    @property
    def is_available(self):
        return self.is_active and self.stock > 0

    @property
    def merchant_name(self):
        """Nama toko dari model Merchant (modul autentikasi); username bila belum dibuat."""
        merchant = getattr(self.seller, 'merchant', None)
        return merchant.name if merchant else self.seller.username

    @property
    def photo_url(self):
        if self.image:
            return self.image.url
        return self.image_url

    @property
    def gallery(self):
        """Semua foto produk: foto utama lalu foto tambahan."""
        photos = [self.photo_url] if self.photo_url else []
        return photos + [extra.image.url for extra in self.images.all()]


class ProductImage(models.Model):
    MAX_PER_PRODUCT = 4

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/%Y/%m/')
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['position', 'pk']  # noqa: RUF012

    def __str__(self):
        return f'Foto {self.product}'


class CartItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart_items'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    # Seperti Shopee: hanya item yang dicentang yang ikut checkout.
    selected = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']  # noqa: RUF012
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=['user', 'product'], name='unique_cart_product'),
        ]

    def __str__(self):
        return f'{self.quantity} x {self.product}'

    @property
    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    """Satu pesanan untuk satu penjual. Checkout dari beberapa toko menghasilkan beberapa pesanan."""

    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    READY = 'ready'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = (
        (PENDING, 'Menunggu konfirmasi'),
        (CONFIRMED, 'Disiapkan'),
        (READY, 'Siap diambil'),
        (COMPLETED, 'Selesai'),
        (CANCELLED, 'Dibatalkan'),
    )

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders'
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sales'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    note = models.TextField(blank=True)
    cancel_reason = models.CharField(max_length=200, blank=True)
    total = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']  # noqa: RUF012
        indexes = [  # noqa: RUF012
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['buyer', 'status']),
        ]

    def __str__(self):
        return f'Pesanan #{self.pk}'

    @property
    def is_open(self):
        return self.status in (self.PENDING, self.CONFIRMED, self.READY)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    # Nama dan harga disalin saat checkout agar riwayat pesanan tidak berubah
    # walaupun produk diedit atau dihapus penjual.
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
    product_name = models.CharField(max_length=150)
    price = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    pickup_location = models.CharField(max_length=150)

    def __str__(self):
        return f'{self.quantity} x {self.product_name}'

    @property
    def subtotal(self):
        return self.price * self.quantity


class Review(models.Model):
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='review')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']  # noqa: RUF012

    def __str__(self):
        return f'{self.rating}/5 untuk {self.product}'
