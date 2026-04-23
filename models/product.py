"""
Что: модель товара.
Зачем: единый контракт данных для всех маркетплейсов.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    title: str
    price: float | int
    category: str
    marketplace: str
    url: str
    image_url: str | None = None
    rating: float | None = None
    description: str | None = None
