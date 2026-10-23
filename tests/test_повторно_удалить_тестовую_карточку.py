"""Проверки защитных ограничений повторного удаления."""

import importlib.util
from pathlib import Path

import pytest

ПУТЬ = Path(__file__).resolve().parents[1] / "scripts/исследование/повторно_удалить_тестовую_карточку.py"
СПЕЦИФИКАЦИЯ = importlib.util.spec_from_file_location("повторное_удаление", ПУТЬ)
assert СПЕЦИФИКАЦИЯ is not None and СПЕЦИФИКАЦИЯ.loader is not None
МОДУЛЬ = importlib.util.module_from_spec(СПЕЦИФИКАЦИЯ)
СПЕЦИФИКАЦИЯ.loader.exec_module(МОДУЛЬ)


def товар(статус: str = "not_on_display", артикул: str = "PROM-TEST-20261022-001") -> dict:
    return {"product": {"id": 3243922294, "sku": артикул, "status": статус}}


def test_исходное_состояние() -> None:
    МОДУЛЬ.проверить_товар(товар())


@pytest.mark.parametrize("статус", ["draft", "deleted", "on_display"])
def test_неверный_статус(статус: str) -> None:
    with pytest.raises(ValueError):
        МОДУЛЬ.проверить_товар(товар(статус))


def test_чужой_артикул() -> None:
    with pytest.raises(ValueError):
        МОДУЛЬ.проверить_товар(товар(артикул="OTHER"))


def test_пустой_get() -> None:
    with pytest.raises(ValueError):
        МОДУЛЬ.проверить_товар({})


def test_успешный_post() -> None:
    МОДУЛЬ.проверить_ответ({"processed_ids": [3243922294], "errors": {}})


@pytest.mark.parametrize("ответ", [
    {"processed_ids": [], "errors": {}},
    {"processed_ids": [3243922294, 1], "errors": {}},
    {"processed_ids": [3243922294], "errors": {"3243922294": "error"}},
    {"processed_ids": [3243922294]},
])
def test_неподтверждённый_post(ответ: dict) -> None:
    with pytest.raises(ValueError):
        МОДУЛЬ.проверить_ответ(ответ)
