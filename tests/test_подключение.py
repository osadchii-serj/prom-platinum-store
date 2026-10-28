"""Проверки подключения без реальной сети."""

import httpx
import pytest

from prom.безопасность.переменные_окружения import ХранилищеПеременныхОкружения
from prom.магазины.магазин import МагазинProm
from prom.подключения.интерфейсы import РезультатПодключения
from prom.подключения.настройки import НастройкиПодключения
from prom.подключения.подключение_prom import ПодключениеProm


class ТестовоеХранилище:
    def получить(self, имя_переменной: str) -> str:
        return "test-token-123"


def создать_подключение(обработчик):
    return ПодключениеProm(
        НастройкиПодключения("PROM_API_TOKEN"),
        ТестовоеХранилище(),
        httpx.MockTransport(обработчик),
    )


def test_успешная_проверка():
    def обработчик(запрос):
        assert запрос.method == "GET"
        assert запрос.headers["Authorization"] == "Bearer test-token-123"
        assert запрос.url.params["limit"] == "5"
        return httpx.Response(200, json={"products": []})

    assert создать_подключение(обработчик).проверить().успешно


@pytest.mark.parametrize("статус", [401, 403, 429, 500])
def test_ошибки_http(статус):
    результат = создать_подключение(lambda запрос: httpx.Response(статус)).проверить()
    assert not результат.успешно
    assert результат.код_http == статус


def test_неожиданная_структура():
    результат = создать_подключение(lambda запрос: httpx.Response(200, json={})).проверить()
    assert not результат.успешно


def test_таймаут():
    def обработчик(запрос):
        raise httpx.ReadTimeout("таймаут")

    assert not создать_подключение(обработчик).проверить().успешно


def test_отсутствующий_токен(monkeypatch):
    monkeypatch.delenv("PROM_API_TOKEN", raising=False)
    подключение = ПодключениеProm(
        НастройкиПодключения("PROM_API_TOKEN"), ХранилищеПеременныхОкружения()
    )
    assert not подключение.проверить().успешно


def test_магазин_не_вызывает_сеть_при_создании():
    class ПоддельноеПодключение:
        вызовов = 0

        def проверить(self):
            self.вызовов += 1
            return РезультатПодключения(True, "OK")

    подключение = ПоддельноеПодключение()
    магазин = МагазинProm("platinum-store", "PLATINUM STORE", подключение)
    assert подключение.вызовов == 0
    assert магазин.проверить_подключение().успешно
    assert подключение.вызовов == 1


def test_невалидные_настройки():
    with pytest.raises(ValueError):
        НастройкиПодключения("", 10)
    with pytest.raises(ValueError):
        НастройкиПодключения("PROM_API_TOKEN", 0)
