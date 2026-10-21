"""Безопасная консольная диагностика подключения к Prom.ua API."""

from dataclasses import dataclass
from time import perf_counter

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from prom.api.клиент import проверить_чтение
from prom.api.настройки import получить_токен


@dataclass(frozen=True)
class РезультатПроверки:
    """Результат проверки одного режима без секретов и данных карточек."""

    режим: str
    настроен: bool
    доступен: bool
    количество: int | None = None
    миллисекунды: int | None = None
    ошибка: str = ""


def проверить_режим(режим: str) -> РезультатПроверки:
    """Проверить наличие токена и выполнить единственный GET-запрос."""
    try:
        получить_токен(режим)
    except RuntimeError:
        return РезультатПроверки(режим, False, False, ошибка="Токен не настроен")

    начало = perf_counter()
    try:
        количество = проверить_чтение(режим)
    except requests.Timeout:
        ошибка = "Превышено время ожидания"
    except requests.HTTPError as исключение:
        статус = исключение.response.status_code if исключение.response is not None else None
        if статус in (401, 403):
            ошибка = f"Отказ в доступе (HTTP {статус})"
        elif статус is not None:
            ошибка = f"Ошибка API (HTTP {статус})"
        else:
            ошибка = "Ошибка HTTP"
    except requests.RequestException:
        ошибка = "Ошибка сетевого соединения"
    except (TypeError, ValueError):
        ошибка = "Неожиданный формат ответа API"
    except RuntimeError:
        ошибка = "Ошибка конфигурации"
    else:
        время = round((perf_counter() - начало) * 1000)
        return РезультатПроверки(режим, True, True, количество, время)

    время = round((perf_counter() - начало) * 1000)
    return РезультатПроверки(режим, True, False, миллисекунды=время, ошибка=ошибка)


def показать_диагностику(консоль: Console | None = None) -> bool:
    """Показать Rich-отчёт; вернуть True, если оба GET-запроса успешны."""
    вывод = консоль if консоль is not None else Console()
    вывод.print(Panel.fit("[bold cyan]PROM · PLATINUM STORE[/]\nДиагностика подключения к API"))

    таблица = Table(title="Проверка токенов", show_lines=True)
    таблица.add_column("Режим")
    таблица.add_column("Токен")
    таблица.add_column("GET /products/list")
    таблица.add_column("Время")

    результаты = [проверить_режим(режим) for режим in ("чтение", "изменение")]
    for результат in результаты:
        состояние = "[green]Настроен[/]" if результат.настроен else "[yellow]Отсутствует[/]"
        if результат.доступен:
            ответ = f"[green]Успешно[/] · карточек: {результат.количество}"
        else:
            ответ = f"[red]{результат.ошибка}[/]"
        время = f"{результат.миллисекунды} мс" if результат.миллисекунды is not None else "—"
        таблица.add_row(результат.режим, состояние, ответ, время)
    вывод.print(таблица)
    вывод.print("[dim]Выполнялись только GET-запросы. Права записи не проверялись.[/]")
    return all(результат.доступен for результат in результаты)
