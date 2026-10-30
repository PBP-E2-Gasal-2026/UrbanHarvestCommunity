from django import template
from django.utils import timezone

register = template.Library()

UNITS = (
    (365 * 24 * 3600, 'tahun'),
    (30 * 24 * 3600, 'bulan'),
    (7 * 24 * 3600, 'minggu'),
    (24 * 3600, 'hari'),
    (3600, 'jam'),
    (60, 'menit'),
)


@register.filter
def waktu_lalu(value):
    """Waktu relatif berbahasa Indonesia, mis. "5 menit yang lalu".

    Dipakai menggantikan ``timesince`` yang mengikuti LANGUAGE_CODE proyek (en-us).
    """
    if not value:
        return ''
    seconds = int((timezone.now() - value).total_seconds())
    if seconds < 60:
        return 'baru saja'
    for size, name in UNITS:
        if seconds >= size:
            return f'{seconds // size} {name} yang lalu'
    return 'baru saja'


@register.filter
def has_liked(user, post):
    """Apakah pengguna sudah menyukai post (memakai likes yang sudah di-prefetch)."""
    return user.is_authenticated and any(liker.pk == user.pk for liker in post.likes.all())


BULAN = ('Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des')


@register.filter
def waktu_lalu_singkat(value):
    """Waktu ringkas ala timeline: "baru", "5m", "3j", "2h", lalu "12 Okt"."""
    if not value:
        return ''
    seconds = int((timezone.now() - value).total_seconds())
    if seconds < 60:
        return 'baru'
    if seconds < 3600:
        return f'{seconds // 60}m'
    if seconds < 24 * 3600:
        return f'{seconds // 3600}j'
    if seconds < 7 * 24 * 3600:
        return f'{seconds // 86400}h'
    local = timezone.localtime(value)
    label = f'{local.day} {BULAN[local.month - 1]}'
    return label if local.year == timezone.localdate().year else f'{label} {local.year}'
