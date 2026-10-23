"""Тесты инвентаризации без сетевых запросов."""
from unittest.mock import Mock

import pytest

from prom.сценарии.инвентаризация_магазина import инвентаризировать


def _сессия(товары):
    ответ = Mock()
    ответ.json.return_value = {"products": товары}
    соединение = Mock()
    соединение.get.return_value = ответ
    return соединение


def test_агрегаты_и_два_прохода():
    соединение = _сессия([
        {"id": 2, "is_variation": False, "status": "draft"},
        {"id": 1, "is_variation": True, "status": "on_display"},
    ])
    результат = инвентаризировать(сессия=соединение)
    assert (результат.всего, результат.основных, результат.разновидностей) == (2, 1, 1)
    assert результат.стабилен
    assert соединение.get.call_count == 2
    assert all(вызов.kwargs["timeout"] == 30 for вызов in соединение.get.call_args_list)


def test_дубли_запрещены():
    соединение = _сессия([{"id": 1}, {"id": 1}])
    with pytest.raises(ValueError, match="Повтор ID"):
        инвентаризировать(сессия=соединение)


def test_неверный_формат_запрещён():
    соединение = _сессия([{"id": 1, "is_variation": "yes"}])
    with pytest.raises(TypeError, match="is_variation"):
        инвентаризировать(сессия=соединение)


def test_изменение_между_проходами():
    первый = Mock()
    первый.json.return_value = {"products": [{"id": 1}]}
    второй = Mock()
    второй.json.return_value = {"products": [{"id": 2}]}
    соединение = Mock()
    соединение.get.side_effect = [первый, второй]
    assert not инвентаризировать(сессия=соединение).стабилен
