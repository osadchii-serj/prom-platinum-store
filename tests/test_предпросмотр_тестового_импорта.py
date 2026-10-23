"""Локальные проверки нового тестового товара."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from prom.сценарии.предпросмотр_тестового_импорта import проверить_файл
from prom.сценарии.сверка_каталога import Карточка, Снимок
from prom.сценарии.хранилище_снимков import сохранить_снимок


def _подготовить(каталог: Path, *, код: str = "PROM-TEST-002", количество: int = 1) -> Path:
    сохранить_снимок(каталог, "job", "до", Снимок((Карточка(1, "OLD", None, False),), True))
    книга = Workbook()
    лист = книга.active
    assert лист is not None
    лист.append(["Код_товару", "Назва_позиції", "Ціна", "Валюта", "Ідентифікатор_товару"])
    for _ in range(количество):
        лист.append([код, "ТЕСТ — не покупать", 1, "UAH", None])
    путь = каталог / "тест.xlsx"
    книга.save(путь)
    return путь


def test_корректный_файл(tmp_path: Path) -> None:
    файл = _подготовить(tmp_path)
    результат = проверить_файл(файл, tmp_path, "job")
    assert результат.артикул == "PROM-TEST-002"
    assert len(результат.sha256) == 64
    assert not результат.разрешено_отправить


def test_два_товара_запрещены(tmp_path: Path) -> None:
    файл = _подготовить(tmp_path, количество=2)
    with pytest.raises(ValueError, match="ровно один"):
        проверить_файл(файл, tmp_path, "job")


def test_артикул_без_префикса_запрещён(tmp_path: Path) -> None:
    файл = _подготовить(tmp_path, код="REAL-SKU")
    with pytest.raises(ValueError, match="PROM-TEST"):
        проверить_файл(файл, tmp_path, "job")


def test_неизвестный_снимок_запрещён(tmp_path: Path) -> None:
    файл = _подготовить(tmp_path)
    with pytest.raises(FileNotFoundError):
        проверить_файл(файл, tmp_path, "other")


def test_совпадение_sku_запрещено(tmp_path: Path) -> None:
    файл = _подготовить(tmp_path, код="PROM-TEST-002")
    сохранить_снимок(
        tmp_path, "same", "до", Снимок((Карточка(1, "PROM-TEST-002", None, False),), True),
    )
    with pytest.raises(ValueError, match="уже присутствует"):
        проверить_файл(файл, tmp_path, "same")
