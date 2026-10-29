"""Только чтение карточек Prom.ua и расчёт одной цены."""

import argparse
from decimal import Decimal

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from prom.безопасность.переменные_окружения import ХранилищеПеременныхОкружения
from prom.подключения.настройки import НастройкиПодключения
from prom.подключения.подключение_prom import ПодключениеProm
from prom.цены.источник_prom import ИсточникТоваровProm
from prom.цены.подготовка_одной_цены import подготовить_одну_цену


def main():
    парсер = argparse.ArgumentParser()
    парсер.add_argument("--id", type=int, required=True)
    парсер.add_argument("--процент", required=True)
    аргументы = парсер.parse_args()
    try:
        процент = Decimal(аргументы.процент.replace(",", "."))
    except ArithmeticError:
        парсер.error("Неверный процент")
    if not процент.is_finite() or процент < 0 or аргументы.id <= 0:
        парсер.error("Неверный процент или ID")
    load_dotenv()
    подключение = ПодключениеProm(
        НастройкиПодключения("PROM_API_TOKEN"), ХранилищеПеременныхОкружения()
    )
    найдено = None
    for страница in ИсточникТоваровProm(подключение).страницы_товаров():
        найдено = next((товар for товар in страница if товар["id"] == аргументы.id), None)
        if найдено is not None:
            break
    if найдено is None:
        raise SystemExit("Карточка не найдена")
    изменение = подготовить_одну_цену(найдено, процент)
    Console().print(
        Panel(
            f"ID: {изменение.идентификатор}\nБыло: {изменение.старая_цена} {изменение.валюта}"
            f"\nПлан: {изменение.новая_цена} {изменение.валюта}\nREAD ONLY — запись отключена",
            title="PROM // SINGLE PRICE",
            border_style="cyan",
        )
    )


if __name__ == "__main__":
    main()
