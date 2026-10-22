"""Проверки безопасной диагностики ответов HTTP."""

from io import StringIO

from rich.console import Console

from prom.диагностика.ошибки_http import извлечь_поля, показать_ошибку_http


def test_неизвестное_тело_не_печатается() -> None:
    поток = StringIO()
    показать_ошибку_http(Console(file=поток, force_terminal=False), 400, "PRIVATE_RESPONSE")
    assert "PRIVATE_RESPONSE" not in поток.getvalue()
    assert "400" in поток.getvalue()


def test_извлекается_сообщение() -> None:
    поля = извлечь_поля('{"message": "Неверный формат", "access_token": "SECRET"}')
    assert поля == [("message", "Неверный формат")]


def test_токен_в_сообщении_скрыт() -> None:
    поля = извлечь_поля('{"error": "Bearer verysecret"}')
    assert "verysecret" not in str(поля)


def test_вложенные_значения_скрыты() -> None:
    поля = извлечь_поля('{"errors": [{"email": "someone@example.com"}]}')
    assert "someone@example.com" not in str(поля)
