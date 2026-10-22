"""Одна подтверждённая отправка тестового XLSX через официальный API."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import requests

from prom.api.настройки import получить_токен

АДРЕС_ИМПОРТА = "https://my.prom.ua/api/v1/products/import_file"
НАСТРОЙКИ = {"force_update": False, "only_update": False, "mark_missing_product_as": "none"}


@dataclass(frozen=True)
class ОтветИмпорта:
    """Ответ сервера без токена и персональных данных."""

    код: int
    тело: str


def отпечаток(путь: Path) -> str:
    """SHA-256 для фиксации именно отправляемого файла."""
    return hashlib.sha256(путь.read_bytes()).hexdigest()


def отправить_один_файл(путь: Path) -> ОтветИмпорта:
    """Выполнить один POST без автоматических повторов."""
    if not путь.is_file() or путь.suffix.lower() != ".xlsx":
        raise ValueError("Требуется существующий XLSX-файл")
    токен = получить_токен("изменение")
    with requests.Session() as соединение:
        соединение.headers.update({"Authorization": f"Bearer {токен}"})
        with путь.open("rb") as файл:
            ответ = соединение.post(
                АДРЕС_ИМПОРТА,
                files={"file": (путь.name, файл, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"data": json.dumps(НАСТРОЙКИ, ensure_ascii=False)},
                timeout=(10, 90),
            )
    # Не сохраняем ответ целиком: сервер может вернуть неожиданные данные.
    return ОтветИмпорта(ответ.status_code, ответ.text[:2000])
