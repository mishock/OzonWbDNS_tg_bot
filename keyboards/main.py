"""
Что: базовые клавиатуры интерфейса.
Зачем: переиспользуемые кнопки главного сценария.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧭 Выбрать категорию", callback_data="open_categories")],
        ]
    )


def result_actions_keyboard(category_slug: str, next_offset: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Показать еще", callback_data=f"more:{category_slug}:{next_offset}")],
            [InlineKeyboardButton(text="🗂 Другую категорию", callback_data="open_categories")],
            [InlineKeyboardButton(text="🆕 Новый поиск", callback_data="new_search")],
        ]
    )
