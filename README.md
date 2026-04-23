# OzonWbDNS_tg_bot

Telegram-бот на `aiogram 3` для подбора товаров по категориям и выдачи прямых ссылок на товары из Ozon, Wildberries и DNS.

## Структура проекта

```text
.
├── main.py
├── config.py
├── handlers/
│   ├── start.py
│   ├── category.py
│   └── search.py
├── services/
│   ├── ozon_service.py
│   ├── wildberries_service.py
│   ├── dns_service.py
│   └── catalog_service.py
├── models/
│   ├── product.py
│   └── category.py
├── keyboards/
│   ├── main.py
│   └── categories.py
├── utils/
│   ├── logger.py
│   ├── formatter.py
│   └── json_storage.py
├── data/
│   ├── categories.json
│   └── mock_products.json
├── .env.example
├── requirements.txt
└── README.md
```

## Что делает MVP

- `/start` с приветствием и кнопкой "Выбрать категорию".
- Меню категорий через `InlineKeyboardMarkup`.
- Выбор категории и выдача списка товаров.
- Для каждого товара: название, цена, категория, маркетплейс, ссылка.
- Кнопки: "Показать еще", "Другую категорию", "Новый поиск".
- Базовая обработка ошибок и логирование.

## Источники данных

Сейчас используется mock-источник `data/mock_products.json`.

Где менять на реальный API/парсинг:
- `services/ozon_service.py`
- `services/wildberries_service.py`
- `services/dns_service.py`

Основная логика бота и формат ответа при этом останутся без изменений.

## Локальный запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# заполните BOT_TOKEN
python main.py
```

## Запуск в Docker

```bash
docker compose up -d --build
docker compose logs -f
docker compose down
```

## Переменные окружения

- `BOT_TOKEN` - основной токен Telegram-бота.
- `TELEGRAM_BOT_TOKEN` - fallback-токен для обратной совместимости.
- `APP_ENV` - окружение запуска (`dev`/`prod`).
- `AI_ENABLED` - включить/выключить AI-рекомендации (`true`/`false`).
- `DEEPSEEK_API_KEY` - ключ DeepSeek API.
- `DEEPSEEK_BASE_URL` - базовый URL DeepSeek API.
- `DEEPSEEK_MODEL` - модель DeepSeek.

## Как отключить AI

- Установите в `.env`: `AI_ENABLED=false`
- Перезапустите контейнер: `docker compose up -d --build`

При `AI_ENABLED=false` бот продолжает работать как обычный MVP без AI.

## Ограничение выдачи

- Сейчас выдача идет по 5 товаров на маркетплейс.
- После объединения список сортируется по цене.
- Пользователь видит страницы по 10 товаров через кнопку "Показать еще".
