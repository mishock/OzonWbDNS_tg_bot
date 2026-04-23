"""
Что: централизованная конфигурация проекта.
Зачем: читаем переменные окружения в одном месте.
Важно: токен можно передать через BOT_TOKEN или TELEGRAM_BOT_TOKEN.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    base_dir: Path
    categories_path: Path
    products_path: Path
    per_marketplace_limit: int = 5
    ai_enabled: bool = False
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"


def _get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN", "").strip() or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Не задан BOT_TOKEN или TELEGRAM_BOT_TOKEN в .env")
    return token


def _get_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "on"}


BASE_DIR = Path(__file__).resolve().parent
settings = Settings(
    bot_token=_get_bot_token(),
    base_dir=BASE_DIR,
    categories_path=BASE_DIR / "data" / "categories.json",
    products_path=BASE_DIR / "data" / "mock_products.json",
    ai_enabled=_get_bool_env("AI_ENABLED", default=False),
    deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
    deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
    deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat",
)
