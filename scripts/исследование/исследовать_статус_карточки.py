"""Безопасное исследование полей одной карточки Prom.ua (только GET)."""

from __future__ import annotations

import argparse
import os
import re
from collections.abc import Mapping
from typing import Any

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

АДРЕС_API = "https://my.prom.ua/api/v1"
КЛЮЧИ_СТАТУСА = (
    "status", "presence", "available", "visibility", "visible", "publish",
    "display", "catalog", "draft", "quantity", "stock", "moderation",
    "state", "selling", "site", "product_id", "external_id", "sku", "id",
)
ЗАПРЕЩЁННЫЕ_КЛЮЧИ = ("token", "secret", "password", "authorization", "email", "phone", "address", "customer")


def безопасные_поля(данные: Any, префикс: str = "", глубина: int = 0) -> list[tuple[str, str]]:
    """Показывает только небольшие скалярные поля, относящиеся к статусам."""
    if not isinstance(данные, Mapping) or глубина > 3:
        return []
    результат: list[tuple[str, str]] = []
    for ключ, значение in данные.items():
        имя = str(ключ)
        путь = f"{префикс}.{имя}" if префикс else имя
        нижний = имя.lower()
        if any(слово in нижний for слово in ЗАПРЕЩЁННЫЕ_КЛЮЧИ):
            continue
        if isinstance(значение, Mapping):
            результат.extend(безопасные_поля(значение, путь, глубина + 1))
        elif not isinstance(значение, (dict, list, tuple)) and any(
            слово in нижний for слово in КЛЮЧИ_СТАТУСА
        ):
            строка = str(значение)
            if len(строка) <= 100 and not re.search(r"https?://|@|\+?\d{10,}", строка):
                результат.append((путь, строка))
    return результат[:50]


def main() -> int:
    парсер = argparse.ArgumentParser(description=__doc__)
    парсер.add_argument("--id", type=int, default=3243922294, help="ID тестовой карточки")
    аргументы = парсер.parse_args()
    консоль = Console()
    load_dotenv()
    токен = os.getenv("PROM_API_TOKEN_READ") or os.getenv("PROM_API_TOKEN")
    if not токен:
        консоль.print("[red]Нет PROM_API_TOKEN_READ (или PROM_API_TOKEN) в .env[/red]")
        return 2
    адрес = f"{АДРЕС_API}/products/{аргументы.id}"
    консоль.print(Panel(f"GET /products/{аргументы.id}\nТолько чтение · без изменения магазина", title="PROM / ИССЛЕДОВАНИЕ СТАТУСА", border_style="cyan"))
    try:
        ответ = requests.get(
            адрес,
            headers={"Authorization": f"Bearer {токен}", "Accept": "application/json"},
            timeout=20,
        )
    except requests.RequestException as ошибка:
        консоль.print(f"[red]Сбой соединения: {type(ошибка).__name__}[/red]")
        return 3
    консоль.print(f"HTTP: {ответ.status_code}")
    if not ответ.ok:
        консоль.print("[red]Запрос отклонён. Тело ответа скрыто во избежание утечки данных.[/red]")
        return 4
    try:
        данные = ответ.json()
    except ValueError:
        консоль.print("[red]Ответ не является JSON.[/red]")
        return 5
    поля = безопасные_поля(данные)
    таблица = Table(title="Поля, потенциально относящиеся к состоянию карточки")
    таблица.add_column("Путь JSON", style="cyan")
    таблица.add_column("Значение", style="green")
    for ключ, значение in поля:
        таблица.add_row(ключ, значение)
    консоль.print(таблица)
    if not поля:
        консоль.print("[yellow]Подходящих полей не найдено; требуется анализ структуры ответа.[/yellow]")
    консоль.print("[yellow]Названия полей не доказывают возможность их изменения через API.[/yellow]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
