"""Сохранённое подтверждение локального предпросмотра XLSX без сетевых запросов."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from prom.сценарии.предпросмотр_массового_импорта import проверить_файл


@dataclass(frozen=True)
class ПланФайловогоИмпорта:
    """Утверждённый снимок параметров конкретной локальной операции."""

    ключ_операции: str
    ключ_снимка: str
    sha256: str
    количество: int
    уникальных_артикулов: int
    пересечений: int
    разрешено: bool


def создать_план(
    файл: Path,
    каталог_снимков: Path,
    ключ_снимка: str,
    ключ_операции: str,
    количество: int,
) -> ПланФайловогоИмпорта:
    """Повторно выполнить предпросмотр; создание плана не разрешает POST."""
    if not ключ_операции or not ключ_операции.isascii() or not all(
        символ.isalnum() or символ in "_-" for символ in ключ_операции
    ):
        raise ValueError("Некорректный ключ операции")
    итог = проверить_файл(
        файл, каталог_снимков, ключ_снимка, количество_ожидаемое=количество
    )
    if итог.пересечений or итог.количество != количество:
        raise ValueError("Предпросмотр не допускает утверждение")
    return ПланФайловогоИмпорта(
        ключ_операции, ключ_снимка, итог.sha256, итог.количество,
        итог.уникальных_артикулов, итог.пересечений, False,
    )


def сохранить_план(путь: Path, план: ПланФайловогоИмпорта) -> None:
    """Создать план один раз: не перезаписывать существующее подтверждение."""
    if not путь.parent.is_dir():
        raise FileNotFoundError("Каталог плана не существует")
    данные = json.dumps(asdict(план), ensure_ascii=False, indent=2).encode()
    временный: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=путь.parent, prefix=".план_", suffix=".tmp", delete=False
        ) as файл:
            временный = файл.name
            os.chmod(временный, 0o600)
            файл.write(данные)
            файл.flush()
            os.fsync(файл.fileno())
        # Эксклюзивное создание: не заменить уже утверждённый план.
        os.link(временный, путь)
    finally:
        if временный is not None:
            Path(временный).unlink(missing_ok=True)


def прочитать_план(путь: Path) -> ПланФайловогоИмпорта:
    """Отвергать посторонние поля и некорректные типы без выполнения POST."""
    данные = json.loads(путь.read_text(encoding="utf-8"))
    if not isinstance(данные, dict):
        raise TypeError("Некорректный формат плана")
    план = ПланФайловогоИмпорта(**данные)
    if (
        not isinstance(план.ключ_операции, str)
        or not isinstance(план.ключ_снимка, str)
        or not isinstance(план.sha256, str)
        or len(план.sha256) != 64
        or any(символ not in "0123456789abcdef" for символ in план.sha256)
        or type(план.количество) is not int
        or not 1 <= план.количество <= 500
        or type(план.уникальных_артикулов) is not int
        or план.уникальных_артикулов != план.количество
        or type(план.пересечений) is not int
        or план.пересечений != 0
        or type(план.разрешено) is not bool
    ):
        raise ValueError("Недопустимые данные плана")
    return план


def утвердить_план(путь: Path, ключ: str, подтверждение: str) -> None:
    """Явное утверждение не вызывает API и не отправляет товары."""
    план = прочитать_план(путь)
    if план.ключ_операции != ключ or подтверждение != f"УТВЕРДИТЬ {ключ}":
        raise PermissionError("Подтверждение плана не совпало")
    if план.разрешено:
        raise RuntimeError("План уже утверждён")
    # Обновление существующего файла атомарно; доступ к каталогу ограничивает доверие.
    данные = json.dumps(asdict(ПланФайловогоИмпорта(
        план.ключ_операции, план.ключ_снимка, план.sha256, план.количество,
        план.уникальных_артикулов, план.пересечений, True,
    )), ensure_ascii=False, indent=2).encode()
    временный: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=путь.parent, prefix=".план_", suffix=".tmp", delete=False
        ) as файл:
            временный = файл.name
            os.chmod(временный, 0o600)
            файл.write(данные)
            файл.flush()
            os.fsync(файл.fileno())
        os.replace(временный, путь)
    finally:
        if временный is not None:
            Path(временный).unlink(missing_ok=True)


def проверить_утверждение(путь: Path, файл: Path, ключ: str, хеш: str) -> None:
    """Сверить утверждённый план с операцией и байтами файла."""
    план = прочитать_план(путь)
    if not план.разрешено:
        raise PermissionError("План не утверждён")
    if план.ключ_операции != ключ or план.sha256 != хеш:
        raise PermissionError("План не соответствует операции или SHA-256")
    if hashlib.sha256(файл.read_bytes()).hexdigest() != план.sha256:
        raise ValueError("XLSX изменился после утверждения")
