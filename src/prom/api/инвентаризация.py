"""Инвентаризация публичной спецификации Prom.ua без запросов к магазину."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
import yaml
from rich.console import Console
from rich.table import Table

АДРЕС_СПЕЦИФИКАЦИИ = "https://public-api.docs.prom.ua/documentation/index.yaml"
РАЗРЕШЁННЫЙ_ХОСТ = "public-api.docs.prom.ua"
МЕТОДЫ = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "trace"})
МАКСИМУМ_ФАЙЛОВ = 250
МАКСИМУМ_БАЙТ = 2_000_000


@dataclass(frozen=True)
class Операция:
    метод: str
    путь: str
    раздел: str
    описание: str
    идентификатор: str


def проверить_адрес(адрес: str) -> None:
    части = urlparse(адрес)
    if (
        части.scheme != "https"
        or части.hostname != РАЗРЕШЁННЫЙ_ХОСТ
        or части.port not in (None, 443)
    ):
        raise ValueError(f"Запрещён адрес спецификации: {адрес}")
    if части.username or части.password:
        raise ValueError("Адрес с учётными данными запрещён")


def загрузить_документы(адрес: str = АДРЕС_СПЕЦИФИКАЦИИ) -> dict[str, dict]:
    """Загрузить документы по внешним $ref; фрагменты # не создают сетевых запросов."""
    проверить_адрес(адрес)
    очередь = [urldefrag(адрес).url]
    документы: dict[str, dict] = {}
    with requests.Session() as сессия:
        while очередь:
            текущий = очередь.pop(0)
            if текущий in документы:
                continue
            проверить_адрес(текущий)
            if len(документы) >= МАКСИМУМ_ФАЙЛОВ:
                raise ValueError("Превышен лимит количества файлов спецификации")
            ответ = сессия.get(текущий, timeout=20, allow_redirects=False)
            ответ.raise_for_status()
            if len(ответ.content) > МАКСИМУМ_БАЙТ:
                raise ValueError(f"Слишком большой файл: {текущий}")
            данные = yaml.safe_load(ответ.content)
            if not isinstance(данные, dict):
                raise TypeError(f"Ожидался YAML-объект: {текущий}")
            документы[текущий] = данные
            for ссылка in найти_ссылки(данные):
                целевой = urldefrag(urljoin(текущий, ссылка)).url
                if целевой == текущий:
                    continue
                проверить_адрес(целевой)
                if целевой not in документы and целевой not in очередь:
                    очередь.append(целевой)
    return документы


def найти_ссылки(узел: object) -> list[str]:
    if isinstance(узел, dict):
        ссылки = []
        for ключ, значение in узел.items():
            if ключ == "$ref" and isinstance(значение, str):
                ссылки.append(значение)
            else:
                ссылки.extend(найти_ссылки(значение))
        return ссылки
    if isinstance(узел, list):
        return [ссылка for элемент in узел for ссылка in найти_ссылки(элемент)]
    return []


def разрешить_ссылку(узел: dict, базовый_адрес: str, документы: dict[str, dict]) -> tuple[dict, str]:
    """Разрешить внешние и локальные ссылки на путь или операцию."""
    посещённые: set[str] = set()
    while "$ref" in узел:
        ссылка = узел["$ref"]
        полный_адрес = urljoin(базовый_адрес, ссылка)
        if полный_адрес in посещённые:
            raise ValueError(f"Циклическая ссылка: {полный_адрес}")
        посещённые.add(полный_адрес)
        файл, фрагмент = urldefrag(полный_адрес)
        проверить_адрес(файл)
        узел = документы[файл]
        if фрагмент:
            if not фрагмент.startswith("/"):
                raise ValueError(f"Некорректный JSON Pointer: {полный_адрес}")
            for часть in фрагмент[1:].split("/"):
                часть = часть.replace("~1", "/").replace("~0", "~")
                узел = узел[часть]
        if not isinstance(узел, dict):
            raise TypeError(f"Ссылка не указывает на объект: {полный_адрес}")
        базовый_адрес = файл
    return узел, базовый_адрес


def получить_операции(
    документы: dict[str, dict], адрес: str = АДРЕС_СПЕЦИФИКАЦИИ
) -> list[Операция]:
    корень = документы[urldefrag(адрес).url]
    пути = корень.get("paths", {})
    if not isinstance(пути, dict):
        raise TypeError("Поле paths должно быть объектом")
    операции = []
    for путь, описание_пути in пути.items():
        if not isinstance(описание_пути, dict):
            continue
        описание_пути, адрес_пути = разрешить_ссылку(описание_пути, адрес, документы)
        for метод, значение in описание_пути.items():
            if метод.lower() not in МЕТОДЫ or not isinstance(значение, dict):
                continue
            операция, _ = разрешить_ссылку(значение, адрес_пути, документы)
            теги = операция.get("tags", [])
            операции.append(
                Операция(
                    метод=метод.upper(),
                    путь=путь,
                    раздел=str(теги[0]) if теги else "Без раздела",
                    описание=str(операция.get("summary", "")).replace("|", "\\|"),
                    идентификатор=str(операция.get("operationId", "")),
                )
            )
    return sorted(операции, key=lambda элемент: (элемент.раздел, элемент.путь, элемент.метод))


def сформировать_отчёт(операции: list[Операция], документы: dict[str, dict]) -> str:
    строки = [
        "# Реестр Prom.ua Public API",
        "",
        f"Источник: {АДРЕС_СПЕЦИФИКАЦИИ}",
        "",
        f"Документов YAML: **{len(документы)}**. Операций: **{len(операции)}**.",
        "",
        "Реестр составлен по документации; доступность методов для токена не проверена.",
        "GET/HEAD/OPTIONS потенциально читают данные; эффекты остальных методов требуют проверки.",
        "",
        "| Раздел | Метод | Путь | Описание | operationId |",
        "|---|---|---|---|---|",
    ]
    for операция in операции:
        поля = (
            операция.раздел, операция.метод, операция.путь,
            операция.описание, операция.идентификатор,
        )
        значения = [поле.replace("|", "\\|").replace("\n", " ") for поле in поля]
        строки.append("| " + " | ".join(значения) + " |")
    return "\n".join(строки) + "\n"


def показать_сводку(операции: list[Операция], количество_документов: int) -> None:
    консоль = Console()
    консоль.print(f"YAML-файлов: {количество_документов}; операций: {len(операции)}")
    таблица = Table(title="Методы Prom.ua API")
    таблица.add_column("Метод")
    таблица.add_column("Количество", justify="right")
    счётчик = Counter(операция.метод for операция in операции)
    for метод, количество in sorted(счётчик.items()):
        таблица.add_row(метод, str(количество))
    консоль.print(таблица)


def выполнить(путь_отчёта: Path) -> None:
    документы = загрузить_документы()
    операции = получить_операции(документы)
    if not операции:
        raise ValueError("В спецификации не найдены операции; отчёт не создан")
    путь_отчёта.parent.mkdir(parents=True, exist_ok=True)
    путь_отчёта.write_text(сформировать_отчёт(операции, документы), encoding="utf-8")
    показать_сводку(операции, len(документы))
    Console().print(f"Отчёт: {путь_отчёта}")
