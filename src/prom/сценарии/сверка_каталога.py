"""Безопасное сопоставление двух полных снимков каталога (только чтение)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from rich.console import Console
from rich.table import Table


@dataclass(frozen=True)
class Карточка:
    """Минимальная запись каталога с обязательным ID Prom."""

    идентификатор: int
    артикул: str | None
    внешний_id: str | None
    вариация: bool


@dataclass(frozen=True)
class Снимок:
    """Снимок допустим только после подтверждения полноты пагинации."""

    карточки: tuple[Карточка, ...]
    полный: bool


@dataclass(frozen=True)
class Сверка:
    """Кандидаты на новые карточки, не разрешение на их изменение."""

    новые_id: tuple[int, ...]
    удалённые_id: tuple[int, ...]
    изменённые_id: tuple[int, ...]
    неоднозначные_sku: tuple[str, ...]
    предупреждения: tuple[str, ...]
    допустим_предпросмотр: bool
    разрешено_изменение: bool = False


def собрать_снимок(товары: Iterable[dict[str, Any]], *, полный: bool) -> Снимок:
    """Отклонять невалидные ID и дубли вместо молчаливого перезаписывания."""
    карточки: list[Карточка] = []
    встреченные: set[int] = set()
    for товар in товары:
        идентификатор = товар.get("id")
        if isinstance(идентификатор, bool) or not isinstance(идентификатор, int):
            raise TypeError("У товара отсутствует целочисленный id")
        if идентификатор <= 0 or идентификатор in встреченные:
            raise ValueError("Недопустимый или повторный id в снимке")
        встреченные.add(идентификатор)
        sku = товар.get("sku")
        внешний = товар.get("external_id")
        if sku is not None and not isinstance(sku, str):
            raise TypeError("sku должен быть строкой или null")
        if внешний is not None and not isinstance(внешний, str):
            raise TypeError("external_id должен быть строкой или null")
        вариация = товар.get("is_variation", False)
        if not isinstance(вариация, bool):
            raise TypeError("is_variation должен быть bool")
        карточки.append(Карточка(идентификатор, sku or None, внешний or None, вариация))
    return Снимок(tuple(sorted(карточки, key=lambda к: к.идентификатор)), полный)


def сопоставить(до: Снимок, после: Снимок) -> Сверка:
    """Не связывать карточки по SKU: только по устойчивому ID."""
    если_неполный = not (до.полный and после.полный)
    старые = {к.идентификатор: к for к in до.карточки}
    текущие = {к.идентификатор: к for к in после.карточки}
    новые = tuple(sorted(текущие.keys() - старые.keys()))
    удалённые = tuple(sorted(старые.keys() - текущие.keys()))
    изменённые = tuple(
        sorted(ид for ид in старые.keys() & текущие.keys() if старые[ид] != текущие[ид])
    )
    количество = Counter(
        к.артикул for к in после.карточки if к.артикул is not None
    )
    повторные = tuple(sorted(артикул for артикул, число in количество.items() if число > 1))
    предупреждения: list[str] = []
    if если_неполный:
        предупреждения.append("Снимок неполный: сравнение не является надёжным")
    if удалённые:
        предупреждения.append("Между снимками исчезли карточки")
    if изменённые:
        предупреждения.append("Изменены данные существующих ID")
    if повторные:
        предупреждения.append("Есть повторяющиеся SKU; сопоставление по SKU запрещено")
    if новые:
        предупреждения.append("Новые ID не доказывают принадлежность конкретному импорту")
    return Сверка(
        новые, удалённые, изменённые, повторные,
        tuple(предупреждения), not если_неполный,
    )


def показать_сверку(сверка: Сверка, *, консоль: Console | None = None) -> None:
    """Rich-предпросмотр без операций изменения магазина."""
    вывод = консоль if консоль is not None else Console()
    таблица = Table(title="PROM / сверка снимков каталога")
    таблица.add_column("Показатель")
    таблица.add_column("Значение", justify="right")
    таблица.add_row("Новые ID (кандидаты)", str(len(сверка.новые_id)))
    таблица.add_row("Исчезнувшие ID", str(len(сверка.удалённые_id)))
    таблица.add_row("Изменённые ID", str(len(сверка.изменённые_id)))
    таблица.add_row("Повторяющиеся SKU", str(len(сверка.неоднозначные_sku)))
    таблица.add_row("Полнота снимков", "подтверждена" if сверка.допустим_предпросмотр else "НЕ подтверждена")
    таблица.add_row("Изменение карточек", "ЗАПРЕЩЕНО")
    вывод.print(таблица)
    for предупреждение in сверка.предупреждения:
        вывод.print(f"[yellow]Внимание:[/yellow] {предупреждение}")
