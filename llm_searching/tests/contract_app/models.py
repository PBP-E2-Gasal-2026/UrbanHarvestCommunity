from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(default="")

    class Meta:
        app_label = "llm_contract"
        db_table = "marketplace_category"


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    seller_id = models.BigIntegerField(default=1)
    name = models.CharField(max_length=150)
    description = models.TextField(default="Deskripsi produk untuk pengujian kontrak.")
    image = models.CharField(max_length=200, blank=True)
    image_url = models.URLField(blank=True)
    price = models.PositiveIntegerField()
    unit = models.CharField(max_length=20, default="kg")
    stock = models.PositiveIntegerField(default=10)
    min_order = models.PositiveIntegerField(default=1)
    location = models.CharField(max_length=150, default="Depok")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "llm_contract"
        db_table = "marketplace_product"
