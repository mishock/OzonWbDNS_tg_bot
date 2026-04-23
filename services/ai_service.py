"""
Что: сервис AI-рекомендаций.
Зачем: дать краткую умную сводку по товарам в выбранной категории.
Важно: полностью отключается через AI_ENABLED=false.
"""

from __future__ import annotations

import logging
from typing import Sequence

import aiohttp

from config import settings
from models import Product

logger = logging.getLogger(__name__)


class AIService:
    async def build_recommendation(self, category_title: str, products: Sequence[Product]) -> str | None:
        """
        Возвращает короткую AI-рекомендацию или None, если AI выключен/недоступен.
        """
        if not settings.ai_enabled:
            return None
        if not settings.deepseek_api_key:
            logger.warning("AI включен, но DEEPSEEK_API_KEY не задан")
            return None
        if not products:
            return None

        endpoint = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": settings.deepseek_model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты ассистент по подбору товаров. Отвечай по-русски, коротко и по делу. "
                        "Дай 2-4 предложения: что лучше выбрать из списка и почему."
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_user_prompt(category_title=category_title, products=products),
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }

        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(endpoint, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as error:
            logger.warning("Не удалось получить AI-рекомендацию: %s", error)
            return None

    @staticmethod
    def _build_user_prompt(category_title: str, products: Sequence[Product]) -> str:
        lines = [f"Категория: {category_title}", "Список товаров:"]
        for index, product in enumerate(products[:10], start=1):
            lines.append(
                f"{index}) {product.title}; цена={product.price}; площадка={product.marketplace}; рейтинг={product.rating}"
            )
        lines.append("Сделай краткую рекомендацию, какой товар выбрать пользователю в первую очередь.")
        return "\n".join(lines)


ai_service = AIService()
