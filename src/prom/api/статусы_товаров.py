"""Контракт и проверяемые операции изменения статусов товаров Prom.ua.

Модуль не содержит массовых операций, автоматических повторов и CLI.
Сетевой запрос выполняется только при явном вызове ``изменить_статус``.
"""

from __future__ import annotations

from typing import Any, Literal

import requests

Статус = Literal["on_display", "draft", "not_on_display", "deleted"]
АДРЕС_API = "https://my.prom.ua/api/v1"
ПОДТВЕРЖДЁННЫЕ_ПЕРЕХОДЫ: frozenset[tuple[str, str]] = frozenset(
    {
        ("on_display", "draft"),
        ("draft", "on_display"),
        ("draft", "not_on_display"),
        ("not_on_display", "draft"),
        ("draft", "deleted"),
        ("not_on_display", "deleted"),
        ("deleted", "not_on_display"),
    }
)


class НеопределённыйРезультат(RuntimeError):
    """POST мог быть обработан; повторять его автоматически запрещено."""


def проверить_переход(исходный: str, целевой: str) -> None:
    """Разрешить только переходы, проверенные на тестовой карточке."""
    if (исходный, целевой) not in ПОДТВЕРЖДЁННЫЕ_ПЕРЕХОДЫ:
        raise ValueError(f"Переход не подтверждён испытаниями: {исходный} → {целевой}")


def проверить_товар(данные: Any, идентификатор: int, артикул: str, статус: str) -> None:
    """Проверить ID, SKU и статус ответа GET /products/{id}."""
    if not isinstance(данные, dict) or not isinstance(данные.get("product"), dict):
        raise TypeError("GET не содержит объект product")
    товар = данные["product"]
    if (товар.get("id"), товар.get("sku"), товар.get("status")) != (
        идентификатор,
        артикул,
        статус,
    ):
        raise ValueError("GET не подтвердил ID, SKU и статус")


def проверить_ответ(данные: Any, идентификатор: int) -> None:
    """HTTP 200 не означает успех: необходим точный processed_ids без ошибок."""
    if not isinstance(данные, dict):
        raise TypeError("Ответ POST не является объектом")
    if данные.get("processed_ids") != [идентификатор] or данные.get("errors"):
        raise ValueError("POST не подтвердил обработку единственного ID без ошибок")


def подготовить_запрос(
    идентификатор: int, исходный: str, целевой: Статус
) -> list[dict[str, int | str]]:
    """Подготовить единственный товар; никаких запросов к сети."""
    if isinstance(идентификатор, bool) or not isinstance(идентификатор, int) or идентификатор <= 0:
        raise ValueError("Требуется положительный числовой ID")
    проверить_переход(исходный, целевой)
    return [{"id": идентификатор, "status": целевой}]


def изменить_статус(
    соединение: requests.Session,
    *,
    идентификатор: int,
    исходный: str,
    целевой: Статус,
    токен_записи: str,
    подтверждено: bool = False,
) -> None:
    """Выполнить ровно один POST по явному подтверждению вызывающего кода.

    Предварительная GET-сверка и последующая сверка состояния обязательны
    для вызывающего сценария; этот метод подтверждает только ответ POST.
    """
    тело = подготовить_запрос(идентификатор, исходный, целевой)
    if not подтверждено:
        raise PermissionError("POST требует явного подтверждения")
    if not токен_записи:
        raise ValueError("Не указан токен записи")
    try:
        ответ = соединение.post(
            f"{АДРЕС_API}/products/edit",
            headers={"Authorization": f"Bearer {токен_записи}", "Accept": "application/json"},
            json=тело,
            timeout=20,
        )
        ответ.raise_for_status()
        проверить_ответ(ответ.json(), идентификатор)
    except (requests.RequestException, ValueError, TypeError) as ошибка:
        raise НеопределённыйРезультат(
            "Результат POST не подтверждён; не повторяйте запрос без независимой сверки"
        ) from ошибка
