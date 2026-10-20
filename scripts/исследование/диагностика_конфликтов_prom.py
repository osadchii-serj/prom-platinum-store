"""Диагностика совпадающих артикулов Prom.ua. Только чтение API."""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

АДРЕС = "https://my.prom.ua/api/v1/products/list"
РАЗМЕР_СТРАНИЦЫ = 100
ПРЕДЕЛ_СТРАНИЦ = 1000


def получить_страницу(токен, последний_id):
    параметры = {"limit": РАЗМЕР_СТРАНИЦЫ}
    if последний_id is not None:
        параметры["last_id"] = последний_id
    адрес = АДРЕС + "?" + urllib.parse.urlencode(параметры)
    запрос = urllib.request.Request(
        адрес, headers={"Authorization": f"Bearer {токен}", "Accept": "application/json"}
    )
    with urllib.request.urlopen(запрос, timeout=30) as ответ:
        данные = json.load(ответ)
    if not isinstance(данные, dict) or not isinstance(данные.get("products"), list):
        raise ValueError("Неожиданная структура ответа API")
    return данные["products"]


def нормализовать(значение):
    return str(значение).strip() if значение is not None else ""


def классифицировать(группа):
    разновидности = [т for т in группа if т.get("is_variation") is True]
    if len(разновидности) == len(группа):
        return "только разновидности"
    if not разновидности:
        return "только обычные"
    return "смешанная группа"


def анализировать(товары):
    по_артикулу = defaultdict(list)
    for товар in товары:
        артикул = нормализовать(товар.get("sku"))
        if артикул:
            по_артикулу[артикул].append(товар)
    повторы = {а: г for а, г in по_артикулу.items() if len(г) > 1}
    обычные = [(а, г) for а, г in повторы.items() if классифицировать(г) == "только обычные"]
    смешанные = [(а, г) for а, г in повторы.items() if классифицировать(г) == "смешанная группа"]
    разные_базы = [
        (а, г) for а, г in повторы.items()
        if len({нормализовать(т.get("variation_base_id")) for т in г
                if т.get("is_variation") is True and т.get("variation_base_id") is not None}) > 1
    ]
    ключ = lambda пара: (-len(пара[1]), пара[0])
    обычные.sort(key=ключ)
    смешанные.sort(key=ключ)
    разные_базы.sort(key=ключ)
    выбранные = []
    использованные = set()
    for категория, кандидаты, количество in (
        ("Обычные товары", обычные, 3),
        ("Обычные товары и разновидности", смешанные, 3),
        ("Разные базовые товары", разные_базы, 1),
    ):
        for артикул, группа in кандидаты:
            if артикул in использованные:
                continue
            выбранные.append((категория, артикул, группа))
            использованные.add(артикул)
            количество -= 1
            if количество == 0:
                break
    return повторы, обычные, смешанные, разные_базы, выбранные


def главное():
    токен = os.environ.get("PROM_API_TOKEN")
    if not токен:
        print("Ошибка: переменная PROM_API_TOKEN не найдена.", file=sys.stderr)
        return 1
    товары = {}
    последний_id = None
    try:
        for номер in range(1, ПРЕДЕЛ_СТРАНИЦ + 1):
            страница = получить_страницу(токен, последний_id)
            if not страница:
                break
            идентификаторы = []
            новые = 0
            for товар in страница:
                идентификатор = товар.get("id")
                if not isinstance(идентификатор, int):
                    raise ValueError("У товара отсутствует числовой id")
                идентификаторы.append(идентификатор)
                if идентификатор not in товары:
                    товары[идентификатор] = товар
                    новые += 1
            минимальный = min(идентификаторы)
            if последний_id is not None and минимальный > последний_id:
                raise ValueError("Пагинация перестала продвигаться")
            if новые == 0:
                raise ValueError("Страница без новых товаров; остановка для защиты от цикла")
            print(f"Страница {номер}: получено {len(страница)}, новых {новые}, всего {len(товары)}", flush=True)
            последний_id = минимальный - 1
            if len(страница) < РАЗМЕР_СТРАНИЦЫ:
                break
        else:
            raise ValueError("Достигнут предел страниц; полнота выборки не подтверждена")
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as ошибка:
        print(f"Диагностика остановлена: {ошибка}", file=sys.stderr)
        return 1

    повторы, обычные, смешанные, разные_базы, выбранные = анализировать(товары.values())
    print("\n=== СВОДКА КОНФЛИКТОВ ===")
    print("Всего уникальных записей:", len(товары))
    print("Групп повторяющихся sku:", len(повторы))
    print("Групп только из обычных товаров:", len(обычные))
    print("Смешанных групп:", len(смешанные))
    print("Групп с несколькими базами разновидностей:", len(разные_базы))
    print("\n=== ПРИМЕРЫ КОНФЛИКТОВ ===")
    for категория, артикул, группа in выбранные:
        print(f"\nКатегория: {категория}; sku: {артикул}; записей: {len(группа)}")
        for товар in sorted(группа, key=lambda т: т["id"]):
            print(json.dumps({
                "id": товар.get("id"),
                "external_id": товар.get("external_id"),
                "sku": товар.get("sku"),
                "name": товар.get("name"),
                "is_variation": товар.get("is_variation"),
                "variation_base_id": товар.get("variation_base_id"),
                "variation_group_id": товар.get("variation_group_id"),
            }, ensure_ascii=False))
    print("\nГотово. Данные не сохранялись на диск. Токен не выводился.")
    return 0


if __name__ == "__main__":
    sys.exit(главное())
