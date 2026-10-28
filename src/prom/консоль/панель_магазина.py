"""Консольная панель состояния магазина."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def показать_панель_магазина(
    консоль: Console,
    название: str,
    подключён: bool,
) -> None:
    """Отобразить состояние магазина в стиле Cyber Terminal."""
    бирюзовый = "#24E6C1"
    приглушённый = "#92A8BA"
    основной = "#F0F6FF"

    статус = "ONLINE" if подключён else "OFFLINE"
    цвет_статуса = бирюзовый if подключён else "#FF647C"

    таблица = Table.grid(padding=(0, 2), expand=True)
    таблица.add_column(style=приглушённый)
    таблица.add_column(style=основной, justify="right")

    таблица.add_row("МАГАЗИН", название)
    таблица.add_row("ПЛАТФОРМА", "Prom.ua")
    таблица.add_row(
        "СОЕДИНЕНИЕ",
        Text(статус, style=f"bold {цвет_статуса}"),
    )
    таблица.add_row(
        "АВТОРИЗАЦИЯ",
        "Подтверждена" if подключён else "Не подтверждена",
    )
    таблица.add_row("ОПЕРАЦИЯ", "Проверка доступа · чтение")

    заголовок = Text(
        "◈  PROM // CYBER TERMINAL",
        style=f"bold {бирюзовый}",
    )

    консоль.print()
    консоль.print(
        Panel(
            таблица,
            title=заголовок,
            subtitle=Text(
                "● API CONNECTED" if подключён else "● CONNECTION FAILED",
                style=f"bold {цвет_статуса}",
            ),
            border_style=бирюзовый if подключён else цвет_статуса,
            padding=(1, 2),
        )
    )
