"""Локальные тесты контракта статусов; без реальных запросов к Prom.ua."""

from unittest.mock import Mock

import pytest

from prom.api.статусы_товаров import (
    НеопределённыйРезультат,
    изменить_статус,
    подготовить_запрос,
    проверить_ответ,
    проверить_товар,
)

ИД = 3243922294
SKU = "PROM-TEST-20261022-001"


@pytest.mark.parametrize("начало,конец", [
    ("draft", "deleted"),
    ("not_on_display", "deleted"),
    ("deleted", "not_on_display"),
    ("on_display", "draft"),
    ("draft", "on_display"),
    ("draft", "not_on_display"),
    ("not_on_display", "draft"),
])
def test_подтверждённые_переходы(начало: str, конец: str) -> None:
    assert подготовить_запрос(ИД, начало, конец) == [{"id": ИД, "status": конец}]


@pytest.mark.parametrize("начало,конец", [
    ("deleted", "draft"), ("deleted", "on_display"), ("on_display", "deleted"),
])
def test_неисследованные_переходы_запрещены(начало: str, конец: str) -> None:
    with pytest.raises(ValueError):
        подготовить_запрос(ИД, начало, конец)  # type: ignore[arg-type]


def test_ответ_проверяется_по_id() -> None:
    проверить_ответ({"processed_ids": [ИД], "errors": {}}, ИД)
    with pytest.raises(ValueError):
        проверить_ответ({"processed_ids": [], "errors": {}}, ИД)
    with pytest.raises(ValueError):
        проверить_ответ({"processed_ids": [ИД], "errors": {str(ИД): "ошибка"}}, ИД)


def test_сверка_get() -> None:
    проверить_товар({"product": {"id": ИД, "sku": SKU, "status": "not_on_display"}},
                    ИД, SKU, "not_on_display")
    with pytest.raises(ValueError):
        проверить_товар({"product": {"id": ИД, "sku": "OTHER", "status": "not_on_display"}},
                        ИД, SKU, "not_on_display")


def test_без_подтверждения_нет_post() -> None:
    соединение = Mock()
    with pytest.raises(PermissionError):
        изменить_статус(соединение, идентификатор=ИД, исходный="deleted",
                        целевой="not_on_display", токен_записи="тест")
    соединение.post.assert_not_called()


def test_ровно_один_post() -> None:
    соединение = Mock()
    соединение.post.return_value.json.return_value = {"processed_ids": [ИД], "errors": {}}
    изменить_статус(соединение, идентификатор=ИД, исходный="deleted",
                    целевой="not_on_display", токен_записи="тест", подтверждено=True)
    соединение.post.assert_called_once()
    assert соединение.post.call_args.kwargs["json"] == [{"id": ИД, "status": "not_on_display"}]


def test_ошибка_без_повтора() -> None:
    соединение = Mock()
    соединение.post.side_effect = __import__("requests").Timeout("тайм-аут")
    with pytest.raises(НеопределённыйРезультат):
        изменить_статус(соединение, идентификатор=ИД, исходный="draft",
                        целевой="deleted", токен_записи="тест", подтверждено=True)
    соединение.post.assert_called_once()
