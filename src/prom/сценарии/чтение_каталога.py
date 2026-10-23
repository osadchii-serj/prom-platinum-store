"""Чтение полного каталога Prom.ua и проверка стабильности снимка.

Только GET. Никаких операций изменения товаров.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from prom.api.настройки import получить_токен
from prom.сценарии.сверка_каталога import Снимок, собрать_снимок

АДРЕС_КАТАЛОГА = "https://my.prom.ua/api/v1/products/list"
РАЗМЕР_СТРАНИЦЫ = 100
ПРЕДЕЛ_СТРАНИЦ = 100


@dataclass(frozen=True)
class ИтогЧтения:
    """Два чтения без расхождений дают стабильный наблюдаемый снимок."""

    снимок: Снимок
    страниц_за_проход: tuple[int, int]
    стабилен: bool


def прочитать_каталог(
    соединение: requests.Session,
    *,
    размер_страницы: int = РАЗМЕР_СТРАНИЦЫ,
    предел_страниц: int = ПРЕДЕЛ_СТРАНИЦ,
) -> tuple[Снимок, int]:
    """Читать все страницы по last_id; неполный проход отклонять исключением."""
    if not 1 <= размер_страницы <= 100:
        raise ValueError("Размер страницы должен быть от 1 до 100")
    if предел_страниц < 1:
        raise ValueError("Предел страниц должен быть положительным")
    последний_id: int | None = None
    встреченные: set[int] = set()
    все_товары: list[dict[str, Any]] = []
    for номер in range(1, предел_страниц + 1):
        параметры = {"limit": размер_страницы}
        if последний_id is not None:
            параметры["last_id"] = последний_id
        ответ = соединение.get(АДРЕС_КАТАЛОГА, params=параметры, timeout=30)
        ответ.raise_for_status()
        данные: Any = ответ.json()
        if not isinstance(данные, dict) or not isinstance(данные.get("products"), list):
            raise TypeError("Ответ каталога не содержит список products")
        товары: list[Any] = данные["products"]
        if len(товары) > размер_страницы:
            raise ValueError("API вернул больше товаров, чем запрошено")
        идентификаторы: list[int] = []
        for товар in товары:
            if not isinstance(товар, dict):
                raise TypeError("Элемент products должен быть объектом")
            идентификатор = товар.get("id")
            if type(идентификатор) is not int:
                raise TypeError("ID товара должен быть целым числом")
            if идентификатор <= 0 or идентификатор in встреченные:
                raise ValueError("Недопустимый или повторный ID в пагинации")
            if последний_id is not None and идентификатор >= последний_id:
                raise ValueError("Страница содержит ID вне ожидаемого диапазона")
            идентификаторы.append(идентификатор)
            встреченные.add(идентификатор)
            все_товары.append(товар)
        if not товары or len(товары) < размер_страницы:
            return собрать_снимок(все_товары, полный=True), номер
        следующий_id = min(идентификаторы)
        if последний_id is not None and следующий_id >= последний_id:
            raise ValueError("Пагинация не продвигается")
        последний_id = следующий_id
    raise RuntimeError("Достигнут предел страниц: полнота каталога не подтверждена")


def получить_стабильный_снимок(
    *,
    консоль: Console | None = None,
    соединение: requests.Session | None = None,
) -> ИтогЧтения:
    """Дважды прочитать каталог; несовпадение означает нестабильный снимок.

    Совпадение двух чтений не гарантирует отсутствия промежуточных изменений.
    """
    вывод = консоль if консоль is not None else Console()
    собственная_сессия = соединение is None
    сессия = соединение if соединение is not None else requests.Session()
    try:
        if собственная_сессия:
            токен = получить_токен("чтение")
            сессия.headers.update({"Authorization": f"Bearer {токен}"})
        with Progress(
            SpinnerColumn(), TextColumn("{task.description}"),
            console=вывод, transient=True,
        ) as прогресс:
            задача = прогресс.add_task("Чтение каталога: проход 1", total=None)
            первый, страниц_1 = прочитать_каталог(сессия)
            прогресс.update(задача, description="Чтение каталога: проход 2")
            второй, страниц_2 = прочитать_каталог(сессия)
        стабилен = первый.карточки == второй.карточки
        return ИтогЧтения(
            Снимок(второй.карточки, полный=стабилен),
            (страниц_1, страниц_2),
            стабилен,
        )
    finally:
        if собственная_сессия:
            сессия.close()


def показать_чтение(итог: ИтогЧтения, *, консоль: Console | None = None) -> None:
    """Rich-сводка без вывода персональных данных и токенов."""
    вывод = консоль if консоль is not None else Console()
    вывод.print("[bold cyan]PROM / проверка каталога[/bold cyan]")
    вывод.print(f"Карточек: {len(итог.снимок.карточки)}")
    вывод.print(f"Страниц: {итог.страниц_за_проход[0]} / {итог.страниц_за_проход[1]}")
    if итог.стабилен:
        вывод.print("[green]Два чтения совпали; снимок пригоден для предварительной сверки[/green]")
    else:
        вывод.print("[yellow]Снимки различаются: использовать как полный запрещено[/yellow]")
    вывод.print("[yellow]Изменение карточек заблокировано[/yellow]")
