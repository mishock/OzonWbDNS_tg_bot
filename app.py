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
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import settings

logger = logging.getLogger(__name__)
ai_runtime_enabled = settings.ai_enabled

# Итоговый проект по ТЗ: «Telegram-бот-агрегатор AKEM-bot» (@OzonWbDNS_bot)
BOT_BRAND_NAME = "AKEM-bot"
BOT_USERNAME_DISPLAY = "@OzonWbDNS_bot"

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
MARKETPLACE_ORDER: tuple[str, ...] = ("Ozon", "Wildberries", "DNS")

SPINNER_FRAMES: tuple[str, ...] = ("◐", "◓", "◑", "◒")
SPARK_FRAMES: tuple[str, ...] = ("✨", "💫", "⭐", "🌟")
PAGE_SIZE = 3
MAX_TOTAL_RESULTS = 15

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


def is_ai_enabled() -> bool:
    return ai_runtime_enabled


def ai_status_label() -> str:
    return "🟢 AI: ВКЛ" if is_ai_enabled() else "⚪ AI: ВЫКЛ"


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
    """Вывод по ТЗ п. 2.5: название, цена, площадка, ссылка (рейтинг — при наличии в данных)."""
    safe_title = escape(product.title)
    safe_marketplace = escape(product.marketplace)
    safe_url = escape(product.url, quote=True)
    category_icon = CATEGORY_ICONS.get(product.category, "📦")
    marketplace_icon = MARKETPLACE_ICONS.get(product.marketplace, "🏪")
    lines: list[str] = [
        f"{category_icon} <b>Название:</b> {safe_title}",
        f"💰 <b>Цена:</b> {format_price(product.price)}",
    ]
    if product.rating is not None:
        lines.append(f"⭐ <b>Рейтинг:</b> {product.rating}")
    lines.extend(
        [
            f"{marketplace_icon} <b>Площадка:</b> {safe_marketplace}",
            f"🔗 <b>Ссылка:</b> <a href=\"{safe_url}\">Открыть товар</a>",
        ]
    )
    return "\n".join(lines)


def product_image_url(product: Product) -> str:
    return product.image_url or DEFAULT_PRODUCT_IMAGE_URL


def sort_products_by_price(products: list[Product]) -> list[Product]:
    return sorted(products, key=lambda item: float(item.price))


def interleave_by_marketplace(products: list[Product]) -> list[Product]:
    """
    Собирает выдачу "по кругу" маркетплейсов:
    Ozon -> Wildberries -> DNS -> ...
    Это дает блоки по 3 товара из разных источников (если в источниках есть товары).
    """
    buckets: dict[str, list[Product]] = {name: [] for name in MARKETPLACE_ORDER}
    fallback: list[Product] = []
    for product in products:
        if product.marketplace in buckets:
            buckets[product.marketplace].append(product)
        else:
            fallback.append(product)

    result: list[Product] = []
    while True:
        appended = False
        for marketplace in MARKETPLACE_ORDER:
            if buckets[marketplace]:
                result.append(buckets[marketplace].pop(0))
                appended = True
        if not appended:
            break

    # Если появятся нестандартные площадки, добавляем их в конец.
    result.extend(fallback)
    return result


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
        if not is_ai_enabled():
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
                        "Ты ассистент по подбору товаров (Telegram AKEM-bot). Отвечай по-русски, коротко и по делу. "
                        "Обязательно учитывай соотношение цены и рейтинга. Дай 2–4 предложения: что выбрать в первую "
                        "очередь и почему."
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

    async def build_live_products(
        self,
        category_title: str,
        category_slug: str,
        per_marketplace_limit: int,
    ) -> list[Product] | None:
        """
        Пытается получить "живой" список товаров через AI.
        Возвращает None, если AI выключен/недоступен или ответ невалидный.
        """
        if not is_ai_enabled():
            return None
        if not settings.deepseek_api_key:
            return None

        endpoint = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
        total_limit = max(per_marketplace_limit * 3, 6)
        payload = {
            "model": settings.deepseek_model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты помощник по подбору товаров. Верни ТОЛЬКО JSON-массив без пояснений. "
                        "Элементы массива: title, price, marketplace, rating, description. "
                        "marketplace только из: Ozon, Wildberries, DNS."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Категория: {category_title}. Подбери до {total_limit} актуальных товаров "
                        "и верни JSON-массив объектов."
                    ),
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=25)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(endpoint, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
            content = data["choices"][0]["message"]["content"].strip()
            products = self._parse_live_products_json(
                content=content,
                category_slug=category_slug,
                per_marketplace_limit=per_marketplace_limit,
            )
            if not products:
                return None
            return products
        except Exception as error:
            logger.warning("Не удалось получить AI-каталог: %s", error)
            return None

    @staticmethod
    def _build_user_prompt(category_title: str, products: list[Product]) -> str:
        lines = [f"Категория: {category_title}", "Список товаров:"]
        for index, product in enumerate(products[:10], start=1):
            lines.append(
                f"{index}) {product.title}; цена={product.price}; площадка={product.marketplace}; рейтинг={product.rating}"
            )
        lines.append(
            "Сделай краткую рекомендацию: какой товар выбрать в первую очередь с учётом цены и рейтинга."
        )
        return "\n".join(lines)

    @staticmethod
    def _parse_live_products_json(
        content: str,
        category_slug: str,
        per_marketplace_limit: int,
    ) -> list[Product]:
        """
        Парсит JSON-массив товаров из ответа AI и нормализует в Product.
        """
        start = content.find("[")
        end = content.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []

        raw_array = content[start : end + 1]
        data = json.loads(raw_array)
        if not isinstance(data, list):
            return []

        result: list[Product] = []
        per_marketplace_count: dict[str, int] = {"Ozon": 0, "Wildberries": 0, "DNS": 0}
        for item in data:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            marketplace = str(item.get("marketplace", "")).strip()
            if not title or marketplace not in per_marketplace_count:
                continue
            if per_marketplace_count[marketplace] >= per_marketplace_limit:
                continue

            try:
                price = float(item.get("price", 0))
            except Exception:
                price = 0.0
            if price <= 0:
                continue

            rating_raw = item.get("rating")
            try:
                rating = float(rating_raw) if rating_raw is not None else None
            except Exception:
                rating = None

            description = item.get("description")
            if description is not None:
                description = str(description).strip()

            url = AIService._build_marketplace_search_url(marketplace=marketplace, title=title)
            result.append(
                Product(
                    title=title,
                    price=price,
                    category=category_slug,
                    marketplace=marketplace,
                    url=url,
                    image_url=None,
                    rating=rating,
                    description=description or None,
                )
            )
            per_marketplace_count[marketplace] += 1

        return sort_products_by_price(result)

    @staticmethod
    def _build_marketplace_search_url(marketplace: str, title: str) -> str:
        query = quote_plus(title)
        if marketplace == "Ozon":
            return f"https://www.ozon.ru/search/?text={query}"
        if marketplace == "Wildberries":
            return f"https://www.wildberries.ru/catalog/0/search.aspx?search={query}"
        return f"https://www.dns-shop.ru/search/?q={query}"


# =========================
# Telegram-клавиатуры
# =========================

def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧭 Выбрать категорию", callback_data="open_categories")],
            [InlineKeyboardButton(text=ai_status_label(), callback_data="ai_toggle")],
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
    rows.append([InlineKeyboardButton(text=ai_status_label(), callback_data="ai_toggle")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def result_actions_keyboard(category_slug: str, next_offset: int, has_more: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if has_more:
        rows.append(
            [InlineKeyboardButton(text="🔄 Показать ещё", callback_data=f"more:{category_slug}:{next_offset}")]
        )
    rows.extend(
        [
            [InlineKeyboardButton(text=ai_status_label(), callback_data="ai_toggle")],
            [InlineKeyboardButton(text="🗂 Другие категории", callback_data="open_categories")],
            [InlineKeyboardButton(text="🆕 Новый поиск", callback_data="new_search")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
        f"👋 Привет! Я <b>{BOT_BRAND_NAME}</b> ({BOT_USERNAME_DISPLAY}) — бот-агрегатор для поиска товаров "
        "на маркетплейсах <b>Ozon</b>, <b>Wildberries</b> и <b>DNS</b>.\n\n"
        "Что умею:\n"
        "• выбор категории (смартфоны, ноутбуки, техника для дома и др.);\n"
        "• выдача предложений с ценой, площадкой и ссылкой на покупку;\n"
        "• при включённом AI — краткие рекомендации с учётом цены и рейтинга.\n\n"
        "Откройте категории кнопкой ниже или введите /help."
    )
    await message.answer(text, reply_markup=start_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = (
        f"<b>{BOT_BRAND_NAME}</b> ({BOT_USERNAME_DISPLAY})\n\n"
        "<b>Команды</b>\n"
        "/start — приветствие и главное меню\n"
        "/help — эта справка\n\n"
        "<b>Кнопки</b>\n"
        "• «Выбрать категорию» — список категорий товаров\n"
        "• «Показать ещё» — следующие три товара (до 15 на категорию)\n"
        "• «Другие категории» — сменить категорию\n"
        "• «Новый поиск» — начать заново\n"
        "• «AI: ВКЛ/ВЫКЛ» — подсказки и подбор через AI (если задан ключ API)\n\n"
        "Ссылки ведут на поиск маркетплейсов по названию товара (как в ТЗ)."
    )
    await message.answer(text, reply_markup=start_keyboard())


@router.callback_query(F.data == "new_search")
async def callback_new_search(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🆕 Новый поиск запущен. Выберите категорию.",
        reply_markup=start_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "ai_toggle")
async def callback_ai_toggle(callback: CallbackQuery) -> None:
    global ai_runtime_enabled
    ai_runtime_enabled = not ai_runtime_enabled
    status_text = "включен" if ai_runtime_enabled else "выключен"
    await callback.answer(f"AI-режим {status_text}", show_alert=True)
    await callback.message.answer(
        f"🤖 AI-режим {status_text}.",
        reply_markup=start_keyboard(),
    )


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
    await render_category_products(callback, category_slug=category_slug, offset=0)


@router.callback_query(F.data.startswith("more:"))
async def callback_more(callback: CallbackQuery) -> None:
    _, category_slug, offset_str = callback.data.split(":")
    offset = int(offset_str)
    await render_category_products(callback, category_slug=category_slug, offset=offset)


async def render_category_products(callback: CallbackQuery, category_slug: str, offset: int) -> None:
    try:
        step = offset // PAGE_SIZE
        await callback.answer(f"{spinner_frame(step)} Ищу товары...", show_alert=False)
        category = catalog_service.resolve_category(category_slug)
        if not category:
            await callback.message.edit_text("Категория не найдена. Выберите другую.", reply_markup=None)
            return

        products = await ai_service.build_live_products(
            category_title=category.title,
            category_slug=category_slug,
            per_marketplace_limit=settings.per_marketplace_limit,
        )
        if not products:
            products = catalog_service.search_by_category(
                category_slug=category_slug,
                per_marketplace_limit=settings.per_marketplace_limit,
            )
        products = interleave_by_marketplace(products)[:MAX_TOTAL_RESULTS]

        if not products:
            await callback.message.edit_text(
                "По этой категории товары не найдены. Попробуйте выбрать другую категорию.",
            )
            return
        page = products[offset : offset + PAGE_SIZE]
        if not page:
            await callback.answer("Больше товаров нет.", show_alert=True)
            return
        next_offset = offset + PAGE_SIZE
        has_more = next_offset < len(products)

        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        await callback.message.edit_text(
            f"{spark_frame(step)} <b>Категория:</b> {category.title}\n"
            f"Показаны товары {offset + 1}-{offset + len(page)} из {len(products)}.",
            disable_web_page_preview=True,
        )

        ai_text = None
        if offset == 0:
            ai_text = await ai_service.build_recommendation(category_title=category.title, products=products)
        if ai_text:
            await callback.message.answer(f"{spark_frame(step + 1)} <b>AI-рекомендация:</b>\n{ai_text}")

        for product in page:
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
            reply_markup=result_actions_keyboard(
                category_slug=category_slug,
                next_offset=next_offset,
                has_more=has_more,
            ),
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
