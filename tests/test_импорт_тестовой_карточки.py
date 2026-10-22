"""Локальные тесты безопасности запроса импорта."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from prom.api.импорт_тестовой_карточки import НАСТРОЙКИ, отпечаток, отправить_один_файл


def test_отпечаток_изменяется_с_содержимым(tmp_path: Path) -> None:
    путь = tmp_path / "тест.xlsx"
    путь.write_bytes(b"first")
    первый = отпечаток(путь)
    путь.write_bytes(b"second")
    assert отпечаток(путь) != первый


def test_неверное_расширение_не_отправляется(tmp_path: Path) -> None:
    путь = tmp_path / "тест.txt"
    путь.write_text("test")
    with pytest.raises(ValueError, match="XLSX"):
        отправить_один_файл(путь)


def test_один_post_с_файлом_и_настройками(tmp_path: Path) -> None:
    путь = tmp_path / "тест.xlsx"
    путь.write_bytes(b"mock-file")
    ответ = MagicMock(status_code=200, text='{"status":"ok"}')
    соединение = MagicMock()
    соединение.__enter__.return_value = соединение
    соединение.post.return_value = ответ
    with (
        patch("prom.api.импорт_тестовой_карточки.получить_токен", return_value="dummy"),
        patch("prom.api.импорт_тестовой_карточки.requests.Session", return_value=соединение),
    ):
        результат = отправить_один_файл(путь)
    assert результат.код == 200
    соединение.post.assert_called_once()
    параметры = соединение.post.call_args.kwargs
    assert параметры["data"]["data"]
    assert НАСТРОЙКИ["mark_missing_product_as"] == "none"
