from __future__ import annotations

from datetime import date, datetime, time


def cell_value_to_str(value: object) -> str:
    """Нормализация значения ячейки Excel для extract и round-trip export."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, datetime):
        if value.time() != time(0, 0):
            return value.strftime("%d.%m.%Y %H:%M")
        return value.strftime("%d.%m.%Y")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def apply_mapping_to_text(text: str, mapping: dict[str, str]) -> str:
    """Замена original → placeholder; длинные ключи первыми."""
    if not text or not mapping:
        return text
    result = text
    for original, placeholder in sorted(
        mapping.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if original and original in result:
            result = result.replace(original, placeholder)
    return result


def apply_mapping_to_cell_value(
    value: object, mapping: dict[str, str]
) -> object:
    """Применить mapping к значению ячейки. Формулы не трогаем."""
    if value is None:
        return None
    if isinstance(value, str) and value.startswith("="):
        return value

    text = cell_value_to_str(value)
    if not text:
        return value

    new_text = apply_mapping_to_text(text, mapping)
    if new_text == text:
        return value
    return new_text
