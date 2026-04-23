"""
Что: форматирование данных для UI.
Зачем: централизованно формировать текст карточек товара.
"""

from html import escape

from models import Product

# Что: дефолтное изображение товара.
# Зачем: если в данных нет image_url, пользователь все равно видит картинку.
DEFAULT_PRODUCT_IMAGE_URL = "https://raw.githubusercontent.com/github/explore/main/topics/python/python.png"

# Что: иконки категорий и маркетплейсов.
# Зачем: сделать карточки товаров визуально приятнее.
CATEGORY_ICONS = {
    "smartphones": "📱",
    "laptops": "💻",
    "tvs": "📺",
    "fridges": "🧊",
    "headphones": "🎧",
    "vacuums": "🧹",
    "monitors": "🖥️",
    "washers": "🧺",
}

MARKETPLACE_ICONS = {
    "Ozon": "🟦",
    "Wildberries": "🟣",
    "DNS": "🟧",
}


def format_price(value: float | int) -> str:
    return f"{int(value):,}".replace(",", " ") + " ₽"


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
    """
    Возвращает URL изображения товара.
    Если image_url отсутствует, отдает дефолтную заглушку.
    """
    return product.image_url or DEFAULT_PRODUCT_IMAGE_URL


def sort_products_by_price(products: list[Product]) -> list[Product]:
    return sorted(products, key=lambda item: float(item.price))
