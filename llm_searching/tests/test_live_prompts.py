"""Opt-in model regression checks; uses the configured, potentially paid API."""

import os
from unittest import skipUnless

from django.test import SimpleTestCase

from llm_searching.openrouter import OpenRouterClient


@skipUnless(
    os.getenv("LLM_RUN_LIVE_TESTS") == "1", "Live OpenRouter evaluation is opt-in"
)
class LivePromptTests(SimpleTestCase):
    categories = ("sayuran", "buah", "bibit", "kompos", "media-tanam")

    def test_lowercase_and_capitalized_city_preserve_same_category_and_descriptor(self):
        observed = []
        for prompt in (
            "sayuran segar di sekitar depok",
            "sayuran segar di sekitar Depok",
        ):
            with self.subTest(prompt=prompt):
                result = OpenRouterClient().extract(prompt, self.categories)
                self.assertEqual(result["status"], "search")
                filters = result["filters"]
                self.assertEqual(filters["categories"], ["sayuran"])
                self.assertEqual(filters["keyword"].casefold(), "")
                self.assertEqual(filters["location"].casefold(), "depok")
                self.assertEqual(result["unsupported_conditions"], [])
                observed.append(
                    (
                        filters["categories"],
                        filters["keyword"].casefold(),
                        filters["location"].casefold(),
                    )
                )
        self.assertEqual(observed[0], observed[1])

    def test_fruit_plural_and_misspelled_thousands_are_category_only(self):
        result = OpenRouterClient().extract(
            "carikan saya buah buahan dibawah 70 roibu", self.categories
        )
        self.assertEqual(result["status"], "search")
        self.assertEqual(result["filters"]["categories"], ["buah"])
        self.assertFalse(result["filters"].get("keyword"))
        self.assertEqual(result["filters"]["max_price"], 70000)
        self.assertEqual(result["unsupported_conditions"], [])

    def test_specific_fruit_name_is_not_reduced_to_category_only(self):
        result = OpenRouterClient().extract(
            "carikan saya buah naga dibawah 70 ribu", self.categories
        )
        self.assertEqual(result["status"], "search")
        self.assertIn("naga", result["filters"]["keyword"].casefold())
        self.assertEqual(result["filters"]["max_price"], 70000)

    def test_cheapest_vegetable_recommendation_is_a_category_search(self):
        result = OpenRouterClient().extract(
            "rekomendasikan sayuran kepada saya dengan harga termurah", self.categories
        )
        self.assertEqual(result["status"], "search")
        self.assertEqual(result["filters"]["categories"], ["sayuran"])
        self.assertFalse(result["filters"].get("keyword"))
        self.assertEqual(result["filters"]["sort"], "price_asc")
        self.assertEqual(result["unsupported_conditions"], [])

    def test_obvious_product_and_city_typos_preserve_budget(self):
        result = OpenRouterClient().extract(
            "tolong cariin tomta di dpok maksimal 30 ribu", self.categories
        )
        self.assertEqual(result["status"], "search")
        self.assertEqual(result["filters"]["keyword"].casefold(), "tomat")
        self.assertEqual(result["filters"]["location"].casefold(), "depok")
        self.assertEqual(result["filters"]["max_price"], 30000)
        self.assertEqual(result["unsupported_conditions"], [])

    def test_typo_in_category_still_supports_cheapest_search(self):
        result = OpenRouterClient().extract(
            "rekomndasikan syuran yang termurah", self.categories
        )
        self.assertEqual(result["status"], "search")
        self.assertEqual(result["filters"]["categories"], ["sayuran"])
        self.assertFalse(result["filters"].get("keyword"))
        self.assertEqual(result["filters"]["sort"], "price_asc")

    def test_unseen_typo_variants_generalize_beyond_prompt_examples(self):
        result = OpenRouterClient().extract(
            "rekomendasikan sayruan paling murha", self.categories
        )
        self.assertEqual(result["status"], "search")
        self.assertEqual(result["filters"]["categories"], ["sayuran"])
        self.assertFalse(result["filters"].get("keyword"))
        self.assertEqual(result["filters"]["sort"], "price_asc")

    def test_product_name_alone_is_enough_to_search(self):
        result = OpenRouterClient().extract("carikan saya tomat", self.categories)
        self.assertEqual(result["status"], "search")
        self.assertEqual(result["filters"]["keyword"].casefold(), "tomat")
        self.assertEqual(result["unsupported_conditions"], [])
        self.assertFalse(result["filters"].get("categories"))
        self.assertIsNone(result["filters"].get("max_price"))
        self.assertFalse(result["filters"].get("location"))
        self.assertIsNone(result["filters"].get("min_price"))
        self.assertFalse(result["filters"].get("in_stock"))

    def test_ordinary_location_and_price_need_no_followup(self):
        result = OpenRouterClient().extract(
            "cari tomat di Depok di bawah 30 ribu", self.categories
        )
        self.assertEqual(result["status"], "search")
        self.assertEqual(result["filters"]["keyword"].casefold(), "tomat")
        self.assertEqual(result["filters"]["location"].casefold(), "depok")
        self.assertEqual(result["filters"]["max_price"], 30000)
        self.assertEqual(result["unsupported_conditions"], [])

    def test_quantity_budget_still_requires_clarification(self):
        result = OpenRouterClient().extract(
            "cari tomat 3 kg dengan total maksimal Rp50.000", self.categories
        )
        self.assertEqual(result["status"], "needs_clarification")
        self.assertTrue(result["unsupported_conditions"])
