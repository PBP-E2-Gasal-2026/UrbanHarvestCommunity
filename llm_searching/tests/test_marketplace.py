from django.db import connection
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext

from llm_searching.exceptions import InvalidSearch, MarketplaceUnavailable
from llm_searching.filters import parse_filters
from llm_searching.marketplace import MarketplaceRepository
from llm_searching.tests.contract_app.models import Category, Product


class MarketplaceTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as editor:
            editor.create_model(Category)
            editor.create_model(Product)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            editor.delete_model(Product)
            editor.delete_model(Category)
        super().tearDownClass()

    def setUp(self):
        Product.objects.all().delete()
        Category.objects.all().delete()
        category = Category.objects.create(name="Sayuran", slug="sayuran")
        self.repo = MarketplaceRepository(
            product_model=Product, category_model=Category
        )
        self.tomato = Product.objects.create(
            name="Tomat",
            price=25000,
            category=category,
            image_url="https://example.com/tomat.jpg",
        )
        Product.objects.create(name="Tomat mahal", price=50000, category=category)
        Product.objects.create(
            name="Tomat arsip", price=1000, category=category, is_active=False
        )
        Product.objects.create(
            name="Tomat habis", price=20000, category=category, stock=0
        )

    def test_filters_in_database_and_projects_safe_cards(self):
        with CaptureQueriesContext(connection) as queries:
            cards = self.repo.search(
                parse_filters(
                    {
                        "keyword": "tomat",
                        "max_price": 30000,
                        "in_stock": True,
                        "categories": ["sayuran"],
                    }
                )
            )
        self.assertEqual([card.id for card in cards], [self.tomato.pk])
        self.assertEqual(cards[0].url, f"/marketplace/products/{self.tomato.pk}/")
        self.assertEqual(cards[0].image_url, "https://example.com/tomat.jpg")
        self.assertNotIn("merchant", cards[0].to_dict())
        for query in queries:
            self.assertTrue(query["sql"].lstrip().upper().startswith("SELECT"))
            self.assertNotIn("authentication_", query["sql"])
            self.assertNotIn("seller_id", query["sql"])
        self.assertIn("LIMIT 20", queries[-1]["sql"])

    def test_stable_price_order_inactive_and_zero_stock(self):
        cards = self.repo.search(
            parse_filters({"keyword": "tomat", "sort": "price_asc"})
        )
        self.assertEqual(
            [c.name for c in cards], ["Tomat habis", "Tomat", "Tomat mahal"]
        )
        self.assertFalse(cards[0].is_available)
        Product.objects.create(
            name="Tomat sama", price=25000, category=self.tomato.category
        )
        cards = self.repo.search(
            parse_filters({"keyword": "tomat", "sort": "price_asc", "limit": 2})
        )
        self.assertEqual([c.name for c in cards], ["Tomat habis", "Tomat"])

    def test_missing_dependency_is_not_empty_results(self):
        with self.assertRaises(MarketplaceUnavailable):
            MarketplaceRepository().search(parse_filters({"keyword": "tomat"}))

    def test_unknown_category_rejected(self):
        with self.assertRaises(InvalidSearch):
            self.repo.search(parse_filters({"categories": ["not-real"]}))
