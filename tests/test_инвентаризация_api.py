"""Проверки безопасной инвентаризации API."""

import pytest

from prom.api.инвентаризация import (
    найти_ссылки,
    получить_операции,
    проверить_адрес,
    сформировать_отчёт,
)


def test_ссылки_вложенных_схем():
    данные = {"paths": {"/a": {"get": {"$ref": "GetA.yaml"}}}, "schemas": [{"$ref": "B.yaml#/x"}]}
    assert найти_ссылки(данные) == ["GetA.yaml", "B.yaml#/x"]


@pytest.mark.parametrize("адрес", ["http://public-api.docs.prom.ua/x", "https://example.org/x", "https://public-api.docs.prom.ua.evil.org/x"])
def test_запрет_посторонних_адресов(адрес):
    with pytest.raises(ValueError):
        проверить_адрес(адрес)


def test_внешняя_операция_и_отчёт():
    адрес = "https://public-api.docs.prom.ua/documentation/index.yaml"
    документы = {
        адрес: {"paths": {"/products/list": {"get": {"$ref": "GetProductList.yaml"}}}},
        "https://public-api.docs.prom.ua/documentation/GetProductList.yaml": {
            "tags": ["Products"], "summary": "Список товаров", "operationId": "getProducts"
        },
    }
    операции = получить_операции(документы)
    assert len(операции) == 1
    assert операции[0].метод == "GET"
    assert "/products/list" in сформировать_отчёт(операции, документы)


def test_ссылка_на_описание_пути():
    адрес = "https://public-api.docs.prom.ua/documentation/index.yaml"
    документы = {
        адрес: {"paths": {"/orders/list": {"$ref": "Orders/paths/GetOrderList.yaml"}}},
        "https://public-api.docs.prom.ua/documentation/Orders/paths/GetOrderList.yaml": {
            "get": {"tags": ["Orders"], "summary": "Список заказов"}
        },
    }
    операции = получить_операции(документы)
    assert len(операции) == 1
    assert операции[0].метод == "GET"
    assert операции[0].путь == "/orders/list"
