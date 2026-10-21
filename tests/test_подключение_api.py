"""Тесты разделения токенов и чтения API без сетевых запросов."""

from unittest.mock import Mock

import pytest

from prom.api import клиент, настройки


def test_отдельный_токен_изменения(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(настройки, "load_dotenv", lambda **_kwargs: None)
    monkeypatch.setenv("PROM_API_TOKEN_WRITE", "секрет_для_теста")
    assert настройки.получить_токен("изменение") == "секрет_для_теста"


def test_нет_токена_изменения(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(настройки, "load_dotenv", lambda **_kwargs: None)
    monkeypatch.delenv("PROM_API_TOKEN_WRITE", raising=False)
    with pytest.raises(RuntimeError, match="PROM_API_TOKEN_WRITE"):
        настройки.получить_токен("изменение")


def test_неизвестный_режим() -> None:
    with pytest.raises(ValueError, match="Неизвестный режим"):
        настройки.получить_токен("удаление")


def test_чтение_без_операций_записи(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(клиент, "получить_токен", lambda _режим: "тестовый")
    ответ = Mock()
    ответ.json.return_value = {"products": [{"id": 1}]}
    соединение = Mock()
    соединение.get.return_value = ответ
    соединение.__enter__ = Mock(return_value=соединение)
    соединение.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(клиент.requests, "Session", lambda: соединение)

    assert клиент.проверить_чтение() == 1
    соединение.get.assert_called_once_with(
        клиент.АДРЕС_СПИСКА_ТОВАРОВ, params={"limit": 1}, timeout=20
    )
    соединение.post.assert_not_called()
    соединение.put.assert_not_called()
    соединение.delete.assert_not_called()
