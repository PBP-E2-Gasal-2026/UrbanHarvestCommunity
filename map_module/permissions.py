"""Aturan hak akses modul peta.

Peran mengikuti ``authentication.models.ROLE_CHOICES``: admin, user, farmer,
farmer-seller. Admin juga dikenali lewat ``is_staff`` / ``is_superuser``.
"""

from .models import Location

# PRD §5.1 butir 3: "Pengguna baru memperoleh peran Petani". Registrasi saat ini
# memberi peran 'user', jadi 'user' diperlakukan sama dengan Petani ('farmer').
# Ubah di sini saja bila modul autentikasi memisahkan keduanya.
MEMBER_ROLES = frozenset({'user', 'farmer', 'farmer-seller'})
SELLER_ROLES = frozenset({'farmer-seller'})


def role_names(user):
    """Himpunan nama peran user. Di-cache pada objek user agar 1 query per request."""
    if not user.is_authenticated:
        return frozenset()
    cached = getattr(user, '_map_role_names', None)
    if cached is None:
        cached = frozenset(user.roles.values_list('name', flat=True))
        user._map_role_names = cached
    return cached


def is_admin(user):
    return user.is_authenticated and (
        user.is_staff or user.is_superuser or 'admin' in role_names(user)
    )


def allowed_kinds(user):
    """Jenis lokasi yang boleh dibuat user ini (kosong = tidak boleh membuat)."""
    if is_admin(user):
        return list(Location.Kind.values)
    roles = role_names(user)
    kinds = []
    if roles & MEMBER_ROLES:
        kinds += list(Location.GARDEN_KINDS)
    if roles & SELLER_ROLES:
        kinds += list(Location.SELLER_KINDS)
    return kinds


def can_manage_locations(user):
    return bool(allowed_kinds(user))


def can_edit_location(user, location):
    if not user.is_authenticated:
        return False
    return is_admin(user) or (location.owner_id is not None and location.owner_id == user.pk)


def can_view_details(user, location):
    """Alamat lengkap + kontak tampil sesuai pilihan pemilik; pemilik dan Admin selalu boleh."""
    visibility = location.detail_visibility
    if visibility == Location.DetailVisibility.PUBLIC:
        return True
    if not user.is_authenticated:
        return False
    if visibility == Location.DetailVisibility.MEMBERS:
        return True
    return can_edit_location(user, location)
