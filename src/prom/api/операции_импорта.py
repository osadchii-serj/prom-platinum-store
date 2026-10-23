"""Контролируемые запросы импорта Prom.ua без автоматических повторов записи."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests

from prom.api.настройки import получить_токен

ОСНОВА = "https://my.prom.ua/api/v1/products"
РАСШИРЕНИЯ = {".xls", ".xlsx", ".csv", ".xml"}
ТИПЫ = {
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".xml": "application/xml",
}


@dataclass(frozen=True)
class НастройкиИмпорта:
    """Безопасные настройки: без массового обновления и скрытия отсутствующих."""

    force_update: bool = False
    only_available: bool = False
    only_update: bool = False
    mark_missing_product_as: str = "none"

    def данные(self) -> dict[str, bool | str]:
        return {
            "force_update": self.force_update,
            "only_available": self.only_available,
            "only_update": self.only_update,
            "mark_missing_product_as": self.mark_missing_product_as,
        }


@dataclass(frozen=True)
class КвитанцияИмпорта:
    """Подтверждение приёма запроса, не подтверждение создания товаров."""

    идентификатор: str | None
    статус: str | None


def _проверить_настройки(настройки: НастройкиИмпорта) -> None:
    if настройки.mark_missing_product_as != "none":
        raise ValueError("Изменение отсутствующих в импорте товаров запрещено на этом этапе")
    if настройки.force_update or настройки.only_update or настройки.only_available:
        raise ValueError("Нестандартные параметры импорта требуют отдельного сценария")


def _соединение() -> requests.Session:
    соединение = requests.Session()
    соединение.headers.update({"Authorization": f"Bearer {получить_токен('изменение')}"})
    return соединение


class ОшибкаЗапросаИмпорта(requests.HTTPError):
    """Отказ HTTP с безопасными метаданными, без тела ответа и токена."""

    def __init__(
        self,
        статус_http: int,
        код_ошибки: str | None,
        *,
        ответ: requests.Response | None = None,
    ) -> None:
        self.статус_http = статус_http
        self.код_ошибки = код_ошибки
        super().__init__(
            f"Prom.ua отклонил запрос импорта: HTTP {статус_http}", response=ответ
        )


def _безопасный_код(ответ: requests.Response) -> str | None:
    """Только короткий машинный код из белого списка полей JSON."""
    try:
        данные: Any = ответ.json()
    except (ValueError, requests.exceptions.RequestException):
        return None
    if not isinstance(данные, dict):
        return None
    for поле in ("code", "error_code"):
        значение = данные.get(поле)
        if (
            isinstance(значение, str)
            and 1 <= len(значение) <= 48
            and значение.isascii()
            and all(символ.isalnum() or символ == "_" for символ in значение)
        ):
            return значение
    return None


def _квитанция(ответ: requests.Response) -> КвитанцияИмпорта:
    if isinstance(ответ.status_code, int) and ответ.status_code >= 400:
        raise ОшибкаЗапросаИмпорта(
            ответ.status_code, _безопасный_код(ответ), ответ=ответ
        )
    ответ.raise_for_status()
    данные: Any = ответ.json()
    if not isinstance(данные, dict):
        raise TypeError("Ответ импорта не является объектом")
    идентификатор = данные.get("id")
    статус = данные.get("status")
    if идентификатор is not None and not isinstance(идентификатор, (str, int)):
        raise ValueError("Неизвестный формат идентификатора импорта")
    if статус is not None and not isinstance(статус, str):
        raise ValueError("Неизвестный формат статуса импорта")
    return КвитанцияИмпорта(
        str(идентификатор) if идентификатор is not None else None,
        статус,
    )


def импортировать_файл(
    путь: Path, *, настройки: НастройкиИмпорта | None = None, подтверждено: bool = False
) -> КвитанцияИмпорта:
    """Один POST; повтор после тайм-аута вручную только после сверки."""
    if not подтверждено:
        raise PermissionError("Запись заблокирована: требуется явное подтверждение")
    параметры = настройки or НастройкиИмпорта()
    _проверить_настройки(параметры)
    if not путь.is_file() or путь.suffix.lower() not in РАСШИРЕНИЯ:
        raise ValueError("Нужен существующий файл XLS, XLSX, CSV или XML")
    with _соединение() as соединение, путь.open("rb") as файл:
        ответ = соединение.post(
            f"{ОСНОВА}/import_file",
            files={"file": (путь.name, файл, ТИПЫ[путь.suffix.lower()])},
            data={"data": json.dumps(параметры.данные())},
            timeout=(10, 90),
        )
    return _квитанция(ответ)


def импортировать_url(
    адрес: str, *, настройки: НастройкиИмпорта | None = None, подтверждено: bool = False
) -> КвитанцияИмпорта:
    """Один POST URL-импорта; URL должен вести на HTTPS-ресурс."""
    if not подтверждено:
        raise PermissionError("Запись заблокирована: требуется явное подтверждение")
    параметры = настройки or НастройкиИмпорта()
    _проверить_настройки(параметры)
    части = urlsplit(адрес)
    if части.scheme != "https" or not части.hostname or части.username or части.password:
        raise ValueError("Требуется HTTPS URL без встроенных учётных данных")
    with _соединение() as соединение:
        ответ = соединение.post(
            f"{ОСНОВА}/import_url",
            json={"url": адрес, **параметры.данные()},
            timeout=(10, 90),
        )
    return _квитанция(ответ)


def получить_статус_импорта(идентификатор: int | str) -> dict[str, Any]:
    """Прочитать состояние импорта; не интерпретировать неизвестные статусы."""
    текст = str(идентификатор)
    if not текст.isascii() or not текст.isdecimal() or int(текст) <= 0:
        raise ValueError("Для status API нужен положительный числовой ID")
    with _соединение() as соединение:
        ответ = соединение.get(f"{ОСНОВА}/import/status/{int(текст)}", timeout=(10, 30))
    ответ.raise_for_status()
    данные: Any = ответ.json()
    if not isinstance(данные, dict):
        raise TypeError("Некорректный ответ статуса импорта")
    return данные
