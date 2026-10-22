"""Проверки защитных ограничений сценария смены статуса."""

import importlib.util
from pathlib import Path

import pytest

ПУТЬ = Path(__file__).resolve().parents[1] / "scripts/исследование/изменить_статус_тестовой_карточки.py"
СПЕЦИФИКАЦИЯ = importlib.util.spec_from_file_location("проверка_статуса", ПУТЬ)
assert СПЕЦИФИКАЦИЯ is not None and СПЕЦИФИКАЦИЯ.loader is not None
МОДУЛЬ = importlib.util.module_from_spec(СПЕЦИФИКАЦИЯ)
СПЕЦИФИКАЦИЯ.loader.exec_module(МОДУЛЬ)


def test_допустимый_переход() -> None:
    товар = {"id": 3243922294, "sku": "PROM-TEST-20261022-001", "status": "on_display"}
    assert МОДУЛЬ.проверить_переход(товар, "draft") == "on_display"


@pytest.mark.parametrize("статус", ["deleted", "not_on_display", "on_display"])
def test_запрет_лишних_переходов(статус: str) -> None:
    товар = {"id": 3243922294, "sku": "PROM-TEST-20261022-001", "status": "on_display"}
    with pytest.raises(ValueError):
        МОДУЛЬ.проверить_переход(товар, статус)


def test_запрет_чужого_артикула() -> None:
    with pytest.raises(ValueError):
        МОДУЛЬ.проверить_переход({"id": 3243922294, "sku": "OTHER", "status": "on_display"}, "draft")


def test_проверка_ответа() -> None:
    МОДУЛЬ.проверить_ответ_редактирования({"processed_ids": [3243922294], "errors": {}})
    with pytest.raises(ValueError):
        МОДУЛЬ.проверить_ответ_редактирования({"processed_ids": [], "errors": {}})
