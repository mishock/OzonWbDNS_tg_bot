"""
Что: точка входа aiogram 3 бота.
Зачем: инициализирует бота, роутеры и запускает polling.
Важно: перед запуском должен быть задан BOT_TOKEN или TELEGRAM_BOT_TOKEN.
"""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app import router, setup_logging
from config import settings


async def main() -> None:
    """Запускает приложение бота."""
    setup_logging()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
