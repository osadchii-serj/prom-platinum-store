"""Локальная проверка макета XLSX перед импортом; запросов к API нет."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from rich.console import Console

from prom.интерфейс.стиль import заголовок, сообщение, таблица_параметров

ПРОСТРАНСТВО = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
КЛЮЧИ = ("Код_товару", "Унікальний_ідентифікатор", "Ідентифікатор_товару")


def прочитать_строки(путь: Path) -> list[dict[str, str]]:
    """Прочитать первую таблицу XLSX без дополнительных зависимостей."""
    if not путь.is_file() or путь.suffix.lower() != ".xlsx":
        raise ValueError("Требуется существующий файл XLSX")
    try:
        with ZipFile(путь) as архив:
            строки_текста: list[str] = []
            if "xl/sharedStrings.xml" in архив.namelist():
                корень = ElementTree.fromstring(архив.read("xl/sharedStrings.xml"))
                for элемент in корень.findall(f"{ПРОСТРАНСТВО}si"):
                    строки_текста.append("".join(
                        узел.text or "" for узел in элемент.iter(f"{ПРОСТРАНСТВО}t")
                    ))
            корень = ElementTree.fromstring(архив.read("xl/worksheets/sheet1.xml"))
    except (BadZipFile, KeyError, ElementTree.ParseError) as ошибка:
        raise ValueError("Файл XLSX повреждён или имеет неподдерживаемую структуру") from ошибка
    таблица: list[list[str]] = []
    for строка in корень.findall(f".//{ПРОСТРАНСТВО}sheetData/{ПРОСТРАНСТВО}row"):
        ячейки: dict[int, str] = {}
        for ячейка in строка.findall(f"{ПРОСТРАНСТВО}c"):
            адрес = ячейка.attrib.get("r", "")
            буквы = "".join(символ for символ in адрес if символ.isalpha())
            индекс = 0
            for буква in буквы.upper():
                индекс = индекс * 26 + ord(буква) - ord("A") + 1
            значение = ячейка.find(f"{ПРОСТРАНСТВО}v")
            текст = значение.text if значение is not None and значение.text else ""
            if ячейка.attrib.get("t") == "s" and текст:
                текст = строки_текста[int(текст)]
            elif ячейка.attrib.get("t") == "inlineStr":
                текст = "".join(
                    узел.text or "" for узел in ячейка.iter(f"{ПРОСТРАНСТВО}t")
                )
            if индекс:
                ячейки[индекс - 1] = текст
        if ячейки:
            таблица.append([ячейки.get(индекс, "") for индекс in range(max(ячейки) + 1)])
    if not таблица:
        raise ValueError("Товарный лист пуст")
    заголовки = таблица[0]
    # В экспорте Prom.ua встречаются пустые служебные столбцы.
    индексы: dict[str, int] = {}
    for индекс, имя in enumerate(заголовки):
        if имя and имя not in индексы:
            индексы[имя] = индекс
    return [
        {имя: значения[индекс] if индекс < len(значения) else ""
         for имя, индекс in индексы.items()}
        for значения in таблица[1:]
    ]


def проверить_макет(макет: Path, экспорт: Path) -> tuple[dict[str, str], list[str]]:
    """Проверить одну строку и отсутствие совпадений с экспортом."""
    строки = прочитать_строки(макет)
    if len(строки) != 1:
        raise ValueError(f"В макете должна быть одна строка, обнаружено: {len(строки)}")
    карточка = строки[0]
    каталог = прочитать_строки(экспорт)
    ошибки = []
    for ключ in КЛЮЧИ[:2]:
        значение = карточка.get(ключ, "").strip()

        if not значение:
            if ключ == "Код_товару":
                ошибки.append(f"Не заполнено поле {ключ}")
            continue

        if any(товар.get(ключ, "").strip() == значение for товар in каталог):
            ошибки.append(f"Совпадение в экспорте: {ключ}")
    return карточка, ошибки


def показать(макет: Path, экспорт: Path, консоль: Console | None = None) -> bool:
    """Показать локальную проверку без сетевых запросов."""
    вывод = консоль if консоль is not None else Console()
    заголовок(вывод, "Предпросмотр / одна тестовая карточка")
    try:
        карточка, ошибки = проверить_макет(макет, экспорт)
    except (ValueError, OSError, IndexError) as ошибка:
        сообщение(вывод, "ошибка", f"Проверка не выполнена: {ошибка}")
        return False
    таблица = таблица_параметров()
    for имя, значение in карточка.items():
        if значение:
            таблица.add_row(имя, значение[:120])
    вывод.print(таблица)
    for описание_ошибки in ошибки:
        сообщение(вывод, "ошибка", описание_ошибки)
    if not ошибки:
        сообщение(вывод, "успех", "Совпадений идентификаторов в экспорте нет")
    сообщение(вывод, "внимание", "Запись заблокирована: формат импорта не подтверждён")
    вывод.print("[dim]Режим локальной проверки · Запросов к API не было[/]")
    return not ошибки
