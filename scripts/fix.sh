#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
uv run ruff check --fix main.py src tests предпросмотр_цен_prom.py подготовить_цену_одной_карточки.py
uv run ruff format main.py src tests предпросмотр_цен_prom.py подготовить_цену_одной_карточки.py
