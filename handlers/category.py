"""
Что: обработчики выбора категории.
Зачем: показать меню категорий и запустить первый поиск.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.categories import categories_keyboard
from services.catalog_service import catalog_service
from handlers.search import render_category_products

router = Router()


@router.callback_query(F.data == "open_categories")
async def callback_open_categories(callback: CallbackQuery) -> None:
    categories = catalog_service.get_categories()
    await callback.message.edit_text(
        "Выберите категорию товара:",
        reply_markup=categories_keyboard(categories),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def callback_choose_category(callback: CallbackQuery) -> None:
    category_slug = callback.data.split(":", maxsplit=1)[1]
    await render_category_products(callback, category_slug=category_slug, offset=0)
