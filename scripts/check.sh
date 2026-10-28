
#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

echo "=== PROM: исправление Ruff ==="
uv run ruff check --fix main.py src tests

echo "=== PROM: форматирование ==="
uv run ruff format main.py src tests

echo "=== PROM: проверка Ruff ==="
uv run ruff check main.py src tests

echo "=== PROM: проверка MyPy ==="
uv run mypy main.py src

echo "=== PROM: тестирование Pytest ==="
uv run pytest -q

echo "=== PROM: все проверки пройдены ==="
