"""Выполнить максимум один подтверждённый этап плана двух тестовых карточек."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from prom.api.исполнитель_групповых_статусов import (
    ОстановкаОперации,
    выполнить_этап,
    проверить_план,
)


def main() -> int:
    парсер = argparse.ArgumentParser(description=__doc__)
    парсер.add_argument('--план', type=Path, default=Path('data/групповые_операции/план_двух_карточек.json'))
    парсер.add_argument('--отправить', action='store_true')
    аргументы = парсер.parse_args()
    консоль = Console()
    load_dotenv()
    try:
        план = json.loads(аргументы.план.read_text(encoding='utf-8'))
        проверить_план(план)
        журнал = аргументы.план.with_suffix('.журнал.jsonl')
        журнал.parent.mkdir(parents=True, exist_ok=True)
        with журнал.with_suffix('.lock').open('a+') as блокировка:
            fcntl.flock(блокировка, fcntl.LOCK_EX | fcntl.LOCK_NB)
            токен = os.getenv('PROM_API_TOKEN_READ') or os.getenv('PROM_API_TOKEN')
            if not токен:
                raise ОстановкаОперации('Не указан токен чтения')
            with requests.Session() as соединение:
                соединение.headers.update({'Authorization': f'Bearer {токен}'})
                номер, этап = выполнить_этап(план, журнал, соединение, None, None)
                таблица = Table(title=f'PROM / ЭТАП {номер + 1}: {этап["этап"]}')
                for имя in ('ID', 'Исходный статус', 'Целевой статус'):
                    таблица.add_column(имя)
                for пункт in этап['запрос']:
                    таблица.add_row(str(пункт['id']), этап.get('исходные_статусы', {}).get(пункт['id'], этап['из']), этап['в'])
                консоль.print(таблица)
                if not аргументы.отправить:
                    консоль.print('[yellow]Только GET: POST не выполнялся.[/yellow]')
                    return 0
                консоль.print('[yellow]Один POST, без автоматических повторов.[/yellow]')
                фраза = f'ВЫПОЛНИТЬ {номер + 1} {этап["этап"]}'
                консоль.print(f'Для подтверждения введите: [bold]{фраза}[/bold]')
                введено = input('Подтверждение: ').strip()
                выполнить_этап(
                    план, журнал, соединение, os.getenv('PROM_API_TOKEN_WRITE'), введено,
                )
                консоль.print('[green]Этап подтверждён GET и записан в журнал.[/green]')
                return 0
    except (OSError, ValueError, TypeError, requests.RequestException, ОстановкаОперации) as ошибка:
        консоль.print(f'[red]Операция остановлена: {ошибка}[/red]')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
