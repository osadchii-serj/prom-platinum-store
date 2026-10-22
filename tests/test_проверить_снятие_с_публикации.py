"""Проверки второго эксперимента смены статуса."""
import importlib.util
from pathlib import Path

import pytest

ПУТЬ = Path(__file__).resolve().parents[1] / "scripts/исследование/проверить_снятие_с_публикации.py"
СПЕЦИФИКАЦИЯ = importlib.util.spec_from_file_location("снятие_с_публикации", ПУТЬ)
assert СПЕЦИФИКАЦИЯ is not None and СПЕЦИФИКАЦИЯ.loader is not None
МОДУЛЬ = importlib.util.module_from_spec(СПЕЦИФИКАЦИЯ)
СПЕЦИФИКАЦИЯ.loader.exec_module(МОДУЛЬ)

@pytest.mark.parametrize("начало,цель", [("draft", "not_on_display"), ("not_on_display", "draft")])
def test_разрешённые_переходы(начало: str, цель: str) -> None:
    товар = {"id": 3243922294, "sku": "PROM-TEST-20261022-001", "status": начало}
    assert МОДУЛЬ.проверить_переход(товар, цель) == начало

@pytest.mark.parametrize("начало,цель", [("draft", "deleted"), ("draft", "on_display"), ("on_display", "not_on_display"), ("draft", "draft")])
def test_запрещённые_переходы(начало: str, цель: str) -> None:
    товар = {"id": 3243922294, "sku": "PROM-TEST-20261022-001", "status": начало}
    with pytest.raises(ValueError):
        МОДУЛЬ.проверить_переход(товар, цель)

def test_проверка_ответа_обработки() -> None:
    МОДУЛЬ.проверить_ответ_редактирования({"processed_ids": [3243922294], "errors": {}})
    with pytest.raises(ValueError):
        МОДУЛЬ.проверить_ответ_редактирования({"processed_ids": [], "errors": {}})
