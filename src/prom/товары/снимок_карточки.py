"""Безопасное чтение и сохранение исходной карточки Prom.ua."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

ИДЕНТИФИКАТОР_ТЕСТОВОГО_ТОВАРА = 3253021850
АДРЕС_API = "https://my.prom.ua/api/v1"
КАТАЛОГ_СНИМКОВ = Path("data/исследование_товаров/снимки")


def получить_карточку(
    токен: str,
    идентификатор: int = ИДЕНТИФИКАТОР_ТЕСТОВОГО_ТОВАРА,
) -> dict[str, Any]:
    """Получить карточку без операций изменения."""
    if идентификатор != ИДЕНТИФИКАТОР_ТЕСТОВОГО_ТОВАРА:
        raise ValueError("Разрешено исследовать только утверждённую тестовую карточку")

    with httpx.Client(timeout=20.0, follow_redirects=False) as клиент:
        ответ = клиент.get(
            f"{АДРЕС_API}/products/{идентификатор}",
            headers={
                "Authorization": f"Bearer {токен}",
                "Accept": "application/json",
            },
        )
        ответ.raise_for_status()
        данные = ответ.json()

    if not isinstance(данные, dict):
        raise TypeError("API вернул не JSON-объект")

    товар = данные.get("product", данные)
    if (
        not isinstance(товар, dict)
        or type(товар.get("id")) is not int
        or товар["id"] != идентификатор
    ):
        raise ValueError("Не удалось подтвердить идентификатор полученного товара")

    return данные


def сохранить_снимок(
    данные: dict[str, Any],
    каталог: Path = КАТАЛОГ_СНИМКОВ,
) -> Path:
    """Сохранить уникальный неизменяемый снимок; существующие файлы не перезаписывать."""
    товар = данные.get("product", данные)

    if not isinstance(товар, dict) or товар.get("id") != ИДЕНТИФИКАТОР_ТЕСТОВОГО_ТОВАРА:
        raise ValueError("Снимок не соответствует тестовому товару")

    каталог.mkdir(parents=True, exist_ok=True, mode=0o700)

    метка = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    путь = каталог / f"карточка_{ИДЕНТИФИКАТОР_ТЕСТОВОГО_ТОВАРА}_{метка}.json"

    содержимое = (
        json.dumps(
            данные,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )

    with путь.open("x", encoding="utf-8") as файл:
        os.chmod(путь, 0o600)
        файл.write(содержимое)

    return путь


def main() -> None:
    """Выполнить одну операцию чтения и показать путь сохранённого снимка."""
    load_dotenv()

    токен = os.getenv("PROM_API_TOKEN")
    if not токен:
        raise SystemExit("PROM_API_TOKEN отсутствует в окружении")

    консоль = Console()

    try:
        данные = получить_карточку(токен)
        путь = сохранить_снимок(данные)
    except (
        httpx.HTTPError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as ошибка:
        консоль.print(f"[red]Снимок не создан: {type(ошибка).__name__}[/red]")
        raise SystemExit(1) from None

    таблица = Table(title="PROM // СНИМОК ТЕСТОВОЙ КАРТОЧКИ")
    таблица.add_column("Показатель")
    таблица.add_column("Значение")

    таблица.add_row(
        "ID",
        str(ИДЕНТИФИКАТОР_ТЕСТОВОГО_ТОВАРА),
    )
    таблица.add_row("Режим", "Только чтение")
    таблица.add_row("Снимок", str(путь))
    таблица.add_row(
        "Поля карточки",
        str(len(данные.get("product", данные))),
    )

    консоль.print(таблица)


if __name__ == "__main__":
    main()
