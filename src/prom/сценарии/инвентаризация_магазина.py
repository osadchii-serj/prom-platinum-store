"""Агрегированная инвентаризация каталога через GET."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

import requests
from rich.console import Console
from rich.table import Table

from prom.api.настройки import получить_токен
from prom.сценарии.чтение_каталога import АДРЕС_КАТАЛОГА, ПРЕДЕЛ_СТРАНИЦ, РАЗМЕР_СТРАНИЦЫ


@dataclass(frozen=True)
class Отчёт:
    всего: int
    разновидностей: int
    основных: int
    без_признака: int
    статусы: tuple[tuple[str, int], ...]
    страниц: tuple[int, int]
    стабилен: bool

def _прочитать(сессия: requests.Session) -> tuple[dict[int, tuple[bool | None, str]], int]:
    последний: int | None = None
    карточки: dict[int, tuple[bool | None, str]] = {}
    for номер in range(1, ПРЕДЕЛ_СТРАНИЦ + 1):
        параметры = {"limit": РАЗМЕР_СТРАНИЦЫ}
        if последний is not None:
            параметры["last_id"] = последний
        ответ = сессия.get(АДРЕС_КАТАЛОГА, params=параметры, timeout=30)
        ответ.raise_for_status()
        данные: Any = ответ.json()
        if not isinstance(данные, dict) or not isinstance(данные.get("products"), list):
            raise TypeError("Некорректная структура ответа")
        товары = данные["products"]
        if len(товары) > РАЗМЕР_СТРАНИЦЫ:
            raise ValueError("Размер страницы превышен")
        идентификаторы: list[int] = []
        for товар in товары:
            if not isinstance(товар, dict) or type(товар.get("id")) is not int:
                raise TypeError("Некорректная карточка или ID")
            ид = товар["id"]
            if ид <= 0 or ид in карточки or (последний is not None and ид >= последний):
                raise ValueError("Повтор ID или нарушение пагинации")
            признак = товар.get("is_variation")
            статус = товар.get("status")
            if признак is not None and not isinstance(признак, bool):
                raise TypeError("Некорректный is_variation")
            if статус is not None and not isinstance(статус, str):
                raise TypeError("Некорректный status")
            карточки[ид] = (признак, статус if статус is not None else "<не передан>")
            идентификаторы.append(ид)
        if len(товары) < РАЗМЕР_СТРАНИЦЫ:
            return карточки, номер
        последний = min(идентификаторы)
    raise RuntimeError("Предел страниц: полнота не подтверждена")

def инвентаризировать(*, сессия: requests.Session | None = None) -> Отчёт:
    своя = сессия is None
    соединение = сессия if сессия is not None else requests.Session()
    try:
        if своя:
            соединение.headers.update({"Authorization": f"Bearer {получить_токен('чтение')}"})
        первый, страниц_1 = _прочитать(соединение)
        второй, страниц_2 = _прочитать(соединение)
    finally:
        if своя:
            соединение.close()
    значения = list(второй.values())
    статусы = Counter(статус for _, статус in значения)
    return Отчёт(
        всего=len(значения),
        разновидностей=sum(признак is True for признак, _ in значения),
        основных=sum(признак is False for признак, _ in значения),
        без_признака=sum(признак is None for признак, _ in значения),
        статусы=tuple(sorted(статусы.items())),
        страниц=(страниц_1, страниц_2),
        стабилен=первый == второй,
    )

def показать_отчёт(отчёт: Отчёт, *, консоль: Console | None = None) -> None:
    вывод = консоль if консоль is not None else Console()
    таблица = Table(title="PROM // ИНВЕНТАРИЗАЦИЯ [GET ONLY]")
    таблица.add_column("Показатель")
    таблица.add_column("Количество", justify="right")
    таблица.add_row("Уникальные ID", str(отчёт.всего))
    таблица.add_row("Основные (is_variation=false)", str(отчёт.основных))
    таблица.add_row("Разновидности (is_variation=true)", str(отчёт.разновидностей))
    таблица.add_row("Признак не передан", str(отчёт.без_признака))
    таблица.add_row("Страниц, два прохода", f"{отчёт.страниц[0]} / {отчёт.страниц[1]}")
    for статус, число in отчёт.статусы:
        таблица.add_row(f"Статус: {статус}", str(число))
    вывод.print(таблица)
    вывод.print("[green]Два прохода совпали[/]" if отчёт.стабилен else "[red]Снимки различаются[/]")
    вывод.print("[yellow]Удалённые позиции и лимиты кабинета отдельно не подтверждены.[/]")
    вывод.print("[dim]Изменений магазина не выполнялось.[/]")
