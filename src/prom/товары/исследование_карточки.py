"""Безопасное исследование структуры ответа Prom.ua о товарах."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

АДРЕС_API = "https://my.prom.ua/api/v1/products/list"


def название_типа(значение: Any) -> str:
    """Определить тип JSON, отличая boolean от integer."""
    if значение is None:
        return "null"
    if isinstance(значение, bool):
        return "boolean"
    if isinstance(значение, str):
        return "string"
    if isinstance(значение, int):
        return "integer"
    if isinstance(значение, float):
        return "number"
    if isinstance(значение, list):
        return "array"
    if isinstance(значение, dict):
        return "object"
    raise TypeError("Ответ содержит значение вне формата JSON")


def собрать_реестр(данные: Any) -> list[dict[str, str]]:
    """Собрать пути и наблюдаемые типы полей из JSON-ответа."""
    типы: dict[str, set[str]] = defaultdict(set)

    def обойти(значение: Any, путь: str) -> None:
        if путь:
            типы[путь].add(название_типа(значение))
        if isinstance(значение, dict):
            for ключ, вложенное in значение.items():
                следующий = f"{путь}.{ключ}" if путь else ключ
                обойти(вложенное, следующий)
        elif isinstance(значение, list):
            for элемент in значение:
                обойти(элемент, f"{путь}[]")

    обойти(данные, "")
    return [
        {"путь": путь, "наблюдаемые_типы": ", ".join(sorted(значения))}
        for путь, значения in sorted(типы.items())
    ]


def получить_ответ(токен: str) -> Any:
    """Получить один товар через подтверждённый метод чтения API."""
    with httpx.Client(timeout=20.0, follow_redirects=False) as клиент:
        ответ = клиент.get(
            АДРЕС_API,
            params={"limit": 1},
            headers={"Authorization": f"Bearer {токен}", "Accept": "application/json"},
        )
        ответ.raise_for_status()
        return ответ.json()


def сохранить_исследование(данные: Any, каталог: Path) -> tuple[Path, Path]:
    """Сохранить исходный ответ и наблюдаемые типы, не перезаписывая файлы."""
    каталог.mkdir(parents=True, exist_ok=True, mode=0o700)
    метка = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    исходный = каталог / f"ответ_prom_{метка}.json"
    реестр = каталог / f"реестр_полей_{метка}.json"
    for путь, содержимое in (
        (исходный, данные),
        (реестр, собрать_реестр(данные)),
    ):
        with путь.open("x", encoding="utf-8") as файл:
            json.dump(содержимое, файл, ensure_ascii=False, indent=2)
            файл.write("\n")
        путь.chmod(0o600)
    return исходный, реестр


def main() -> None:
    """Выполнить только чтение и локальный анализ."""
    парсер = argparse.ArgumentParser(description="Исследование карточки Prom.ua (только чтение)")
    парсер.add_argument("--каталог", type=Path, default=Path("data/исследование_товаров"))
    аргументы = парсер.parse_args()
    load_dotenv()
    токен = os.getenv("PROM_API_TOKEN")
    if not токен:
        raise SystemExit("Переменная PROM_API_TOKEN не найдена")

    консоль = Console()
    try:
        данные = получить_ответ(токен)
    except (httpx.HTTPError, ValueError) as ошибка:
        # Не выводим детали исключения: HTTP-адрес может содержать чувствительные данные.
        raise SystemExit(f"Не удалось получить ответ API: {type(ошибка).__name__}") from None

    исходный, реестр = сохранить_исследование(данные, аргументы.каталог)
    таблица = Table(title="PROM // ИССЛЕДОВАНИЕ ТОВАРА")
    таблица.add_column("Показатель", style="cyan")
    таблица.add_column("Значение")
    таблица.add_row("Режим", "Только чтение")
    таблица.add_row("Метод", "GET /api/v1/products/list?limit=1")
    таблица.add_row("Обнаружено путей", str(len(собрать_реестр(данные))))
    таблица.add_row("Исходный JSON", str(исходный))
    таблица.add_row("Реестр", str(реестр))
    консоль.print(таблица)
    консоль.print(
        "[yellow]Внимание:[/] наблюдаемые типы не являются подтверждённым контрактом записи."
    )


if __name__ == "__main__":
    main()
