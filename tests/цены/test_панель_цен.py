"""Проверки консольного отчёта без доступа к Prom.ua."""

from decimal import Decimal
from io import StringIO

import pytest
from rich.console import Console

from prom.цены.массовое_обновление_цен import ИзменениеЦены, ПланЦен, ПропускТовара
from prom.цены.предпросмотр_цен import показать_план


def test_показатели_и_динамический_процент():
    поток = StringIO()
    консоль = Console(file=поток, force_terminal=False, width=110)
    план = ПланЦен(
        (ИзменениеЦены(123, "Товар", "UAH", Decimal(100), Decimal(130)),),
        (ПропускТовара(124, "Нет цены"),),
        2,
    )
    показать_план(план, консоль, процент=Decimal(30))
    текст = поток.getvalue()
    assert "30%" in текст
    assert "130.00" in текст
    assert "100.00" in текст
    assert "SKIP" in текст
    assert "DRY RUN" in текст
    assert "20%" not in текст


def test_пустой_план():
    поток = StringIO()
    показать_план(ПланЦен((), (), 0), Console(file=поток, width=110), процент=Decimal(0))
    assert "0%" in поток.getvalue()


def test_некорректное_число_строк():
    with pytest.raises(ValueError):
        показать_план(ПланЦен((), (), 0), Console(file=StringIO()), максимум_строк=-1)
