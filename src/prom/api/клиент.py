"""Минимальный клиент для безопасной проверки доступа на чтение."""

import requests

from prom.api.настройки import получить_токен

АДРЕС_СПИСКА_ТОВАРОВ = "https://my.prom.ua/api/v1/products/list"


def проверить_чтение(режим: str = "изменение") -> int:
    """Выполняет один GET, возвращает число полученных карточек без их содержимого."""
    токен = получить_токен(режим)
    with requests.Session() as соединение:
        соединение.headers.update({"Authorization": f"Bearer {токен}"})
        ответ = соединение.get(
            АДРЕС_СПИСКА_ТОВАРОВ,
            params={"limit": 1},
            timeout=20,
        )
        ответ.raise_for_status()
        данные = ответ.json()
    if not isinstance(данные, dict):
        raise TypeError("Ответ API должен быть объектом")
    товары = данные.get("products")
    if not isinstance(товары, list):
        raise TypeError("В ответе API отсутствует список products")
    return len(товары)
