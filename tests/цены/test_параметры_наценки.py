"""Тесты разбора процента без динамического выполнения кода."""

import pytest

from prom.цены.параметры_наценки import разобрать_процент


@pytest.mark.parametrize(
    ("ввод", "ожидаемое"),
    [("20", "20"), ("12,5", "12.5"), ("0", "0"), (" 2.25 ", "2.25")],
)
def test_корректный_процент(ввод: str, ожидаемое: str) -> None:
    assert str(разобрать_процент(ввод)) == ожидаемое


@pytest.mark.parametrize("ввод", ["-1", "NaN", "Infinity", "", "abc"])
def test_ошибочный_процент(ввод: str) -> None:
    with pytest.raises(ValueError):
        разобрать_процент(ввод)
