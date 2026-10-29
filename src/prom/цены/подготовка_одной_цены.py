"""Подготовка одной цены: без операций записи."""

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from prom.цены.массовое_обновление_цен import МассовоеОбновлениеЦен


class _Источник:
    def __init__(self, карточка: Mapping[str, Any]):
        self.карточка = карточка

    def страницы_товаров(self):
        yield [self.карточка]


def подготовить_одну_цену(карточка: Mapping[str, Any], процент: Decimal):
    """Использовать утверждённый расчёт, без отправки изменений."""
    план = МассовоеОбновлениеЦен(_Источник(карточка), процент).подготовить_изменения()
    if len(план.изменения) != 1:
        raise ValueError(план.пропуски[0].причина if план.пропуски else "Нет изменения")
    изменение = план.изменения[0]
    if изменение.старая_цена == изменение.новая_цена:
        raise ValueError("Цена не меняется")
    return изменение


def сверить_цену(изменение, карточка: Mapping[str, Any]) -> bool:
    if (
        карточка.get("id") != изменение.идентификатор
        or карточка.get("currency") != изменение.валюта
    ):
        return False
    try:
        цена = Decimal(str(карточка["price"]))
    except (KeyError, ValueError, ArithmeticError):
        return False
    return цена.is_finite() and цена == изменение.новая_цена
