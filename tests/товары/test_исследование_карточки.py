"""Тесты локального анализа JSON без обращения к Prom.ua."""

import pytest

from prom.товары.исследование_карточки import название_типа, собрать_реестр


@pytest.mark.parametrize(
    ("значение", "ожидаемый"),
    [
        (None, "null"),
        (True, "boolean"),
        (3, "integer"),
        (3.5, "number"),
        ("3", "string"),
        ([], "array"),
        ({}, "object"),
    ],
)
def test_типы_json(значение: object, ожидаемый: str) -> None:
    assert название_типа(значение) == ожидаемый


def test_вложенные_поля_и_разные_типы() -> None:
    реестр = собрать_реестр({"products": [{"id": 1, "price": 10}, {"id": 2, "price": None}]})
    поля = {строка["путь"]: строка["наблюдаемые_типы"] for строка in реестр}
    assert поля["products[].id"] == "integer"
    assert поля["products[].price"] == "integer, null"


def test_пустой_массив() -> None:
    поля = {строка["путь"] for строка in собрать_реестр({"products": []})}
    assert "products" in поля
    assert "products[]" not in поля
