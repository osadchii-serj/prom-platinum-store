"""Только чтение полного каталога перед испытанием импорта."""

from dataclasses import dataclass

import requests

from prom.api.настройки import получить_токен

АДРЕС = "https://my.prom.ua/api/v1/products/list"
РАЗМЕР_СТРАНИЦЫ = 100
ПРЕДЕЛ_СТРАНИЦ = 100


@dataclass(frozen=True)
class Сверка:
    """Итог полного чтения каталога."""

    просмотрено: int
    совпадения: tuple[int, ...]


def сверить_с_api(карточка: dict[str, str]) -> Сверка:
    """Искать совпадения по артикулу и external_id во всём каталоге."""
    артикул = карточка.get("Код_товару", "").strip()
    внешний = карточка.get("Унікальний_ідентифікатор", "").strip()
    if not артикул:
        raise ValueError("Отсутствует артикул товара")
    токен = получить_токен("чтение")
    просмотренные: set[int] = set()
    совпадения: set[int] = set()
    последний_id: int | None = None
    завершено = False
    with requests.Session() as соединение:
        соединение.headers.update({"Authorization": f"Bearer {токен}"})
        for _ in range(ПРЕДЕЛ_СТРАНИЦ):
            параметры: dict[str, int] = {"limit": РАЗМЕР_СТРАНИЦЫ}
            if последний_id is not None:
                параметры["last_id"] = последний_id
            ответ = соединение.get(АДРЕС, params=параметры, timeout=30)
            ответ.raise_for_status()
            данные = ответ.json()
            if not isinstance(данные, dict) or not isinstance(данные.get("products"), list):
                raise TypeError("Неожиданная структура ответа API")
            товары = данные["products"]
            if not товары:
                завершено = True
                break
            идентификаторы = []
            for товар in товары:
                if not isinstance(товар, dict) or type(товар.get("id")) is not int:
                    raise ValueError("Некорректный идентификатор товара в ответе")
                идентификатор = товар["id"]
                идентификаторы.append(идентификатор)
                просмотренные.add(идентификатор)
                if (str(товар.get("sku") or "").strip() == артикул or
                        (bool(внешний) and str(товар.get("external_id") or "").strip() == внешний)):
                    совпадения.add(идентификатор)
            следующий_id = min(идентификаторы)
            if последний_id is not None and следующий_id >= последний_id:
                raise ValueError("Пагинация API не продвигается; сверка неполная")
            последний_id = следующий_id
            if len(товары) < РАЗМЕР_СТРАНИЦЫ:
                завершено = True
                break
    if not завершено:
        raise ValueError("Достигнут предел страниц; сверка неполная")
    return Сверка(len(просмотренные), tuple(sorted(совпадения)))
