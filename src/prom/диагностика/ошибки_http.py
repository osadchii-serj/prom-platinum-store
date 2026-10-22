"""Ограниченный вывод ошибок HTTP без раскрытия произвольного ответа сервера."""

from __future__ import annotations

import json
import re
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Показываем только типовые диагностические поля; остальное не печатаем.
ПОЛЯ = ("error", "errors", "message", "detail", "code", "status")
ЗАПРЕТНЫЕ_КЛЮЧИ = ("token", "secret", "password", "authorization", "cookie", "email", "phone")


def очистить(значение: object) -> str:
    """Удалить потенциальные секреты из короткого диагностического текста."""
    строка = str(значение)
    строка = re.sub(r"(?i)bearer\s+\S+", "Bearer [СКРЫТО]", строка)
    строка = re.sub(r"(?i)(?:token|password|secret|api[_-]?key)\s*[:=]\s*\S+", "[СКРЫТО]", строка)
    строка = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL СКРЫТ]", строка)
    строка = re.sub(r"https?://\S+", "[ССЫЛКА СКРЫТА]", строка)
    строка = re.sub(r"[\r\n\t]+", " ", строка)
    return строка[:240]


def извлечь_поля(тело: str) -> list[tuple[str, str]]:
    """Извлечь ограниченное число безопасных диагностических полей JSON."""
    try:
        данные: Any = json.loads(тело)
    except (ValueError, TypeError):
        return []
    if not isinstance(данные, dict):
        return []
    результат: list[tuple[str, str]] = []
    for ключ in ПОЛЯ:
        значение = данные.get(ключ)
        if значение is None:
            continue
        if isinstance(значение, (str, int, float, bool)):
            результат.append((ключ, очистить(значение)))
        elif isinstance(значение, dict):
            # Не раскрываем произвольные вложенные данные.
            результат.append((ключ, "Объект с подробностями (содержимое скрыто)"))
        elif isinstance(значение, list):
            результат.append((ключ, f"Список элементов: {len(значение)} (содержимое скрыто)"))
    return результат[:6]


def показать_ошибку_http(консоль: Console, код: int, тело: str) -> None:
    """Вывести безопасный Rich-отчёт о неуспешном HTTP-ответе."""
    таблица = Table(show_header=False, box=None, padding=(0, 2))
    таблица.add_column("Поле", style="#829ba5")
    таблица.add_column("Значение", style="white")
    таблица.add_row("HTTP-статус", str(код))
    таблица.add_row("Класс", "Ошибка запроса (4xx)" if 400 <= код < 500 else "Ошибка сервера (5xx)")
    поля = извлечь_поля(тело)
    for ключ, значение in поля:
        таблица.add_row(ключ, значение)
    if not поля:
        таблица.add_row("Ответ", "Нет безопасных диагностических полей JSON; произвольное тело скрыто")
    таблица.add_row("Действие", "Не повторять POST до анализа причины и сверки каталога")
    консоль.print(Panel(таблица, title="ДИАГНОСТИКА ОТКАЗА API", border_style="#ff7582"))
