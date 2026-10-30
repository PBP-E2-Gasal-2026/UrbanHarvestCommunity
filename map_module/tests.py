import json
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from authentication.models import Role, Session, User

from .geo import format_distance, haversine_km, parse_coordinates
from .models import Location
from .permissions import allowed_kinds
from .services import (
    parse_kinds,
    parse_radius,
    product_map_url,
    product_pin,
    summary_counts,
)


def make_user(username, role=None, **extra):
    user = User.objects.create_user(
        username=username, email=f'{username}@example.com', password='pass12345!', **extra
    )
    if role:
        role_obj, _ = Role.objects.get_or_create(name=role, defaults={'description': role})
        user.roles.add(role_obj)
    return user


def login(client, user):
    """Login seperti ``login_view``: SingleSessionMiddleware menolak sesi tanpa baris Session."""
    client.force_login(user)
    Session.objects.create(
        user=user,
        session_token=client.session.session_key,
        expires_at=timezone.now() + timedelta(days=1),
    )


def make_location(**overrides):
    data = {
        'kind': Location.Kind.COMMUNITY_GARDEN,
        'name': 'Kebun Kota',
        'latitude': Decimal('-6.200000'),
        'longitude': Decimal('106.816666'),
        'area': 'Menteng, Jakarta Pusat',
        'address': 'Jl. Contoh No. 1',
    }
    data.update(overrides)
    return Location.objects.create(**data)


class GeoTests(SimpleTestCase):
    def test_haversine_zero_for_same_point(self):
        self.assertEqual(haversine_km(-6.2, 106.8, -6.2, 106.8), 0)

    def test_haversine_known_distance(self):
        # Jakarta (Monas) -> Bandung (Gedung Sate) kira-kira 117 km garis lurus.
        km = haversine_km(-6.1754, 106.8272, -6.9025, 107.6186)
        self.assertAlmostEqual(km, 117, delta=3)

    def test_haversine_one_degree_of_latitude(self):
        self.assertAlmostEqual(haversine_km(0, 0, 1, 0), 111.2, delta=0.2)

    def test_haversine_is_symmetric(self):
        a = haversine_km(-6.2, 106.8, -7.25, 112.75)
        b = haversine_km(-7.25, 112.75, -6.2, 106.8)
        self.assertAlmostEqual(a, b, places=9)

    def test_parse_coordinates_valid(self):
        self.assertEqual(parse_coordinates('-6.2', '106.8'), (-6.2, 106.8))

    def test_parse_coordinates_rejects_bad_input(self):
        for lat, lng in [
            ('abc', '1'), (None, '1'), ('1', None), ('91', '0'), ('0', '181'),
            ('nan', '0'), ('inf', '0'), ('', ''),
        ]:
            with self.subTest(lat=lat, lng=lng), self.assertRaises(ValueError):
                parse_coordinates(lat, lng)

    def test_format_distance(self):
        self.assertEqual(format_distance(0.85), '850 m')
        self.assertEqual(format_distance(3.44), '3,4 km')
        self.assertEqual(format_distance(120.4), '120 km')

    def test_parse_radius(self):
        self.assertIsNone(parse_radius(None))
        self.assertIsNone(parse_radius(''))
        self.assertEqual(parse_radius('5'), 5.0)
        self.assertEqual(parse_radius(2.5), 2.5)
        for bad in (0, -1, 501, 'abc', True, [], float('nan'), float('inf')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_radius(bad)

    def test_parse_kinds_ignores_unknown_and_splits_commas(self):
        self.assertEqual(
            parse_kinds(['merchant,bogus', 'pickup_point', 'merchant']),
            ['merchant', 'pickup_point'],
        )
        self.assertEqual(parse_kinds(None), [])


class LocationModelTests(TestCase):
    def test_latitude_out_of_range_rejected(self):
        loc = Location(kind='merchant', name='X', latitude=Decimal(95), longitude=Decimal(10))
        with self.assertRaises(ValidationError) as ctx:
            loc.full_clean()
        self.assertIn('latitude', ctx.exception.message_dict)

    def test_longitude_out_of_range_rejected(self):
        loc = Location(kind='merchant', name='X', latitude=Decimal(10), longitude=Decimal(-181))
        with self.assertRaises(ValidationError) as ctx:
            loc.full_clean()
        self.assertIn('longitude', ctx.exception.message_dict)

    def test_null_island_rejected(self):
        loc = Location(kind='merchant', name='X', latitude=Decimal(0), longitude=Decimal(0))
        with self.assertRaises(ValidationError):
            loc.full_clean()

    def test_map_url_focuses_location(self):
        loc = make_location()
        self.assertEqual(loc.get_map_url(), f"{reverse('map_module:map')}?focus={loc.pk}")


class PermissionTests(TestCase):
    def test_allowed_kinds_by_role(self):
        no_role = make_user('norole')
        plain = make_user('plain', 'user')
        farmer = make_user('farmer', 'farmer')
        seller = make_user('seller', 'farmer-seller')
        admin = make_user('boss', 'admin')
        gardens = {Location.Kind.COMMUNITY_GARDEN, Location.Kind.FARMER_GARDEN}
        self.assertEqual(allowed_kinds(no_role), [])
        # Registrasi memberi peran 'user'; PRD: pengguna baru = Petani.
        self.assertEqual(set(allowed_kinds(plain)), gardens)
        self.assertEqual(set(allowed_kinds(farmer)), gardens)
        self.assertEqual(set(allowed_kinds(seller)), set(Location.Kind.values))
        self.assertEqual(set(allowed_kinds(admin)), set(Location.Kind.values))


class MapPageAndApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.garden = make_location(name='Kebun Anggrek', description='Sayur hidroponik')
        cls.shop = make_location(
            name='Toko Tani', kind=Location.Kind.MERCHANT,
            latitude=Decimal('-6.400000'), longitude=Decimal('106.800000'),
        )
        cls.hidden = make_location(name='Kebun Rahasia', is_active=False)

    def test_map_page_renders_for_guest_without_hidden_locations(self):
        resp = self.client.get(reverse('map_module:map'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Kebun Anggrek')
        self.assertNotContains(resp, 'Kebun Rahasia')

    def test_map_page_empty_state_does_not_error(self):
        Location.objects.all().delete()
        self.assertEqual(self.client.get(reverse('map_module:map')).status_code, 200)

    def test_map_page_ignores_garbage_params(self):
        resp = self.client.get(reverse('map_module:map'), {'kind': 'nope', 'focus': 'abc', 'q': 'x' * 500})
        self.assertEqual(resp.status_code, 200)

    def test_referrer_policy_lets_osm_tiles_load(self):
        # OSM memblokir tile tanpa Referer; "same-origin" membuat peta 403 di PWS.
        resp = self.client.get(reverse('map_module:map'))
        self.assertEqual(resp['Referrer-Policy'], 'strict-origin-when-cross-origin')

    def test_focused_location_kept_even_when_filtered_out(self):
        resp = self.client.get(reverse('map_module:map'), {'kind': 'merchant', 'focus': self.garden.pk})
        names = [loc['name'] for loc in resp.context['locations']]
        self.assertEqual(names, ['Kebun Anggrek', 'Toko Tani'])
        # Lokasi nonaktif tetap tidak bisa dimunculkan lewat ?focus=.
        resp = self.client.get(reverse('map_module:map'), {'focus': self.hidden.pk})
        self.assertNotContains(resp, 'Kebun Rahasia')

    def test_unicode_digits_and_huge_ids_do_not_crash(self):
        # '²'.isdigit() == True tetapi int('²') gagal: dulu memicu 500.
        for value in ('²', '٣', '9' * 40, '-1', '1.5'):
            with self.subTest(value=value):
                resp = self.client.get(reverse('map_module:map'), {'focus': value, 'product': value})
                self.assertEqual(resp.status_code, 200)
                self.assertIsNone(resp.context['config']['focus_id'])

    def test_short_label_badge_tone_and_schedule_in_api(self):
        make_location(name='Titik UI', kind='pickup_point', schedule='Sabtu 08.00–11.00')
        data = {r['name']: r for r in self.client.get(reverse('map_module:api_locations')).json()['results']}
        self.assertEqual((data['Titik UI']['kind_short'], data['Titik UI']['badge_tone']), ('Titik ambil', 'warning'))
        self.assertEqual(data['Titik UI']['schedule'], 'Sabtu 08.00–11.00')
        self.assertEqual((data['Toko Tani']['kind_short'], data['Toko Tani']['badge_tone']), ('Merchant', 'brand'))
        self.assertEqual(data['Kebun Anggrek']['kind_short'], 'Komunitas')
        found = self.client.get(reverse('map_module:api_locations'), {'q': 'Sabtu'}).json()['results']
        self.assertEqual([r['name'] for r in found], ['Titik UI'])

    def test_search_matches_commodities_area_and_manager(self):
        make_location(name='Kebun Cabai', commodities='Cabai, tomat', area='Beji, Depok',
                      managed_by='Komunitas Hijau')
        url = reverse('map_module:api_locations')
        for q in ('tomat', 'Beji', 'Komunitas Hijau'):
            with self.subTest(q=q):
                names = [r['name'] for r in self.client.get(url, {'q': q}).json()['results']]
                self.assertEqual(names, ['Kebun Cabai'])

    def test_api_returns_only_active(self):
        data = self.client.get(reverse('map_module:api_locations')).json()
        names = {r['name'] for r in data['results']}
        self.assertEqual(names, {'Kebun Anggrek', 'Toko Tani'})
        self.assertEqual(data['count'], 2)

    def test_api_marker_coordinates_are_exact(self):
        data = self.client.get(reverse('map_module:api_locations'), {'q': 'Anggrek'}).json()
        self.assertEqual(data['results'][0]['lat'], -6.2)
        self.assertEqual(data['results'][0]['lng'], 106.816666)

    def test_api_filters_by_kind_and_query(self):
        url = reverse('map_module:api_locations')
        merchants = self.client.get(url, {'kind': 'merchant'}).json()['results']
        self.assertEqual([r['name'] for r in merchants], ['Toko Tani'])
        by_text = self.client.get(url, {'q': 'hidroponik'}).json()['results']
        self.assertEqual([r['name'] for r in by_text], ['Kebun Anggrek'])

    def test_api_unknown_kind_is_ignored_not_an_error(self):
        resp = self.client.get(reverse('map_module:api_locations'), {'kind': 'bogus'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['count'], 2)

    def test_api_rejects_post(self):
        self.assertEqual(self.client.post(reverse('map_module:api_locations')).status_code, 405)


class NearbyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Titik pengguna dekat Depok; "Dekat" ~1 km, "Tengah" ~ 20 km, "Jauh" ~ 120 km.
        cls.near = make_location(name='Dekat', latitude=Decimal('-6.370000'), longitude=Decimal('106.830000'))
        cls.mid = make_location(name='Tengah', latitude=Decimal('-6.200000'), longitude=Decimal('106.816000'))
        cls.far = make_location(name='Jauh', latitude=Decimal('-6.900000'), longitude=Decimal('107.610000'))

    def post(self, payload, **kwargs):
        return self.client.post(
            reverse('map_module:api_nearby'), data=json.dumps(payload),
            content_type='application/json', **kwargs,
        )

    def test_sorted_by_distance_with_label(self):
        resp = self.post({'lat': -6.3688, 'lng': 106.8284})
        self.assertEqual(resp.status_code, 200)
        results = resp.json()['results']
        self.assertEqual([r['name'] for r in results], ['Dekat', 'Tengah', 'Jauh'])
        distances = [r['distance_km'] for r in results]
        self.assertEqual(distances, sorted(distances))
        self.assertLess(distances[0], 1)
        self.assertTrue(results[0]['distance_label'])

    def test_order_follows_the_given_coordinates(self):
        results = self.post({'lat': -6.9, 'lng': 107.6}).json()['results']
        self.assertEqual(results[0]['name'], 'Jauh')

    def test_nearby_respects_filters(self):
        results = self.post({'lat': -6.37, 'lng': 106.83, 'q': 'Tengah'}).json()['results']
        self.assertEqual([r['name'] for r in results], ['Tengah'])

    def test_invalid_coordinates_return_400_not_500(self):
        for payload in [{}, {'lat': 'x', 'lng': 1}, {'lat': 200, 'lng': 0}, {'lat': 0, 'lng': 999}, {'lat': 1}]:
            with self.subTest(payload=payload):
                resp = self.post(payload)
                self.assertEqual(resp.status_code, 400)
                self.assertIn('error', resp.json())

    def test_malformed_body_returns_400(self):
        resp = self.client.post(reverse('map_module:api_nearby'), data='{oops', content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(reverse('map_module:api_nearby'), data='[1,2]', content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse('map_module:api_nearby')).status_code, 405)

    def test_coordinates_are_not_stored_or_echoed(self):
        before = list(Location.objects.values_list('latitude', 'longitude'))
        resp = self.post({'lat': -6.3688, 'lng': 106.8284})
        self.assertNotIn('-6.3688', resp.content.decode())
        self.assertEqual(list(Location.objects.values_list('latitude', 'longitude')), before)

    def test_radius_filters_out_far_locations(self):
        results = self.post({'lat': -6.3688, 'lng': 106.8284, 'radius_km': 5}).json()['results']
        self.assertEqual([r['name'] for r in results], ['Dekat'])
        results = self.post({'lat': -6.3688, 'lng': 106.8284, 'radius_km': 50}).json()['results']
        self.assertEqual([r['name'] for r in results], ['Dekat', 'Tengah'])
        self.assertTrue(all(r['distance_km'] <= 50 for r in results))

    def test_radius_null_means_no_limit(self):
        results = self.post({'lat': -6.3688, 'lng': 106.8284, 'radius_km': None}).json()['results']
        self.assertEqual(len(results), 3)

    def test_invalid_radius_returns_400(self):
        for radius in (0, -3, 'abc', 10000, True):
            with self.subTest(radius=radius):
                resp = self.post({'lat': -6.37, 'lng': 106.83, 'radius_km': radius})
                self.assertEqual(resp.status_code, 400)

    def test_csrf_is_enforced(self):
        from django.test import Client
        strict = Client(enforce_csrf_checks=True)
        resp = strict.post(
            reverse('map_module:api_nearby'), data=json.dumps({'lat': 1, 'lng': 1}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 403)


class DetailPrivacyTests(TestCase):
    """PRD §5.5 butir 3: alamat lengkap & kontak mengikuti izin pemilik; Guest lihat ringkasan."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user('owner', 'farmer')
        cls.other = make_user('other', 'user')
        common = {'owner': cls.owner, 'area': 'Beji, Depok', 'commodities': 'Selada'}
        cls.public = make_location(name='Pub', address='Jl. Publik 1', contact_info='0811-pub',
                                   detail_visibility='public', **common)
        cls.members = make_location(name='Mem', address='Jl. Anggota 2', contact_info='0811-mem',
                                    detail_visibility='members', **common)
        cls.private = make_location(name='Priv', address='Jl. Rahasia 3', contact_info='0811-priv',
                                    detail_visibility='private', **common)

    def results(self):
        data = self.client.get(reverse('map_module:api_locations')).json()['results']
        return {r['name']: r for r in data}

    def test_guest_sees_public_summary_only(self):
        r = self.results()
        self.assertEqual((r['Pub']['address'], r['Pub']['contact']), ('Jl. Publik 1', '0811-pub'))
        for name in ('Mem', 'Priv'):
            with self.subTest(name=name):
                self.assertEqual((r[name]['address'], r[name]['contact']), ('', ''))
                self.assertTrue(r[name]['detail_login_required'])
                # Ringkasan publik tetap ada.
                self.assertEqual(r[name]['area'], 'Beji, Depok')
                self.assertEqual(r[name]['commodities'], 'Selada')

    def test_member_sees_members_but_not_private(self):
        login(self.client, self.other)
        r = self.results()
        self.assertEqual(r['Mem']['address'], 'Jl. Anggota 2')
        self.assertEqual(r['Mem']['contact'], '0811-mem')
        self.assertEqual((r['Priv']['address'], r['Priv']['contact']), ('', ''))
        self.assertTrue(r['Priv']['detail_owner_only'])
        self.assertFalse(r['Priv']['detail_login_required'])

    def test_owner_sees_own_private_details(self):
        login(self.client, self.owner)
        r = self.results()['Priv']
        self.assertEqual((r['address'], r['contact']), ('Jl. Rahasia 3', '0811-priv'))
        self.assertFalse(r['detail_locked'])

    def test_hidden_details_not_in_guest_html(self):
        pages = [reverse('map_module:map'), self.members.get_absolute_url(), self.private.get_absolute_url()]
        for url in pages:
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                for secret in ('0811-priv', '0811-mem', 'Jl. Rahasia 3', 'Jl. Anggota 2'):
                    self.assertNotIn(secret, html)

    def test_detail_page_shows_login_prompt_for_guest_and_owner_note_for_member(self):
        html = self.client.get(self.private.get_absolute_url()).content.decode()
        self.assertIn('Masuk untuk melihat alamat lengkap', html)
        login(self.client, self.other)
        html = self.client.get(self.private.get_absolute_url()).content.decode()
        self.assertIn('Hanya ditampilkan untuk pemilik', html)
        self.assertNotIn('Jl. Rahasia 3', html)

    def test_hidden_address_cannot_be_probed_by_search(self):
        resp = self.client.get(reverse('map_module:api_locations'), {'q': 'Rahasia'})
        self.assertEqual(resp.json()['count'], 0)

    def test_manager_name_falls_back_to_owner_username(self):
        self.assertEqual(self.results()['Pub']['managed_by'], 'owner')
        loc = make_location(name='Komunal', managed_by='Komunitas Kukusan')
        self.assertEqual(loc.manager_name, 'Komunitas Kukusan')


class DetailTests(TestCase):
    def test_detail_ok_and_hidden_returns_404_for_guest(self):
        active = make_location(name='Aktif')
        hidden = make_location(name='Sembunyi', is_active=False)
        self.assertEqual(self.client.get(active.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(hidden.get_absolute_url()).status_code, 404)

    def test_owner_can_view_own_hidden_location(self):
        owner = make_user('own', 'farmer')
        hidden = make_location(name='Sembunyi', is_active=False, owner=owner)
        login(self.client, owner)
        self.assertEqual(self.client.get(hidden.get_absolute_url()).status_code, 200)

    def test_missing_location_is_404(self):
        self.assertEqual(self.client.get(reverse('map_module:location_detail', args=[9999])).status_code, 404)


class CrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.farmer = make_user('farmer', 'farmer')
        cls.seller = make_user('seller', 'farmer-seller')
        cls.other_farmer = make_user('farmer2', 'farmer')
        cls.plain = make_user('plain', 'user')
        cls.no_role = make_user('norole')
        cls.admin = make_user('boss', 'admin')

    def payload(self, **overrides):
        data = {
            'kind': 'farmer_garden', 'name': '  Kebun Baru  ', 'latitude': '-6.360000',
            'longitude': '106.820000', 'address': 'Jl. Margonda 1', 'description': 'Halo',
            'area': 'Beji, Depok', 'commodities': 'selada,  kangkung ,,cabai', 'managed_by': '',
            'photo_url': '', 'contact_info': '0812', 'detail_visibility': 'members',
            'is_active': 'on',
        }
        data.update(overrides)
        return data

    def test_anonymous_redirected_to_login(self):
        for name in ('location_create', 'my_locations'):
            resp = self.client.get(reverse(f'map_module:{name}'))
            self.assertEqual(resp.status_code, 302)
            self.assertIn(reverse('authentication:login'), resp.url)

    def test_user_without_role_forbidden(self):
        login(self.client, self.no_role)
        self.assertEqual(self.client.get(reverse('map_module:location_create')).status_code, 403)
        self.assertEqual(self.client.post(reverse('map_module:location_create'), self.payload()).status_code, 403)
        self.assertEqual(Location.objects.count(), 0)

    def test_farmer_creates_own_location(self):
        login(self.client, self.farmer)
        resp = self.client.post(reverse('map_module:location_create'), self.payload())
        loc = Location.objects.get()
        self.assertRedirects(resp, loc.get_absolute_url())
        self.assertEqual(loc.owner, self.farmer)
        self.assertEqual(loc.name, 'Kebun Baru')  # spasi dipangkas
        self.assertEqual(loc.commodities, 'selada, kangkung, cabai')  # daftar dirapikan

    def test_registered_user_role_can_add_garden(self):
        login(self.client, self.plain)
        self.client.post(reverse('map_module:location_create'), self.payload())
        self.assertEqual(Location.objects.get().owner, self.plain)

    def test_farmer_cannot_create_seller_kinds(self):
        login(self.client, self.farmer)
        for kind in ('merchant', 'pickup_point'):
            resp = self.client.post(reverse('map_module:location_create'), self.payload(kind=kind))
            self.assertEqual(resp.status_code, 200)
            self.assertIn('kind', resp.context['form'].errors)
        self.assertEqual(Location.objects.count(), 0)

    def test_seller_can_create_pickup_point(self):
        login(self.client, self.seller)
        self.client.post(reverse('map_module:location_create'), self.payload(kind='pickup_point'))
        self.assertEqual(Location.objects.get().kind, 'pickup_point')

    def test_invalid_coordinates_show_field_errors(self):
        login(self.client, self.farmer)
        for lat, lng in [('95', '106'), ('-6', '200'), ('abc', '106'), ('0', '0')]:
            with self.subTest(lat=lat, lng=lng):
                resp = self.client.post(
                    reverse('map_module:location_create'), self.payload(latitude=lat, longitude=lng)
                )
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(resp.context['form'].errors)
        self.assertEqual(Location.objects.count(), 0)

    def test_only_owner_can_edit_and_delete(self):
        loc = make_location(owner=self.farmer)
        login(self.client, self.other_farmer)
        self.assertEqual(self.client.get(reverse('map_module:location_update', args=[loc.pk])).status_code, 403)
        self.assertEqual(
            self.client.post(reverse('map_module:location_update', args=[loc.pk]), self.payload()).status_code, 403
        )
        self.assertEqual(self.client.post(reverse('map_module:location_delete', args=[loc.pk])).status_code, 403)
        self.assertTrue(Location.objects.filter(pk=loc.pk).exists())

    def test_owner_updates_and_deletes(self):
        loc = make_location(owner=self.farmer)
        login(self.client, self.farmer)
        self.client.post(reverse('map_module:location_update', args=[loc.pk]), self.payload(name='Ganti Nama'))
        loc.refresh_from_db()
        self.assertEqual(loc.name, 'Ganti Nama')
        resp = self.client.post(reverse('map_module:location_delete', args=[loc.pk]))
        self.assertRedirects(resp, reverse('map_module:my_locations'))
        self.assertFalse(Location.objects.filter(pk=loc.pk).exists())

    def test_delete_requires_post(self):
        loc = make_location(owner=self.farmer)
        login(self.client, self.farmer)
        self.assertEqual(self.client.get(reverse('map_module:location_delete', args=[loc.pk])).status_code, 405)

    def test_admin_can_edit_anyones_location(self):
        loc = make_location(owner=self.farmer)
        login(self.client, self.admin)
        resp = self.client.post(reverse('map_module:location_update', args=[loc.pk]), self.payload(name='Diubah Admin'))
        self.assertEqual(resp.status_code, 302)
        loc.refresh_from_db()
        self.assertEqual(loc.name, 'Diubah Admin')
        self.assertEqual(loc.owner, self.farmer)  # pemilik tidak berubah

    def test_my_locations_lists_only_own(self):
        mine = make_location(name='Milik Saya', owner=self.farmer)
        make_location(name='Milik Orang', owner=self.other_farmer)
        login(self.client, self.farmer)
        resp = self.client.get(reverse('map_module:my_locations'))
        self.assertEqual(list(resp.context['locations']), [mine])

    def test_xss_in_name_is_escaped_everywhere_server_side(self):
        make_location(name='<script>alert(1)</script>')
        html = self.client.get(reverse('map_module:map')).content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)


class MarketplaceLinkTests(TestCase):
    def test_store_url_only_for_seller_kinds_with_owner(self):
        from django.urls import NoReverseMatch
        from django.urls import reverse as rev

        seller = make_user('tokoku', 'farmer-seller')
        shop = make_location(name='Toko', kind='merchant', owner=seller)
        garden = make_location(name='Kebun', owner=seller)
        data = {r['name']: r for r in self.client.get(reverse('map_module:api_locations')).json()['results']}
        # Modul marketplace belum ter-install di cabang ini → tautan etalase disembunyikan, bukan error.
        try:
            expected = rev('marketplace:seller_store', args=['tokoku'])
        except NoReverseMatch:
            expected = None
        self.assertEqual(data[shop.name]['store_url'], expected)
        self.assertIsNone(data[garden.name]['store_url'])


class ProductPinTests(TestCase):
    """PRD §5.5 butir 5 + 'selesai bila': tautan dari produk membuka lokasi terkait."""

    def fake_model(self, row):
        qs = mock.MagicMock()
        qs.filter.return_value.values.return_value.first.return_value = row
        return SimpleNamespace(objects=qs)

    def row(self, **overrides):
        data = {'pk': 7, 'name': 'Tomat Ceri', 'location': 'Beji, Depok',
                'pickup_address': 'Jl. Margonda 9', 'latitude': Decimal('-6.37'),
                'longitude': Decimal('106.83')}
        data.update(overrides)
        return data

    def test_product_map_url(self):
        self.assertEqual(product_map_url(7), f"{reverse('map_module:map')}?product=7")
        self.assertEqual(product_map_url(SimpleNamespace(pk=8)), f"{reverse('map_module:map')}?product=8")

    def test_without_marketplace_app_pin_is_none_and_page_ok(self):
        self.assertIsNone(product_pin(7))
        resp = self.client.get(reverse('map_module:map'), {'product': '7'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context['config']['product_pin'])
        self.assertTrue(resp.context['config']['product_missing'])

    def test_pin_from_product_coordinates(self):
        with mock.patch('map_module.services._product_model', return_value=self.fake_model(self.row())):
            resp = self.client.get(reverse('map_module:map'), {'product': '7'})
        pin = resp.context['config']['product_pin']
        self.assertEqual((pin['id'], pin['name'], pin['lat'], pin['lng']), (7, 'Tomat Ceri', -6.37, 106.83))
        self.assertEqual(pin['area'], 'Beji, Depok')
        self.assertFalse(resp.context['config']['product_missing'])

    def test_product_without_coordinates_or_inactive_gives_no_pin(self):
        for row in (self.row(latitude=None), self.row(longitude=None), None):
            with self.subTest(row=row), mock.patch(
                'map_module.services._product_model', return_value=self.fake_model(row)
            ):
                self.assertIsNone(product_pin(7))

    def test_only_active_products_are_queried(self):
        model = self.fake_model(self.row())
        with mock.patch('map_module.services._product_model', return_value=model):
            product_pin(7)
        model.objects.filter.assert_called_once_with(pk=7, is_active=True)


class SummaryTests(TestCase):
    def test_summary_counts_active_only(self):
        make_location(kind='community_garden')
        make_location(kind='farmer_garden')
        make_location(kind='merchant')
        make_location(kind='pickup_point')
        make_location(kind='community_garden', is_active=False)
        self.assertEqual(
            summary_counts(), {'gardens': 2, 'merchants': 1, 'pickup_points': 1, 'total': 4}
        )
