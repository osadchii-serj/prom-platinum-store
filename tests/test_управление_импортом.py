"""Сценарии запуска и сверки импорта без сетевых запросов."""

from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

from prom.api.операции_импорта import КвитанцияИмпорта
from prom.api.результаты_импорта import прочитать_запись
from prom.сценарии.управление_импортом import (
    запустить_url,
    показать_состояние,
    сверить_статус,
)


def test_без_подтверждения_нет_журнала(tmp_path: Path) -> None:
    путь = tmp_path / "операция.json"
    with pytest.raises(PermissionError):
        запустить_url("https://example.org/feed.xml", путь, "операция")
    assert not путь.exists()


def test_квитанция_не_равна_завершению(tmp_path: Path) -> None:
    путь = tmp_path / "операция.json"
    with patch(
        "prom.сценарии.управление_импортом.импортировать_url",
        return_value=КвитанцияИмпорта("123", "success"),
    ) as запрос:
        запись = запустить_url("https://example.org/feed.xml", путь, "операция", подтверждено=True)
    assert запись.состояние == "неопределённо"
    assert запись.идентификатор_импорта == "123"
    assert запрос.call_count == 1
    assert прочитать_запись(путь).ключ == запись.ключ


def test_повтор_после_квитанции_запрещён(tmp_path: Path) -> None:
    путь = tmp_path / "операция.json"
    with patch(
        "prom.сценарии.управление_импортом.импортировать_url",
        return_value=КвитанцияИмпорта("123", "success"),
    ) as запрос:
        запустить_url("https://example.org/feed.xml", путь, "операция", подтверждено=True)
        with pytest.raises(RuntimeError, match="Повтор POST"):
            запустить_url("https://example.org/feed.xml", путь, "операция", подтверждено=True)
    assert запрос.call_count == 1


def test_таймаут_блокирует_повтор(tmp_path: Path) -> None:
    путь = tmp_path / "операция.json"
    with (
        patch(
            "prom.сценарии.управление_импортом.импортировать_url",
            side_effect=TimeoutError("таймаут"),
        ),
        pytest.raises(TimeoutError),
    ):
        запустить_url("https://example.org/feed.xml", путь, "операция", подтверждено=True)

    assert прочитать_запись(путь).состояние == "неопределённо"


def test_сверка_успешного_итога(tmp_path: Path) -> None:
    путь = tmp_path / "операция.json"
    with patch(
        "prom.сценарии.управление_импортом.импортировать_url",
        return_value=КвитанцияИмпорта("123", "success"),
    ):
        запустить_url("https://example.org/feed.xml", путь, "операция", подтверждено=True)
    with patch(
        "prom.сценарии.управление_импортом.получить_статус_импорта",
        return_value={"status": "SUCCESS", "created": 2},
    ) as запрос:
        запись, результат = сверить_статус(путь)
    assert запрос.call_count == 1
    assert запись.состояние == "завершено"
    assert результат.счётчики["created"] == 2


def test_неизвестный_статус_остаётся_неопределённым(tmp_path: Path) -> None:
    путь = tmp_path / "операция.json"
    with patch(
        "prom.сценарии.управление_импортом.импортировать_url",
        return_value=КвитанцияИмпорта("123", "success"),
    ):
        запустить_url("https://example.org/feed.xml", путь, "операция", подтверждено=True)
    with patch(
        "prom.сценарии.управление_импортом.получить_статус_импорта",
        return_value={"status": "PROCESSING"},
    ):
        запись, результат = сверить_статус(путь)
    assert not результат.завершён
    assert запись.состояние == "неопределённо"


def test_без_id_сверка_не_вызывает_api(tmp_path: Path) -> None:
    путь = tmp_path / "операция.json"
    with patch(
        "prom.сценарии.управление_импортом.импортировать_url",
        return_value=КвитанцияИмпорта(None, "success"),
    ):
        запустить_url("https://example.org/feed.xml", путь, "операция", подтверждено=True)
    with (
        patch("prom.сценарии.управление_импортом.получить_статус_импорта") as запрос,
        pytest.raises(RuntimeError, match="ручная сверка"),
    ):
        сверить_статус(путь)

    запрос.assert_not_called()


def test_rich_без_секретов(tmp_path: Path) -> None:
    путь = tmp_path / "операция.json"
    with patch(
        "prom.сценарии.управление_импортом.импортировать_url",
        return_value=КвитанцияИмпорта("123", "success"),
    ):
        запись = запустить_url("https://example.org/private-token", путь, "операция", подтверждено=True)
    with Console(record=True, width=110) as консоль:
        показать_состояние(запись, консоль=консоль)
    текст = консоль.export_text()
    assert "Импорт" in текст.upper() or "ИМПОРТ" in текст
    assert "private-token" not in текст
