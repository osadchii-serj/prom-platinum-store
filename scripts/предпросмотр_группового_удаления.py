"""Прочитать две тестовые карточки и сохранить план без POST-запросов."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from prom.api.план_групповых_статусов import извлечь_снимок, построить_план

АДРЕС_API = "https://my.prom.ua/api/v1"
ИД_001 = 3243922294


def main() -> int:
    парсер = argparse.ArgumentParser(description=__doc__)
    парсер.add_argument("--id-002", type=int, required=True, help="ID второй тестовой карточки")
    парсер.add_argument(
        "--снимок", type=Path, default=Path("data/групповые_операции/план_двух_карточек.json")
    )
    аргументы = парсер.parse_args()
    консоль = Console()
    if аргументы.id_002 != 3244158641:
        консоль.print("[red]Требуется другой положительный ID второй карточки.[/red]")
        return 2
    load_dotenv()
    токен = os.getenv("PROM_API_TOKEN_READ") or os.getenv("PROM_API_TOKEN")
    if not токен:
        консоль.print("[red]Не найден токен чтения.[/red]")
        return 2
    карточки = []
    try:
        with requests.Session() as соединение:
            соединение.headers.update({"Authorization": f"Bearer {токен}"})
            for идентификатор, артикул in (
                (ИД_001, "PROM-TEST-20261022-001"),
                (аргументы.id_002, "PROM-TEST-20261022-002"),
            ):
                ответ = соединение.get(f"{АДРЕС_API}/products/{идентификатор}", timeout=20)
                ответ.raise_for_status()
                карточки.append(извлечь_снимок(ответ.json(), идентификатор, артикул))
        план = построить_план(карточки)
    except (requests.RequestException, ValueError, TypeError) as ошибка:
        консоль.print(f"[red]Предпросмотр заблокирован: {ошибка}[/red]")
        return 3
    таблица = Table(title="PROM / ПЛАН ДВУХ ТЕСТОВЫХ КАРТОЧЕК")
    for колонка in ("ID", "SKU", "Исходный статус", "План"):
        таблица.add_column(колонка)
    for карточка in карточки:
        таблица.add_row(
            str(карточка.идентификатор), карточка.артикул,
            карточка.исходный_статус, " → ".join(
                [карточка.исходный_статус]
                + [шаг["в"] for шаг in план["этапы"]
                   if any(пункт["id"] == карточка.идентификатор for пункт in шаг["запрос"])]
            ),
        )
    консоль.print(таблица)
    консоль.print("[yellow]Публикация после восстановления требует отдельного испытания.[/yellow]")
    аргументы.снимок.parent.mkdir(parents=True, exist_ok=True)
    # Создаём новый снимок атомарно, не перезаписывая предыдущий.
    try:
        дескриптор = os.open(
            аргументы.снимок, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        with os.fdopen(дескриптор, "w", encoding="utf-8") as файл:
            json.dump(план, файл, ensure_ascii=False, indent=2)
            файл.write("\n")
            файл.flush()
            os.fsync(файл.fileno())
    except FileExistsError:
        консоль.print("[red]Снимок уже существует: перезапись запрещена.[/red]")
        return 4
    консоль.print(f"[green]План сохранён: {аргументы.снимок}[/green]")
    консоль.print("[yellow]POST-запросы отсутствуют. Товары не изменены.[/yellow]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
