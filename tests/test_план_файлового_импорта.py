"""Проверки утверждения плана без запросов к API."""

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from prom.сценарии.план_файлового_импорта import (
    ПланФайловогоИмпорта,
    проверить_утверждение,
    прочитать_план,
    сохранить_план,
    утвердить_план,
)


def _подготовить(tmp_path: Path) -> tuple[Path, Path, str]:
    файл = tmp_path / "товары.xlsx"
    файл.write_bytes(b"test xlsx bytes")
    хеш = hashlib.sha256(файл.read_bytes()).hexdigest()
    путь = tmp_path / "план.json"
    сохранить_план(путь, ПланФайловогоИмпорта("опыт_2", "снимок", хеш, 2, 2, 0, False))
    return файл, путь, хеш


def test_неутверждённый_план_не_разрешает_запуск(tmp_path: Path) -> None:
    файл, путь, хеш = _подготовить(tmp_path)
    with pytest.raises(PermissionError, match="не утверждён"):
        проверить_утверждение(путь, файл, "опыт_2", хеш)


def test_утверждение_и_проверка(tmp_path: Path) -> None:
    файл, путь, хеш = _подготовить(tmp_path)
    утвердить_план(путь, "опыт_2", "УТВЕРДИТЬ опыт_2")
    assert прочитать_план(путь).разрешено
    проверить_утверждение(путь, файл, "опыт_2", хеш)


def test_ошибочная_фраза_не_утверждает(tmp_path: Path) -> None:
    _, путь, _ = _подготовить(tmp_path)
    with pytest.raises(PermissionError):
        утвердить_план(путь, "опыт_2", "УТВЕРДИТЬ другое")
    assert not прочитать_план(путь).разрешено


def test_подмена_файла_после_утверждения(tmp_path: Path) -> None:
    файл, путь, хеш = _подготовить(tmp_path)
    утвердить_план(путь, "опыт_2", "УТВЕРДИТЬ опыт_2")
    файл.write_bytes(b"changed")
    with pytest.raises(ValueError, match="изменился"):
        проверить_утверждение(путь, файл, "опыт_2", хеш)


def test_чужой_ключ_запрещён(tmp_path: Path) -> None:
    файл, путь, хеш = _подготовить(tmp_path)
    утвердить_план(путь, "опыт_2", "УТВЕРДИТЬ опыт_2")
    with pytest.raises(PermissionError, match="не соответствует"):
        проверить_утверждение(путь, файл, "чужой", хеш)


def test_перезапись_плана_запрещена(tmp_path: Path) -> None:
    _, путь, хеш = _подготовить(tmp_path)
    with pytest.raises(FileExistsError):
        сохранить_план(путь, ПланФайловогоИмпорта("другой", "снимок", хеш, 2, 2, 0, False))


def test_ошибка_записи_журнала_не_выполняет_post(tmp_path: Path) -> None:
    from prom.сценарии.управление_импортом import запустить_файл

    файл, путь, хеш = _подготовить(tmp_path)
    утвердить_план(путь, "опыт_2", "УТВЕРДИТЬ опыт_2")
    with (
        patch("prom.сценарии.управление_импортом.сохранить_запись", side_effect=OSError("диск")),
        patch("prom.сценарии.управление_импортом.импортировать_файл") as запрос,
        pytest.raises(OSError, match="диск"),
    ):
        запустить_файл(
            файл, tmp_path / "журнал.json", "опыт_2", подтверждено=True,
            ожидаемый_sha256=хеш, путь_плана=путь,
        )
    запрос.assert_not_called()
