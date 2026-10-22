"""Проверки постраничного чтения и поиска совпадений без реального API."""

from unittest.mock import Mock, patch

import pytest

from prom.api.проверка_тестовой_карточки import сверить_с_api


@patch("prom.api.проверка_тестовой_карточки.получить_токен", return_value="заглушка")
@patch("prom.api.проверка_тестовой_карточки.requests.Session")
def test_совпадение_артикула(сеанс: Mock, _токен: Mock) -> None:
    ответы = [Mock(), Mock()]
    ответы[0].json.return_value = {"products": [{"id": 12, "sku": "TEST", "external_id": ""}]}
    ответы[1].json.return_value = {"products": []}
    клиент = сеанс.return_value.__enter__.return_value
    клиент.get.side_effect = ответы
    итог = сверить_с_api({"Код_товару": "TEST", "Унікальний_ідентифікатор": "X"})
    assert итог.просмотрено == 1
    assert итог.совпадения == (12,)
    assert клиент.get.call_count == 1


def test_пустые_идентификаторы() -> None:
    with pytest.raises(ValueError, match="Отсутствует"):
        сверить_с_api({"Код_товару": "", "Унікальний_ідентифікатор": "X"})


@patch("prom.api.проверка_тестовой_карточки.получить_токен", return_value="заглушка")
@patch("prom.api.проверка_тестовой_карточки.requests.Session")
def test_пустой_внешний_id_допустим(сеанс: Mock, _токен: Mock) -> None:
    ответ = Mock()
    ответ.json.return_value = {"products": [{"id": 42, "sku": "TEST", "external_id": ""}]}
    клиент = сеанс.return_value.__enter__.return_value
    клиент.get.return_value = ответ
    итог = сверить_с_api({"Код_товару": "TEST", "Унікальний_ідентифікатор": ""})
    assert итог.совпадения == (42,)


@patch("prom.api.проверка_тестовой_карточки.получить_токен", return_value="заглушка")
@patch("prom.api.проверка_тестовой_карточки.requests.Session")
def test_пустой_внешний_id_не_совпадает_с_чужим(сеанс: Mock, _токен: Mock) -> None:
    ответ = Mock()
    ответ.json.return_value = {"products": [{"id": 42, "sku": "OTHER", "external_id": ""}]}
    клиент = сеанс.return_value.__enter__.return_value
    клиент.get.return_value = ответ
    итог = сверить_с_api({"Код_товару": "TEST", "Унікальний_ідентифікатор": ""})
    assert итог.совпадения == ()
