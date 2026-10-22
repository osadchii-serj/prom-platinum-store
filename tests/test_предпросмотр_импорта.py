"""Проверки безопасного предпросмотра."""

from pathlib import Path

import pytest

from prom.диагностика.предпросмотр_импорта import прочитать_строки


def test_несуществующий_файл() -> None:
    with pytest.raises(ValueError, match="существующий файл"):
        прочитать_строки(Path("нет_такого_файла.xlsx"))


def test_неподдерживаемый_формат(tmp_path: Path) -> None:
    путь = tmp_path / "данные.csv"
    путь.write_text("abc", encoding="utf-8")
    with pytest.raises(ValueError, match="XLSX"):
        прочитать_строки(путь)


def test_повреждённый_xlsx(tmp_path: Path) -> None:
    путь = tmp_path / "данные.xlsx"
    путь.write_text("не архив", encoding="utf-8")
    with pytest.raises(ValueError, match="повреждён"):
        прочитать_строки(путь)
