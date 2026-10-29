from decimal import Decimal

import pytest

from prom.цены.подготовка_одной_цены import подготовить_одну_цену, сверить_цену


def test_расчёт_и_сверка():
    изменение = подготовить_одну_цену({"id": 42, "price": 100, "currency": "UAH"}, Decimal(20))
    assert изменение.новая_цена == Decimal("120.00")
    assert сверить_цену(изменение, {"id": 42, "price": 120, "currency": "UAH"})
    assert not сверить_цену(изменение, {"id": 42, "price": 100, "currency": "UAH"})


@pytest.mark.parametrize("цена,валюта", [(None, "UAH"), (0, "UAH"), (100, "USD")])
def test_отклонение(цена, валюта):
    with pytest.raises(ValueError):
        подготовить_одну_цену({"id": 42, "price": цена, "currency": валюта}, Decimal(20))
