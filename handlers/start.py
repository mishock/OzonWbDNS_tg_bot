"""
Что: стартовые обработчики.
Зачем: вход в бота через /start и reset сценария.
"""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from keyboards.main import start_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "Привет! Я помогу подобрать товары по категориям.\n\n"
        "Что умею в MVP:\n"
        "- выбор категории;\n"
        "- показ товаров из Ozon, Wildberries и DNS;\n"
        "- прямые ссылки на каждый товар."
    )
    await message.answer(text, reply_markup=start_keyboard())


@router.callback_query(F.data == "new_search")
async def callback_new_search(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Новый поиск запущен. Выберите категорию.",
        reply_markup=start_keyboard(),
    )
    await callback.answer()
