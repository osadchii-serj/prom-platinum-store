"""Один контролируемый переход тестовой карточки not_on_display → deleted."""

from __future__ import annotations

import argparse
import os
from typing import Any

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

АДРЕС_API = "https://my.prom.ua/api/v1"
ИДЕНТИФИКАТОР = 3243922294
АРТИКУЛ = "PROM-TEST-20261022-001"
ИСТОЧНИК = "not_on_display"
ЦЕЛЬ = "deleted"


def проверить_товар(данные: Any) -> None:
    """Требует точного совпадения ID, SKU и исходного статуса."""
    if not isinstance(данные, dict) or not isinstance(данные.get("product"), dict):
        raise ValueError("GET не содержит product")
    товар = данные["product"]
    if (товар.get("id"), товар.get("sku"), товар.get("status")) != (
        ИДЕНТИФИКАТОР, АРТИКУЛ, ИСТОЧНИК
    ):
        raise ValueError("ID, SKU или исходный статус не совпадают")


def проверить_ответ(данные: Any) -> None:
    """Успех только при обработке единственного закреплённого ID без ошибок."""
    if not isinstance(данные, dict) or данные.get("processed_ids") != [ИДЕНТИФИКАТОР]:
        raise ValueError("API не подтвердил обработку закреплённого ID")
    if данные.get("errors") != {}:
        raise ValueError("Ответ API содержит ошибки или не содержит errors")


def main() -> int:
    парсер = argparse.ArgumentParser(description=__doc__)
    парсер.add_argument("--отправить", action="store_true")
    аргументы = парсер.parse_args()
    консоль = Console()
    load_dotenv()
    токен_чтения = os.getenv("PROM_API_TOKEN_READ") or os.getenv("PROM_API_TOKEN")
    if not токен_чтения:
        консоль.print("[red]Нет токена чтения[/red]")
        return 2

    def проверить_get() -> None:
        ответ = requests.get(
            f"{АДРЕС_API}/products/{ИДЕНТИФИКАТОР}",
            headers={"Authorization": f"Bearer {токен_чтения}"},
            timeout=20,
        )
        ответ.raise_for_status()
        проверить_товар(ответ.json())

    try:
        проверить_get()
    except (requests.RequestException, ValueError) as ошибка:
        консоль.print(f"[red]GET-проверка не пройдена: {type(ошибка).__name__}[/red]")
        return 3

    таблица = Table(title="PROM / ПОВТОРНОЕ УДАЛЕНИЕ")
    таблица.add_column("Параметр")
    таблица.add_column("Значение")
    for ключ, значение in (
        ("ID", str(ИДЕНТИФИКАТОР)),
        ("SKU", АРТИКУЛ),
        ("Переход", f"{ИСТОЧНИК} → {ЦЕЛЬ}"),
        ("POST", "Только id и status"),
    ):
        таблица.add_row(ключ, значение)
    консоль.print(таблица)
    if not аргументы.отправить:
        консоль.print("[yellow]Предпросмотр. POST не отправлен.[/yellow]")
        return 0

    токен_записи = os.getenv("PROM_API_TOKEN_WRITE")
    if not токен_записи:
        консоль.print("[red]Нет PROM_API_TOKEN_WRITE[/red]")
        return 4
    фраза = f"УДАЛИТЬ {ИДЕНТИФИКАТОР} ПОВТОРНО"
    if input(f"Для подтверждения введи точно «{фраза}»: ").strip() != фраза:
        консоль.print("[yellow]Отменено[/yellow]")
        return 5
    try:
        проверить_get()
    except (requests.RequestException, ValueError):
        консоль.print("[red]Повторный GET не пройден; POST не отправлен[/red]")
        return 6

    try:
        ответ = requests.post(
            f"{АДРЕС_API}/products/edit",
            headers={"Authorization": f"Bearer {токен_записи}"},
            json=[{"id": ИДЕНТИФИКАТОР, "status": ЦЕЛЬ}],
            timeout=20,
        )
        консоль.print(f"HTTP POST: {ответ.status_code}")
        ответ.raise_for_status()
        проверить_ответ(ответ.json())
    except (requests.RequestException, ValueError) as ошибка:
        консоль.print(f"[red]Результат не подтверждён: {type(ошибка).__name__}[/red]")
        консоль.print("[yellow]Не повторяй POST. Проверь кабинет и GET.[/yellow]")
        return 7

    консоль.print("[green]API подтвердил обработку ID.[/green]")
    консоль.print("[yellow]Проверь «Видалені позиції». Не восстанавливай пока.[/yellow]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
