"""Проверки извлечения контрактов без обращения к сети."""

from typing import Any

import pytest

from prom.api.контракты_товаров import разрешить_ссылку, сформировать_контракты

АДРЕС = "https://public-api.docs.prom.ua/documentation/index.yaml"


def test_внешней_ссылки_и_схемы() -> None:
    адрес_операции = "https://public-api.docs.prom.ua/documentation/Products/paths/Edit.yaml"
    документы: dict[str, dict[Any, Any]] = {
        АДРЕС: {"paths": {"/products/edit": {"post": {"$ref": "Products/paths/Edit.yaml"}}}},
        адрес_операции: {
            "summary": "Редактирование товара",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"type": "object", "required": ["products"], "properties": {
                            "products": {"type": "array"}
                        }}
                    }
                },
            },
            "responses": {"200": {"description": "OK"}},
        },
    }
    отчёт = сформировать_контракты(документы)
    assert "POST /products/edit" in отчёт
    assert "products" in отчёт
    assert "200" in отчёт
    assert "Запросы к магазину НЕ выполнялись" in отчёт


def test_внутренней_ссылки() -> None:
    документы = {АДРЕС: {"components": {"schemas": {"Товар": {"type": "object"}}}}}
    схема, адрес = разрешить_ссылку(документы, АДРЕС, "#/components/schemas/Товар")
    assert схема == {"type": "object"}
    assert адрес == АДРЕС


def test_отсутствия_операций() -> None:
    with pytest.raises(ValueError, match="не обнаружены"):
        сформировать_контракты({АДРЕС: {"paths": {"/products/list": {"get": {}}}}})


def test_ссылки_на_весь_путь_официальный_формат() -> None:
    """Корневой index.yaml ссылается на отдельные файлы Path Item."""
    адрес_пути = "https://public-api.docs.prom.ua/documentation/Products/paths/Edit.yaml"
    адрес_схемы = "https://public-api.docs.prom.ua/documentation/Products/schemas/Body.yaml"
    документы: dict[str, dict[Any, Any]] = {
        АДРЕС: {"paths": {"/products/edit": {"$ref": "Products/paths/Edit.yaml"}}},
        адрес_пути: {
            "post": {
                "summary": "Изменить товар",
                "requestBody": {
                    "content": {"application/json": {"schema": {"$ref": "../schemas/Body.yaml"}}}
                },
                "responses": {"200": {"description": "OK"}},
            }
        },
        адрес_схемы: {
            "type": "object",
            "required": ["products"],
            "properties": {"products": {"type": "array"}},
        },
    }
    отчёт = сформировать_контракты(документы)
    assert "POST /products/edit" in отчёт
    assert "Обязательные поля: products" in отчёт
