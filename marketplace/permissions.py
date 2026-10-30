from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse

SELLER_ROLES = ('farmer-seller', 'admin')


def is_seller(user):
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.roles.filter(name__in=SELLER_ROLES).exists()


def can_manage(user, product):
    if not is_seller(user):
        return False
    return product.seller_id == user.id or user.is_superuser or user.roles.filter(name='admin').exists()


def seller_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse('authentication:login'))
        if not is_seller(request.user):
            raise PermissionDenied('Hanya Petani - Penjual yang dapat mengelola produk.')
        return view(request, *args, **kwargs)

    return wrapper
