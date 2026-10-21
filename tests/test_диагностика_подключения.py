"""Проверки диагностики без обращения к реальному API."""

from io import StringIO

import pytest
import requests
from rich.console import Console

from prom.api import диагностика_подключения as диагностика


def test_успешное_чтение(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(диагностика, "получить_токен", lambda _режим: "секрет")
    monkeypatch.setattr(диагностика, "проверить_чтение", lambda _режим: 1)
    результат = диагностика.проверить_режим("изменение")
    assert результат.доступен
    assert результат.количество == 1


def test_отсутствующий_токен(monkeypatch: pytest.MonkeyPatch) -> None:
    def нет_токена(_режим: str) -> str:
        raise RuntimeError("Секретное значение")

    monkeypatch.setattr(диагностика, "получить_токен", нет_токена)
    результат = диагностика.проверить_режим("чтение")
    assert not результат.настроен
    assert "Секретное" not in результат.ошибка


def test_ошибка_сети_не_раскрывает_токен(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(диагностика, "получить_токен", lambda _режим: "секрет")

    def сбой(_режим: str) -> int:
        raise requests.ConnectionError("Authorization: Bearer секрет")

    monkeypatch.setattr(диагностика, "проверить_чтение", сбой)
    результат = диагностика.проверить_режим("чтение")
    assert not результат.доступен
    assert "секрет" not in результат.ошибка


def test_отчёт_без_секретов(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(диагностика, "получить_токен", lambda _режим: "секрет")
    monkeypatch.setattr(диагностика, "проверить_чтение", lambda _режим: 1)
    поток = StringIO()
    консоль = Console(file=поток, force_terminal=False, width=110)
    assert диагностика.показать_диагностику(консоль)
    содержимое = поток.getvalue()
    assert "секрет" not in содержимое
    assert "чтение" in содержимое
    assert "изменение" in содержимое
    assert "Права записи не проверялись" in содержимое
