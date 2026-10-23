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


def test_файл_без_хеша_не_отправляется(tmp_path: Path) -> None:
    from prom.сценарии.управление_импортом import запустить_файл

    файл = tmp_path / "товары.xlsx"
    файл.write_bytes(b"xlsx")
    with (
        patch("prom.сценарии.управление_импортом.импортировать_файл") as запрос,
        pytest.raises(PermissionError, match="SHA-256"),
    ):
        запустить_файл(файл, tmp_path / "операция.json", "тест", подтверждено=True)
    запрос.assert_not_called()


def test_изменённый_файл_не_отправляется(tmp_path: Path) -> None:
    import hashlib

    from prom.сценарии.управление_импортом import запустить_файл

    файл = tmp_path / "товары.xlsx"
    ожидаемый = hashlib.sha256("проверенные данные".encode()).hexdigest()
    файл.write_bytes("изменённые данные".encode())
    from prom.сценарии.план_файлового_импорта import (
        ПланФайловогоИмпорта,
        сохранить_план,
        утвердить_план,
    )
    путь_плана = tmp_path / "план.json"
    сохранить_план(путь_плана, ПланФайловогоИмпорта("тест", "снимок", ожидаемый, 2, 2, 0, False))
    утвердить_план(путь_плана, "тест", "УТВЕРДИТЬ тест")
    with (
        patch("prom.сценарии.управление_импортом.импортировать_файл") as запрос,
        pytest.raises(ValueError, match="изменился"),
    ):
        запустить_файл(
                файл, tmp_path / "операция.json", "тест",
                подтверждено=True, ожидаемый_sha256=ожидаемый, путь_плана=путь_плана,
            )
    запрос.assert_not_called()


def test_файл_отправляется_из_копии_и_запоминает_хеш(tmp_path: Path) -> None:
    import hashlib

    from prom.сценарии.управление_импортом import запустить_файл

    файл = tmp_path / "товары.xlsx"
    файл.write_bytes("проверенные данные".encode())
    хеш = hashlib.sha256(файл.read_bytes()).hexdigest()
    содержимое = []

    def отправить(путь: Path, **_: object) -> КвитанцияИмпорта:
        assert путь != файл
        содержимое.append(путь.read_bytes())
        файл.write_bytes("изменено во время POST".encode())
        assert путь.read_bytes() == "проверенные данные".encode()
        return КвитанцияИмпорта("123", "success")

    with (
        patch("prom.сценарии.управление_импортом.импортировать_файл", side_effect=отправить),
        patch("prom.сценарии.управление_импортом.проверить_утверждение"),
    ):
        запись = запустить_файл(
            файл, tmp_path / "операция.json", "тест",
            подтверждено=True, ожидаемый_sha256=хеш, путь_плана=tmp_path / "план.json",
        )
    assert содержимое == ["проверенные данные".encode()]
    assert запись.sha256_файла == хеш
    assert not list(tmp_path.glob(".prom_import_*"))


def test_занятая_блокировка_не_отправляет(tmp_path: Path) -> None:
    import fcntl
    import hashlib
    import os

    from prom.сценарии.управление_импортом import запустить_файл

    файл = tmp_path / "товары.xlsx"
    файл.write_bytes("проверенные данные".encode())
    хеш = hashlib.sha256(файл.read_bytes()).hexdigest()
    путь = tmp_path / "операция.json"
    from prom.сценарии.план_файлового_импорта import (
        ПланФайловогоИмпорта,
        сохранить_план,
        утвердить_план,
    )
    путь_плана = tmp_path / "план.json"
    сохранить_план(путь_плана, ПланФайловогоИмпорта("тест", "снимок", хеш, 2, 2, 0, False))
    утвердить_план(путь_плана, "тест", "УТВЕРДИТЬ тест")
    дескриптор = os.open(str(путь) + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(дескриптор, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (
            patch("prom.сценарии.управление_импортом.импортировать_файл") as запрос,
            pytest.raises(RuntimeError, match="уже выполняется"),
        ):
            запустить_файл(
                    файл, путь, "тест", подтверждено=True, ожидаемый_sha256=хеш, путь_плана=путь_плана,
                )
        запрос.assert_not_called()
    finally:
        os.close(дескриптор)


def test_план_обязателен_до_отправки(tmp_path: Path) -> None:
    from prom.сценарии.управление_импортом import запустить_файл

    файл = tmp_path / "товары.xlsx"
    файл.write_bytes(b"xlsx")
    with (
        patch("prom.сценарии.управление_импортом.импортировать_файл") as запрос,
        pytest.raises(PermissionError, match="план"),
    ):
        запустить_файл(
            файл, tmp_path / "операция.json", "тест", подтверждено=True,
            ожидаемый_sha256="0" * 64,
        )
    запрос.assert_not_called()


def test_неутверждённый_план_блокирует_post(tmp_path: Path) -> None:
    import hashlib

    from prom.сценарии.план_файлового_импорта import (
        ПланФайловогоИмпорта,
        сохранить_план,
    )
    from prom.сценарии.управление_импортом import запустить_файл

    файл = tmp_path / "товары.xlsx"
    файл.write_bytes(b"xlsx")
    хеш = hashlib.sha256(файл.read_bytes()).hexdigest()
    путь_плана = tmp_path / "план.json"
    сохранить_план(
        путь_плана, ПланФайловогоИмпорта("тест", "снимок", хеш, 2, 2, 0, False)
    )
    with (
        patch("prom.сценарии.управление_импортом.импортировать_файл") as запрос,
        pytest.raises(PermissionError, match="не утверждён"),
    ):
        запустить_файл(
            файл, tmp_path / "операция.json", "тест", подтверждено=True,
            ожидаемый_sha256=хеш, путь_плана=путь_плана,
        )
    запрос.assert_not_called()
