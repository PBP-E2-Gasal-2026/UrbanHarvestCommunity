"""Query dan serialisasi lokasi. Satu-satunya tempat bentuk data marker didefinisikan.

Kontrak untuk modul lain ada di docs/map_module.md. Ringkasnya:
- Marketplace → Peta: ``product_map_url(product)``, ``Location.get_map_url()``,
  ``locations_for_owner(seller)``.
- Admin dashboard: ``summary_counts()``.
"""

from django.apps import apps
from django.core.exceptions import FieldError
from django.db.models import Count, Q
from django.urls import NoReverseMatch, reverse

from .geo import format_distance, haversine_km, parse_coordinates
from .models import Location
from .permissions import can_view_details

MAX_MARKERS = 500  # batas pengaman agar respons/peta tetap ringan pada MVP
RADIUS_CHOICES_KM = (1, 3, 5, 10, 25)  # pilihan di UI; API menerima angka 0 < r <= MAX_RADIUS_KM
MAX_RADIUS_KM = 500


def active_locations():
    return Location.objects.filter(is_active=True).select_related('owner')


def locations_for_owner(user):
    """Lokasi aktif milik satu merchant/penjual (dipakai marketplace untuk tautan ke peta)."""
    return active_locations().filter(owner=user)


def search_locations(queryset, query='', kinds=None):
    """Filter teks dan jenis. Jenis tak dikenal diabaikan.

    Teks dicocokkan ke field ringkasan publik saja (nama, wilayah, deskripsi,
    komoditas, pengelola). Alamat lengkap sengaja TIDAK dicari, supaya Guest
    tidak bisa menebak alamat yang disembunyikan pemiliknya lewat pencarian.
    """
    query = (query or '').strip()
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(area__icontains=query)
            | Q(description__icontains=query)
            | Q(commodities__icontains=query)
            | Q(schedule__icontains=query)
            | Q(managed_by__icontains=query)
        )
    valid_kinds = [k for k in (kinds or []) if k in Location.Kind.values]
    if valid_kinds:
        queryset = queryset.filter(kind__in=valid_kinds)
    return queryset


def parse_kinds(raw_values):
    """Terima ['a,b', 'c'] atau 'a,b' dan kembalikan daftar jenis yang valid."""
    if isinstance(raw_values, str):
        raw_values = [raw_values]
    kinds = []
    for raw in raw_values or []:
        kinds.extend(part.strip() for part in str(raw).split(','))
    return [k for k in dict.fromkeys(kinds) if k in Location.Kind.values]


def parse_radius(raw):
    """None/'' = tanpa batas. Selain itu harus angka 0 < r <= MAX_RADIUS_KM, kalau tidak ValueError."""
    if raw in (None, ''):
        return None
    if isinstance(raw, bool):  # float(True) == 1.0, jadi tolak eksplisit
        # Sengaja ValueError (bukan TypeError): view memetakan ValueError ke respons 400.
        raise ValueError('Radius harus berupa angka.')  # noqa: TRY004
    try:
        radius = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError('Radius harus berupa angka.') from exc
    if not 0 < radius <= MAX_RADIUS_KM:
        raise ValueError(f'Radius harus lebih dari 0 dan paling besar {MAX_RADIUS_KM} km.')
    return radius


def _reverse_or_none(name, *args):
    try:
        return reverse(name, args=args)
    except NoReverseMatch:
        return None


def _store_url(location):
    """Tautan etalase merchant bila modul marketplace terpasang; kalau tidak, None."""
    if location.owner is None or location.kind not in Location.SELLER_KINDS:
        return None
    return _reverse_or_none('marketplace:seller_store', location.owner.username)


def serialize_location(location, user, distance_km=None):
    """Dict JSON-aman untuk satu lokasi. Alamat lengkap & kontak hanya bila user berhak."""
    has_details = bool(location.address or location.contact_info)
    show_details = has_details and can_view_details(user, location)
    data = {
        'id': location.pk,
        'kind': location.kind,
        'kind_label': location.get_kind_display(),
        'kind_short': location.short_label,
        'badge_tone': location.badge_tone,
        'name': location.name,
        'lat': float(location.latitude),
        'lng': float(location.longitude),
        'area': location.area,
        'description': location.description,
        'commodities': ', '.join(location.commodity_list),
        'schedule': location.schedule,
        'managed_by': location.manager_name,
        'photo_url': location.photo_url,
        'detail_url': location.get_absolute_url(),
        'store_url': _store_url(location),
        'address': location.address if show_details else '',
        'contact': location.contact_info if show_details else '',
        # Ada detail yang disembunyikan. Guest ditawari "Masuk untuk melihat";
        # pengguna yang sudah masuk diberi tahu bahwa detail hanya untuk pemilik.
        'detail_locked': has_details and not show_details,
        'detail_login_required': has_details and not show_details and not user.is_authenticated,
        'detail_owner_only': has_details and not show_details and user.is_authenticated,
        'distance_km': None,
        'distance_label': '',
    }
    if distance_km is not None:
        data['distance_km'] = round(distance_km, 3)
        data['distance_label'] = format_distance(distance_km)
    return data


def build_payload(locations, user, origin=None, radius_km=None):
    """Serialisasi daftar lokasi.

    Bila ``origin=(lat, lng)``: urutkan dari yang terdekat, dan bila ``radius_km``
    diberikan, buang lokasi yang lebih jauh dari radius itu.
    """
    if origin is None:
        return [serialize_location(loc, user) for loc in locations]
    lat, lng = origin
    with_distance = [
        (haversine_km(lat, lng, loc.latitude, loc.longitude), loc) for loc in locations
    ]
    if radius_km is not None:
        with_distance = [pair for pair in with_distance if pair[0] <= radius_km]
    with_distance.sort(key=lambda pair: (pair[0], pair[1].name.lower()))
    return [serialize_location(loc, user, distance_km=km) for km, loc in with_distance]


# ------------------------------------------------------------ marketplace → peta


def product_map_url(product):
    """URL peta yang langsung membuka titik pengambilan satu produk (PRD §5.5 butir 5)."""
    pk = getattr(product, 'pk', product)
    return f"{reverse('map_module:map')}?product={int(pk)}"


def _product_model():
    """Model Product marketplace, atau None bila modul itu belum terpasang."""
    if not apps.is_installed('marketplace'):
        return None
    try:
        return apps.get_model('marketplace', 'Product')
    except LookupError:
        return None


def product_pin(product_id):
    """Titik pengambilan satu produk aktif sebagai dict marker, atau None.

    Marketplace menyimpan koordinat titik ambil di ``Product`` (latitude,
    longitude, location, pickup_address). Dibaca lewat ``apps.get_model`` agar
    modul peta tidak meng-import marketplace dan tetap jalan tanpanya.
    """
    model = _product_model()
    if model is None:
        return None
    try:
        row = (
            model.objects.filter(pk=product_id, is_active=True)
            .values('pk', 'name', 'location', 'pickup_address', 'latitude', 'longitude')
            .first()
        )
    except FieldError:
        return None  # kontrak field marketplace berubah: tampilkan peta biasa, jangan 500
    if row is None:
        return None
    try:
        lat, lng = parse_coordinates(row['latitude'], row['longitude'])
    except ValueError:
        return None
    return {
        'id': row['pk'],
        'name': row['name'],
        'lat': lat,
        'lng': lng,
        'area': row['location'] or '',
        'address': row['pickup_address'] or '',
        'detail_url': _reverse_or_none('marketplace:product_detail', row['pk']),
    }


# ------------------------------------------------------------------ admin


def summary_counts():
    """Jumlah lokasi aktif per kelompok, untuk dashboard Admin (PRD §5.6)."""
    counts = active_locations().aggregate(
        gardens=Count('pk', filter=Q(kind__in=Location.GARDEN_KINDS)),
        merchants=Count('pk', filter=Q(kind=Location.Kind.MERCHANT)),
        pickup_points=Count('pk', filter=Q(kind=Location.Kind.PICKUP_POINT)),
        total=Count('pk'),
    )
    return counts
