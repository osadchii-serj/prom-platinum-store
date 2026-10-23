"""Локальные тесты результатов и журнала импорта."""

from dataclasses import replace
from pathlib import Path

import pytest

from prom.api.результаты_импорта import (
    ЗаписьИмпорта,
    можно_повторить_импорт,
    прочитать_запись,
    разобрать_статус,
    сохранить_запись,
)


def test_успешный_результат() -> None:
    результат = разобрать_статус({
        "status": "SUCCESS", "created": 3,
        "created_active": 2, "created_hidden": 1, "errors": [],
    })
    assert результат.завершён
    assert результат.успешен
    assert результат.счётчики["created"] == 3


@pytest.mark.parametrize("статус", ["PARTIAL", "FATAL"])
def test_ошибочные_итоги(статус: str) -> None:
    результат = разобрать_статус({"status": статус, "with_errors_count": 1})
    assert результат.завершён
    assert not результат.успешен


def test_неизвестный_статус_не_финальный() -> None:
    результат = разобрать_статус({"status": "PROCESSING"})
    assert not результат.завершён
    assert not результат.успешен


def test_несогласованные_счётчики() -> None:
    результат = разобрать_статус({
        "status": "SUCCESS", "created": 3,
        "created_active": 1, "created_hidden": 1,
    })
    assert not результат.успешен


@pytest.mark.parametrize("значение", [-1, True, "5"])
def test_недопустимые_счётчики(значение: object) -> None:
    with pytest.raises(ValueError, match="счётчик"):
        разобрать_статус({"status": "SUCCESS", "created": значение})


def test_ошибки_без_разглашения_содержимого() -> None:
    результат = разобрать_статус({
        "status": "PARTIAL", "errors": [{"validation": "секретное описание"}],
    })
    assert результат.категории_ошибок == ("validation",)
    assert "секретное описание" not in str(результат)


def test_сохранение_и_чтение(tmp_path: Path) -> None:
    запись = ЗаписьИмпорта("пакет_1", "файл", "подготовлено")
    путь = tmp_path / "операция.json"
    сохранить_запись(путь, запись)
    assert прочитать_запись(путь).ключ == "пакет_1"
    assert путь.stat().st_mode & 0o077 == 0


def test_повтор_после_отправки_запрещён() -> None:
    запись = ЗаписьИмпорта("пакет_1", "url", "подготовлено")
    assert можно_повторить_импорт(запись)
    for состояние in ("запрос_отправлен", "неопределённо"):
        assert not можно_повторить_импорт(replace(запись, состояние=состояние))
    assert not можно_повторить_импорт(replace(запись, состояние="завершено", статус_api="SUCCESS"))


def test_завершение_без_итога_запрещено() -> None:
    with pytest.raises(ValueError, match="итогового"):
        ЗаписьИмпорта("пакет_1", "файл", "завершено")


def test_неверный_формат_журнала(tmp_path: Path) -> None:
    путь = tmp_path / "операция.json"
    путь.write_text("[]", encoding="utf-8")
    with pytest.raises(TypeError):
        прочитать_запись(путь)
