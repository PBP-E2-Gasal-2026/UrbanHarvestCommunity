from itertools import groupby

from django.db import transaction
from django.db.models import F

from .models import CartItem, Order, OrderItem, Product, Review


class CartError(Exception):
    """Kesalahan yang aman ditampilkan ke pengguna."""


# ---------- Keranjang ----------

def cart_items(user):
    return (CartItem.objects.filter(user=user)
            .select_related('product', 'product__seller', 'product__seller__merchant', 'product__category')
            .order_by('product__seller__username', '-added_at'))


def cart_count(user):
    if not user.is_authenticated:
        return 0
    return sum(CartItem.objects.filter(user=user).values_list('quantity', flat=True))


def group_by_seller(items):
    """Kelompokkan item keranjang per toko, seperti keranjang Shopee."""
    groups = []
    for seller, seller_items in groupby(items, key=lambda item: item.product.seller):
        seller_items = list(seller_items)
        groups.append({
            'seller': seller,
            'name': seller_items[0].product.merchant_name,
            'items': seller_items,
            'all_selected': all(item.selected for item in seller_items),
            'subtotal': sum(item.subtotal for item in seller_items if item.selected),
        })
    return groups


def selected_total(items):
    return sum(item.subtotal for item in items if item.selected)


def add_to_cart(user, product, quantity=1, replace=False):
    if quantity < 1:
        raise CartError('Jumlah minimal 1.')
    if product.seller_id == user.id:
        raise CartError('Kamu tidak bisa membeli produkmu sendiri.')
    if not product.is_available:
        raise CartError('Produk ini sedang tidak tersedia.')

    item, created = CartItem.objects.get_or_create(
        user=user, product=product, defaults={'quantity': 0}
    )
    new_quantity = quantity if replace else item.quantity + quantity
    if new_quantity < product.min_order:
        if created:
            item.delete()
        raise CartError(f'Minimal pembelian {product.name} adalah {product.min_order} {product.unit}.')
    if new_quantity > product.stock:
        if created:
            item.delete()
        raise CartError(f'Stok {product.name} hanya {product.stock}.')
    item.quantity = new_quantity
    item.selected = True
    item.save(update_fields=['quantity', 'selected'])
    return item


def buy_now(user, product, quantity=1):
    """Beli sekarang: hanya produk ini yang dicentang untuk checkout."""
    item = add_to_cart(user, product, quantity, replace=True)
    CartItem.objects.filter(user=user).exclude(pk=item.pk).update(selected=False)
    return item


def update_quantity(item, quantity):
    if quantity <= 0:
        item.delete()
        return None
    if quantity < item.product.min_order:
        raise CartError(f'Minimal pembelian {item.product.name} adalah {item.product.min_order} {item.product.unit}.')
    if quantity > item.product.stock:
        raise CartError(f'Stok {item.product.name} hanya {item.product.stock}.')
    item.quantity = quantity
    item.save(update_fields=['quantity'])
    return item


def set_selected(user, selected, item_id=None, seller_id=None):
    items = CartItem.objects.filter(user=user)
    if item_id is not None:
        items = items.filter(pk=item_id)
    elif seller_id is not None:
        items = items.filter(product__seller_id=seller_id)
    items.update(selected=selected)


# ---------- Checkout & pesanan ----------

@transaction.atomic
def checkout(user, note=''):
    """Buat satu pesanan per penjual dari item yang dicentang."""
    items = list(cart_items(user).filter(selected=True))
    if not items:
        raise CartError('Pilih minimal satu produk untuk di-checkout.')

    # Kunci baris produk agar dua checkout bersamaan tidak menjual stok yang sama.
    products = Product.objects.select_for_update().in_bulk([item.product_id for item in items])
    for item in items:
        product = products[item.product_id]
        if not product.is_active or product.stock < item.quantity:
            raise CartError(f'Stok {product.name} tidak mencukupi (tersisa {product.stock}).')

    orders = []
    for group in group_by_seller(items):
        order = Order.objects.create(buyer=user, seller=group['seller'], note=note)
        total = 0
        for item in group['items']:
            product = products[item.product_id]
            OrderItem.objects.create(
                order=order, product=product, product_name=product.name, price=product.price,
                quantity=item.quantity, pickup_location=product.location,
            )
            Product.objects.filter(pk=product.pk).update(stock=F('stock') - item.quantity)
            total += product.price * item.quantity
        order.total = total
        order.save(update_fields=['total'])
        orders.append(order)

    CartItem.objects.filter(pk__in=[item.pk for item in items]).delete()
    return orders


# Aksi yang boleh dilakukan per peran, dari status asal ke status tujuan.
SELLER_TRANSITIONS = {
    'confirm': (Order.PENDING, Order.CONFIRMED),
    'ready': (Order.CONFIRMED, Order.READY),
    'complete': (Order.READY, Order.COMPLETED),
}
BUYER_TRANSITIONS = {
    'receive': (Order.READY, Order.COMPLETED),
}
CANCELLABLE = {
    'seller': (Order.PENDING, Order.CONFIRMED),
    'buyer': (Order.PENDING,),
}


def _restore_stock(order):
    for item in order.items.all():
        if item.product_id:
            Product.objects.filter(pk=item.product_id).update(stock=F('stock') + item.quantity)


@transaction.atomic
def change_status(original, user, action, reason=''):
    order = Order.objects.select_for_update().get(pk=original.pk)
    if user.id == order.seller_id:
        role, transitions = 'seller', SELLER_TRANSITIONS
    elif user.id == order.buyer_id:
        role, transitions = 'buyer', BUYER_TRANSITIONS
    else:
        raise CartError('Kamu tidak memiliki akses ke pesanan ini.')

    if action == 'cancel':
        if order.status not in CANCELLABLE[role]:
            raise CartError('Pesanan ini tidak bisa dibatalkan lagi.')
        _restore_stock(order)
        order.status = Order.CANCELLED
        order.cancel_reason = reason[:200] or ('Ditolak penjual' if role == 'seller' else 'Dibatalkan pembeli')
    elif action in transitions:
        source, target = transitions[action]
        if order.status != source:
            raise CartError('Status pesanan sudah berubah. Muat ulang halaman.')
        order.status = target
    else:
        raise CartError('Aksi tidak dikenal.')

    order.save(update_fields=['status', 'cancel_reason', 'updated_at'])
    # Samakan objek milik pemanggil agar tidak memegang status lama.
    original.status, original.cancel_reason = order.status, order.cancel_reason
    return order


def allowed_actions(order, user):
    actions = []
    if user.id == order.seller_id:
        actions = [a for a, (source, _) in SELLER_TRANSITIONS.items() if order.status == source]
        if order.status in CANCELLABLE['seller']:
            actions.append('cancel')
    elif user.id == order.buyer_id:
        actions = [a for a, (source, _) in BUYER_TRANSITIONS.items() if order.status == source]
        if order.status in CANCELLABLE['buyer']:
            actions.append('cancel')
    return actions


# ---------- Ulasan ----------

def can_review(item, user):
    return (item.order.buyer_id == user.id and item.order.status == Order.COMPLETED
            and item.product_id is not None and not hasattr(item, 'review'))


def add_review(item, user, rating, comment=''):
    if not can_review(item, user):
        raise CartError('Ulasan hanya bisa diberikan sekali untuk pesanan yang sudah selesai.')
    if rating not in range(1, 6):
        raise CartError('Rating harus 1 sampai 5.')
    return Review.objects.create(
        order_item=item, product_id=item.product_id, buyer=user,
        rating=rating, comment=comment.strip()[:1000],
    )
