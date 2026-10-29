"""Проверка пользовательского значения наценки."""

from decimal import Decimal, InvalidOperation


def разобрать_процент(значение: str) -> Decimal:
    """Разобрать процент; допускается десятичная запятая."""
    try:
        процент = Decimal(значение.strip().replace(",", "."))
    except (InvalidOperation, ValueError) as ошибка:
        raise ValueError("Процент должен быть числом, например 20 или 12,5") from ошибка
    if not процент.is_finite() or процент < 0:
        raise ValueError("Процент должен быть конечным неотрицательным числом")
    return процент
