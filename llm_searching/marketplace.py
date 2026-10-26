from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist, FieldError
from django.core.files.storage import default_storage
from django.db import DatabaseError, models
from django.db.models import Q

from .exceptions import InvalidSearch, MarketplaceUnavailable


@dataclass(frozen=True)
class ProductCard:
    id: int
    name: str
    description: str
    image_url: str
    price: int
    unit: str
    stock: int
    category: dict
    location: str
    url: str
    is_available: bool

    def to_dict(self):
        return asdict(self)


def safe_image_url(value):
    if not value:
        return ""
    parts = urlsplit(value)
    if parts.scheme in ("https", "http") or (
        not parts.scheme and value.startswith("/") and not value.startswith("//")
    ):
        return value
    return ""


class MarketplaceRepository:
    def __init__(self, *, product_model=None, category_model=None, using="default"):
        self.product_model = product_model
        self.category_model = category_model
        self.using = using

    def _models(self):
        try:
            product = self.product_model or apps.get_model("marketplace", "Product")
            category = self.category_model or apps.get_model("marketplace", "Category")
            if (
                product._meta.db_table != "marketplace_product"
                or category._meta.db_table != "marketplace_category"
            ):
                raise LookupError("Unexpected marketplace tables")
            if product._meta.get_field("category").related_model is not category:
                raise LookupError("Unexpected category relation")
            for field in (
                "id",
                "name",
                "description",
                "image",
                "image_url",
                "price",
                "unit",
                "stock",
                "location",
                "is_active",
                "updated_at",
            ):
                product._meta.get_field(field)
            for field in ("id", "name", "slug"):
                category._meta.get_field(field)
            return product, category
        except (LookupError, AttributeError, FieldDoesNotExist, FieldError) as exc:
            raise MarketplaceUnavailable(
                "Dependency marketplace belum tersedia atau kontraknya berbeda."
            ) from exc

    def category_slugs(self):
        _, category = self._models()
        try:
            return list(
                models.QuerySet(model=category, using=self.using)
                .order_by("slug")
                .values_list("slug", flat=True)[:200]
            )
        except (DatabaseError, FieldDoesNotExist, FieldError) as exc:
            raise MarketplaceUnavailable(
                "Kategori marketplace belum tersedia."
            ) from exc

    def search(self, filters):
        product, _ = self._models()
        if filters.categories and not set(filters.categories) <= set(
            self.category_slugs()
        ):
            raise InvalidSearch("Kategori tidak dikenal; perjelas pencarian.")
        try:
            query = models.QuerySet(model=product, using=self.using).filter(
                is_active=True
            )
            if filters.keyword:
                query = query.filter(
                    Q(name__icontains=filters.keyword)
                    | Q(description__icontains=filters.keyword)
                )
            if filters.categories:
                query = query.filter(category__slug__in=filters.categories)
            if filters.location:
                query = query.filter(location__icontains=filters.location)
            if filters.min_price is not None:
                query = query.filter(price__gte=filters.min_price)
            if filters.max_price is not None:
                query = query.filter(price__lte=filters.max_price)
            if filters.in_stock:
                query = query.filter(stock__gt=0)
            order = {
                "newest": ("-updated_at", "-id"),
                "price_asc": ("price", "id"),
                "price_desc": ("-price", "id"),
            }[filters.sort]
            rows = query.order_by(*order).values(
                "id",
                "name",
                "description",
                "image",
                "image_url",
                "price",
                "unit",
                "stock",
                "category__name",
                "category__slug",
                "location",
            )[: filters.limit]
            cards = []
            for row in rows:
                image = row["image_url"]
                if row["image"]:
                    # Use the field's configured storage, without accessing model properties.
                    storage = getattr(
                        product._meta.get_field("image"), "storage", default_storage
                    )
                    image = storage.url(row["image"])
                cards.append(
                    ProductCard(
                        id=row["id"],
                        name=row["name"],
                        description=row["description"][:1000],
                        image_url=safe_image_url(image),
                        price=row["price"],
                        unit=row["unit"],
                        stock=row["stock"],
                        category={
                            "name": row["category__name"],
                            "slug": row["category__slug"],
                        },
                        location=row["location"],
                        url=f"/marketplace/products/{row['id']}/",
                        is_available=row["stock"] > 0,
                    )
                )
            return cards
        except (
            DatabaseError,
            LookupError,
            AttributeError,
            FieldDoesNotExist,
            FieldError,
        ) as exc:
            raise MarketplaceUnavailable(
                "Data marketplace belum kompatibel dengan kontrak."
            ) from exc
