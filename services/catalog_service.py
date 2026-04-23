"""
Что: агрегатор каталога товаров.
Зачем: объединяет результаты Ozon/WB/DNS в едином формате.
"""

from dataclasses import asdict

from config import settings
from models import Category, Product
from services.dns_service import DNSService
from services.ozon_service import OzonService
from services.wildberries_service import WildberriesService
from utils.formatter import sort_products_by_price
from utils.json_storage import read_json


class CatalogService:
    def __init__(self) -> None:
        self._categories = self._load_categories()
        self._ozon_service = OzonService(settings.products_path)
        self._wb_service = WildberriesService(settings.products_path)
        self._dns_service = DNSService(settings.products_path)

    def _load_categories(self) -> list[Category]:
        raw = read_json(settings.categories_path)
        return [Category(slug=item["slug"], title=item["title"]) for item in raw]

    def get_categories(self) -> list[Category]:
        return self._categories

    def resolve_category(self, slug: str) -> Category | None:
        for category in self._categories:
            if category.slug == slug:
                return category
        return None

    def search_by_category(self, category_slug: str, per_marketplace_limit: int) -> list[Product]:
        """
        Возвращает объединенный список товаров из трех маркетплейсов.
        """
        ozon = self._ozon_service.search(category_slug, per_marketplace_limit)
        wb = self._wb_service.search(category_slug, per_marketplace_limit)
        dns = self._dns_service.search(category_slug, per_marketplace_limit)
        merged = [*ozon, *wb, *dns]
        return sort_products_by_price(merged)

    def to_dict(self) -> dict:
        """Служебный метод, удобно для отладки."""
        return {"categories": [asdict(c) for c in self._categories]}


catalog_service = CatalogService()
