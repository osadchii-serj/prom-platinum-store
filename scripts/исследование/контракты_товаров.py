"""Получить описание методов изменения товаров из официальной документации."""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from prom.api.контракты_товаров import выполнить


if __name__ == "__main__":
    консоль = Console()
    путь = Path("docs/КОНТРАКТЫ_ТОВАРОВ.md")
    консоль.print(Panel("Изучение контрактов товаров · только публичная документация", title="PROM"))
    выполнить(путь)
    консоль.print(f"[green]Готово:[/green] {путь}")
    консоль.print("[yellow]Запросы к магазину и операции записи не выполнялись.[/yellow]")
