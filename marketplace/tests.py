import shutil
import tempfile
from datetime import timedelta
from io import BytesIO, StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.http import QueryDict
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from authentication.models import Role, Session, User

from .cart import (
    CartError,
    add_review,
    add_to_cart,
    buy_now,
    change_status,
    checkout,
    update_quantity,
)
from .forms import ProductForm
from .models import CartItem, Category, Order, Product, Review
from .permissions import can_manage, is_seller
from .services import category_facets, clean_search_params, search_products
from .templatetags.marketplace_tags import rupiah


class MarketplaceTestCase(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username='budi', email='budi@example.com', password='secret-123!'
        )
        self.sayuran = Category.objects.create(name='Sayuran', slug='sayuran')
        self.bibit = Category.objects.create(name='Bibit', slug='bibit')
        self.tomat = self._product('Tomat Cherry', self.sayuran, 25000, 10, 'Depok')
        self.kangkung = self._product('Kangkung', self.sayuran, 8000, 0, 'Jakarta')
        self.cabai = self._product('Bibit Cabai', self.bibit, 15000, 5, 'Depok')
        self.hidden = self._product('Tomat Lama', self.sayuran, 1000, 3, 'Depok', is_active=False)

    def _product(self, name, category, price, stock, location, **extra):
        return Product.objects.create(
            seller=self.seller, category=category, name=name,
            price=price, stock=stock, location=location, **extra
        )

    def login(self, user):
        self.client.force_login(user)
        Session.objects.update_or_create(
            session_token=self.client.session.session_key,
            defaults={'user': user, 'expires_at': timezone.now() + timedelta(days=1)},
        )

    def _names(self, params):
        products, _ = search_products(params)
        return set(products.values_list('name', flat=True))


class ProductModelTests(MarketplaceTestCase):
    def test_product_without_stock_is_not_available(self):
        self.assertTrue(self.tomat.is_available)
        self.assertFalse(self.kangkung.is_available)

    def test_inactive_product_is_not_available(self):
        self.assertFalse(self.hidden.is_available)

    def test_merchant_name_uses_seller(self):
        self.assertEqual(self.tomat.merchant_name, 'budi')


class SearchServiceTests(MarketplaceTestCase):
    def test_inactive_products_are_never_returned(self):
        self.assertNotIn('Tomat Lama', self._names({}))

    def test_keyword_matches_name(self):
        self.assertEqual(self._names({'q': 'tomat'}), {'Tomat Cherry'})

    def test_filter_by_category_slug_or_name(self):
        self.assertEqual(self._names({'category': 'bibit'}), {'Bibit Cabai'})
        self.assertEqual(self._names({'category': 'Sayuran'}), {'Tomat Cherry', 'Kangkung'})

    def test_filter_by_price_range(self):
        self.assertEqual(self._names({'min_price': '10000', 'max_price': '20000'}), {'Bibit Cabai'})

    def test_swapped_price_range_is_corrected(self):
        self.assertEqual(self._names({'min_price': 20000, 'max_price': 10000}), {'Bibit Cabai'})

    def test_filter_by_location(self):
        self.assertEqual(self._names({'location': 'depok'}), {'Tomat Cherry', 'Bibit Cabai'})

    def test_filter_by_stock(self):
        self.assertNotIn('Kangkung', self._names({'in_stock': '1'}))
        self.assertEqual(self._names({'in_stock': False}), {'Kangkung'})

    def test_filter_by_multiple_categories(self):
        params = QueryDict('category=bibit&category=sayuran&in_stock=1')
        self.assertEqual(self._names(params), {'Tomat Cherry', 'Bibit Cabai'})

    def test_single_category_from_llm_dict_still_works(self):
        self.assertEqual(self._names({'category': 'Bibit'}), {'Bibit Cabai'})

    def test_price_range_preset(self):
        self.assertEqual(self._names({'price_range': 'under-10k'}), {'Kangkung'})
        self.assertEqual(self._names({'price_range': '10k-25k'}), {'Tomat Cherry', 'Bibit Cabai'})

    def test_explicit_price_overrides_preset_and_unknown_preset_is_ignored(self):
        self.assertEqual(self._names({'price_range': 'under-10k', 'min_price': 20000}), {'Tomat Cherry'})
        self.assertEqual(clean_search_params({'price_range': 'gratis'})['price_range'], '')

    def test_combined_filters(self):
        params = {'category': 'sayuran', 'max_price': 30000, 'location': 'Depok', 'in_stock': True}
        self.assertEqual(self._names(params), {'Tomat Cherry'})

    def test_sort_by_price(self):
        products, _ = search_products({'sort': 'price_asc'})
        self.assertEqual([p.price for p in products], [15000, 25000, 8000])

    def test_invalid_params_are_ignored(self):
        params = clean_search_params({'min_price': 'abc', 'max_price': '-5', 'sort': 'drop'})
        self.assertIsNone(params['min_price'])
        self.assertIsNone(params['max_price'])
        self.assertEqual(params['sort'], 'newest')

    def test_default_sort_follows_keyword(self):
        self.assertEqual(clean_search_params({'q': 'tomat'})['sort'], 'relevance')
        self.assertEqual(clean_search_params({'sort': 'relevance'})['sort'], 'newest')
        self.assertEqual(clean_search_params({'q': 'tomat', 'sort': 'price_asc'})['sort'], 'price_asc')

    def test_relevance_ranks_name_match_above_description_match(self):
        self._product('Pupuk Organik', self.bibit, 9000, 4, 'Depok', description='Cocok untuk tomat')
        self._product('Tomat Beef', self.sayuran, 30000, 2, 'Bogor')
        products, _ = search_products({'q': 'tomat'})
        names = [p.name for p in products]
        self.assertEqual(names[-1], 'Pupuk Organik')
        self.assertEqual(set(names[:2]), {'Tomat Cherry', 'Tomat Beef'})

    def test_out_of_stock_is_always_last(self):
        for sort in ('newest', 'price_asc', 'price_desc'):
            products, _ = search_products({'sort': sort})
            self.assertEqual(list(products)[-1].name, 'Kangkung', sort)

    def test_category_facets_ignore_selected_category_but_keep_other_filters(self):
        params = clean_search_params({'category': 'bibit', 'location': 'depok'})
        counts = {c.slug: c.product_count for c in category_facets(params)}
        self.assertEqual(counts, {'bibit': 1, 'sayuran': 1})


class MarketplaceViewTests(MarketplaceTestCase):
    def test_guest_can_open_catalog(self):
        response = self.client.get(reverse('marketplace:catalog'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tomat Cherry')
        self.assertContains(response, 'Rp25.000')

    def test_catalog_with_invalid_params_does_not_error(self):
        response = self.client.get(reverse('marketplace:catalog'), {'min_price': 'x', 'page': 'zz'})
        self.assertEqual(response.status_code, 200)

    def test_out_of_stock_badge_is_shown(self):
        response = self.client.get(reverse('marketplace:catalog'), {'q': 'kangkung'})
        self.assertContains(response, 'Habis')

    def test_product_detail(self):
        response = self.client.get(reverse('marketplace:product_detail', args=[self.tomat.pk]))
        self.assertContains(response, 'Tomat Cherry')
        self.assertContains(response, 'budi')

    def test_inactive_product_detail_returns_404(self):
        response = self.client.get(reverse('marketplace:product_detail', args=[self.hidden.pk]))
        self.assertEqual(response.status_code, 404)

    def test_product_api_returns_detail_json(self):
        response = self.client.get(reverse('marketplace:product_api', args=[self.tomat.pk]))
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual((data['id'], data['name'], data['price']), (self.tomat.pk, 'Tomat Cherry', 25000))
        self.assertEqual(data['category']['slug'], 'sayuran')
        self.assertEqual((data['sold_count'], data['rating_count'], data['rating_avg']), (0, 0, None))
        self.assertTrue(data['url'].endswith(reverse('marketplace:product_detail', args=[self.tomat.pk])))
        search_item = self.client.get(reverse('marketplace:search_api'), {'q': 'cherry'}).json()['results'][0]
        self.assertTrue(set(search_item) <= set(data))

    def test_product_api_hides_inactive_and_missing(self):
        for pk in (self.hidden.pk, 99999):
            response = self.client.get(reverse('marketplace:product_api', args=[pk]))
            self.assertEqual(response.status_code, 404)
            self.assertIn('error', response.json())

    def test_product_api_is_read_only(self):
        response = self.client.post(reverse('marketplace:product_api', args=[self.tomat.pk]))
        self.assertEqual(response.status_code, 405)

    def test_search_api_returns_grounded_json(self):
        response = self.client.get(reverse('marketplace:search_api'), {'q': 'tomat', 'max_price': 30000})
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['name'], 'Tomat Cherry')
        self.assertEqual(data['params']['max_price'], 30000)


class RupiahFilterTests(TestCase):
    def test_formats_with_dot_separator(self):
        self.assertEqual(rupiah(1250000), 'Rp1.250.000')

    def test_invalid_value_is_returned_as_is(self):
        self.assertEqual(rupiah('gratis'), 'gratis')


class ModelStrTests(MarketplaceTestCase):
    def test_str(self):
        self.assertEqual(str(self.sayuran), 'Sayuran')
        self.assertEqual(str(self.tomat), 'Tomat Cherry')


class SeedCommandTests(TestCase):
    def test_seed_is_idempotent(self):
        call_command('seed_marketplace', stdout=StringIO())
        call_command('seed_marketplace', stdout=StringIO())
        self.assertEqual(Product.objects.count(), 18)
        for username in ('petani_penjual', 'kebun_sinta'):
            self.assertTrue(is_seller(User.objects.get(username=username)))
        self.assertTrue(Product.objects.filter(seller__username='kebun_sinta').exists())
        self.assertFalse(Product.objects.filter(latitude__isnull=True).exists())


class ProductCrudTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        seller_role = Role.objects.create(name='farmer-seller', description='Petani - Penjual')
        self.seller.roles.add(seller_role)
        self.other_seller = User.objects.create_user(
            username='sinta', email='sinta@example.com', password='secret-123!'
        )
        self.other_seller.roles.add(seller_role)
        self.farmer = User.objects.create_user(
            username='tono', email='tono@example.com', password='secret-123!'
        )
        self.farmer.roles.add(Role.objects.create(name='farmer', description='Petani'))
        self.admin = User.objects.create_user(
            username='admin1', email='admin1@example.com', password='secret-123!'
        )
        self.admin.roles.add(Role.objects.create(name='admin', description='Admin'))

    def _payload(self, **overrides):
        data = {
            'name': 'Selada Romaine', 'category': self.sayuran.pk,
            'description': 'Selada segar dari kebun hidroponik komunitas.',
            'image_url': 'https://example.com/selada.jpg', 'price': 12000, 'unit': 'kg', 'stock': 7,
            'min_order': 1, 'location': 'Depok', 'pickup_address': 'Jl. Margonda No. 1',
            'latitude': '-6.4', 'longitude': '106.8', 'is_active': 'on',
        }
        data.update(overrides)
        return data

    def test_roles_are_checked(self):
        self.assertTrue(is_seller(self.seller))
        self.assertTrue(is_seller(self.admin))
        self.assertFalse(is_seller(self.farmer))
        self.assertTrue(can_manage(self.seller, self.tomat))
        self.assertFalse(can_manage(self.other_seller, self.tomat))
        self.assertTrue(can_manage(self.admin, self.tomat))

    def test_guest_is_redirected_to_login(self):
        response = self.client.get(reverse('marketplace:product_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    def test_farmer_without_seller_role_is_forbidden(self):
        self.login(self.farmer)
        self.assertEqual(self.client.get(reverse('marketplace:product_create')).status_code, 403)
        self.assertEqual(self.client.get(reverse('marketplace:my_products')).status_code, 403)

    def test_seller_can_create_product(self):
        self.login(self.seller)
        response = self.client.post(reverse('marketplace:product_create'), self._payload())
        self.assertRedirects(response, reverse('marketplace:my_products'))
        product = Product.objects.get(name='Selada Romaine')
        self.assertEqual(product.seller, self.seller)

    def test_seller_cannot_spoof_owner(self):
        self.login(self.seller)
        payload = self._payload(seller=self.other_seller.pk)
        self.client.post(reverse('marketplace:product_create'), payload)
        self.assertEqual(Product.objects.get(name='Selada Romaine').seller, self.seller)

    def test_invalid_product_is_rejected(self):
        self.login(self.seller)
        response = self.client.post(reverse('marketplace:product_create'),
                                    self._payload(price=-1, name='ab'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(name='ab').exists())

    def test_valid_payload_passes(self):
        form = ProductForm(data=self._payload())
        self.assertTrue(form.is_valid(), form.errors)

    def test_map_point_is_required_and_must_be_in_indonesia(self):
        form = ProductForm(data=self._payload(latitude='', longitude=''))
        self.assertIn('latitude', form.errors)
        form = ProductForm(data=self._payload(latitude='48.85', longitude='2.35'))
        self.assertIn('latitude', form.errors)

    def test_listing_quality_rules(self):
        cases = {
            'description': {'description': 'Terlalu pendek'},
            'name': {'name': 'Abc'},
            'price': {'price': 50},
            'min_order': {'min_order': 10, 'stock': 5},
            'pickup_address': {'pickup_address': ''},
            'image': {'image_url': ''},
            'harvested_at': {'harvested_at': '2999-01-01'},
        }
        for field, overrides in cases.items():
            with self.subTest(field=field):
                form = ProductForm(data=self._payload(**overrides))
                self.assertIn(field, form.errors)

    def test_error_messages_are_in_indonesian(self):
        form = ProductForm(data={})
        self.assertEqual(form.errors['name'], ['Wajib diisi.'])
        self.assertEqual(form.errors['latitude'], ['Tandai titik pengambilan di peta.'])

    def test_name_whitespace_is_normalised(self):
        form = ProductForm(data=self._payload(name='  Selada    Romaine  '))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['name'], 'Selada Romaine')

    def test_seller_can_update_own_product(self):
        self.login(self.seller)
        response = self.client.post(
            reverse('marketplace:product_update', args=[self.tomat.pk]),
            self._payload(name='Tomat Cherry Premium', stock=0),
        )
        self.assertRedirects(response, reverse('marketplace:my_products'))
        self.tomat.refresh_from_db()
        self.assertEqual(self.tomat.name, 'Tomat Cherry Premium')
        self.assertFalse(self.tomat.is_available)

    def test_seller_cannot_update_others_product(self):
        self.login(self.other_seller)
        url = reverse('marketplace:product_update', args=[self.tomat.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, self._payload(name='Diretas')).status_code, 403)
        self.tomat.refresh_from_db()
        self.assertEqual(self.tomat.name, 'Tomat Cherry')

    def test_seller_can_archive_and_restore_own_product(self):
        self.login(self.seller)
        url = reverse('marketplace:product_archive', args=[self.tomat.pk])
        self.client.post(url)
        self.tomat.refresh_from_db()
        self.assertFalse(self.tomat.is_active)
        self.assertNotIn('Tomat Cherry', self._names({}))
        self.client.post(url)
        self.tomat.refresh_from_db()
        self.assertTrue(self.tomat.is_active)

    def test_active_product_cannot_be_deleted_permanently(self):
        self.login(self.seller)
        self.client.post(reverse('marketplace:product_delete', args=[self.tomat.pk]))
        self.assertTrue(Product.objects.filter(pk=self.tomat.pk).exists())

    def test_seller_can_delete_archived_product(self):
        self.login(self.seller)
        self.client.post(reverse('marketplace:product_archive', args=[self.tomat.pk]))
        self.client.post(reverse('marketplace:product_delete', args=[self.tomat.pk]))
        self.assertFalse(Product.objects.filter(pk=self.tomat.pk).exists())

    def test_seller_cannot_archive_others_product(self):
        self.login(self.other_seller)
        response = self.client.post(reverse('marketplace:product_archive', args=[self.tomat.pk]))
        self.assertEqual(response.status_code, 403)
        self.tomat.refresh_from_db()
        self.assertTrue(self.tomat.is_active)

    def test_delete_requires_post(self):
        self.login(self.seller)
        response = self.client.get(reverse('marketplace:product_delete', args=[self.tomat.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Product.objects.filter(pk=self.tomat.pk).exists())

    def test_seller_cannot_delete_others_product(self):
        Product.objects.filter(pk=self.tomat.pk).update(is_active=False)
        self.login(self.other_seller)
        response = self.client.post(reverse('marketplace:product_delete', args=[self.tomat.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.tomat.pk).exists())

    def test_admin_can_delete_any_product(self):
        self.login(self.admin)
        self.client.post(reverse('marketplace:product_archive', args=[self.tomat.pk]))
        self.client.post(reverse('marketplace:product_delete', args=[self.tomat.pk]))
        self.assertFalse(Product.objects.filter(pk=self.tomat.pk).exists())

    def test_my_products_only_lists_own_products(self):
        Product.objects.create(
            seller=self.other_seller, category=self.sayuran, name='Produk Sinta',
            price=5000, stock=1, location='Bogor',
        )
        self.login(self.seller)
        response = self.client.get(reverse('marketplace:my_products'))
        self.assertContains(response, 'Tomat Cherry')
        self.assertNotContains(response, 'Produk Sinta')

    def test_manage_buttons_only_for_owner(self):
        url = reverse('marketplace:product_detail', args=[self.tomat.pk])
        self.login(self.other_seller)
        self.assertNotContains(self.client.get(url), 'Edit produk')
        self.login(self.seller)
        self.assertContains(self.client.get(url), 'Edit produk')


class CatalogAjaxTests(MarketplaceTestCase):
    def test_ajax_request_returns_results_partial(self):
        response = self.client.get(reverse('marketplace:catalog'), {'q': 'cabai'},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        data = response.json()
        self.assertIn('Bibit Cabai', data['content_html'])
        self.assertNotIn('<html', data['content_html'])
        self.assertEqual(data['facets'], {'bibit': 1, 'sayuran': 0})
        self.assertEqual(data['total'], 1)

    def test_catalog_without_filters_shows_category_sections(self):
        response = self.client.get(reverse('marketplace:catalog'))
        sections = response.context['sections']
        self.assertEqual([s['category'].name for s in sections], ['Bibit', 'Sayuran'])
        self.assertEqual([p.name for p in sections[1]['products']], ['Tomat Cherry', 'Kangkung'])

    def test_catalog_with_filters_shows_grid_and_active_filter_chips(self):
        response = self.client.get(reverse('marketplace:catalog'),
                                   {'category': 'sayuran', 'price_range': '10k-25k'})
        self.assertEqual(response.context['sections'], [])
        labels = [f['label'] for f in response.context['active_filters']]
        self.assertEqual(labels, ['Sayuran', 'Rp10.000 – Rp25.000'])


class FooterTests(MarketplaceTestCase):
    COMPACT = 'aria-label="Tautan footer"'
    LANDING = 'Cultivating A Sustainable'

    def test_list_view_uses_compact_footer(self):
        response = self.client.get(reverse('marketplace:catalog'))
        self.assertContains(response, self.COMPACT)
        self.assertNotContains(response, self.LANDING)

    def test_map_view_and_cart_have_no_footer(self):
        response = self.client.get(reverse('marketplace:catalog'), {'view': 'map'})
        self.assertNotContains(response, self.COMPACT)
        self.assertNotContains(response, self.LANDING)
        buyer = User.objects.create_user(username='rina', email='r@example.com', password='x')
        self.login(buyer)
        response = self.client.get(reverse('marketplace:cart'))
        self.assertNotContains(response, self.COMPACT)
        self.assertNotContains(response, self.LANDING)

    def test_other_pages_keep_landing_footer(self):
        self.assertContains(self.client.get(reverse('main:show_main')), self.LANDING)


class StoreAndRelatedTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.seller.roles.add(Role.objects.create(name='farmer-seller', description='Petani - Penjual'))
        self.other = User.objects.create_user(username='sinta', email='s@example.com', password='x')
        self.other.roles.add(Role.objects.get(name='farmer-seller'))
        self.selada = Product.objects.create(
            seller=self.other, category=self.sayuran, name='Selada', price=7000, stock=3, location='Bogor',
        )

    def test_store_page_lists_only_active_products_of_seller(self):
        response = self.client.get(reverse('marketplace:seller_store', args=['budi']))
        self.assertContains(response, 'Tomat Cherry')
        self.assertNotContains(response, 'Tomat Lama')
        self.assertNotContains(response, 'Selada')

    def test_store_lists_out_of_stock_last(self):
        response = self.client.get(reverse('marketplace:seller_store', args=['budi']))
        self.assertEqual(list(response.context['page_obj'])[-1].name, 'Kangkung')

    def test_store_of_non_seller_returns_404(self):
        User.objects.create_user(username='pembeli', email='p@example.com', password='x')
        response = self.client.get(reverse('marketplace:seller_store', args=['pembeli']))
        self.assertEqual(response.status_code, 404)

    def test_detail_shows_breadcrumb_seller_products_and_similar(self):
        response = self.client.get(reverse('marketplace:product_detail', args=[self.tomat.pk]))
        self.assertContains(response, 'aria-label="Breadcrumb"')
        self.assertContains(response, reverse('marketplace:seller_store', args=['budi']))
        seller_names = [p.name for p in response.context['seller_products']]
        similar_names = [p.name for p in response.context['similar_products']]
        self.assertIn('Bibit Cabai', seller_names)
        self.assertNotIn('Tomat Cherry', seller_names)
        self.assertNotIn('Tomat Lama', seller_names)
        self.assertEqual(similar_names, ['Selada'])

    def test_my_products_separates_active_and_archived(self):
        self.login(self.seller)
        response = self.client.get(reverse('marketplace:my_products'))
        self.assertIn(self.hidden, response.context['archived_products'])
        self.assertIn(self.tomat, response.context['active_products'])


class CartAndCheckoutTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.buyer = User.objects.create_user(username='rina', email='r@example.com', password='x')
        self.other_seller = User.objects.create_user(username='sinta', email='s@example.com', password='x')
        self.selada = Product.objects.create(
            seller=self.other_seller, category=self.sayuran, name='Selada', price=7000, stock=5,
            location='Bogor',
        )

    def test_add_to_cart_merges_quantity_and_respects_stock(self):
        add_to_cart(self.buyer, self.tomat, 4)
        add_to_cart(self.buyer, self.tomat, 3)
        self.assertEqual(CartItem.objects.get(user=self.buyer).quantity, 7)
        with self.assertRaises(CartError):
            add_to_cart(self.buyer, self.tomat, 4)
        self.assertEqual(CartItem.objects.get(user=self.buyer).quantity, 7)

    def test_min_order_is_enforced(self):
        Product.objects.filter(pk=self.tomat.pk).update(min_order=3)
        self.tomat.refresh_from_db()
        with self.assertRaises(CartError):
            add_to_cart(self.buyer, self.tomat, 2)
        self.assertFalse(CartItem.objects.exists())
        item = add_to_cart(self.buyer, self.tomat, 3)
        with self.assertRaises(CartError):
            update_quantity(item, 2)

    def test_cannot_add_out_of_stock_or_own_product(self):
        with self.assertRaises(CartError):
            add_to_cart(self.buyer, self.kangkung)
        with self.assertRaises(CartError):
            add_to_cart(self.seller, self.tomat)
        self.assertFalse(CartItem.objects.exists())

    def test_guest_is_redirected_to_login(self):
        response = self.client.post(reverse('marketplace:cart_add', args=[self.tomat.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('authentication:login'), response['Location'])

    def test_add_via_ajax_returns_cart_count(self):
        self.login(self.buyer)
        response = self.client.post(reverse('marketplace:cart_add', args=[self.tomat.pk]),
                                    {'quantity': 2}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.json()['count'], 2)
        self.assertEqual(self.client.get(reverse('marketplace:catalog')).context['cart_count'], 2)

    def test_ajax_add_error_returns_400(self):
        self.login(self.buyer)
        response = self.client.post(reverse('marketplace:cart_add', args=[self.kangkung.pk]),
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])

    def test_update_and_remove_cart_item(self):
        self.login(self.buyer)
        item = add_to_cart(self.buyer, self.tomat, 1)
        self.client.post(reverse('marketplace:cart_update', args=[item.pk]), {'quantity': 5})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)
        self.client.post(reverse('marketplace:cart_update', args=[item.pk]), {'quantity': 0})
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())

    def test_cannot_touch_another_users_cart(self):
        item = add_to_cart(self.buyer, self.tomat, 1)
        self.login(self.seller)
        response = self.client.post(reverse('marketplace:cart_remove', args=[item.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(CartItem.objects.filter(pk=item.pk).exists())

    def test_cart_is_grouped_per_seller(self):
        self.login(self.buyer)
        add_to_cart(self.buyer, self.tomat, 2)
        add_to_cart(self.buyer, self.cabai, 1)
        add_to_cart(self.buyer, self.selada, 1)
        groups = self.client.get(reverse('marketplace:cart')).context['groups']
        self.assertEqual([g['seller'].username for g in groups], ['budi', 'sinta'])
        self.assertEqual(groups[0]['subtotal'], 2 * 25000 + 15000)

    def test_select_items_and_sellers(self):
        self.login(self.buyer)
        tomat = add_to_cart(self.buyer, self.tomat, 1)
        add_to_cart(self.buyer, self.selada, 1)
        url = reverse('marketplace:cart_select')
        self.client.post(url, {'target': 'item', 'id': tomat.pk, 'selected': '0'})
        self.assertFalse(CartItem.objects.get(pk=tomat.pk).selected)
        self.client.post(url, {'target': 'seller', 'id': self.other_seller.pk, 'selected': '0'})
        self.assertFalse(CartItem.objects.filter(user=self.buyer, selected=True).exists())
        self.client.post(url, {'target': 'all', 'selected': '1'})
        self.assertEqual(CartItem.objects.filter(user=self.buyer, selected=True).count(), 2)

    def test_buy_now_selects_only_that_product(self):
        add_to_cart(self.buyer, self.selada, 1)
        buy_now(self.buyer, self.tomat, 3)
        selected = CartItem.objects.filter(user=self.buyer, selected=True)
        self.assertEqual([(i.product.name, i.quantity) for i in selected], [('Tomat Cherry', 3)])

    def test_buy_now_view_redirects_to_cart(self):
        self.login(self.buyer)
        response = self.client.post(reverse('marketplace:buy_now', args=[self.tomat.pk]), {'quantity': 2})
        self.assertRedirects(response, reverse('marketplace:cart'))

    def test_checkout_splits_orders_per_seller(self):
        add_to_cart(self.buyer, self.tomat, 3)
        add_to_cart(self.buyer, self.cabai, 2)
        add_to_cart(self.buyer, self.selada, 1)
        orders = checkout(self.buyer, note='Ambil sore')
        self.assertEqual(len(orders), 2)
        by_seller = {o.seller.username: o for o in orders}
        self.assertEqual(by_seller['budi'].total, 3 * 25000 + 2 * 15000)
        self.assertEqual(by_seller['sinta'].total, 7000)
        self.tomat.refresh_from_db()
        self.assertEqual(self.tomat.stock, 7)
        self.assertFalse(CartItem.objects.filter(user=self.buyer).exists())

    def test_checkout_only_selected_items(self):
        add_to_cart(self.buyer, self.tomat, 1)
        keep = add_to_cart(self.buyer, self.selada, 1)
        CartItem.objects.filter(pk=keep.pk).update(selected=False)
        orders = checkout(self.buyer)
        self.assertEqual([o.seller.username for o in orders], ['budi'])
        self.assertTrue(CartItem.objects.filter(pk=keep.pk).exists())

    def test_checkout_fails_when_stock_changed_and_keeps_cart(self):
        add_to_cart(self.buyer, self.tomat, 5)
        Product.objects.filter(pk=self.tomat.pk).update(stock=2)
        with self.assertRaises(CartError):
            checkout(self.buyer)
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.filter(user=self.buyer).exists())

    def test_checkout_without_selection_fails(self):
        with self.assertRaises(CartError):
            checkout(self.buyer)

    def test_order_keeps_snapshot_after_product_changes(self):
        add_to_cart(self.buyer, self.tomat, 1)
        order = checkout(self.buyer)[0]
        Product.objects.filter(pk=self.tomat.pk).update(name='Tomat Baru', price=99999)
        item = order.items.get()
        self.assertEqual((item.product_name, item.price), ('Tomat Cherry', 25000))

    def test_checkout_view_redirects_to_single_order_or_list(self):
        self.login(self.buyer)
        add_to_cart(self.buyer, self.tomat, 1)
        response = self.client.post(reverse('marketplace:checkout'))
        order = Order.objects.get(buyer=self.buyer)
        self.assertRedirects(response, reverse('marketplace:order_detail', args=[order.pk]))
        add_to_cart(self.buyer, self.tomat, 1)
        add_to_cart(self.buyer, self.selada, 1)
        response = self.client.post(reverse('marketplace:checkout'))
        self.assertRedirects(response, reverse('marketplace:orders'))

    def test_checkout_view_with_empty_cart_redirects_back(self):
        self.login(self.buyer)
        response = self.client.post(reverse('marketplace:checkout'))
        self.assertRedirects(response, reverse('marketplace:cart'))


class OrderFlowTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.seller.roles.add(Role.objects.create(name='farmer-seller', description='Penjual'))
        self.buyer = User.objects.create_user(username='rina', email='r@example.com', password='x')
        add_to_cart(self.buyer, self.tomat, 4)
        self.order = checkout(self.buyer)[0]

    def _act(self, user, action, expected_status=None):
        self.login(user)
        response = self.client.post(reverse('marketplace:order_action', args=[self.order.pk, action]))
        self.order.refresh_from_db()
        if expected_status:
            self.assertEqual(self.order.status, expected_status)
        return response

    def test_full_happy_path(self):
        self._act(self.seller, 'confirm', Order.CONFIRMED)
        self._act(self.seller, 'ready', Order.READY)
        self._act(self.buyer, 'receive', Order.COMPLETED)

    def test_seller_can_complete_ready_order(self):
        change_status(self.order, self.seller, 'confirm')
        change_status(self.order, self.seller, 'ready')
        self._act(self.seller, 'complete', Order.COMPLETED)

    def test_buyer_cannot_confirm_and_seller_cannot_receive(self):
        self._act(self.buyer, 'confirm', Order.PENDING)
        change_status(self.order, self.seller, 'confirm')
        change_status(self.order, self.seller, 'ready')
        self._act(self.seller, 'receive', Order.READY)

    def test_cannot_skip_steps(self):
        self._act(self.seller, 'ready', Order.PENDING)

    def test_seller_reject_restores_stock(self):
        change_status(self.order, self.seller, 'confirm')
        self._act(self.seller, 'cancel', Order.CANCELLED)
        self.tomat.refresh_from_db()
        self.assertEqual(self.tomat.stock, 10)
        self.assertEqual(self.order.cancel_reason, 'Ditolak penjual')

    def test_buyer_can_only_cancel_while_pending(self):
        change_status(self.order, self.seller, 'confirm')
        self._act(self.buyer, 'cancel', Order.CONFIRMED)
        self.tomat.refresh_from_db()
        self.assertEqual(self.tomat.stock, 6)

    def test_buyer_cancel_pending_order(self):
        self._act(self.buyer, 'cancel', Order.CANCELLED)
        self.tomat.refresh_from_db()
        self.assertEqual(self.tomat.stock, 10)

    def test_stranger_cannot_see_or_act_on_order(self):
        stranger = User.objects.create_user(username='x', email='x@example.com', password='x')
        self.login(stranger)
        self.assertEqual(self.client.get(reverse('marketplace:order_detail', args=[self.order.pk])).status_code, 404)
        response = self.client.post(reverse('marketplace:order_action', args=[self.order.pk, 'confirm']))
        self.assertEqual(response.status_code, 404)
        with self.assertRaises(CartError):
            change_status(self.order, stranger, 'confirm')

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(CartError):
            change_status(self.order, self.seller, 'teleport')

    def test_next_redirect_rejects_external_urls(self):
        self.login(self.seller)
        response = self.client.post(reverse('marketplace:order_action', args=[self.order.pk, 'confirm']),
                                    {'next': 'https://evil.example.com/'})
        self.assertEqual(response['Location'], reverse('marketplace:order_detail', args=[self.order.pk]))

    def test_seller_and_buyer_lists_with_status_tabs(self):
        self.login(self.seller)
        response = self.client.get(reverse('marketplace:sales'), {'status': 'pending'})
        self.assertEqual(list(response.context['orders']), [self.order])
        self.assertEqual({k: c for k, _, c in response.context['tabs']}['pending'], 1)
        response = self.client.get(reverse('marketplace:sales'), {'status': 'completed'})
        self.assertEqual(list(response.context['orders']), [])
        self.login(self.buyer)
        self.assertContains(self.client.get(reverse('marketplace:orders')), f'#{self.order.pk}')

    def test_detail_shows_actions_per_role(self):
        self.login(self.seller)
        response = self.client.get(reverse('marketplace:order_detail', args=[self.order.pk]))
        self.assertEqual(response.context['actions'], ['confirm', 'cancel'])
        self.assertContains(response, 'Terima pesanan')
        self.login(self.buyer)
        response = self.client.get(reverse('marketplace:order_detail', args=[self.order.pk]))
        self.assertEqual(response.context['actions'], ['cancel'])

    def _complete(self):
        for action in ('confirm', 'ready'):
            change_status(self.order, self.seller, action)
        change_status(self.order, self.buyer, 'receive')
        return self.order.items.get()

    def test_review_only_after_completed_and_only_once(self):
        item = self.order.items.get()
        with self.assertRaises(CartError):
            add_review(item, self.buyer, 5)
        item = self._complete()
        add_review(item, self.buyer, 4, 'Segar')
        item.refresh_from_db()
        with self.assertRaises(CartError):
            add_review(item, self.buyer, 5)

    def test_review_rating_must_be_valid_and_by_buyer(self):
        item = self._complete()
        with self.assertRaises(CartError):
            add_review(item, self.buyer, 9)
        with self.assertRaises(CartError):
            add_review(item, self.seller, 5)

    def test_review_view_and_product_stats(self):
        item = self._complete()
        self.login(self.buyer)
        self.client.post(reverse('marketplace:review_create', args=[item.pk]), {'rating': 4, 'comment': 'Mantap'})
        self.assertEqual(Review.objects.get().rating, 4)
        response = self.client.get(reverse('marketplace:product_detail', args=[self.tomat.pk]))
        product = response.context['product']
        self.assertEqual((product.sold_count, product.rating_count, product.rating_avg), (4, 1, 4.0))
        self.assertContains(response, 'Mantap')

    def test_stats_are_not_double_counted(self):
        # Pesanan kedua yang selesai + satu ulasan tidak boleh menggandakan jumlah terjual.
        self._complete()
        add_review(self.order.items.get(), self.buyer, 5)
        add_to_cart(self.buyer, self.tomat, 2)
        second = checkout(self.buyer)[0]
        for action in ('confirm', 'ready', 'complete'):
            change_status(second, self.seller, action)
        product = Product.objects.with_stats().get(pk=self.tomat.pk)
        self.assertEqual((product.sold_count, product.rating_count), (6, 1))

    def test_store_page_shows_sales_and_rating(self):
        add_review(self._complete(), self.buyer, 5)
        response = self.client.get(reverse('marketplace:seller_store', args=['budi']))
        self.assertEqual(response.context['sold_total'], 4)
        self.assertEqual(response.context['rating_avg'], 5)
        self.assertEqual(response.context['main_location'], 'Depok')

    def test_store_search_category_and_popular_sort(self):
        self._complete()
        url = reverse('marketplace:seller_store', args=['budi'])
        names = [p.name for p in self.client.get(url, {'sort': 'popular'}).context['page_obj']]
        self.assertEqual(names[0], 'Tomat Cherry')
        names = [p.name for p in self.client.get(url, {'q': 'cabai'}).context['page_obj']]
        self.assertEqual(names, ['Bibit Cabai'])
        names = [p.name for p in self.client.get(url, {'category': 'bibit'}).context['page_obj']]
        self.assertEqual(names, ['Bibit Cabai'])


class ProductImageTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.seller.roles.add(Role.objects.create(name='farmer-seller', description='Penjual'))
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def _png(self, size=(10, 10)):
        buffer = BytesIO()
        Image.new('RGB', size, 'green').save(buffer, 'PNG')
        return SimpleUploadedFile('foto.png', buffer.getvalue(), content_type='image/png')

    def _payload(self, **extra):
        data = {
            'name': 'Selada Air', 'category': self.sayuran.pk,
            'description': 'Selada segar dari kebun hidroponik komunitas.',
            'image_url': '', 'price': 12000, 'unit': 'kg', 'stock': 7,
            'min_order': 1, 'location': 'Depok', 'pickup_address': 'Jl. Margonda No. 1',
            'latitude': '-6.4', 'longitude': '106.8', 'is_active': 'on',
        }
        data.update(extra)
        return data

    def test_upload_photo_takes_priority_over_url(self):
        self.login(self.seller)
        self.client.post(reverse('marketplace:product_create'),
                         self._payload(image=self._png(), image_url='https://example.com/a.jpg'))
        product = Product.objects.get(name='Selada Air')
        self.assertTrue(product.image.name.startswith('products/'))
        self.assertEqual(product.photo_url, product.image.url)

    def test_form_page_has_photo_and_map_picker(self):
        self.login(self.seller)
        response = self.client.get(reverse('marketplace:product_create'))
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, 'id="location-picker"')

    def test_extra_photos_are_saved_limited_and_shown_in_gallery(self):
        self.login(self.seller)
        files = [self._png() for _ in range(2)]
        self.client.post(reverse('marketplace:product_create'),
                         self._payload(image=self._png(), extra_images=files))
        product = Product.objects.get(name='Selada Air')
        self.assertEqual(product.images.count(), 2)
        self.assertEqual(len(product.gallery), 3)
        response = self.client.get(reverse('marketplace:product_detail', args=[product.pk]))
        self.assertEqual(len(response.context['gallery']), 3)

        too_many = [self._png() for _ in range(3)]
        response = self.client.post(reverse('marketplace:product_update', args=[product.pk]),
                                    self._payload(extra_images=too_many))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(product.images.count(), 2)

    def test_remove_extra_photo(self):
        self.login(self.seller)
        self.client.post(reverse('marketplace:product_create'),
                         self._payload(image=self._png(), extra_images=[self._png()]))
        product = Product.objects.get(name='Selada Air')
        extra = product.images.get()
        self.client.post(reverse('marketplace:product_update', args=[product.pk]),
                         self._payload(remove_images=[extra.pk]))
        self.assertFalse(product.images.exists())

    def test_url_is_used_when_no_upload(self):
        product = Product(image_url='https://example.com/a.jpg')
        self.assertEqual(product.photo_url, 'https://example.com/a.jpg')

    def test_rejects_non_image_and_large_files(self):
        self.login(self.seller)
        fake = SimpleUploadedFile('x.png', b'bukan gambar', content_type='image/png')
        response = self.client.post(reverse('marketplace:product_create'), self._payload(image=fake))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(name='Selada Air').exists())
        form = ProductForm(data=self._payload(), files={'image': self._png()})
        form.is_valid()
        big = self._png()
        big.size = 3 * 1024 * 1024
        form = ProductForm(data=self._payload(), files={'image': big})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)


class StarsTagTests(TestCase):
    def test_stars(self):
        from .templatetags.marketplace_tags import stars
        self.assertEqual(stars(3), '\u2605\u2605\u2605\u2606\u2606')
        self.assertEqual(stars(None), '\u2606' * 5)
