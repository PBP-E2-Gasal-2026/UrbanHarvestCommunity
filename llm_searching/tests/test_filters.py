from django.test import SimpleTestCase
from llm_searching.filters import parse_filters, validate_prompt
from llm_searching.exceptions import InvalidSearch


class FiltersTests(SimpleTestCase):
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
