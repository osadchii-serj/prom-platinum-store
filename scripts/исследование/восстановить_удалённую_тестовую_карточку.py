"""Одна контролируемая попытка восстановления закреплённой удалённой карточки."""

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
ЦЕЛЕВОЙ_СТАТУС = "not_on_display"


def проверить_ответ(данные: Any) -> None:
    """Проверить результат для единственного закреплённого товара."""
    if not isinstance(данные, dict):
        raise TypeError("Ответ POST не является объектом")
    if данные.get("processed_ids") != [ИДЕНТИФИКАТОР] or данные.get("errors"):
        raise ValueError("API не подтвердил обработку единственного ID без ошибок")


def проверить_товар(данные: Any) -> None:
    """Сверить восстановленную карточку по трём независимым признакам."""
    if not isinstance(данные, dict) or not isinstance(данные.get("product"), dict):
        raise TypeError("GET не содержит объект product")
    товар = данные["product"]
    if (товар.get("id"), товар.get("sku"), товар.get("status")) != (
        ИДЕНТИФИКАТОР, АРТИКУЛ, ЦЕЛЕВОЙ_СТАТУС
    ):
        raise ValueError("GET не подтвердил ID, SKU и целевой статус")


def main() -> int:
    парсер = argparse.ArgumentParser(description=__doc__)
    парсер.add_argument("--отправить", action="store_true", help="Разрешить один POST")
    аргументы = парсер.parse_args()
    консоль = Console()
    таблица = Table(title="PROM / ВОССТАНОВЛЕНИЕ УДАЛЁННОЙ КАРТОЧКИ")
    таблица.add_column("Параметр", style="cyan")
    таблица.add_column("Значение")
    for ключ, значение in (
        ("ID", str(ИДЕНТИФИКАТОР)),
        ("SKU (ранее подтверждён)", АРТИКУЛ),
        ("Состояние", "deleted — подтверждено кабинетом; GET возвращал 404"),
        ("Цель", ЦЕЛЕВОЙ_СТАТУС),
        ("POST", "Только id и status; один запрос без повторов"),
    ):
        таблица.add_row(ключ, значение)
    консоль.print(таблица)
    if not аргументы.отправить:
        консоль.print("[yellow]Предпросмотр: запросы к API не выполнялись.[/yellow]")
        return 0

    load_dotenv()
    токен_записи = os.getenv("PROM_API_TOKEN_WRITE")
    токен_чтения = os.getenv("PROM_API_TOKEN_READ") or os.getenv("PROM_API_TOKEN")
    if not токен_записи or not токен_чтения:
        консоль.print("[red]Нужны PROM_API_TOKEN_WRITE и токен чтения в .env.[/red]")
        return 2
    фраза = f"ВОССТАНОВИТЬ {ИДЕНТИФИКАТОР}"
    консоль.print(f"Введите точно: {фраза}")
    if input("Подтверждение: ").strip() != фраза:
        консоль.print("[yellow]Отменено.[/yellow]")
        return 3

    # GET 404 подтверждает недоступность в обычном каталоге, но не доказывает
    # идентичность удалённого товара. Она установлена прежними GET и кабинетом.
    try:
        предварительный = requests.get(
            f"{АДРЕС_API}/products/{ИДЕНТИФИКАТОР}",
            headers={"Authorization": f"Bearer {токен_чтения}"}, timeout=20,
        )
        if предварительный.status_code != 404:
            консоль.print("[red]GET уже не 404: состояние изменилось. POST отменён.[/red]")
            return 4
    except requests.RequestException:
        консоль.print("[red]Не удалось проверить GET. POST отменён.[/red]")
        return 4

    консоль.print("[yellow]Отправляем один POST. Не повторяйте при неопределённом результате.[/yellow]")
    try:
        ответ = requests.post(
            f"{АДРЕС_API}/products/edit",
            headers={"Authorization": f"Bearer {токен_записи}", "Accept": "application/json"},
            json=[{"id": ИДЕНТИФИКАТОР, "status": ЦЕЛЕВОЙ_СТАТУС}],
            timeout=20,
        )
        консоль.print(f"HTTP POST: {ответ.status_code}")
        ответ.raise_for_status()
        проверить_ответ(ответ.json())
        консоль.print("[green]API подтвердил обработку ID.[/green]")
    except (requests.RequestException, ValueError) as ошибка:
        консоль.print(f"[red]Результат POST не подтверждён: {type(ошибка).__name__}.[/red]")
        консоль.print("[yellow]Не повторяйте POST. Проверьте карточку в кабинете.[/yellow]")
        return 5

    try:
        итог = requests.get(
            f"{АДРЕС_API}/products/{ИДЕНТИФИКАТОР}",
            headers={"Authorization": f"Bearer {токен_чтения}"}, timeout=20,
        )
        консоль.print(f"HTTP GET: {итог.status_code}")
        итог.raise_for_status()
        проверить_товар(итог.json())
    except (requests.RequestException, ValueError) as ошибка:
        консоль.print(f"[yellow]GET-сверка не завершена: {type(ошибка).__name__}.[/yellow]")
        консоль.print("Проверьте кабинет и выполните отдельный GET; POST не повторяйте.")
        return 6
    консоль.print("[green]Восстановление подтверждено: ID, SKU, status совпадают.[/green]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
