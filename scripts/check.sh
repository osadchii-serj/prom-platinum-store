#!/usr/bin/env bash
set -Eeuo pipefail

# Запускать из любого каталога: скрипт переходит в корень проекта.
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

printf '\n[1/5] Ruff: безопасные автоматические исправления\n'
uv run ruff check . --fix

printf '\n[2/5] Ruff: контрольная проверка\n'
uv run ruff check .

printf '\n[3/5] MyPy: проверка типов\n'
uv run mypy src

printf '\n[4/5] Python: компиляция исходников и тестов\n'
uv run python -m compileall -q src tests

printf '\n[5/5] Pytest: тесты\n'
uv run pytest -q

printf '\nВсе проверки пройдены.\n'
