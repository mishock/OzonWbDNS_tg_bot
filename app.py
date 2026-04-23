"""
Компактный модуль приложения:
- модели данных,
- сервисы каталога и AI,
- клавиатуры,
- обработчики aiogram.
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from html import escape
from pathlib import Path
from urllib.parse import quote_plus

import aiohttp
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import settings

logger = logging.getLogger(__name__)

# =========================
# Константы и словари
# =========================

# 1x1 PNG (белый пиксель) как гарантированный fallback.
FALLBACK_IMAGE_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMBAAZ/q8kAAAAASUVORK5CYII="
)

DEFAULT_PRODUCT_IMAGE_URL = "https://raw.githubusercontent.com/github/explore/main/topics/python/python.png"

CATEGORY_ICONS: dict[str, str] = {
    "smartphones": "📱",
    "laptops": "💻",
    "tvs": "📺",
    "fridges": "🧊",
    "headphones": "🎧",
    "vacuums": "🧹",
    "monitors": "🖥",
    "washers": "🧺",
}

MARKETPLACE_ICONS: dict[str, str] = {
    "Ozon": "🟦",
    "Wildberries": "🟣",
    "DNS": "🟧",
}

SPINNER_FRAMES: tuple[str, ...] = ("◐", "◓", "◑", "◒")
SPARK_FRAMES: tuple[str, ...] = ("✨", "💫", "⭐", "🌟")

# =========================
# Утилиты
# =========================


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def read_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"Ожидался список в JSON: {path}")
    return data


def spinner_frame(step: int) -> str:
    return SPINNER_FRAMES[step % len(SPINNER_FRAMES)]


def spark_frame(step: int) -> str:
    return SPARK_FRAMES[step % len(SPARK_FRAMES)]


def format_price(value: float | int) -> str:
    return f"{int(value):,}".replace(",", " ") + " ₽"


# =========================
# Модели данных
# =========================

@dataclass(frozen=True)
class Category:
    slug: str
    title: str


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


def format_product(product: Product) -> str:
    safe_title = escape(product.title)
    safe_category = escape(product.category)
    safe_marketplace = escape(product.marketplace)
    safe_url = escape(product.url, quote=True)
    category_icon = CATEGORY_ICONS.get(product.category, "📦")
    marketplace_icon = MARKETPLACE_ICONS.get(product.marketplace, "🏪")
    return (
        f"{category_icon} <b>Название:</b> {safe_title}\n"
        f"💰 <b>Цена:</b> {format_price(product.price)}\n"
        f"🗂️ <b>Категория:</b> {safe_category}\n"
        f"{marketplace_icon} <b>Площадка:</b> {safe_marketplace}\n"
        f"🔗 <b>Ссылка:</b> <a href=\"{safe_url}\">Открыть товар</a>"
    )


def product_image_url(product: Product) -> str:
    return product.image_url or DEFAULT_PRODUCT_IMAGE_URL


def sort_products_by_price(products: list[Product]) -> list[Product]:
    return sorted(products, key=lambda item: float(item.price))


# =========================
# Сервисы приложения
# =========================

class MarketplaceService:
    def __init__(self, products_path: Path, marketplace_name: str, search_url_template: str) -> None:
        self._products_path = products_path
        self._marketplace_name = marketplace_name
        self._search_url_template = search_url_template

    def search(self, category_slug: str, limit: int) -> list[Product]:
        raw = read_json(self._products_path)
        filtered: list[Product] = []
        for item in raw:
            if item["marketplace"] != self._marketplace_name or item["category"] != category_slug:
                continue
            query = quote_plus(item["title"])
            item_with_real_url = {**item, "url": self._search_url_template.format(query=query)}
            filtered.append(Product(**item_with_real_url))
        return filtered[:limit]


class CatalogService:
    def __init__(self) -> None:
        self._categories = self._load_categories()
        self._ozon_service = MarketplaceService(
            settings.products_path,
            marketplace_name="Ozon",
            search_url_template="https://www.ozon.ru/search/?text={query}",
        )
        self._wb_service = MarketplaceService(
            settings.products_path,
            marketplace_name="Wildberries",
            search_url_template="https://www.wildberries.ru/catalog/0/search.aspx?search={query}",
        )
        self._dns_service = MarketplaceService(
            settings.products_path,
            marketplace_name="DNS",
            search_url_template="https://www.dns-shop.ru/search/?q={query}",
        )

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
        ozon = self._ozon_service.search(category_slug, per_marketplace_limit)
        wb = self._wb_service.search(category_slug, per_marketplace_limit)
        dns = self._dns_service.search(category_slug, per_marketplace_limit)
        return sort_products_by_price([*ozon, *wb, *dns])


class AIService:
    async def build_recommendation(self, category_title: str, products: list[Product]) -> str | None:
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
    def _build_user_prompt(category_title: str, products: list[Product]) -> str:
        lines = [f"Категория: {category_title}", "Список товаров:"]
        for index, product in enumerate(products[:10], start=1):
            lines.append(
                f"{index}) {product.title}; цена={product.price}; площадка={product.marketplace}; рейтинг={product.rating}"
            )
        lines.append("Сделай краткую рекомендацию, какой товар выбрать пользователю в первую очередь.")
        return "\n".join(lines)


# =========================
# Telegram-клавиатуры
# =========================

def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧭 Выбрать категорию", callback_data="open_categories")],
        ]
    )


def categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for category in categories:
        icon = CATEGORY_ICONS.get(category.slug, "🛍")
        current_row.append(
            InlineKeyboardButton(
                text=f"{icon} {category.title}",
                callback_data=f"cat:{category.slug}",
            )
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)

    rows.append([InlineKeyboardButton(text="🆕 Новый поиск", callback_data="new_search")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def result_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗂 Другую категорию", callback_data="open_categories")],
            [InlineKeyboardButton(text="🆕 Новый поиск", callback_data="new_search")],
        ]
    )


# =========================
# Инициализация и роутер
# =========================

catalog_service = CatalogService()
ai_service = AIService()
router = Router()


# =========================
# Обработчики Telegram-событий
# =========================

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "👋 Привет! Я помогу подобрать товары по категориям.\n\n"
        "Что умею в MVP:\n"
        "- 🧭 выбор категории;\n"
        "- 🛒 показ товаров из Ozon, Wildberries и DNS;\n"
        "- 🔗 прямые ссылки на каждый товар."
    )
    await message.answer(text, reply_markup=start_keyboard())


@router.callback_query(F.data == "new_search")
async def callback_new_search(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🆕 Новый поиск запущен. Выберите категорию.",
        reply_markup=start_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "open_categories")
async def callback_open_categories(callback: CallbackQuery) -> None:
    categories = catalog_service.get_categories()
    await callback.message.edit_text(
        "🧩 Выберите категорию товара:",
        reply_markup=categories_keyboard(categories),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def callback_choose_category(callback: CallbackQuery) -> None:
    category_slug = callback.data.split(":", maxsplit=1)[1]
    await render_category_products(callback, category_slug=category_slug)


async def render_category_products(callback: CallbackQuery, category_slug: str) -> None:
    try:
        step = 0
        await callback.answer(f"{spinner_frame(step)} Ищу товары...", show_alert=False)
        category = catalog_service.resolve_category(category_slug)
        if not category:
            await callback.message.edit_text("Категория не найдена. Выберите другую.", reply_markup=None)
            return

        products = catalog_service.search_by_category(
            category_slug=category_slug,
            per_marketplace_limit=settings.per_marketplace_limit,
        )

        if not products:
            await callback.message.edit_text(
                "По этой категории товары не найдены. Попробуйте выбрать другую категорию.",
            )
            return

        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        await callback.message.edit_text(
            f"{spark_frame(step)} <b>Категория:</b> {category.title}\n"
            f"Показано товаров: {len(products)}.",
            disable_web_page_preview=True,
        )

        ai_text = await ai_service.build_recommendation(category_title=category.title, products=products)
        if ai_text:
            await callback.message.answer(f"{spark_frame(step + 1)} <b>AI-рекомендация:</b>\n{ai_text}")

        for product in products:
            card_text = format_product(product)
            if product.image_url:
                image_url = product_image_url(product)
                try:
                    await callback.message.answer_photo(
                        photo=image_url,
                        caption=card_text,
                    )
                    continue
                except TelegramBadRequest:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url, timeout=10) as response:
                                response.raise_for_status()
                                data = await response.read()
                        await callback.message.answer_photo(
                            photo=BufferedInputFile(data, filename="product.jpg"),
                            caption=card_text,
                        )
                        continue
                    except Exception:
                        pass

            try:
                await callback.message.answer_photo(
                    photo=BufferedInputFile(FALLBACK_IMAGE_BYTES, filename="product.png"),
                    caption=card_text,
                )
            except Exception:
                await callback.message.answer(
                    card_text,
                    disable_web_page_preview=False,
                )

        await callback.message.answer(
            f"{spinner_frame(step + 1)} Выберите действие:",
            reply_markup=result_actions_keyboard(),
        )
    except Exception as error:
        logger.exception("Ошибка при выдаче товаров: %s", error)
        await callback.message.edit_text(
            "Произошла ошибка при получении товаров. Попробуйте еще раз.",
        )
        try:
            await callback.answer()
        except Exception:
            pass
