"""Fungsi geografi murni (tanpa database) untuk modul peta.

Dipisah dari model/view supaya mudah diuji dan tidak bergantung pada Django.
"""

from math import asin, cos, isfinite, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088  # jari-jari rata-rata bumi (IUGG)


def haversine_km(lat1, lng1, lat2, lng2):
    """Jarak lingkaran-besar antara dua titik (derajat), dalam kilometer.

    a = sin²(Δφ/2) + cos φ1 · cos φ2 · sin²(Δλ/2)
    d = 2R · asin(√a)
    """
    phi1, phi2 = radians(float(lat1)), radians(float(lat2))
    d_phi = phi2 - phi1
    d_lambda = radians(float(lng2) - float(lng1))
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    # min(1, ...) menjaga dari galat pembulatan floating point di titik antipodal.
    return 2 * EARTH_RADIUS_KM * asin(min(1.0, sqrt(a)))


def parse_coordinates(lat, lng):
    """Ubah input mentah (str/angka) menjadi (lat, lng) float yang valid.

    Raises ValueError bila bukan angka hingga, atau di luar rentang
    lat -90..90 / lng -180..180.
    """
    try:
        lat_f, lng_f = float(lat), float(lng)
    except (TypeError, ValueError) as exc:
        raise ValueError('Koordinat harus berupa angka.') from exc
    if not (isfinite(lat_f) and isfinite(lng_f)):
        raise ValueError('Koordinat harus berupa angka hingga.')
    if not -90 <= lat_f <= 90:
        raise ValueError('Latitude harus di antara -90 dan 90.')
    if not -180 <= lng_f <= 180:
        raise ValueError('Longitude harus di antara -180 dan 180.')
    return lat_f, lng_f


def format_distance(km):
    """'850 m' untuk < 1 km, '3,4 km' untuk < 100 km, '120 km' selebihnya."""
    if km < 1:
        return f'{round(km * 1000 / 10) * 10:d} m'
    if km < 100:
        return f'{km:.1f}'.replace('.', ',') + ' km'
    return f'{round(km):d} km'
