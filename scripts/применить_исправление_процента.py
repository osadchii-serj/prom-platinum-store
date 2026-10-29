"""Однократное безопасное обновление точки входа и старого теста."""
from pathlib import Path

корень = Path(__file__).resolve().parent.parent
точка = корень / "предпросмотр_цен_prom.py"
текст = точка.read_text(encoding="utf-8")
начало = "def разобрать_процент(значение: str) -> Decimal:"
конец = "def получить_процент() -> Decimal:"
if начало in текст:
    до, остаток = текст.split(начало, 1)
    if конец not in остаток:
        raise SystemExit("Не найден конец функции; файл не изменён")
    _, после = остаток.split(конец, 1)
    текст = до + конец + после
    текст = текст.replace("from decimal import Decimal, InvalidOperation", "from decimal import Decimal")
    маркер = "from prom.цены.источник_prom import ИсточникТоваровProm"
    if маркер not in текст:
        raise SystemExit("Не найден ожидаемый импорт; файл не изменён")
    текст = текст.replace(маркер, маркер + "\nfrom prom.цены.параметры_наценки import разобрать_процент")
    точка.write_text(текст, encoding="utf-8")
else:
    if "from prom.цены.параметры_наценки import разобрать_процент" not in текст:
        raise SystemExit("Неожиданная версия точки входа; файл не изменён")
старый = корень / "tests/цены/test_процент_консоли.py"
if старый.exists():
    старый.unlink()
print("Готово: логика процента вынесена, устаревший тест удалён")
