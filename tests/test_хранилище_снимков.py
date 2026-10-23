"""Снимки каталога: целостность, повторный запуск и Rich."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

from prom.сценарии.сверка_каталога import Карточка, Снимок
from prom.сценарии.хранилище_снимков import (
    показать_сохранённую_сверку,
    прочитать_снимок,
    путь_снимка,
    сверить_сохранённые,
    снять_и_сохранить,
    сохранить_снимок,
)


def снимок(*номера: int, полный: bool = True) -> Снимок:
    return Снимок(
        tuple(Карточка(номер, f"SKU-{номер}", None, False) for номер in номера),
        полный,
    )


def test_сохранение_и_чтение(tmp_path: Path) -> None:
    сохранить_снимок(tmp_path, "import_1", "до", снимок(2, 1))
    результат, метаданные = прочитать_снимок(tmp_path, "import_1", "до")
    assert [карточка.идентификатор for карточка in результат.карточки] == [1, 2]
    assert метаданные.количество == 2
    assert len(метаданные.sha256) == 64


def test_пустой_каталог(tmp_path: Path) -> None:
    сохранить_снимок(tmp_path, "empty", "до", снимок())
    результат, _ = прочитать_снимок(tmp_path, "empty", "до")
    assert результат.карточки == ()


def test_не_перезаписывать(tmp_path: Path) -> None:
    путь = сохранить_снимок(tmp_path, "job", "до", снимок(1))
    исходные = путь.read_bytes()
    with pytest.raises(FileExistsError):
        сохранить_снимок(tmp_path, "job", "до", снимок(2))
    assert путь.read_bytes() == исходные


def test_запрет_неполного_снимка(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="неполный"):
        сохранить_снимок(tmp_path, "job", "до", снимок(1, полный=False))


@pytest.mark.parametrize("ключ", ["../escape", "", "а", "a b", "a/b", "x" * 81])
def test_ключ_не_позволяет_выйти_из_каталога(tmp_path: Path, ключ: str) -> None:
    with pytest.raises(ValueError):
        путь_снимка(tmp_path, ключ, "до")


def test_повреждение_файла(tmp_path: Path) -> None:
    путь = сохранить_снимок(tmp_path, "job", "до", снимок(1))
    данные = json.loads(путь.read_text(encoding="utf-8"))
    данные["карточки"][0]["артикул"] = "подмена"
    путь.write_text(json.dumps(данные), encoding="utf-8")
    with pytest.raises(ValueError, match="целостность"):
        прочитать_снимок(tmp_path, "job", "до")


def test_подмена_операции(tmp_path: Path) -> None:
    путь = сохранить_снимок(tmp_path, "job", "до", снимок(1))
    данные = json.loads(путь.read_text(encoding="utf-8"))
    данные["операция"] = "other"
    путь.write_text(json.dumps(данные), encoding="utf-8")
    with pytest.raises(ValueError, match="другой операции"):
        прочитать_снимок(tmp_path, "job", "до")


def test_повторные_id_при_сохранении(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Повторные"):
        сохранить_снимок(tmp_path, "job", "до", снимок(1, 1))


def test_сверка_двух_снимков(tmp_path: Path) -> None:
    сохранить_снимок(tmp_path, "job", "до", снимок(1, 2))
    сохранить_снимок(tmp_path, "job", "после", снимок(1, 2, 3))
    итог = сверить_сохранённые(tmp_path, "job")
    assert итог.новые_id == (3,)
    assert not итог.разрешено_изменение


def test_rich_не_печатает_sku(tmp_path: Path) -> None:
    сохранить_снимок(tmp_path, "job", "до", снимок(1))
    сохранить_снимок(tmp_path, "job", "после", снимок(1, 2))
    поток = StringIO()
    показать_сохранённую_сверку(
        tmp_path, "job", консоль=Console(file=поток, force_terminal=False),
    )
    assert "ЗАПРЕЩЕНО" in поток.getvalue()
    assert "SKU-2" not in поток.getvalue()


def test_несовпадение_двух_проходов_не_сохраняется(tmp_path: Path) -> None:
    from prom.сценарии.чтение_каталога import ИтогЧтения

    итог = ИтогЧтения(снимок(1, полный=False), (1, 1), False)
    with (
        patch(
            "prom.сценарии.хранилище_снимков.получить_стабильный_снимок",
            return_value=итог,
        ),
        pytest.raises(RuntimeError, match="изменился"),
    ):
        снять_и_сохранить(tmp_path, "job", "до")
    assert not путь_снимка(tmp_path, "job", "до").exists()


def test_существующий_снимок_не_вызывает_api(tmp_path: Path) -> None:
    сохранить_снимок(tmp_path, "job", "до", снимок(1))
    with (
        patch("prom.сценарии.хранилище_снимков.получить_стабильный_снимок") as запрос,
        pytest.raises(FileExistsError),
    ):
        снять_и_сохранить(tmp_path, "job", "до")
    запрос.assert_not_called()
