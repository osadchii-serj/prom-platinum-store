"""Безопасная проверка доступа к Prom.ua API."""

import httpx

from prom.подключения.интерфейсы import (
    ИнтерфейсХранилищаТокенов,
    РезультатПодключения,
)
from prom.подключения.настройки import НастройкиПодключения


class ПодключениеProm:
    АДРЕС_ПРОВЕРКИ = "https://my.prom.ua/api/v1/products/list"

    def __init__(
        self,
        настройки: НастройкиПодключения,
        хранилище: ИнтерфейсХранилищаТокенов,
        транспорт: httpx.BaseTransport | None = None,
    ) -> None:
        self.настройки = настройки
        self.хранилище = хранилище
        self._транспорт = транспорт

    def проверить(self) -> РезультатПодключения:
        try:
            токен = self.хранилище.получить(self.настройки.имя_переменной_токена)
        except ValueError:
            return РезультатПодключения(False, "Токен отсутствует или не настроен")

        try:
            with httpx.Client(
                timeout=self.настройки.таймаут_секунд,
                transport=self._транспорт,
                follow_redirects=False,
                trust_env=False,
            ) as клиент:
                ответ = клиент.get(
                    self.АДРЕС_ПРОВЕРКИ,
                    params={"limit": 5},
                    headers={"Authorization": f"Bearer {токен}"},
                )
        except httpx.TimeoutException:
            return РезультатПодключения(False, "Превышено время ожидания Prom.ua")
        except httpx.RequestError:
            return РезультатПодключения(False, "Ошибка сети при обращении к Prom.ua")

        if ответ.status_code == 200:
            try:
                данные = ответ.json()
            except ValueError:
                return РезультатПодключения(False, "Ответ API не является JSON", 200)
            if not isinstance(данные, dict) or not isinstance(данные.get("products"), list):
                return РезультатПодключения(False, "Неожиданная структура ответа API", 200)
            return РезультатПодключения(True, "Подключение подтверждено", 200)
        if ответ.status_code in (401, 403):
            return РезультатПодключения(
                False, "Нет доступа: проверьте токен и его права", ответ.status_code
            )
        return РезультатПодключения(False, "API вернул ошибку HTTP", ответ.status_code)
