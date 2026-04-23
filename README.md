# OzonWbDNS_tg_bot

Telegram-бот на `aiogram 3` для подбора товаров по категориям и выдачи прямых ссылок на товары из Ozon, Wildberries и DNS.

## Для ученика: с чего начать

Если вы только учитесь программированию, идите в таком порядке:

1. `config.py` — как читаются переменные окружения (`BOT_TOKEN`, `AI_ENABLED` и т.д.).
2. `data/categories.json` и `data/mock_products.json` — какие данные использует бот.
3. `app.py`:
   - блок "Модели данных" (`Category`, `Product`);
   - блок "Сервисы" (`MarketplaceService`, `CatalogService`, `AIService`);
   - блок "Клавиатуры";
   - блок "Обработчики Telegram-событий" (`/start`, выбор категории).
4. `main.py` — как запускается polling и подключается роутер.

Минимальная практика для закрепления:
- добавить новую категорию в `data/categories.json`;
- добавить товары этой категории в `data/mock_products.json`;
- перезапустить `docker compose restart app` и проверить в Telegram.

## Структура проекта

```text
.
├── app.py
├── main.py
├── config.py
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
- Выбор категории и выдача списка товаров единым блоком.
- Для каждого товара: название, цена, категория, маркетплейс, ссылка.
- Кнопки: "Другую категорию", "Новый поиск".
- Базовая обработка ошибок и логирование.

## Источники данных

Сейчас используется mock-источник `data/mock_products.json`.
При `AI_ENABLED=false` бот полностью работает на локальном JSON-каталоге:
- `data/categories.json` (категории),
- `data/mock_products.json` (товары).

Где менять на реальный API/парсинг:
- `app.py` (класс `MarketplaceService` и инициализация `CatalogService`)

Основная логика бота и формат ответа при этом останутся без изменений.

## Как работать с проектом

1. Заполните переменные в `.env` (см. разделы ниже).
2. Запустите проект в Docker:
   - `docker compose up -d --build`
3. Проверьте, что контейнер жив:
   - `docker compose ps`
4. Проверьте логи бота:
   - `docker compose logs -f app`
5. Остановить проект:
   - `docker compose down`

Типовой цикл при изменениях:
- правите `app.py` или файлы в `data/`,
- перезапускаете сервис `docker compose restart app`,
- проверяете поведение в Telegram.

## Как не запутаться в `app.py`

В файле логика идет сверху вниз:
- сначала константы и утилиты;
- затем модели данных;
- затем сервисы (работа с товарами и AI);
- затем Telegram-клавиатуры;
- затем обработчики команд и callback.

Совет ученику: сначала читайте сигнатуры функций и названия классов, потом уже детали внутри.

## Что за JSON-файлы в `data/`

### `data/categories.json`

Справочник категорий для меню выбора.  
Каждый объект содержит:
- `slug` — технический идентификатор категории (используется в коде и `mock_products.json`);
- `title` — название категории, которое видит пользователь в боте.

Важно:
- `slug` должен быть уникальным;
- если добавляете новую категорию, используйте тот же `slug` в товарах в `mock_products.json`.

### `data/mock_products.json`

Тестовая база товаров для MVP (вместо реального API).

Поля товара:
- `title` — название товара;
- `price` — цена (число);
- `category` — `slug` категории из `categories.json`;
- `marketplace` — одно из: `Ozon`, `Wildberries`, `DNS`;
- `url` — исходная ссылка (в текущей логике заменяется на поисковую ссылку по названию);
- `image_url` — ссылка на картинку или `null`;
- `rating` — рейтинг (опционально);
- `description` — описание (опционально).

## Перед первым запуском

1. Откройте и отредактируйте `/.env.example` (в корне проекта) под свои значения:
   - `BOT_TOKEN` / `TELEGRAM_BOT_TOKEN`
   - `DEEPSEEK_API_KEY` (если `AI_ENABLED=true`)
2. Сохраните рабочий файл окружения:
   - `cp .env.example .env`

## Локальный запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# убедитесь, что в .env заполнены нужные значения
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

- Лимит в коде: до 5 товаров на маркетплейс (`per_marketplace_limit=5` в `config.py`).
- В текущем `data/mock_products.json` по каждой категории фактически по 1 товару на площадку (итого 3).
- После объединения список сортируется по цене и показывается одной выдачей.
