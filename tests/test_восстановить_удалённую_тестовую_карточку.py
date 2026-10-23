"""Тесты проверок восстановления без обращений к сети."""

import importlib.util
from pathlib import Path

import pytest

ПУТЬ = Path(__file__).resolve().parents[1] / "scripts/исследование/восстановить_удалённую_тестовую_карточку.py"
СПЕЦИФИКАЦИЯ = importlib.util.spec_from_file_location("восстановление_теста", ПУТЬ)
assert СПЕЦИФИКАЦИЯ is not None and СПЕЦИФИКАЦИЯ.loader is not None
МОДУЛЬ = importlib.util.module_from_spec(СПЕЦИФИКАЦИЯ)
СПЕЦИФИКАЦИЯ.loader.exec_module(МОДУЛЬ)


def test_успешный_ответ() -> None:
    МОДУЛЬ.проверить_ответ({"processed_ids": [3243922294], "errors": {}})


@pytest.mark.parametrize("ответ", [{}, {"processed_ids": []}, {"processed_ids": [3243922294], "errors": {"3243922294": "error"}}, {"processed_ids": [3243922294, 1], "errors": {}}])
def test_отклонить_неподтверждённый_ответ(ответ: object) -> None:
    with pytest.raises(ValueError):
        МОДУЛЬ.проверить_ответ(ответ)


def test_успешный_get() -> None:
    МОДУЛЬ.проверить_товар({"product": {"id": 3243922294, "sku": "PROM-TEST-20261022-001", "status": "not_on_display"}})


@pytest.mark.parametrize("поле,значение", [("id", 1), ("sku", "OTHER"), ("status", "draft")])
def test_несовпадение_get(поле: str, значение: object) -> None:
    товар = {"id": 3243922294, "sku": "PROM-TEST-20261022-001", "status": "not_on_display"}
    товар[поле] = значение
    with pytest.raises(ValueError):
        МОДУЛЬ.проверить_товар({"product": товар})


def test_неверный_тип_post() -> None:
    with pytest.raises(TypeError):
        МОДУЛЬ.проверить_ответ(None)


@pytest.mark.parametrize("ответ", [None, {}, {"product": None}])
def test_неверная_структура_get(ответ: object) -> None:
    with pytest.raises(TypeError):
        МОДУЛЬ.проверить_товар(ответ)
