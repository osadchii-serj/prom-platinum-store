"""Эксперимент с черновиком и снятием с публикации одной карточки Prom.ua."""

from __future__ import annotations

import argparse
import os
from typing import Any

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

АДРЕС_API = "https://my.prom.ua/api/v1"
ИДЕНТИФИКАТОР = 3243922294
АРТИКУЛ = "PROM-TEST-20261022-001"
ПЕРЕХОДЫ = {("draft", "not_on_display"), ("not_on_display", "draft")}


def извлечь_товар(данные: Any) -> dict[str, Any]:
    """Возвращает объект товара из документированной оболочки ответа GET."""
    if not isinstance(данные, dict) or not isinstance(данные.get("product"), dict):
        raise ValueError("Неожиданная структура GET: отсутствует product")
    return данные["product"]


def проверить_переход(товар: dict[str, Any], цель: str) -> str:
    """Проверяет идентичность и допустимый переход до изменения."""
    if товар.get("id") != ИДЕНТИФИКАТОР or товар.get("sku") != АРТИКУЛ:
        raise ValueError("Карточка не совпадает с закреплённым ID/SKU")
    текущий = товар.get("status")
    if not isinstance(текущий, str) or (текущий, цель) not in ПЕРЕХОДЫ:
        raise ValueError(f"Недопустимый переход: {текущий!r} → {цель!r}")
    return текущий


def проверить_ответ_редактирования(данные: Any) -> None:
    """HTTP 200 недостаточно: проверяем обработанные ID и ошибки."""
    if not isinstance(данные, dict):
        raise ValueError("Ответ редактирования не является объектом")
    if данные.get("errors") or данные.get("processed_ids") != [ИДЕНТИФИКАТОР]:
        raise ValueError("Ответ не подтвердил обработку только тестового ID")


def main() -> int:
    парсер = argparse.ArgumentParser(description=__doc__)
    парсер.add_argument("--статус", required=True, choices=("draft", "not_on_display"))
    парсер.add_argument("--отправить", action="store_true", help="Разрешить один POST после подтверждения")
    аргументы = парсер.parse_args()
    консоль = Console()
    load_dotenv()
    токен_чтения = os.getenv("PROM_API_TOKEN_READ") or os.getenv("PROM_API_TOKEN")
    if not токен_чтения:
        консоль.print("[red]Нет токена чтения в .env[/red]")
        return 2

    def получить() -> dict[str, Any]:
        ответ = requests.get(
            f"{АДРЕС_API}/products/{ИДЕНТИФИКАТОР}",
            headers={"Authorization": f"Bearer {токен_чтения}", "Accept": "application/json"},
            timeout=20,
        )
        ответ.raise_for_status()
        return извлечь_товар(ответ.json())

    консоль.print(Panel("Только одна закреплённая тестовая карточка. По умолчанию — предпросмотр.", title="PROM / СТАТУС КАРТОЧКИ", border_style="cyan"))
    try:
        товар = получить()
        текущий = проверить_переход(товар, аргументы.статус)
    except (requests.RequestException, ValueError) as ошибка:
        консоль.print(f"[red]Предварительная проверка не пройдена: {type(ошибка).__name__}: {ошибка if isinstance(ошибка, ValueError) else 'сбой API'}[/red]")
        return 3
    таблица = Table(title="Предпросмотр изменения")
    таблица.add_column("Параметр", style="cyan")
    таблица.add_column("Значение")
    for ключ, значение in (("ID", str(ИДЕНТИФИКАТОР)), ("Артикул", АРТИКУЛ), ("Текущий статус", текущий), ("Целевой статус", аргументы.статус), ("Поля POST", "id, status")):
        таблица.add_row(ключ, значение)
    консоль.print(таблица)
    if not аргументы.отправить:
        консоль.print("[yellow]ПРЕДПРОСМОТР: POST не отправлен. Для изменения добавь --отправить.[/yellow]")
        return 0
    токен_записи = os.getenv("PROM_API_TOKEN_WRITE")
    if not токен_записи:
        консоль.print("[red]Нет PROM_API_TOKEN_WRITE в .env[/red]")
        return 4
    фраза = f"ИЗМЕНИТЬ {ИДЕНТИФИКАТОР} НА {аргументы.статус}"
    консоль.print(f"[yellow]Для подтверждения введи точно: {фраза}[/yellow]")
    if input("Подтверждение: ").strip() != фраза:
        консоль.print("[yellow]Отменено[/yellow]")
        return 5
    try:
        # Повторная GET-проверка защищает от устаревшего предпросмотра.
        повторный = получить()
        проверить_переход(повторный, аргументы.статус)
        if повторный.get("status") != текущий:
            raise ValueError("Статус изменился после предпросмотра")
        ответ = requests.post(
            f"{АДРЕС_API}/products/edit",
            headers={"Authorization": f"Bearer {токен_записи}", "Accept": "application/json"},
            json=[{"id": ИДЕНТИФИКАТОР, "status": аргументы.статус}],
            timeout=20,
        )
        консоль.print(f"HTTP POST: {ответ.status_code}")
        ответ.raise_for_status()
        проверить_ответ_редактирования(ответ.json())
        итог = получить()
        if итог.get("id") != ИДЕНТИФИКАТОР or итог.get("sku") != АРТИКУЛ or итог.get("status") != аргументы.статус:
            raise ValueError("GET-сверка не подтвердила целевой статус")
        for поле in ("price", "presence", "quantity_in_stock", "in_stock"):
            if итог.get(поле) != повторный.get(поле):
                raise ValueError(f"Обнаружено неожиданное изменение поля {поле}")
    except (requests.RequestException, ValueError) as ошибка:
        консоль.print(f"[red]Не подтверждено: {type(ошибка).__name__}: {ошибка if isinstance(ошибка, ValueError) else 'сбой API'}[/red]")
        консоль.print("[yellow]Не повторяй POST автоматически. Выполни GET-сверку и установи фактический статус.[/yellow]")
        return 6
    консоль.print(f"[green]Подтверждено GET: {текущий} → {аргументы.статус}[/green]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
