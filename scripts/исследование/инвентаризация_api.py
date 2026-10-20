"""Создание реестра API на основе официальной спецификации."""

from pathlib import Path

from prom.api.инвентаризация import выполнить


if __name__ == "__main__":
    выполнить(Path("docs/РЕЕСТР_API.md"))
