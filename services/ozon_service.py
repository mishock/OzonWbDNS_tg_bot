"""
Что: сервис Ozon.
Зачем: изолировать источник данных маркетплейса.
Важно: в MVP читает mock JSON; позже заменяется на API/парсинг.
"""

from pathlib import Path
from urllib.parse import quote_plus

from models import Product
from utils.json_storage import read_json


class OzonService:
    marketplace_name = "Ozon"
    search_url_template = "https://www.ozon.ru/search/?text={query}"

    def __init__(self, products_path: Path) -> None:
        self._products_path = products_path

    def search(self, category_slug: str, limit: int) -> list[Product]:
        raw = read_json(self._products_path)
        filtered: list[Product] = []
        for item in raw:
            if item["marketplace"] != self.marketplace_name or item["category"] != category_slug:
                continue
            query = quote_plus(item["title"])
            item_with_real_url = {**item, "url": self.search_url_template.format(query=query)}
            filtered.append(Product(**item_with_real_url))
        return filtered[:limit]
