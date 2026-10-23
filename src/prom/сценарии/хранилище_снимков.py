"""Сохранение и сверка снимков каталога без операций изменения Prom.ua."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from rich.console import Console
from rich.table import Table

from prom.сценарии.сверка_каталога import Карточка, Сверка, Снимок, сопоставить
from prom.сценарии.чтение_каталога import получить_стабильный_снимок

ВЕРСИЯ = 1
Этап = Literal["до", "после"]


@dataclass(frozen=True)
class МетаданныеСнимка:
    операция: str
    этап: Этап
    создан_utc: str
    количество: int
    sha256: str


def _проверить_операцию(операция: str) -> None:
    if not 1 <= len(операция) <= 80 or not all(
        символ.isascii() and (символ.isalnum() or символ in "-_")
        for символ in операция
    ):
        raise ValueError("Ключ операции: только латинские буквы, цифры, '-' и '_', до 80 знаков")


def путь_снимка(каталог: Path, операция: str, этап: Этап) -> Path:
    """Возвращать безопасный путь, исключая произвольные имена файлов."""
    _проверить_операцию(операция)
    if этап not in ("до", "после"):
        raise ValueError("Недопустимый этап снимка")
    return каталог / f"{операция}_{этап}.json"


def _канонические_карточки(снимок: Снимок) -> list[dict[str, Any]]:
    if not снимок.полный:
        raise ValueError("Запрещено сохранять неполный снимок")
    номера = [карточка.идентификатор for карточка in снимок.карточки]
    if any(type(номер) is not int or номер <= 0 for номер in номера):
        raise ValueError("Некорректные идентификаторы карточек")
    if len(set(номера)) != len(номера):
        raise ValueError("Повторные идентификаторы карточек")
    return [
        asdict(карточка)
        for карточка in sorted(снимок.карточки, key=lambda элемент: элемент.идентификатор)
    ]


def _байты_json(значение: Any) -> bytes:
    return json.dumps(
        значение, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def сохранить_снимок(
    каталог: Path, операция: str, этап: Этап, снимок: Снимок,
) -> Path:
    """Создать новый снимок без перезаписи; синхронизировать файл и каталог."""
    путь = путь_снимка(каталог, операция, этап)
    карточки = _канонические_карточки(снимок)
    if not каталог.is_dir():
        raise FileNotFoundError("Каталог снимков должен существовать заранее")
    контрольная_сумма = hashlib.sha256(_байты_json(карточки)).hexdigest()
    документ = {
        "версия": ВЕРСИЯ,
        "операция": операция,
        "этап": этап,
        "создан_utc": datetime.now(UTC).isoformat(),
        "количество": len(карточки),
        "sha256": контрольная_сумма,
        "карточки": карточки,
    }
    временный: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=каталог, prefix=".снимок_", suffix=".tmp",
            delete=False,
        ) as файл:
            временный = файл.name
            os.chmod(временный, 0o600)
            файл.write(_байты_json(документ))
            файл.flush()
            os.fsync(файл.fileno())
        # Hard link атомарно создаёт целевой путь и не заменяет существующий.
        os.link(временный, путь)
        дескриптор = os.open(каталог, os.O_RDONLY)
        try:
            os.fsync(дескриптор)
        finally:
            os.close(дескриптор)
    finally:
        if временный is not None:
            Path(временный).unlink(missing_ok=True)
    return путь


def прочитать_снимок(
    каталог: Path, операция: str, этап: Этап,
) -> tuple[Снимок, МетаданныеСнимка]:
    """Проверить схему, принадлежность операции, SHA-256 и уникальность ID."""
    путь = путь_снимка(каталог, операция, этап)
    данные: Any = json.loads(путь.read_text(encoding="utf-8"))
    if not isinstance(данные, dict):
        raise TypeError("Повреждённый формат снимка")
    if данные.get("версия") != ВЕРСИЯ:
        raise ValueError("Неподдерживаемая версия снимка")
    if данные.get("операция") != операция or данные.get("этап") != этап:
        raise ValueError("Снимок относится к другой операции или этапу")
    строки = данные.get("карточки")
    if not isinstance(строки, list):
        raise TypeError("Карточки снимка должны быть списком")
    карточки: list[Карточка] = []
    for строка in строки:
        if not isinstance(строка, dict) or set(строка) != {
            "идентификатор", "артикул", "внешний_id", "вариация",
        }:
            raise ValueError("Некорректная схема карточки")
        идентификатор = строка["идентификатор"]
        if type(идентификатор) is not int or идентификатор <= 0:
            raise ValueError("Некорректный ID в снимке")
        if any(
            значение is not None and not isinstance(значение, str)
            for значение in (строка["артикул"], строка["внешний_id"])
        ):
            raise ValueError("Некорректный строковый атрибут карточки")
        if type(строка["вариация"]) is not bool:
            raise ValueError("Некорректный признак вариации")
        карточки.append(Карточка(**строка))
    снимок = Снимок(tuple(карточки), полный=True)
    канонические = _канонические_карточки(снимок)
    сумма = hashlib.sha256(_байты_json(канонические)).hexdigest()
    if данные.get("sha256") != сумма or данные.get("количество") != len(карточки):
        raise ValueError("Нарушена целостность снимка")
    if канонические != строки:
        raise ValueError("Нарушен порядок карточек")
    дата = данные.get("создан_utc")
    if not isinstance(дата, str):
        raise TypeError("Отсутствует время создания")
    try:
        момент = datetime.fromisoformat(дата)
    except ValueError as ошибка:
        raise ValueError("Некорректное время создания") from ошибка
    if момент.tzinfo is None or момент.utcoffset() is None:
        raise ValueError("Время должно содержать часовой пояс")
    метаданные = МетаданныеСнимка(операция, этап, дата, len(карточки), сумма)
    return снимок, метаданные


def сверить_сохранённые(каталог: Path, операция: str) -> Сверка:
    """Сопоставить два проверенных снимка, не изменяя магазин."""
    до, сведения_до = прочитать_снимок(каталог, операция, "до")
    после, сведения_после = прочитать_снимок(каталог, операция, "после")
    if datetime.fromisoformat(сведения_после.создан_utc) <= datetime.fromisoformat(
        сведения_до.создан_utc
    ):
        raise ValueError("Снимок 'после' не позднее снимка 'до'")
    return сопоставить(до, после)


def показать_сохранённую_сверку(
    каталог: Path, операция: str, *, консоль: Console | None = None,
) -> Сверка:
    """Rich-отчёт: только агрегаты и предупреждения, без данных карточек."""
    результат = сверить_сохранённые(каталог, операция)
    вывод = консоль if консоль is not None else Console()
    таблица = Table(title="PROM / сохранённая сверка каталога")
    таблица.add_column("Показатель")
    таблица.add_column("Количество", justify="right")
    таблица.add_row("Новые ID — кандидаты", str(len(результат.новые_id)))
    таблица.add_row("Исчезнувшие ID", str(len(результат.удалённые_id)))
    таблица.add_row("Изменённые ID", str(len(результат.изменённые_id)))
    таблица.add_row("Повторяющиеся SKU", str(len(результат.неоднозначные_sku)))
    таблица.add_row("Изменение товаров", "ЗАПРЕЩЕНО")
    вывод.print(таблица)
    for предупреждение in результат.предупреждения:
        вывод.print(f"[yellow]Внимание:[/yellow] {предупреждение}")
    return результат


def снять_и_сохранить(
    каталог: Path, операция: str, этап: Этап, *, консоль: Console | None = None,
) -> Path:
    """Два GET-прохода и запись снимка; никаких POST/PATCH."""
    путь = путь_снимка(каталог, операция, этап)
    if путь.exists():
        raise FileExistsError("Снимок уже существует")
    результат = получить_стабильный_снимок(консоль=консоль)
    if not результат.стабилен:
        raise RuntimeError("Каталог изменился между проходами; снимок не сохранён")
    return сохранить_снимок(каталог, операция, этап, результат.снимок)
