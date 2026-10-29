# Исправление архитектуры тестов PROM

Выполнять из корня проекта после резервного копирования / проверки `git status`.

1. `unzip -o ~/Загрузки/prom_quality_fix.zip -d .`
2. `PYTHONPATH=src uv run python scripts/применить_исправление_процента.py`
3. `PYTHONPATH=src uv run pytest -q tests/цены/test_параметры_наценки.py`
4. `./scripts/check.sh`

`check.sh` теперь только проверяет, `fix.sh` отдельно исправляет файлы.
При неуспехе форматирования запустить `bash scripts/fix.sh`, изучить `git diff`, повторить `./scripts/check.sh`.
Архив НЕ содержит изменений бизнес-логики цены и НЕ выполняет запись в Prom.ua.
Важно: общий gate в окружении пользователя ещё не запускался.
