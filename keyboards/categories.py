"""
Что: клавиатура категорий.
Зачем: отрисовать список категорий динамически из данных.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models import Category

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
