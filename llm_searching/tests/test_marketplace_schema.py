from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps

from llm_searching.exceptions import MarketplaceUnavailable
from llm_searching.filters import parse_filters
from llm_searching.marketplace import MarketplaceRepository


class MarketplaceSchemaTests(SimpleTestCase):
    @isolate_apps()
    def test_missing_category_relation_is_dependency_unavailable(self):
        class Category(models.Model):
            slug = models.SlugField()

            class Meta:
                app_label = "contract_missing_fk"
                db_table = "marketplace_category"

        class Product(models.Model):
            class Meta:
                app_label = "contract_missing_fk"
                db_table = "marketplace_product"

        repo = MarketplaceRepository(product_model=Product, category_model=Category)
        with self.assertRaises(MarketplaceUnavailable):
            repo.search(parse_filters({"keyword": "tomat"}))

    @isolate_apps()
    def test_missing_product_fields_are_dependency_unavailable(self):
        class Category(models.Model):
            name = models.CharField(max_length=100)
            slug = models.SlugField()

            class Meta:
                app_label = "contract_missing_fields"
                db_table = "marketplace_category"

        class Product(models.Model):
            category = models.ForeignKey(Category, on_delete=models.PROTECT)

            class Meta:
                app_label = "contract_missing_fields"
                db_table = "marketplace_product"

        repo = MarketplaceRepository(product_model=Product, category_model=Category)
        with self.assertRaises(MarketplaceUnavailable):
            repo.search(parse_filters({"keyword": "tomat"}))

    @isolate_apps()
    def test_missing_category_slug_is_dependency_unavailable(self):
        class Category(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "contract_missing_slug"
                db_table = "marketplace_category"

        class Product(models.Model):
            category = models.ForeignKey(Category, on_delete=models.PROTECT)

            class Meta:
                app_label = "contract_missing_slug"
                db_table = "marketplace_product"

        repo = MarketplaceRepository(product_model=Product, category_model=Category)
        with self.assertRaises(MarketplaceUnavailable):
            repo.category_slugs()
