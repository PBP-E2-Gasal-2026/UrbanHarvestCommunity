from django.test import SimpleTestCase

from llm_searching.exceptions import InvalidSearch
from llm_searching.filters import (
    normalize_category_filters,
    parse_filters,
    validate_prompt,
)


class FiltersTests(SimpleTestCase):
    def test_category_with_freshness_preserves_descriptor_and_location(self):
        result = normalize_category_filters(
            parse_filters(
                {
                    "keyword": "Sayuran Segar",
                    "categories": ["sayuran"],
                    "location": "Depok",
                    "max_price": 30000,
                }
            ),
            ["sayuran", "buah"],
        )
        self.assertEqual(result.keyword, "segar")
        self.assertEqual(result.categories, ("sayuran",))
        self.assertEqual(result.location, "Depok")
        self.assertEqual(result.max_price, 30000)

    def test_category_only_aliases_become_category_filters(self):
        for keyword, category in (
            ("buah", "buah"),
            ("buah buahan", "buah"),
            ("Buah-buahan", "buah"),
            ("sayur mayur", "sayuran"),
        ):
            with self.subTest(keyword=keyword):
                result = normalize_category_filters(
                    parse_filters({"keyword": keyword, "max_price": 70000}),
                    ["buah", "sayuran"],
                )
                self.assertEqual(result.keyword, "")
                self.assertEqual(result.categories, (category,))
                self.assertEqual(result.max_price, 70000)

    def test_redundant_category_keyword_is_removed_without_loosening_constraints(self):
        result = normalize_category_filters(
            parse_filters(
                {
                    "keyword": "buah",
                    "categories": ["buah"],
                    "max_price": 70000,
                    "location": "Depok",
                    "in_stock": True,
                    "sort": "price_asc",
                    "limit": 3,
                }
            ),
            ["buah", "bibit"],
        )
        self.assertEqual(result.keyword, "")
        self.assertEqual(result.categories, ("buah",))
        self.assertEqual(result.max_price, 70000)
        self.assertEqual(result.location, "Depok")
        self.assertTrue(result.in_stock)
        self.assertEqual(result.sort, "price_asc")
        self.assertEqual(result.limit, 3)

    def test_specific_product_or_different_category_keeps_keyword(self):
        for keyword, categories in (
            ("buah naga", ["buah"]),
            ("bibit tomat", ["bibit"]),
            ("buah", ["bibit"]),
            ("buah", ["buah", "bibit"]),
        ):
            with self.subTest(keyword=keyword, categories=categories):
                result = normalize_category_filters(
                    parse_filters({"keyword": keyword, "categories": categories}),
                    ["buah", "bibit"],
                )
                self.assertEqual(result.keyword, keyword)
                self.assertEqual(result.categories, tuple(categories))

    def test_normalization_does_not_invent_missing_marketplace_categories(self):
        result = normalize_category_filters(
            parse_filters({"keyword": "buah buahan"}), ["sayuran"]
        )
        self.assertEqual(result.keyword, "buah buahan")
        self.assertEqual(result.categories, ())

    def test_complete_neutral_model_response_accepts_product_only_search(self):
        filters = parse_filters(
            {
                "keyword": "tomat",
                "categories": [],
                "min_price": None,
                "max_price": None,
                "location": "",
                "in_stock": False,
                "sort": "newest",
                "limit": 20,
            }
        )
        self.assertEqual(filters.keyword, "tomat")
        self.assertIsNone(filters.min_price)
        self.assertIsNone(filters.max_price)
        self.assertEqual(filters.categories, ())
        self.assertFalse(filters.in_stock)

    def test_prompt_bounds_and_controls(self):
        self.assertEqual(validate_prompt("  cari tomat  "), "cari tomat")
        for value in (None, [], " ", "x" * 2001, "tomat\x00"):
            with self.subTest(value=str(value)[:30]), self.assertRaises(InvalidSearch):
                validate_prompt(value)

    def test_valid_filters_and_defaults(self):
        result = parse_filters({"keyword": "tomat", "max_price": 30000})
        self.assertEqual(result.max_price, 30000)
        self.assertEqual(result.limit, 20)
        self.assertEqual(result.sort, "newest")

    def test_rejects_arbitrary_lookups_sql_and_invalid_values(self):
        for payload in (
            {"seller__email": "x"},
            {"sql": "DELETE FROM marketplace_product"},
            {"max_price": True},
            {"max_price": -1},
            {"min_price": 20, "max_price": 10},
            {"limit": 51},
            {"limit": 0},
            {"categories": "sayuran"},
            {"sort": "seller__email"},
            {"in_stock": "true"},
            {"keyword": []},
            {},
        ):
            with self.subTest(payload=payload), self.assertRaises(InvalidSearch):
                parse_filters(payload)
