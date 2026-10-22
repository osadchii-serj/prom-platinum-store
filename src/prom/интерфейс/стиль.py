"""Единый терминальный стиль PROM без дополнительных библиотек."""

from rich.box import ROUNDED, SIMPLE_HEAVY
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

БИРЮЗОВЫЙ = "#00e5c2"
ПРИГЛУШЁННЫЙ = "#829ba5"
ЗЕЛЁНЫЙ = "#62e6a4"
ЯНТАРНЫЙ = "#f5be57"
КРАСНЫЙ = "#ff7582"
РАМКА = "#31505b"


def заголовок(консоль: Console, раздел: str) -> None:
    """Показать заголовок единого оформления."""
    текст = Text()
    текст.append("◈  PROM", style=f"bold {БИРЮЗОВЫЙ}")
    текст.append("  /  PLATINUM STORE\n", style="bold white")
    текст.append(раздел.upper(), style=ПРИГЛУШЁННЫЙ)
    консоль.print(Panel(текст, border_style=РАМКА, box=ROUNDED, padding=(1, 2)))


def таблица_параметров() -> Table:
    """Создать компактную таблицу для карточки."""
    результат = Table(box=SIMPLE_HEAVY, border_style=РАМКА, header_style=f"bold {БИРЮЗОВЫЙ}")
    результат.add_column("ПОЛЕ", style=ПРИГЛУШЁННЫЙ, no_wrap=True)
    результат.add_column("ЗНАЧЕНИЕ", style="white", overflow="fold")
    return результат


def сообщение(консоль: Console, состояние: str, текст: str) -> None:
    """Отобразить статус с русским обозначением."""
    цвет = {"успех": ЗЕЛЁНЫЙ, "внимание": ЯНТАРНЫЙ, "ошибка": КРАСНЫЙ}[состояние]
    значок = {"успех": "✓", "внимание": "!", "ошибка": "×"}[состояние]
    консоль.print(Text(f" {значок}  {текст}", style=цвет))
