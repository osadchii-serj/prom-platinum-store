"""Безопасная подготовка плана повышения розничных цен Prom.ua."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Protocol


class ИсточникТоваров(Protocol):
    """Постраничный источник; реализация API остаётся отдельным компонентом."""

    def страницы_товаров(self) -> Iterable[list[Mapping[str, Any]]]: ...


@dataclass(frozen=True)
class ИзменениеЦены:
    идентификатор: int
    название: str
    валюта: str
    старая_цена: Decimal
    новая_цена: Decimal


@dataclass(frozen=True)
class ПропускТовара:
    идентификатор: object
    причина: str


@dataclass(frozen=True)
class ПланЦен:
    изменения: tuple[ИзменениеЦены, ...]
    пропуски: tuple[ПропускТовара, ...]
    просмотрено: int


class МассовоеОбновлениеЦен:
    """Формирует план; не содержит методов записи в Prom.ua."""

    def __init__(self, источник: ИсточникТоваров, процент: Decimal = Decimal(20)) -> None:
        if not процент.is_finite() or процент < 0:
            raise ValueError("Процент должен быть конечным неотрицательным числом")
        self.источник = источник
        self.процент = процент

    def подготовить_изменения(self) -> ПланЦен:
        изменения: list[ИзменениеЦены] = []
        пропуски: list[ПропускТовара] = []
        увиденные: set[int] = set()
        просмотрено = 0
        коэффициент = Decimal(1) + self.процент / Decimal(100)

        for страница in self.источник.страницы_товаров():
            for товар in страница:
                просмотрено += 1
                идентификатор = товар.get("id")
                if type(идентификатор) is not int or идентификатор <= 0:
                    пропуски.append(ПропускТовара(идентификатор, "Некорректный id"))
                    continue
                if идентификатор in увиденные:
                    пропуски.append(ПропускТовара(идентификатор, "Повторный id"))
                    continue
                увиденные.add(идентификатор)
                значение = товар.get("price")
                if isinstance(значение, bool) or значение is None:
                    пропуски.append(
                        ПропускТовара(идентификатор, "Цена отсутствует или некорректна")
                    )
                    continue
                try:
                    цена = Decimal(str(значение))
                except (InvalidOperation, ValueError):
                    пропуски.append(ПропускТовара(идентификатор, "Цена не является числом"))
                    continue
                if not цена.is_finite() or цена <= 0:
                    пропуски.append(ПропускТовара(идентификатор, "Цена должна быть положительной"))
                    continue
                валюта = товар.get("currency")
                if валюта != "UAH":
                    пропуски.append(ПропускТовара(идентификатор, "Валюта не UAH"))
                    continue
                новая = (цена * коэффициент).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if новая <= 0:
                    пропуски.append(ПропускТовара(идентификатор, "Новая цена недопустима"))
                    continue
                изменения.append(
                    ИзменениеЦены(
                        идентификатор,
                        str(товар.get("name") or ""),
                        валюта,
                        цена,
                        новая,
                    )
                )

        return ПланЦен(tuple(изменения), tuple(пропуски), просмотрено)
