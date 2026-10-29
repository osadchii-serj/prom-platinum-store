"""Технологичный консольный отчёт по предварительному плану цен Prom.ua."""

from decimal import Decimal

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from prom.цены.массовое_обновление_цен import ПланЦен

ЦВЕТ_АКЦЕНТА = "bright_cyan"
ЦВЕТ_УСПЕХА = "bright_green"


def _деньги(значение: Decimal) -> str:
    """Отобразить сумму с двумя десятичными знаками."""
    return f"{значение:,.2f}".replace(",", " ")


def показать_план(
    план: ПланЦен,
    консоль: Console,
    процент: Decimal = Decimal(20),
    *,
    максимум_строк: int = 15,
) -> None:
    """Показать KPI и первые строки плана; никаких запросов записи нет."""
    if максимум_строк < 0:
        raise ValueError("Максимум строк не может быть отрицательным")
    if not процент.is_finite() or процент < 0:
        raise ValueError("Некорректный процент")

    количество = len(план.изменения)
    пропущено = len(план.пропуски)
    сумма_до = sum((строка.старая_цена for строка in план.изменения), Decimal(0))
    сумма_после = sum((строка.новая_цена for строка in план.изменения), Decimal(0))
    разница = сумма_после - сумма_до
    средняя_до = сумма_до / количество if количество else Decimal(0)
    средняя_после = сумма_после / количество if количество else Decimal(0)

    консоль.print()
    консоль.print(
        Panel(
            Text.from_markup(
                f"[bold {ЦВЕТ_АКЦЕНТА}]PROM // PRICE ENGINE[/bold {ЦВЕТ_АКЦЕНТА}]\n"
                f"[white]Предварительный просмотр · наценка {процент:g}%[/white]\n"
                "[bright_yellow]READ ONLY  •  ЗАПИСЬ В МАГАЗИН ОТКЛЮЧЕНА[/bright_yellow]"
            ),
            box=box.DOUBLE_EDGE,
            border_style=ЦВЕТ_АКЦЕНТА,
            expand=True,
        )
    )

    показатели = Table(box=box.SIMPLE_HEAVY, expand=True, show_header=False, padding=(0, 2))
    показатели.add_column("Показатель", style="dim")
    показатели.add_column("Значение", justify="right", style=ЦВЕТ_УСПЕХА)
    for название, значение in (
        ("Карточек просмотрено", str(план.просмотрено)),
        ("Цены рассчитаны", str(количество)),
        ("Пропущено", str(пропущено)),
        ("Средняя цена до / после", f"{_деньги(средняя_до)} / {_деньги(средняя_после)} UAH"),
        ("Сумма каталожных цен до", f"{_деньги(сумма_до)} UAH"),
        ("Сумма каталожных цен после", f"{_деньги(сумма_после)} UAH"),
        (
            "Суммарное изменение цен",
            f"+{_деньги(разница)} UAH" if разница >= 0 else f"{_деньги(разница)} UAH",
        ),
    ):
        показатели.add_row(название, значение)
    консоль.print(
        Panel(показатели, title="[bright_cyan]CATALOG / METRICS[/bright_cyan]", border_style="cyan")
    )

    таблица = Table(
        title=f"[bold bright_cyan]PRICE DIFF[/bold bright_cyan] · первые {min(максимум_строк, количество)} из {количество}",
        box=box.ROUNDED,
        border_style="bright_black",
        header_style="bold bright_cyan",
        expand=True,
    )
    таблица.add_column("ID", style="dim", no_wrap=True)
    таблица.add_column("Название", overflow="ellipsis", max_width=48, ratio=1)
    таблица.add_column("Было", justify="right", no_wrap=True)
    таблица.add_column("Стало", justify="right", style=ЦВЕТ_УСПЕХА, no_wrap=True)
    таблица.add_column("Δ", justify="right", style=ЦВЕТ_АКЦЕНТА, no_wrap=True)
    for изменение in план.изменения[:максимум_строк]:
        таблица.add_row(
            str(изменение.идентификатор),
            изменение.название,
            _деньги(изменение.старая_цена),
            _деньги(изменение.новая_цена),
            _деньги(изменение.новая_цена - изменение.старая_цена),
        )
    консоль.print(таблица)
    if количество > максимум_строк:
        консоль.print(
            f"[dim]Скрыто строк: {количество - максимум_строк}. Расчёт выполнен для всех карточек.[/dim]"
        )
    for пропуск in план.пропуски:
        консоль.print(f"[yellow]SKIP[/yellow] {пропуск.идентификатор}: {пропуск.причина}")
    консоль.print(
        "[bold bright_yellow]DRY RUN[/bold bright_yellow] · Изменения не отправлялись на Prom.ua\n"
    )
