"""Диагностика отказов API без сети и повторных POST."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from prom.api.операции_импорта import ОшибкаЗапросаИмпорта, _квитанция
from prom.api.результаты_импорта import прочитать_запись
from prom.сценарии.управление_импортом import _запустить


def _ответ(статус: int, данные: object) -> requests.Response:
    ответ = requests.Response()
    ответ.status_code = статус
    ответ._content = json.dumps(данные).encode()  # type: ignore[attr-defined]
    return ответ


def test_код_ошибки_без_сообщения() -> None:
    ответ = _ответ(400, {"error_code": "INVALID_FILE", "message": "secret@example.com"})
    with pytest.raises(ОшибкаЗапросаИмпорта) as перехват:
        _квитанция(ответ)
    assert перехват.value.статус_http == 400
    assert перехват.value.код_ошибки == "INVALID_FILE"
    assert "secret" not in str(перехват.value)


def test_небезопасный_код_отбрасывается() -> None:
    ответ = _ответ(400, {"code": "secret@example.com"})
    with pytest.raises(ОшибкаЗапросаИмпорта) as перехват:
        _квитанция(ответ)
    assert перехват.value.код_ошибки is None


def test_обычный_текст_не_сохраняется() -> None:
    ответ = requests.Response()
    ответ.status_code = 400
    ответ._content = b"private details"  # type: ignore[attr-defined]
    with pytest.raises(ОшибкаЗапросаИмпорта) as перехват:
        _квитанция(ответ)
    assert перехват.value.код_ошибки is None
    assert "private" not in str(перехват.value)


def test_журнал_фиксирует_http_и_блокирует_повтор(tmp_path: Path) -> None:
    журнал = tmp_path / "операция.json"
    запрос = Mock(side_effect=ОшибкаЗапросаИмпорта(400, "INVALID_FILE"))
    with pytest.raises(ОшибкаЗапросаИмпорта):
        _запустить(журнал, "test_001", "файл", запрос)
    запись = прочитать_запись(журнал)
    assert запись.состояние == "неопределённо"
    assert запись.статус_http == 400
    assert запись.код_ошибки == "INVALID_FILE"
    with pytest.raises(RuntimeError, match="Повтор POST заблокирован"):
        _запустить(журнал, "test_001", "файл", запрос)
    assert запрос.call_count == 1
