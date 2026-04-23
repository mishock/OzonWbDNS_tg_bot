"""
Что: чтение JSON-данных.
Зачем: простая утилита для работы с mock-файлами MVP.
"""

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"Ожидался список в JSON: {path}")
    return data
