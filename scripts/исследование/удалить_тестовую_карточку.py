"""Контролируемое удаление одной тестовой карточки; по умолчанию предпросмотр."""

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


def извлечь_товар(данные: Any) -> dict[str, Any]:
    if not isinstance(данные, dict) or not isinstance(данные.get("product"), dict):
        raise ValueError("В ответе GET отсутствует объект product")
    return данные["product"]


def проверить_исходный_товар(товар: dict[str, Any]) -> None:
    if (товар.get("id"), товар.get("sku"), товар.get("status")) != (
        ИДЕНТИФИКАТОР,
        АРТИКУЛ,
        "draft",
    ):
        raise ValueError("ID, SKU или статус не соответствуют закреплённой тестовой карточке")


def проверить_ответ(данные: Any) -> None:
    if not isinstance(данные, dict):
        raise ValueError("Ответ POST не является объектом")
    if данные.get("processed_ids") != [ИДЕНТИФИКАТОР] or данные.get("errors") != {}:
        raise ValueError("API не подтвердил успешную обработку единственного ID")


def main() -> int:
    парсер = argparse.ArgumentParser(description=__doc__)
    парсер.add_argument("--отправить", action="store_true", help="Разрешить один POST после подтверждения")
    аргументы = парсер.parse_args()
    консоль = Console()
    load_dotenv()
    токен_чтения = os.getenv("PROM_API_TOKEN_READ") or os.getenv("PROM_API_TOKEN")
    if not токен_чтения:
        консоль.print("[red]Отсутствует токен чтения[/red]")
        return 2

    def получить() -> dict[str, Any]:
        ответ = requests.get(
            f"{АДРЕС_API}/products/{ИДЕНТИФИКАТОР}",
            headers={"Authorization": f"Bearer {токен_чтения}"},
            timeout=20,
        )
        ответ.raise_for_status()
        return извлечь_товар(ответ.json())

    try:
        проверить_исходный_товар(получить())
    except (requests.RequestException, ValueError) as ошибка:
        консоль.print(f"[red]Предварительная GET-проверка не пройдена: {type(ошибка).__name__}[/red]")
        return 3

    таблица = Table(title="PROM / УДАЛЕНИЕ ТЕСТОВОЙ КАРТОЧКИ")
    таблица.add_column("Параметр")
    таблица.add_column("Значение")
    for название, значение in (
        ("ID", str(ИДЕНТИФИКАТОР)),
        ("SKU", АРТИКУЛ),
        ("Переход", "draft → deleted"),
        ("POST", "Только id и status"),
    ):
        таблица.add_row(название, значение)
    консоль.print(таблица)
    if not аргументы.отправить:
        консоль.print("[yellow]Предпросмотр: POST не отправлен[/yellow]")
        return 0

    токен_записи = os.getenv("PROM_API_TOKEN_WRITE")
    if not токен_записи:
        консоль.print("[red]Отсутствует PROM_API_TOKEN_WRITE[/red]")
        return 4
    фраза = f"УДАЛИТЬ {ИДЕНТИФИКАТОР}"
    if input(f"Для подтверждения введи точно «{фраза}»: ").strip() != фраза:
        консоль.print("[yellow]Отменено[/yellow]")
        return 5

    try:
        проверить_исходный_товар(получить())
    except (requests.RequestException, ValueError):
        консоль.print("[red]Повторная GET-проверка не пройдена. POST не отправлен[/red]")
        return 6

    try:
        ответ = requests.post(
            f"{АДРЕС_API}/products/edit",
            headers={"Authorization": f"Bearer {токен_записи}"},
            json=[{"id": ИДЕНТИФИКАТОР, "status": "deleted"}],
            timeout=20,
        )
        консоль.print(f"HTTP POST: {ответ.status_code}")
        ответ.raise_for_status()
        проверить_ответ(ответ.json())
    except (requests.RequestException, ValueError) as ошибка:
        консоль.print(f"[red]Результат не подтверждён: {type(ошибка).__name__}[/red]")
        консоль.print("[yellow]Не повторяй POST. Проверь карточку в кабинете.[/yellow]")
        return 7

    консоль.print("[green]API подтвердил обработку ID.[/green]")
    консоль.print("[yellow]Проверь карточку в «Видалені позиції» кабинета.[/yellow]")
    консоль.print("[yellow]Восстановление выполняй вручную через кабинет; API-восстановление не проверено.[/yellow]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
