"""Тесты постраничного чтения без обращения к магазину."""

import httpx
import pytest

from prom.подключения.настройки import НастройкиПодключения
from prom.подключения.подключение_prom import ПодключениеProm
from prom.цены.источник_prom import ИсточникТоваровProm, ОшибкаОбходаТоваров


class Хранилище:
    def получить(self, имя: str) -> str:
        return "fake-token"


def источник(обработчик, размер=2):
    подключение = ПодключениеProm(
        НастройкиПодключения("PROM_API_TOKEN"),
        Хранилище(),
        httpx.MockTransport(обработчик),
    )
    return ИсточникТоваровProm(подключение, размер)


def test_две_страницы_и_пустой_ответ():
    запросы = []

    def обработчик(запрос):
        запросы.append(dict(запрос.url.params))
        курсор = запрос.url.params.get("last_id")
        данные = {None: [5, 4], "4": [3, 2], "2": []}[курсор]
        return httpx.Response(
            200, json={"products": [{"id": x, "price": 100, "currency": "UAH"} for x in данные]}
        )

    страницы = list(источник(обработчик).страницы_товаров())
    assert sum(map(len, страницы)) == 4
    assert запросы == [
        {"limit": "2"},
        {"limit": "2", "last_id": "4"},
        {"limit": "2", "last_id": "2"},
    ]


def test_повтор_страницы_останавливает_обход():
    def обработчик(запрос):
        return httpx.Response(200, json={"products": [{"id": 5}, {"id": 4}]})

    with pytest.raises(ОшибкаОбходаТоваров):
        list(источник(обработчик).страницы_товаров())


def test_неверная_структура_останавливает_обход():
    with pytest.raises(ОшибкаОбходаТоваров):
        list(источник(lambda запрос: httpx.Response(200, json={"oops": []})).страницы_товаров())


def test_http_ошибка_не_маскируется():
    with pytest.raises(httpx.HTTPStatusError):
        list(источник(lambda запрос: httpx.Response(403)).страницы_товаров())
