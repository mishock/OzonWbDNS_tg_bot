"""
Что: обработчики выдачи товаров.
Зачем: пагинация и форматирование результатов по категории.
"""

import logging
import base64

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
import aiohttp

from config import settings
from keyboards.main import result_actions_keyboard
from services.ai_service import ai_service
from services.catalog_service import catalog_service
from utils.formatter import format_product, product_image_url
from utils.ui_icons import spark_frame, spinner_frame

router = Router()
logger = logging.getLogger(__name__)
PAGE_SIZE = 10

# 1x1 PNG (белый пиксель) в base64.
# Используется как гарантированная fallback-картинка,
# если у товара нет image_url или внешний URL недоступен.
FALLBACK_IMAGE_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMBAAZ/q8kAAAAASUVORK5CYII="
)


async def render_category_products(callback: CallbackQuery, category_slug: str, offset: int) -> None:
    """
    Рисует страницу товаров выбранной категории.
    """
    try:
        step = offset // PAGE_SIZE
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

        page = products[offset : offset + PAGE_SIZE]
        if not page:
            # Для пустой страницы говорим в чат явно: это заметнее, чем скрытый callback.
            await callback.message.answer("ℹ️ Больше товаров нет в этой категории.")
            no_more_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🗂 Другую категорию", callback_data="open_categories")],
                    [InlineKeyboardButton(text="🆕 Новый поиск", callback_data="new_search")],
                ]
            )
            await callback.message.answer(
                "🗂 Выберите другую категорию или начните новый поиск:",
                reply_markup=no_more_keyboard,
            )
            return

        next_offset = offset + PAGE_SIZE
        keyboard = result_actions_keyboard(category_slug=category_slug, next_offset=next_offset)
        # Убираем старую клавиатуру у сообщения, по которому пришел callback,
        # чтобы внизу чата оставался только актуальный блок кнопок.
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        await callback.message.edit_text(
            f"{spark_frame(step)} <b>Категория:</b> {category.title}\n"
            f"Показаны товары {offset + 1}-{offset + len(page)}.",
            disable_web_page_preview=True,
        )

        # Опциональный AI-блок с рекомендацией.
        # Включается только если AI_ENABLED=true в .env.
        ai_text = await ai_service.build_recommendation(category_title=category.title, products=page)
        if ai_text:
            await callback.message.answer(f"{spark_frame(step + 1)} <b>AI-рекомендация:</b>\n{ai_text}")

        # Отправляем каждый товар отдельной карточкой с изображением.
        # Если фото не удалось отправить, падаем в текстовый fallback.
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
                    # Если Telegram не смог забрать изображение по URL,
                    # пробуем скачать картинку сами и отправить как файл.
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

            # Гарантированный fallback: отправляем встроенную PNG-картинку.
            try:
                await callback.message.answer_photo(
                    photo=BufferedInputFile(FALLBACK_IMAGE_BYTES, filename="product.png"),
                    caption=card_text,
                )
            except Exception:
                # Самый последний fallback: текст без картинки.
                await callback.message.answer(
                    card_text,
                    disable_web_page_preview=False,
                )

        # Отправляем кнопки отдельным последним сообщением,
        # чтобы они были в самом низу чата.
        await callback.message.answer(
            f"{spinner_frame(step + 1)} Выберите действие:",
            reply_markup=keyboard,
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


@router.callback_query(F.data.startswith("more:"))
async def callback_more(callback: CallbackQuery) -> None:
    """
    Обрабатывает кнопку "Показать еще" с offset в callback_data.
    """
    _, category_slug, offset_str = callback.data.split(":")
    offset = int(offset_str)
    await render_category_products(callback, category_slug=category_slug, offset=offset)
