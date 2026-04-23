"""
Что: модель категории.
Зачем: хранить slug и отображаемое русское название.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    slug: str
    title: str
