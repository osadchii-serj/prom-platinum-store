"""Контракты подключений и доступа к секретам."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class РезультатПодключения:
    успешно: bool
    сообщение: str
    код_http: int | None = None


class ИнтерфейсПодключения(Protocol):
    def проверить(self) -> РезультатПодключения: ...


class ИнтерфейсХранилищаТокенов(Protocol):
    def получить(self, имя_переменной: str) -> str: ...
