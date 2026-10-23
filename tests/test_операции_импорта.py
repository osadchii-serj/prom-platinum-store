"""Проверки адаптеров импорта без сетевых обращений."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from prom.api.операции_импорта import (
    НастройкиИмпорта,
    _квитанция,
    импортировать_url,
    импортировать_файл,
    получить_статус_импорта,
)


def _соединение(данные: object) -> MagicMock:
    ответ = MagicMock()
    ответ.json.return_value = данные
    соединение = MagicMock()
    соединение.__enter__.return_value = соединение
    соединение.post.return_value = ответ
    соединение.get.return_value = ответ
    return соединение


def test_запись_по_умолчанию_заблокирована(tmp_path: Path) -> None:
    with pytest.raises(PermissionError):
        импортировать_файл(tmp_path / "пример.xlsx")
    with pytest.raises(PermissionError):
        импортировать_url("https://example.org/feed.xml")


def test_опасные_параметры_заблокированы() -> None:
    with pytest.raises(ValueError, match="запрещено"):
        импортировать_url(
            "https://example.org/feed.xml",
            настройки=НастройкиИмпорта(mark_missing_product_as="deleted"),
            подтверждено=True,
        )


def test_импорт_url_один_post() -> None:
    соединение = _соединение({"id": "123", "status": "success"})
    with patch("prom.api.операции_импорта._соединение", return_value=соединение):
        квитанция = импортировать_url("https://example.org/feed.xml", подтверждено=True)
    assert квитанция.идентификатор == "123"
    assert квитанция.статус == "success"
    соединение.post.assert_called_once()
    параметры = соединение.post.call_args.kwargs
    assert параметры["json"]["mark_missing_product_as"] == "none"
    assert параметры["json"]["url"] == "https://example.org/feed.xml"


def test_импорт_файла_один_post(tmp_path: Path) -> None:
    путь = tmp_path / "пример.xlsx"
    путь.write_bytes(b"test")
    соединение = _соединение({"id": 456, "status": "success"})
    with patch("prom.api.операции_импорта._соединение", return_value=соединение):
        квитанция = импортировать_файл(путь, подтверждено=True)
    assert квитанция.идентификатор == "456"
    соединение.post.assert_called_once()


def test_статус_только_по_числовому_id() -> None:
    with pytest.raises(ValueError):
        получить_статус_импорта("abc")
    соединение = _соединение(
        {"status": "PARTIAL", "created": 2, "with_errors_count": 1}
    )
    with patch("prom.api.операции_импорта._соединение", return_value=соединение):
        данные = получить_статус_импорта("123")
    assert данные["status"] == "PARTIAL"
    соединение.get.assert_called_once()


def test_неверный_ответ_не_считается_успехом() -> None:
    соединение = _соединение(["unexpected"])
    with (
        patch("prom.api.операции_импорта._соединение", return_value=соединение),
        pytest.raises(TypeError, match="объектом"),
    ):
        импортировать_url("https://example.org/feed.xml", подтверждено=True)


"""Локальные проверки импорта без сетевых запросов."""


def test_http_400_не_печатает_ответ(capsys: pytest.CaptureFixture[str]) -> None:
    ответ = requests.Response()
    ответ.status_code = 400
    ответ._content = b"secret token in server response"
    ответ.url = "https://my.prom.ua/api/v1/products/import_file"
    with pytest.raises(requests.HTTPError) as ошибка:
        _квитанция(ответ)
    assert ошибка.value.response is ответ
    assert capsys.readouterr().out == ""


def test_импорт_формирует_post_без_сети(tmp_path: Path) -> None:
    файл = tmp_path / "test.xlsx"
    файл.write_bytes(b"not-a-real-xlsx-for-mocked-request")
    ответ = requests.Response()
    ответ.status_code = 200
    ответ._content = b'{"id":"abc123","status":"accepted"}'
    соединение = MagicMock()
    соединение.__enter__.return_value = соединение
    соединение.post.return_value = ответ
    with patch("prom.api.операции_импорта._соединение", return_value=соединение):
        квитанция = импортировать_файл(файл, подтверждено=True)
    assert квитанция.идентификатор == "abc123"
    assert квитанция.статус == "accepted"
    аргументы, параметры = соединение.post.call_args
    assert аргументы == ("https://my.prom.ua/api/v1/products/import_file",)
    assert параметры["files"]["file"][0] == "test.xlsx"
    assert (
        параметры["files"]["file"][2]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert json.loads(параметры["data"]["data"]) == НастройкиИмпорта().данные()
    assert параметры["timeout"] == (10, 90)


def test_без_подтверждения_post_не_выполняется(tmp_path: Path) -> None:
    файл = tmp_path / "test.xlsx"
    файл.write_bytes(b"test")
    with (
        patch("prom.api.операции_импорта._соединение") as соединение,
        pytest.raises(PermissionError),
    ):
        импортировать_файл(файл)

    соединение.assert_not_called()
