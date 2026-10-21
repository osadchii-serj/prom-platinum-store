"""Безопасное получение настроек API из переменных окружения и .env."""

import os
from pathlib import Path

from dotenv import load_dotenv


def получить_токен(режим: str, файл_окружения: Path | None = None) -> str:
    """Возвращает токен указанного режима, не выводя его значение."""
    if режим not in {"чтение", "изменение"}:
        raise ValueError("Неизвестный режим доступа")
    if файл_окружения is not None:
        load_dotenv(dotenv_path=файл_окружения, override=False)
    else:
        load_dotenv(override=False)

    имя = "PROM_API_TOKEN_READ" if режим == "чтение" else "PROM_API_TOKEN_WRITE"
    токен = os.environ.get(имя, "").strip()
    if not токен and режим == "чтение":
        токен = os.environ.get("PROM_API_TOKEN", "").strip()
    if not токен:
        raise RuntimeError(f"Не задана переменная {имя}")
    return токен
