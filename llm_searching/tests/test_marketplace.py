from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext

from llm_searching.exceptions import InvalidSearch, MarketplaceUnavailable
from llm_searching.filters import parse_filters
from llm_searching.marketplace import MarketplaceRepository

MARKETPLACE_INSTALLED = apps.is_installed("marketplace")
if MARKETPLACE_INSTALLED:
    from marketplace.models import Category, Product
else:
    from llm_searching.tests.contract_app.models import Category, Product


class MarketplaceTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not MARKETPLACE_INSTALLED:
            with connection.schema_editor() as editor:
                editor.create_model(Category)
                editor.create_model(Product)

    @classmethod
    def tearDownClass(cls):
        if not MARKETPLACE_INSTALLED:
            with connection.schema_editor() as editor:
                editor.delete_model(Product)
                editor.delete_model(Category)
        super().tearDownClass()

    def setUp(self):
        Product.objects.all().delete()
        Category.objects.all().delete()
        self.seller = get_user_model().objects.create_user(
            "contract_seller", "seller@example.com"
        )
        category = Category.objects.create(name="Sayuran", slug="sayuran")
        self.repo = MarketplaceRepository(
            product_model=Product, category_model=Category
        )
        self.tomato = self.create_product(
            name="Tomat",
            price=25000,
            category=category,
            image_url="https://example.com/tomat.jpg",
        )
        self.create_product(name="Tomat mahal", price=50000, category=category)
        self.create_product(
            name="Tomat arsip", price=1000, category=category, is_active=False
        )
        self.create_product(name="Tomat habis", price=20000, category=category, stock=0)

    def create_product(self, **values):
        defaults = {"stock": 10, "location": "Depok"}
        if MARKETPLACE_INSTALLED:
            defaults["seller"] = self.seller
        defaults.update(values)
        return Product.objects.create(**defaults)

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
        self.create_product(
            name="Tomat sama", price=25000, category=self.tomato.category
        )
        cards = self.repo.search(
            parse_filters({"keyword": "tomat", "sort": "price_asc", "limit": 2})
        )
        self.assertEqual([c.name for c in cards], ["Tomat habis", "Tomat"])

    def test_missing_dependency_is_not_empty_results(self):
        with (
            patch("llm_searching.marketplace.apps.get_model", side_effect=LookupError),
            self.assertRaises(MarketplaceUnavailable),
        ):
            MarketplaceRepository().search(parse_filters({"keyword": "tomat"}))

    def test_unknown_category_rejected(self):
        with self.assertRaises(InvalidSearch):
            self.repo.search(parse_filters({"categories": ["not-real"]}))

    def test_service_removes_redundant_fruit_keyword_before_query(self):
        from unittest.mock import Mock

        from llm_searching.service import SearchService

        fruit_category = Category.objects.create(name="Buah", slug="buah")
        fruit = self.create_product(
            name="Jeruk Lemon", category=fruit_category, price=22000
        )
        self.create_product(name="Melon Premium", category=fruit_category, price=80000)
        client = Mock()
        client.extract.return_value = {
            "status": "search",
            "filters": {"keyword": "buah", "categories": ["buah"], "max_price": 70000},
            "clarification": "",
            "unsupported_conditions": [],
        }
        client.suggest.return_value = {
            "suggestions": [{"id": fruit.pk, "reasons": ["within_budget"]}]
        }
        result = SearchService(self.repo, client).run(
            "carikan saya buah buahan dibawah 70 roibu"
        )
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual([card["name"] for card in result["products"]], ["Jeruk Lemon"])
        self.assertEqual(result["filters"]["keyword"], "")
        self.assertEqual(result["filters"]["categories"], ["buah"])
        self.assertEqual(result["filters"]["max_price"], 70000)

    def test_category_and_freshness_search_preserves_city_and_product_constraint(self):
        from unittest.mock import Mock

        from llm_searching.service import SearchService

        self.tomato.description = "Tomat segar dari kebun di Depok."
        self.tomato.save(update_fields=["description"])
        self.create_product(
            name="Selada",
            description="Selada segar dari kebun.",
            category=self.tomato.category,
            price=12000,
            location="Bogor",
        )
        self.create_product(
            name="Bibit Sayur",
            description="Bibit kering untuk ditanam.",
            category=self.tomato.category,
            price=10000,
        )
        client = Mock()
        client.extract.return_value = {
            "status": "search",
            "filters": {
                "keyword": "sayuran segar",
                "categories": ["sayuran"],
                "location": "Depok",
            },
            "clarification": "",
            "unsupported_conditions": [],
        }
        client.suggest.return_value = {
            "suggestions": [{"id": self.tomato.pk, "reasons": []}]
        }
        result = SearchService(self.repo, client).run("sayuran segar di sekitar depok")
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual([p["id"] for p in result["products"]], [self.tomato.pk])
        self.assertEqual(result["filters"]["keyword"], "")
        self.assertEqual(result["filters"]["location"], "Depok")
