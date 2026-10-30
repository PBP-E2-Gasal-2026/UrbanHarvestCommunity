from django.db.models import Case, Count, IntegerField, Q, Value, When

from .models import Category, Product

PRICE_RANGES = {
    'under-10k': ('Di bawah Rp10.000', None, 10000),
    '10k-25k': ('Rp10.000 – Rp25.000', 10000, 25000),
    '25k-50k': ('Rp25.000 – Rp50.000', 25000, 50000),
    'over-50k': ('Di atas Rp50.000', 50000, None),
}

SORT_OPTIONS = {
    'relevance': None,
    'newest': '-created_at',
    'price_asc': 'price',
    'price_desc': '-price',
}


def _to_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    return str(value).lower() in ('1', 'true', 'yes', 'on')


def _to_list(raw, key):
    values = raw.getlist(key) if hasattr(raw, 'getlist') else raw.get(key)
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    cleaned = []
    for value in values:
        value = str(value).strip()
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned


def clean_search_params(raw):
    """Ubah parameter mentah (GET atau dict dari LLM) jadi filter yang aman.

    Nilai yang tidak valid diabaikan, bukan menimbulkan error.
    """
    min_price = _to_int(raw.get('min_price'))
    max_price = _to_int(raw.get('max_price'))
    price_range = raw.get('price_range')
    if price_range not in PRICE_RANGES:
        price_range = ''
    elif min_price is None and max_price is None:
        _, min_price, max_price = PRICE_RANGES[price_range]
    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price

    keyword = (raw.get('keyword') or raw.get('q') or '').strip()
    sort = raw.get('sort')
    if sort not in SORT_OPTIONS or (sort == 'relevance' and not keyword):
        sort = 'relevance' if keyword else 'newest'

    categories = _to_list(raw, 'category')
    return {
        'keyword': keyword,
        'categories': categories,
        'category': categories[0] if len(categories) == 1 else '',
        'price_range': price_range,
        'min_price': min_price,
        'max_price': max_price,
        'location': (raw.get('location') or '').strip(),
        'in_stock': _to_bool(raw.get('in_stock')),
        'sort': sort,
    }


def _apply_filters(products, params, include_category=True):
    if params['keyword']:
        products = products.filter(
            Q(name__icontains=params['keyword']) | Q(description__icontains=params['keyword'])
        )
    if include_category and params['categories']:
        category_filter = Q(category__slug__in=params['categories'])
        for name in params['categories']:
            category_filter |= Q(category__name__iexact=name)
        products = products.filter(category_filter)
    if params['min_price'] is not None:
        products = products.filter(price__gte=params['min_price'])
    if params['max_price'] is not None:
        products = products.filter(price__lte=params['max_price'])
    if params['location']:
        products = products.filter(location__icontains=params['location'])
    if params['in_stock'] is True:
        products = products.filter(stock__gt=0)
    elif params['in_stock'] is False:
        products = products.filter(stock=0)
    return products


def _order(products, params):
    # Seperti marketplace pada umumnya, produk yang habis selalu diletakkan di akhir.
    products = products.with_stock_rank()
    if params['sort'] == 'relevance':
        keyword = params['keyword']
        products = products.annotate(
            relevance=Case(
                When(name__iexact=keyword, then=Value(3)),
                When(name__istartswith=keyword, then=Value(2)),
                When(name__icontains=keyword, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        return products.order_by('-in_stock_rank', '-relevance', '-created_at')
    return products.order_by('-in_stock_rank', SORT_OPTIONS[params['sort']], '-created_at')


def search_products(raw_params):
    """Satu-satunya pintu query katalog, dipakai view katalog dan LLM Search."""
    params = clean_search_params(raw_params)
    products = Product.objects.active().select_related('category', 'seller', 'seller__merchant')
    products = _apply_filters(products, params)
    return _order(products, params), params


def has_active_filters(params):
    return any([
        params['keyword'], params['categories'], params['min_price'] is not None,
        params['max_price'] is not None, params['location'], params['in_stock'] is not None,
    ])


def category_sections(limit=4):
    """Baris per kategori untuk halaman awal katalog (tanpa filter)."""
    sections = []
    for category in Category.objects.order_by('name'):
        products = list(
            Product.objects.active().filter(category=category)
            .select_related('category', 'seller', 'seller__merchant').in_stock_first('-created_at')[:limit]
        )
        if products:
            sections.append({'category': category, 'products': products})
    return sections


def category_facets(params):
    """Jumlah produk per kategori dengan semua filter lain tetap berlaku."""
    matching = _apply_filters(Product.objects.active(), params, include_category=False)
    return Category.objects.annotate(
        product_count=Count('products', filter=Q(products__in=matching)),
    ).order_by('name')


def serialize_product(product):
    return {
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'image_url': product.photo_url,
        'price': product.price,
        'unit': product.unit,
        'stock': product.stock,
        'min_order': product.min_order,
        'is_available': product.is_available,
        'category': {'name': product.category.name, 'slug': product.category.slug},
        'merchant': product.merchant_name,
        'location': product.location,
        'latitude': float(product.latitude) if product.latitude is not None else None,
        'longitude': float(product.longitude) if product.longitude is not None else None,
        'updated_at': product.updated_at.isoformat(),
    }
