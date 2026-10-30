import json
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import LocationForm
from .geo import parse_coordinates
from .models import Location
from .permissions import (
    allowed_kinds,
    can_edit_location,
    can_manage_locations,
    is_admin,
)
from .services import (
    MAX_MARKERS,
    RADIUS_CHOICES_KM,
    active_locations,
    build_payload,
    parse_kinds,
    parse_radius,
    product_pin,
    search_locations,
    serialize_location,
)

LOGIN_URL = 'authentication:login'


def _require_manager(user):
    if not can_manage_locations(user):
        raise PermissionDenied('Hanya Petani, Petani–Penjual, atau Admin yang dapat mengelola lokasi.')


_ID_PATTERN = re.compile(r'[0-9]{1,18}')  # ASCII saja; 18 digit < batas bigint (2^63-1)


def _parse_id(raw):
    """ID dari query string, atau None. Tidak pakai str.isdigit() karena '²'.isdigit() == True."""
    if raw and _ID_PATTERN.fullmatch(raw):
        return int(raw)
    return None


def _filtered_locations(query, kinds):
    return list(search_locations(active_locations(), query, kinds)[:MAX_MARKERS])


# ---------------------------------------------------------------- halaman peta


@ensure_csrf_cookie  # dibutuhkan JS untuk POST "dekat saya" (termasuk Guest)
def map_page(request):
    """Peta publik. Filter awal dari query string; sisanya ditangani JS lewat API."""
    query = request.GET.get('q', '').strip()[:100]
    kinds = parse_kinds(request.GET.getlist('kind'))
    locations = _filtered_locations(query, kinds)

    focus_id = _parse_id(request.GET.get('focus'))
    # Lokasi yang difokuskan tetap ditampilkan walau tersaring filter jenis/teks,
    # supaya tautan ?focus= tidak berujung pesan "lokasi tidak tersedia".
    if focus_id is not None and all(loc.pk != focus_id for loc in locations):
        focused = active_locations().filter(pk=focus_id).first()
        if focused is not None:
            locations.insert(0, focused)

    # ?product=<id>: buka titik pengambilan produk marketplace (PRD §5.5 butir 5).
    pin = None
    product_missing = False
    if request.GET.get('product'):
        product_id = _parse_id(request.GET['product'])
        pin = product_pin(product_id) if product_id is not None else None
        product_missing = pin is None

    context = {
        'locations': build_payload(locations, request.user),
        'kind_choices': Location.Kind.choices,
        'active_kinds': kinds,
        'query': query,
        'config': {
            'api_url': reverse('map_module:api_locations'),
            'nearby_url': reverse('map_module:api_nearby'),
            'login_url': f"{reverse(LOGIN_URL)}?next={reverse('map_module:map')}",
            'focus_id': focus_id,
            'active_kinds': kinds,
            'product_pin': pin,
            'product_missing': product_missing,
        },
        'radius_choices': RADIUS_CHOICES_KM,
        'can_manage': can_manage_locations(request.user),
        'truncated': len(locations) >= MAX_MARKERS,
    }
    return render(request, 'map_module/map.html', context)


@require_GET
def location_detail(request, pk):
    location = get_object_or_404(Location.objects.select_related('owner'), pk=pk)
    can_edit = can_edit_location(request.user, location)
    if not location.is_active and not can_edit:
        raise Http404('Lokasi tidak ditemukan.')
    context = {
        'location': location,
        'data': serialize_location(location, request.user),
        'can_edit': can_edit,
    }
    return render(request, 'map_module/location_detail.html', context)


# ------------------------------------------------------------------ kelola data


@login_required(login_url=LOGIN_URL)
def my_locations(request):
    _require_manager(request.user)
    qs = Location.objects.select_related('owner').order_by('name')
    if not is_admin(request.user):
        qs = qs.filter(owner=request.user)
    return render(request, 'map_module/my_locations.html', {'locations': qs})


@login_required(login_url=LOGIN_URL)
@require_http_methods(['GET', 'POST'])
def location_create(request):
    _require_manager(request.user)
    form = LocationForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        location = form.save(commit=False)
        location.owner = request.user
        location.save()
        messages.success(request, f'Lokasi "{location.name}" berhasil ditambahkan.')
        return redirect(location)
    return render(
        request,
        'map_module/location_form.html',
        {'form': form, 'mode': 'create', 'kinds_allowed': allowed_kinds(request.user)},
    )


@login_required(login_url=LOGIN_URL)
@require_http_methods(['GET', 'POST'])
def location_update(request, pk):
    location = get_object_or_404(Location, pk=pk)
    if not can_edit_location(request.user, location):
        raise PermissionDenied('Anda hanya dapat mengubah lokasi milik sendiri.')
    form = LocationForm(request.POST or None, instance=location, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Lokasi "{location.name}" berhasil diperbarui.')
        return redirect(location)
    return render(
        request,
        'map_module/location_form.html',
        {'form': form, 'mode': 'update', 'location': location},
    )


@login_required(login_url=LOGIN_URL)
@require_POST
def location_delete(request, pk):
    location = get_object_or_404(Location, pk=pk)
    if not can_edit_location(request.user, location):
        raise PermissionDenied('Anda hanya dapat menghapus lokasi milik sendiri.')
    name = location.name
    location.delete()
    messages.success(request, f'Lokasi "{name}" dihapus.')
    return redirect('map_module:my_locations')


# ------------------------------------------------------------------------- API


def _error(message, status=400):
    return JsonResponse({'error': message}, status=status)


@require_GET
def api_locations(request):
    """Daftar lokasi aktif. Query: ``q``, ``kind`` (boleh diulang / dipisah koma)."""
    locations = _filtered_locations(
        request.GET.get('q', '').strip()[:100], parse_kinds(request.GET.getlist('kind'))
    )
    results = build_payload(locations, request.user)
    return JsonResponse({'count': len(results), 'results': results})


@require_POST
def api_nearby(request):
    """Urutkan lokasi dari yang terdekat.

    Koordinat dikirim di body POST (bukan URL) dan **tidak disimpan**; hanya
    dipakai menghitung jarak pada request ini (PRD §5.5 butir 4, §9 Privasi).
    Body JSON: ``{"lat": -6.36, "lng": 106.82, "q": "", "kind": ["merchant"], "radius_km": 5}``.
    ``radius_km`` opsional; kosong/null = semua jarak.
    """
    try:
        body = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error('Body harus berupa JSON yang valid.')
    if not isinstance(body, dict):
        return _error('Body harus berupa objek JSON.')

    try:
        origin = parse_coordinates(body.get('lat'), body.get('lng'))
    except ValueError as exc:
        return _error(str(exc))

    query = body.get('q', '')
    kinds = body.get('kind', [])
    if not isinstance(query, str) or not isinstance(kinds, (list, str)):
        return _error('Parameter q harus teks dan kind harus daftar/teks.')

    try:
        radius_km = parse_radius(body.get('radius_km'))
    except ValueError as exc:
        return _error(str(exc))

    locations = _filtered_locations(query.strip()[:100], parse_kinds(kinds))
    results = build_payload(locations, request.user, origin=origin, radius_km=radius_km)
    return JsonResponse({'count': len(results), 'results': results})
