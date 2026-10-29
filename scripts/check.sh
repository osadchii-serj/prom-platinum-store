#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
echo "=== PROM: проверка Ruff ==="
uv run ruff check main.py src tests предпросмотр_цен_prom.py подготовить_цену_одной_карточки.py
echo "=== PROM: проверка форматирования ==="
uv run ruff format --check main.py src tests предпросмотр_цен_prom.py подготовить_цену_одной_карточки.py
echo "=== PROM: проверка MyPy ==="
uv run mypy main.py src
echo "=== PROM: тестирование Pytest ==="
uv run pytest -q
echo "=== PROM: все проверки пройдены ==="
