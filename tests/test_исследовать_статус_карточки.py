"""Тесты фильтрации диагностического вывода."""

import importlib.util
from pathlib import Path

ПУТЬ = Path(__file__).resolve().parents[1] / "scripts/исследование/исследовать_статус_карточки.py"
СПЕЦИФИКАЦИЯ = importlib.util.spec_from_file_location("исследовать_статус_карточки", ПУТЬ)
assert СПЕЦИФИКАЦИЯ is not None and СПЕЦИФИКАЦИЯ.loader is not None
МОДУЛЬ = importlib.util.module_from_spec(СПЕЦИФИКАЦИЯ)
СПЕЦИФИКАЦИЯ.loader.exec_module(МОДУЛЬ)


def test_вывод_статуса() -> None:
    assert ("product.status", "active") in МОДУЛЬ.безопасные_поля({"product": {"status": "active"}})


def test_скрытие_секретов() -> None:
    assert МОДУЛЬ.безопасные_поля({"token_status": "secret", "customer_email": "a@b.com"}) == []


def test_без_длинных_значений() -> None:
    assert МОДУЛЬ.безопасные_поля({"status": "x" * 101}) == []
