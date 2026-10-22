"""Предпросмотр тестовой карточки относительно исходного экспорта."""

import argparse
from pathlib import Path

from prom.диагностика.предпросмотр_импорта import показать


def выполнить() -> None:
    """Прочитать аргументы и показать результаты без записи."""
    парсер = argparse.ArgumentParser(description="Безопасный предпросмотр импорта PROM")
    парсер.add_argument("макет", type=Path)
    парсер.add_argument("экспорт", type=Path)
    параметры = парсер.parse_args()
    if not показать(параметры.макет, параметры.экспорт):
        raise SystemExit(1)


if __name__ == "__main__":
    выполнить()
