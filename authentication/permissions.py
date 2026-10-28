from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def has_role(user, *roles):
    if not user.is_authenticated:
        return False
    return user.roles.filter(name__in=roles).exists()


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or has_role(user, 'admin'))


def _guard(check):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not check(request.user):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def role_required(*roles):
    return _guard(lambda user: has_role(user, *roles))


admin_required = _guard(is_admin)

MEMBER_ROLES = ('farmer', 'farmer-seller', 'admin')
SELLER_ROLES = ('farmer-seller', 'admin')


def is_member(user):
    """Boleh post, like, komentar, pakai LLM search (Petani, Penjual, Admin)."""
    return is_admin(user) or has_role(user, *MEMBER_ROLES)


def is_seller(user):
    """Boleh kelola produk dan etalase (Penjual dan Admin)."""
    return is_admin(user) or has_role(user, *SELLER_ROLES)


member_required = _guard(is_member)
seller_required = _guard(is_seller)