"""Проверка идентификаторов и разновидностей Prom.ua (только чтение)."""

import os
import sys
from collections import Counter, defaultdict

import requests

АДРЕС = "https://my.prom.ua/api/v1/products/list"
РАЗМЕР_СТРАНИЦЫ = 100
МАКСИМУМ_СТРАНИЦ = 100


def заполненное(значение):
    return str(значение).strip() if значение is not None else ""


def загрузить_товары(токен):
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
            страница = данные.get("products") if isinstance(данные, dict) else None
            if not isinstance(страница, list):
                raise RuntimeError("В ответе отсутствует список products")
            if not страница:
                print(f"Страница {номер}: пустая; загрузка завершена", flush=True)
                return товары

            идентификаторы = []
            новые = 0
            for товар in страница:
                if not isinstance(товар, dict) or type(товар.get("id")) is not int:
                    raise RuntimeError("Некорректный товар или id в ответе")
                идентификатор = товар["id"]
                идентификаторы.append(идентификатор)
                if идентификатор not in товары:
                    новые += 1
                товары[идентификатор] = товар

            минимальный_id = min(идентификаторы)
            if последний_id is not None and минимальный_id > последний_id:
                raise RuntimeError("Пагинация не продвигается к меньшим id")
            if новые != len(страница):
                raise RuntimeError("Обнаружены повторяющиеся id между страницами")
            print(
                f"Страница {номер}: получено {len(страница)}, "
                f"новых {новые}, всего {len(товары)}",
                flush=True,
            )
            последний_id = минимальный_id - 1
            if len(страница) < РАЗМЕР_СТРАНИЦЫ:
                return товары
    raise RuntimeError("Достигнут предел страниц: выборка может быть неполной")


def анализировать(товары):
    список = list(товары.values())
    по_артикулу = defaultdict(list)
    по_внешнему = defaultdict(list)
    разновидности = []
    без_двух = 0

    for товар in список:
        артикул = заполненное(товар.get("sku"))
        внешний = заполненное(товар.get("external_id"))
        if артикул:
            по_артикулу[артикул].append(товар)
        if внешний:
            по_внешнему[внешний].append(товар)
        if not артикул and not внешний:
            без_двух += 1
        if товар.get("is_variation") is True:
            разновидности.append(товар)

    повторные_артикулы = [группа for группа in по_артикулу.values() if len(группа) > 1]
    повторные_внешние = [группа for группа in по_внешнему.values() if len(группа) > 1]
    только_разновидности = 0
    смешанные = 0
    только_обычные = 0
    несколько_баз = 0
    группы_разных_variation_group_id = 0
    for группа in повторные_артикулы:
        число_разновидностей = sum(товар.get("is_variation") is True for товар in группа)
        if число_разновидностей == len(группа):
            только_разновидности += 1
        elif число_разновидностей == 0:
            только_обычные += 1
        else:
            смешанные += 1
        базы = {
            товар.get("variation_base_id")
            for товар in группа
            if товар.get("is_variation") is True
            and товар.get("variation_base_id") is not None
        }
        if len(базы) > 1:
            несколько_баз += 1
        группы_вариантов = {
            товар.get("variation_group_id")
            for товар in группа
            if товар.get("variation_group_id") is not None
        }
        if len(группы_вариантов) > 1:
            группы_разных_variation_group_id += 1

    базы_не_найдены = 0
    без_базы = 0
    неверные_базы = 0
    без_группы = 0
    с_обеими_связями = 0
    for товар in разновидности:
        база = товар.get("variation_base_id")
        группа = товар.get("variation_group_id")
        if база is None:
            без_базы += 1
        elif база not in товары:
            базы_не_найдены += 1
        elif товары[база].get("is_variation") is True:
            неверные_базы += 1
        if группа is None:
            без_группы += 1
        if база is not None and группа is not None:
            с_обеими_связями += 1

    print("\n=== ДИАГНОСТИКА СВЯЗЕЙ И ИДЕНТИФИКАТОРОВ ===")
    print("Всего записей:", len(список))
    print("Заполнено external_id:", sum(len(группа) for группа in по_внешнему.values()))
    print("Уникальных значений external_id:", len(по_внешнему))
    print("Повторяющихся значений external_id:", len(повторные_внешние))
    print("Записей с повторяющимися external_id:", sum(map(len, повторные_внешние)))
    print("Без external_id и без sku одновременно:", без_двух)
    print("\nПовторяющиеся sku:")
    print("Групп с повторяющимся sku:", len(повторные_артикулы))
    print("Групп только из разновидностей:", только_разновидности)
    print("Групп из разновидностей и обычных товаров:", смешанные)
    print("Групп только из обычных товаров:", только_обычные)
    print("Групп с несколькими variation_base_id:", несколько_баз)
    print("Групп с разными variation_group_id:", группы_разных_variation_group_id)
    print("\nСвязи разновидностей:")
    print("Всего разновидностей:", len(разновидности))
    print("Без variation_base_id:", без_базы)
    print("С базой, отсутствующей в выборке:", базы_не_найдены)
    print("С базой, помеченной как разновидность:", неверные_базы)
    print("Без variation_group_id:", без_группы)
    print("С обеими заполненными связями:", с_обеими_связями)
    print("\nПримечание: отсутствующая в выборке база не обязательно означает ошибку магазина.")
    print("Скрипт не изменял данные и не сохранял каталог на диск.")


def выполнить():
    токен = os.environ.get("PROM_API_TOKEN", "").strip()
    if not токен:
        sys.exit("Не установлена переменная PROM_API_TOKEN. Токен сюда не вставляйте.")
    товары = загрузить_товары(токен)
    анализировать(товары)


if __name__ == "__main__":
    try:
        выполнить()
    except (requests.RequestException, ValueError, RuntimeError) as ошибка:
        sys.exit(f"Диагностика остановлена: {ошибка}")
