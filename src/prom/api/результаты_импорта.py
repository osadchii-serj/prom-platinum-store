"""Проверка результата импорта и локальный журнал без записи в магазин."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

ИТОГОВЫЕ_СТАТУСЫ = frozenset({"SUCCESS", "PARTIAL", "FATAL"})
СЧЁТЧИКИ = (
    "not_changed", "updated", "not_in_file", "imported", "created",
    "actualized", "created_active", "created_hidden", "total",
    "with_errors_count",
)
КАТЕГОРИИ_ОШИБОК = (
    "download", "store_file", "validation", "import", "download_images",
)


@dataclass(frozen=True)
class РезультатИмпорта:
    """Нормализованный ответ статуса без сырых данных магазина."""

    статус: str
    завершён: bool
    счётчики: dict[str, int]
    категории_ошибок: tuple[str, ...]
    предупреждения: tuple[str, ...]

    @property
    def успешен(self) -> bool:
        return self.статус == "SUCCESS" and not self.предупреждения


def разобрать_статус(ответ: dict[str, Any]) -> РезультатИмпорта:
    """Не объявлять неизвестные состояния успешными или завершёнными."""
    статус = ответ.get("status")
    if not isinstance(статус, str) or not статус:
        raise ValueError("Ответ статуса не содержит строковое поле status")
    счётчики: dict[str, int] = {}
    for ключ in СЧЁТЧИКИ:
        значение = ответ.get(ключ)
        if значение is None:
            continue
        if isinstance(значение, bool) or not isinstance(значение, int) or значение < 0:
            raise ValueError(f"Некорректный счётчик: {ключ}")
        счётчики[ключ] = значение

    ошибки = ответ.get("errors", [])
    if not isinstance(ошибки, list):
        raise TypeError("Поле errors должно быть массивом")
    категории: set[str] = set()
    for ошибка in ошибки:
        if not isinstance(ошибка, dict):
            raise TypeError("Элемент errors должен быть объектом")
        for категория in КАТЕГОРИИ_ОШИБОК:
            if ошибка.get(категория):
                категории.add(категория)

    предупреждения: list[str] = []
    if статус not in ИТОГОВЫЕ_СТАТУСЫ:
        предупреждения.append("Неизвестный или промежуточный статус")
    if статус == "PARTIAL":
        предупреждения.append("Импорт завершился частично")
    if статус == "FATAL":
        предупреждения.append("Импорт завершился с критической ошибкой")
    if счётчики.get("with_errors_count", 0) > 0 or категории:
        предупреждения.append("В результате имеются ошибки")
    if (
        "created" in счётчики
        and all(ключ in счётчики for ключ in ("created_active", "created_hidden"))
        and счётчики["created_active"] + счётчики["created_hidden"] != счётчики["created"]
    ):
        предупреждения.append("Счётчики созданных товаров не согласованы")

    return РезультатИмпорта(
        статус=статус,
        завершён=статус in ИТОГОВЫЕ_СТАТУСЫ,
        счётчики=счётчики,
        категории_ошибок=tuple(sorted(категории)),
        предупреждения=tuple(предупреждения),
    )


Состояние = Literal["подготовлено", "запрос_отправлен", "неопределённо", "завершено"]


@dataclass(frozen=True)
class ЗаписьИмпорта:
    """Локальное состояние; идентификатор импорта может отсутствовать."""

    ключ: str
    источник: Literal["файл", "url"]
    состояние: Состояние
    идентификатор_импорта: str | None = None
    статус_api: str | None = None
    обновлено_utc: str = ""
    статус_http: int | None = None
    код_ошибки: str | None = None

    def __post_init__(self) -> None:
        if not self.ключ or "/" in self.ключ or "\\\\" in self.ключ:
            raise ValueError("Некорректный ключ операции")
        if self.состояние == "завершено" and self.статус_api not in ИТОГОВЫЕ_СТАТУСЫ:
            raise ValueError("Завершённая операция требует итогового статуса API")


def сохранить_запись(путь: Path, запись: ЗаписьИмпорта) -> None:
    """Атомарно сохранить локальную запись; каталог должен существовать."""
    if not путь.parent.is_dir():
        raise FileNotFoundError("Каталог журнала не существует")
    данные = asdict(запись)
    данные["обновлено_utc"] = datetime.now(UTC).isoformat()
    временный: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=путь.parent,
            prefix=".импорт_", suffix=".tmp", delete=False,
        ) as файл:
            временный = файл.name
            os.chmod(временный, 0o600)
            json.dump(данные, файл, ensure_ascii=False, indent=2)
            файл.flush()
            os.fsync(файл.fileno())
        os.replace(временный, путь)
    finally:
        if временный is not None and os.path.exists(временный):
            os.unlink(временный)


def прочитать_запись(путь: Path) -> ЗаписьИмпорта:
    """Прочитать состояние для ручной сверки и восстановления."""
    данные = json.loads(путь.read_text(encoding="utf-8"))
    if not isinstance(данные, dict):
        raise TypeError("Журнал операции должен быть объектом")
    return ЗаписьИмпорта(**данные)


def можно_повторить_импорт(запись: ЗаписьИмпорта) -> bool:
    """Повтор POST запрещён после возможной отправки запроса."""
    return запись.состояние == "подготовлено"
