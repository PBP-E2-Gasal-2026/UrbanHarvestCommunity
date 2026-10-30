from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from . import cart
from .forms import ProductForm
from .models import CartItem, Category, Order, OrderItem, Product
from .permissions import can_manage, is_seller, seller_required
from .services import (
    PRICE_RANGES,
    SORT_OPTIONS,
    category_facets,
    category_sections,
    has_active_filters,
    search_products,
    serialize_product,
)
from .templatetags.marketplace_tags import rupiah

PAGE_SIZE = 12
RELATED_LIMIT = 4


SORT_LABELS = {
    'relevance': 'Paling relevan',
    'newest': 'Terbaru',
    'price_asc': 'Harga terendah',
    'price_desc': 'Harga tertinggi',
}


def _active_filters(params, categories):
    """Daftar filter yang sedang aktif, untuk chip yang bisa dihapus (x)."""
    names = {c.slug: c.name for c in categories}
    chips = [{'label': f'"{params["keyword"]}"', 'param': 'q', 'value': ''}] if params['keyword'] else []
    chips += [
        {'label': names.get(slug, slug), 'param': 'category', 'value': slug}
        for slug in params['categories']
    ]
    if params['price_range']:
        chips.append({'label': PRICE_RANGES[params['price_range']][0],
                      'param': 'price_range', 'value': params['price_range']})
    elif params['min_price'] is not None or params['max_price'] is not None:
        low = rupiah(params['min_price'] or 0)
        high = rupiah(params['max_price']) if params['max_price'] is not None else '∞'
        chips.append({'label': f'{low} – {high}', 'param': 'min_price max_price', 'value': ''})
    if params['location']:
        chips.append({'label': params['location'], 'param': 'location', 'value': ''})
    if params['in_stock']:
        chips.append({'label': 'Tersedia', 'param': 'in_stock', 'value': '1'})
    return chips


MAP_POINT_LIMIT = 300


def _map_points(products):
    """Titik produk untuk mode peta: semua hasil filter yang punya koordinat."""
    return [
        {
            'id': product.pk,
            'name': product.name,
            'price': product.price,
            'unit': product.unit,
            'available': product.is_available,
            'lat': float(product.latitude),
            'lng': float(product.longitude),
            'location': product.location,
            'photo': product.photo_url,
            'url': reverse('marketplace:product_detail', args=[product.pk]),
        }
        for product in products.filter(latitude__isnull=False, longitude__isnull=False)[:MAP_POINT_LIMIT]
    ]


@require_GET
def catalog_view(request):
    products, params = search_products(request.GET)
    page = Paginator(products, PAGE_SIZE).get_page(request.GET.get('page'))
    categories = list(category_facets(params))
    filtered = has_active_filters(params)

    map_view = request.GET.get('view') == 'map'
    query = request.GET.copy()
    query.pop('page', None)
    list_query = query.copy()
    list_query.pop('view', None)
    map_query = list_query.copy()
    map_query['view'] = 'map'
    context = {
        'page_obj': page,
        'map_view': map_view,
        'map_points': _map_points(products) if map_view else [],
        'list_url': f'?{list_query.urlencode()}' if list_query else '?',
        'map_url': f'?{map_query.urlencode()}',
        'categories': categories,
        'all_count': sum(c.product_count for c in categories),
        'params': params,
        'has_filters': filtered,
        'custom_price': not params['price_range'] and (
            params['min_price'] is not None or params['max_price'] is not None
        ),
        'active_filters': _active_filters(params, categories),
        'sections': [] if filtered or map_view else category_sections(limit=10),
        'price_ranges': [(key, label) for key, (label, _, _) in PRICE_RANGES.items()],
        'sort_options': [(key, SORT_LABELS[key]) for key in SORT_OPTIONS],
        'querystring': query.urlencode(),
        'is_seller': is_seller(request.user),
    }
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'content_html': render_to_string('marketplace/_catalog_content.html', context, request),
            'facets': {c.slug: c.product_count for c in categories},
            'all_count': context['all_count'],
            'total': page.paginator.count,
        })
    return render(request, 'marketplace/catalog.html', context)


@require_GET
def product_detail_view(request, pk):
    product = get_object_or_404(
        Product.objects.active().select_related('category', 'seller', 'seller__merchant').with_stats(), pk=pk
    )
    others = Product.objects.active().exclude(pk=product.pk).select_related('category', 'seller', 'seller__merchant')
    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'reviews': product.reviews.select_related('buyer')[:10],
        'gallery': product.gallery,
        'can_manage': can_manage(request.user, product),
        'seller_products': others.filter(seller=product.seller).in_stock_first('-created_at')[:RELATED_LIMIT],
        'similar_products': others.filter(category=product.category)
                                  .exclude(seller=product.seller)
                                  .in_stock_first('-created_at')[:RELATED_LIMIT],
    })


STORE_SORTS = {
    'popular': ('Terlaris', ('-sold_count', '-created_at')),
    'newest': ('Terbaru', ('-created_at',)),
    'price_asc': ('Harga terendah', ('price',)),
    'price_desc': ('Harga tertinggi', ('-price',)),
}


@require_GET
def seller_store_view(request, username):
    seller = get_object_or_404(get_user_model(), username=username)
    if not is_seller(seller):
        raise Http404('Toko tidak ditemukan.')

    merchant = getattr(seller, 'merchant', None)
    all_products = Product.objects.active().filter(seller=seller)
    stats = all_products.with_stats()
    rated = [p for p in stats if p.rating_count]
    rating_count = sum(p.rating_count for p in rated)
    rating_avg = (sum(p.rating_avg * p.rating_count for p in rated) / rating_count) if rating_count else None
    locations = list(all_products.values_list('location', flat=True))

    keyword = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    sort = request.GET.get('sort') if request.GET.get('sort') in STORE_SORTS else 'popular'

    products = stats.select_related('category', 'seller', 'seller__merchant')
    if keyword:
        products = products.filter(name__icontains=keyword)
    if category:
        products = products.filter(category__slug=category)
    products = products.in_stock_first(*STORE_SORTS[sort][1])
    page = Paginator(products, PAGE_SIZE).get_page(request.GET.get('page'))

    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'marketplace/seller_store.html', {
        'seller': seller,
        'page_obj': page,
        'querystring': query.urlencode(),
        'product_count': len(stats),
        'available_count': sum(1 for p in stats if p.stock > 0),
        'sold_total': sum(p.sold_count for p in stats),
        'rating_avg': rating_avg,
        'rating_count': rating_count,
        'main_location': max(set(locations), key=locations.count) if locations else '',
        'store_categories': Category.objects.filter(products__in=all_products).distinct(),
        'keyword': keyword,
        'category': category,
        'sort': sort,
        'sort_options': [(key, label) for key, (label, _) in STORE_SORTS.items()],
        'is_owner': request.user.is_authenticated and request.user.pk == seller.pk,
        'merchant': merchant,
        'store_name': merchant.name if merchant else seller.username,
    })


@require_GET
def search_api(request):
    products, params = search_products(request.GET)
    limit = min(int(request.GET['limit']), 50) if request.GET.get('limit', '').isdigit() else 20
    return JsonResponse({
        'params': params,
        'count': products.count(),
        'results': [serialize_product(p) for p in products[:limit]],
    })


@require_GET
def product_api(request, pk):
    """Detail satu produk aktif dalam JSON, format sama dengan item di /api/search/."""
    product = (Product.objects.active().select_related('category', 'seller', 'seller__merchant')
               .prefetch_related('images').with_stats().filter(pk=pk).first())
    if product is None:
        return JsonResponse({'error': 'Produk tidak ditemukan.'}, status=404)
    data = serialize_product(product)
    data.update({
        'url': request.build_absolute_uri(reverse('marketplace:product_detail', args=[product.pk])),
        'gallery': [request.build_absolute_uri(photo) for photo in product.gallery],
        'harvested_at': product.harvested_at.isoformat() if product.harvested_at else None,
        'pickup_address': product.pickup_address,
        'pickup_notes': product.pickup_notes,
        'sold_count': product.sold_count,
        'rating_avg': round(product.rating_avg, 1) if product.rating_avg is not None else None,
        'rating_count': product.rating_count,
    })
    return JsonResponse(data)


@seller_required
def my_products_view(request):
    products = Product.objects.filter(seller=request.user).select_related('category')
    return render(request, 'marketplace/my_products.html', {
        'active_products': [p for p in products if p.is_active],
        'archived_products': [p for p in products if not p.is_active],
    })


@seller_required
def product_create_view(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        product = form.save(commit=False)
        product.seller = request.user
        product.save()
        form.save_images(product)
        messages.success(request, f'Produk "{product.name}" berhasil ditambahkan.')
        return redirect('marketplace:my_products')
    return render(request, 'marketplace/product_form.html', {'form': form, 'is_edit': False})


def _get_managed_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if not can_manage(request.user, product):
        raise PermissionDenied('Kamu hanya dapat mengelola produk milikmu sendiri.')
    return product


@seller_required
def product_update_view(request, pk):
    product = _get_managed_product(request, pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Produk "{product.name}" berhasil diperbarui.')
        return redirect('marketplace:my_products')
    return render(request, 'marketplace/product_form.html', {
        'form': form, 'is_edit': True, 'product': product,
    })


@require_POST
@seller_required
def product_archive_view(request, pk):
    product = _get_managed_product(request, pk)
    product.is_active = not product.is_active
    product.save(update_fields=['is_active', 'updated_at'])
    if product.is_active:
        messages.success(request, f'Produk "{product.name}" kembali ditampilkan.')
    else:
        messages.success(request, f'Produk "{product.name}" diarsipkan.')
    return redirect('marketplace:my_products')


@require_POST
@seller_required
def product_delete_view(request, pk):
    product = _get_managed_product(request, pk)
    if product.is_active:
        messages.error(request, 'Arsipkan produk terlebih dahulu sebelum menghapus permanen.')
        return redirect('marketplace:my_products')
    name = product.name
    product.delete()
    messages.success(request, f'Produk "{name}" dihapus permanen.')
    return redirect('marketplace:my_products')


def _wants_json(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _quantity(request, default=1):
    try:
        return int(request.POST.get('quantity', default))
    except (TypeError, ValueError):
        return default


@login_required
def cart_view(request):
    items = list(cart.cart_items(request.user))
    return render(request, 'marketplace/cart.html', {
        'groups': cart.group_by_seller(items),
        'items': items,
        'total': cart.selected_total(items),
        'selected_count': sum(item.quantity for item in items if item.selected),
    })


@require_POST
@login_required
def cart_add_view(request, pk):
    product = get_object_or_404(Product.objects.active(), pk=pk)
    try:
        cart.add_to_cart(request.user, product, _quantity(request))
    except cart.CartError as error:
        if _wants_json(request):
            return JsonResponse({'ok': False, 'message': str(error)}, status=400)
        messages.error(request, str(error))
        return redirect('marketplace:product_detail', pk=pk)

    message = f'{product.name} ditambahkan ke keranjang.'
    if _wants_json(request):
        return JsonResponse({'ok': True, 'message': message, 'count': cart.cart_count(request.user)})
    messages.success(request, message)
    return redirect('marketplace:cart')


@require_POST
@login_required
def buy_now_view(request, pk):
    product = get_object_or_404(Product.objects.active(), pk=pk)
    try:
        cart.buy_now(request.user, product, _quantity(request))
    except cart.CartError as error:
        messages.error(request, str(error))
        return redirect('marketplace:product_detail', pk=pk)
    return redirect('marketplace:cart')


@require_POST
@login_required
def cart_update_view(request, pk):
    item = get_object_or_404(CartItem, pk=pk, user=request.user)
    try:
        cart.update_quantity(item, _quantity(request, item.quantity))
    except cart.CartError as error:
        messages.error(request, str(error))
    return redirect('marketplace:cart')


@require_POST
@login_required
def cart_remove_view(request, pk):
    get_object_or_404(CartItem, pk=pk, user=request.user).delete()
    return redirect('marketplace:cart')


@require_POST
@login_required
def cart_select_view(request):
    selected = request.POST.get('selected') == '1'
    target = request.POST.get('target', 'all')
    try:
        target_id = int(request.POST.get('id', ''))
    except ValueError:
        target_id = None
    if target == 'item' and target_id:
        cart.set_selected(request.user, selected, item_id=target_id)
    elif target == 'seller' and target_id:
        cart.set_selected(request.user, selected, seller_id=target_id)
    else:
        cart.set_selected(request.user, selected)
    return redirect('marketplace:cart')


@require_POST
@login_required
def checkout_view(request):
    try:
        orders = cart.checkout(request.user, note=request.POST.get('note', '').strip()[:500])
    except cart.CartError as error:
        messages.error(request, str(error))
        return redirect('marketplace:cart')
    if len(orders) == 1:
        messages.success(request, 'Pesanan dibuat. Tunggu konfirmasi penjual.')
        return redirect('marketplace:order_detail', pk=orders[0].pk)
    messages.success(request, f'{len(orders)} pesanan dibuat, satu untuk setiap toko.')
    return redirect('marketplace:orders')


PROGRESS_STEPS = [
    (Order.PENDING, 'Dipesan'),
    (Order.CONFIRMED, 'Disiapkan'),
    (Order.READY, 'Siap diambil'),
    (Order.COMPLETED, 'Selesai'),
]

ORDER_TABS = [
    ('', 'Semua'),
    (Order.PENDING, 'Menunggu'),
    (Order.CONFIRMED, 'Disiapkan'),
    (Order.READY, 'Siap diambil'),
    (Order.COMPLETED, 'Selesai'),
    (Order.CANCELLED, 'Dibatalkan'),
]


def _order_list(request, orders, template, extra=None):
    status = request.GET.get('status', '')
    counts = {key: orders.filter(status=key).count() for key, _ in ORDER_TABS if key}
    if status in counts:
        orders = orders.filter(status=status)
    context = {
        'orders': orders.select_related('buyer', 'seller').prefetch_related('items'),
        'tabs': [(key, label, counts.get(key)) for key, label in ORDER_TABS],
        'status': status,
    }
    context.update(extra or {})
    return render(request, template, context)


@login_required
def orders_view(request):
    return _order_list(request, Order.objects.filter(buyer=request.user), 'marketplace/orders.html')


@seller_required
def sales_view(request):
    return _order_list(request, Order.objects.filter(seller=request.user), 'marketplace/sales.html')


def _get_order_for(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('buyer', 'seller').prefetch_related('items__product'), pk=pk
    )
    if request.user.id not in (order.buyer_id, order.seller_id):
        raise Http404('Pesanan tidak ditemukan.')
    return order


@login_required
def order_detail_view(request, pk):
    order = _get_order_for(request, pk)
    items = list(order.items.all())
    for item in items:
        item.can_review = cart.can_review(item, request.user)
    return render(request, 'marketplace/order_detail.html', {
        'order': order,
        'items': items,
        'is_seller_view': request.user.id == order.seller_id,
        'actions': cart.allowed_actions(order, request.user),
        'progress_steps': PROGRESS_STEPS,
        'current_step': [key for key, _ in PROGRESS_STEPS].index(order.status) + 1
                        if order.status != Order.CANCELLED else 0,
    })


ACTION_MESSAGES = {
    'confirm': 'Pesanan dikonfirmasi.',
    'ready': 'Pesanan ditandai siap diambil.',
    'complete': 'Pesanan selesai.',
    'receive': 'Terima kasih! Pesanan selesai, beri ulasan untuk produknya.',
    'cancel': 'Pesanan dibatalkan dan stok dikembalikan.',
}


@require_POST
@login_required
def order_action_view(request, pk, action):
    order = _get_order_for(request, pk)
    try:
        cart.change_status(order, request.user, action, reason=request.POST.get('reason', ''))
        messages.success(request, ACTION_MESSAGES.get(action, 'Status diperbarui.'))
    except cart.CartError as error:
        messages.error(request, str(error))
    next_url = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
        next_url = reverse('marketplace:order_detail', args=[pk])
    return redirect(next_url)


@require_POST
@login_required
def review_create_view(request, pk):
    item = get_object_or_404(OrderItem.objects.select_related('order'), pk=pk,
                             order__buyer=request.user)
    try:
        rating = int(request.POST.get('rating', 0))
    except ValueError:
        rating = 0
    try:
        cart.add_review(item, request.user, rating, request.POST.get('comment', ''))
        messages.success(request, 'Ulasan terkirim.')
    except cart.CartError as error:
        messages.error(request, str(error))
    return redirect('marketplace:order_detail', pk=item.order_id)
