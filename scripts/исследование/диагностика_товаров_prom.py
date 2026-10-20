"""Диагностика идентификаторов товаров Prom.ua без изменения магазина."""

import os
import sys
from collections import Counter

import requests

АДРЕС = "https://my.prom.ua/api/v1/products/list"
РАЗМЕР_СТРАНИЦЫ = 100
МАКСИМУМ_СТРАНИЦ = 100


def выполнить() -> None:
    токен = os.environ.get("PROM_API_TOKEN", "").strip()
    if not токен:
        sys.exit("Ошибка: переменная PROM_API_TOKEN не установлена. Ничего не запрашивалось.")

    товары = {}
    последний_id = None
    with requests.Session() as соединение:
        соединение.headers.update({"Authorization": f"Bearer {токен}"})
        for номер in range(1, МАКСИМУМ_СТРАНИЦ + 1):
            параметры = {"limit": РАЗМЕР_СТРАНИЦЫ}
            if последний_id is not None:
                параметры["last_id"] = последний_id
            ответ = соединение.get(АДРЕС, params=параметры, timeout=30)
            ответ.raise_for_status()
            данные = ответ.json()
            страница = данные.get("products")
            if not isinstance(страница, list):
                raise RuntimeError("В ответе отсутствует список products")
            if not страница:
                print(f"Страница {номер}: пустая, загрузка завершена", flush=True)
                break

            идентификаторы = []
            новые = 0
            for товар in страница:
                if not isinstance(товар, dict) or not isinstance(товар.get("id"), int):
                    raise RuntimeError("Некорректный товар или id в ответе")
                идентификатор = товар["id"]
                идентификаторы.append(идентификатор)
                if идентификатор not in товары:
                    новые += 1
                товары[идентификатор] = товар

            минимальный_id = min(идентификаторы)
            print(
                f"Страница {номер}: получено {len(страница)}, "
                f"новых {новые}, всего {len(товары)}",
                flush=True,
            )
            if последний_id is not None and минимальный_id > последний_id:
                raise RuntimeError("Пагинация не продвигается к меньшим id")
            if новые == 0:
                raise RuntimeError("Страница не содержит новых товаров")
            последний_id = минимальный_id - 1
            if len(страница) < РАЗМЕР_СТРАНИЦЫ:
                break
        else:
            raise RuntimeError("Достигнут предел страниц; результат может быть неполным")

    список = list(товары.values())
    артикулы = Counter(
        str(товар["sku"]).strip()
        for товар in список
        if товар.get("sku") is not None and str(товар["sku"]).strip()
    )
    повторяющиеся = {
        артикул: количество
        for артикул, количество in артикулы.items()
        if количество > 1
    }
    print("\n=== РЕЗУЛЬТАТ ДИАГНОСТИКИ ===")
    print("Всего уникальных ID:", len(товары))
    print("Без external_id:", sum(not товар.get("external_id") for товар in список))
    print("Без артикула:", sum(not str(товар.get("sku") or "").strip() for товар in список))
    print("Артикулов с повторами:", len(повторяющиеся))
    print("Товаров с повторяющимися артикулами:", sum(повторяющиеся.values()))
    print("Разновидностей:", sum(товар.get("is_variation") is True for товар in список))
    print("Максимальная кратность артикула:", max(повторяющиеся.values(), default=0))


if __name__ == "__main__":
    try:
        выполнить()
    except (requests.RequestException, ValueError, RuntimeError) as ошибка:
        sys.exit(f"Диагностика остановлена: {ошибка}")
