"""Проверки консервативной связи импорта и снимков."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Literal

import pytest
from rich.console import Console

from prom.api.результаты_импорта import ЗаписьИмпорта, сохранить_запись
from prom.сценарии.сверка_каталога import Карточка, Снимок
from prom.сценарии.связь_импорта import показать_операцию, проверить_операцию
from prom.сценарии.хранилище_снимков import сохранить_снимок


def _снимок(*идентификаторы: int) -> Снимок:
    return Снимок(
        tuple(Карточка(номер, f"SKU-{номер}", None, False) for номер in идентификаторы),
        полный=True,
    )


def _подготовить(
    каталог: Path, *, ключ: str = "job", состояние: Literal["неопределённо", "завершено"] = "завершено",
    статус: str = "SUCCESS", номер: str | None = "123",
) -> Path:
    сохранить_снимок(каталог, ключ, "до", _снимок(1))
    журнал = каталог / "журнал.json"
    запись = ЗаписьИмпорта(ключ, "файл", состояние, номер, статус)
    сохранить_запись(журнал, запись)
    сохранить_снимок(каталог, ключ, "после", _снимок(1, 2))
    # При высокой скорости файловых операций часы могут совпасть.
    # Выставляем в тесте строго упорядоченные временные метки.
    начало = datetime.now(UTC) - timedelta(minutes=2)
    _дата(каталог / f"{ключ}_до.json", начало)
    _дата(журнал, начало + timedelta(minutes=1), журнал=True)
    _дата(каталог / f"{ключ}_после.json", начало + timedelta(minutes=2))
    return журнал


def _дата(путь: Path, дата: datetime, *, журнал: bool = False) -> None:
    данные = json.loads(путь.read_text(encoding="utf-8"))
    данные["обновлено_utc" if журнал else "создан_utc"] = дата.isoformat()
    путь.write_text(json.dumps(данные, ensure_ascii=False), encoding="utf-8")


def test_штатная_связь(tmp_path: Path) -> None:
    журнал = _подготовить(tmp_path)
    итог = проверить_операцию(tmp_path, журнал, "job")
    assert итог.связь_подтверждена
    assert итог.сверка.новые_id == (2,)
    assert not итог.разрешено_изменение
    assert any("не доказывают" in текст for текст in итог.предупреждения)


def test_чужой_журнал(tmp_path: Path) -> None:
    журнал = _подготовить(tmp_path)
    with pytest.raises(ValueError, match="Ключ журнала"):
        проверить_операцию(tmp_path, журнал, "other")


@pytest.mark.parametrize(
    ("состояние", "статус", "номер"),
    [
        ("неопределённо", "SUCCESS", "123"),
        ("завершено", "PARTIAL", "123"),
        ("завершено", "FATAL", "123"),
        ("завершено", "SUCCESS", None),
        ("завершено", "SUCCESS", "abc"),
        ("завершено", "SUCCESS", "0"),
    ],
)
def test_нельзя_подтвердить_связь(
    tmp_path: Path, состояние: Literal["неопределённо", "завершено"], статус: str, номер: str | None,
) -> None:
    журнал = _подготовить(
        tmp_path, состояние=состояние, статус=статус, номер=номер,
    )
    assert not проверить_операцию(tmp_path, журнал, "job").связь_подтверждена


def test_журнал_вне_интервала(tmp_path: Path) -> None:
    журнал = _подготовить(tmp_path)
    _дата(журнал, datetime.now(UTC) + timedelta(days=1), журнал=True)
    итог = проверить_операцию(tmp_path, журнал, "job")
    assert not итог.связь_подтверждена


def test_нет_журнала(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        проверить_операцию(tmp_path, tmp_path / "missing.json", "job")


def test_повреждённый_снимок(tmp_path: Path) -> None:
    журнал = _подготовить(tmp_path)
    путь = tmp_path / "job_после.json"
    данные = json.loads(путь.read_text(encoding="utf-8"))
    данные["карточки"][0]["артикул"] = "подмена"
    путь.write_text(json.dumps(данные, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="целостность"):
        проверить_операцию(tmp_path, журнал, "job")


def test_rich_без_sku(tmp_path: Path) -> None:
    журнал = _подготовить(tmp_path)
    поток = StringIO()
    показать_операцию(
        проверить_операцию(tmp_path, журнал, "job"),
        консоль=Console(file=поток, force_terminal=False, width=110),
    )
    текст = поток.getvalue()
    assert "ЗАПРЕЩЕНО" in текст
    assert "SKU-2" not in текст
