"""Неизменяемые настройки подключения."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class НастройкиПодключения:
    имя_переменной_токена: str
    таймаут_секунд: float = 10.0

    def __post_init__(self) -> None:
        if not self.имя_переменной_токена.strip():
            raise ValueError("Имя переменной токена не может быть пустым")
        if self.таймаут_секунд <= 0:
            raise ValueError("Таймаут должен быть положительным")
