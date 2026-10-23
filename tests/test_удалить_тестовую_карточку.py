"""Защитные проверки сценария удаления."""

import importlib.util
from pathlib import Path

import pytest

ПУТЬ = Path(__file__).resolve().parents[1] / "scripts/исследование/удалить_тестовую_карточку.py"
СПЕЦИФИКАЦИЯ = importlib.util.spec_from_file_location("удаление_тестовой_карточки", ПУТЬ)
assert СПЕЦИФИКАЦИЯ is not None and СПЕЦИФИКАЦИЯ.loader is not None
МОДУЛЬ = importlib.util.module_from_spec(СПЕЦИФИКАЦИЯ)
СПЕЦИФИКАЦИЯ.loader.exec_module(МОДУЛЬ)


def test_исходная_карточка() -> None:
    МОДУЛЬ.проверить_исходный_товар(
        {"id": 3243922294, "sku": "PROM-TEST-20261022-001", "status": "draft"}
    )


@pytest.mark.parametrize("поле,значение", [("id", 1), ("sku", "OTHER"), ("status", "deleted")])
def test_чужая_карточка_или_статус(поле: str, значение: object) -> None:
    товар = {"id": 3243922294, "sku": "PROM-TEST-20261022-001", "status": "draft"}
    товар[поле] = значение
    with pytest.raises(ValueError):
        МОДУЛЬ.проверить_исходный_товар(товар)


def test_ответ_post() -> None:
    МОДУЛЬ.проверить_ответ({"processed_ids": [3243922294], "errors": {}})
    for ответ in ({"processed_ids": [], "errors": {}}, {"processed_ids": [3243922294], "errors": {"3243922294": "error"}}, []):
        with pytest.raises(ValueError):
            МОДУЛЬ.проверить_ответ(ответ)


def test_сообщения_rich_не_ломают_разметку() -> None:
    from io import StringIO

    from rich.console import Console

    поток = StringIO()
    консоль = Console(file=поток, force_terminal=False, markup=True)
    консоль.print("[yellow]Проверь карточку в «Видалені позиції» кабинета.[/yellow]")
    консоль.print("[yellow]Восстановление выполняй вручную через кабинет; API-восстановление не проверено.[/yellow]")
    assert "API-восстановление не проверено" in поток.getvalue()
