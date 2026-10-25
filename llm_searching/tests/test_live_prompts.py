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
