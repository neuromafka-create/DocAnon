from __future__ import annotations

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from core.models import ENTITY_LABELS_RU, AnonymizedDocument, Entity

# Цвета подсветки по типу (фон)
_LABEL_COLORS: dict[str, str] = {
    "PERSON": "#FFE082",
    "ORGANIZATION": "#C5E1A5",
    "LOCATION": "#B3E5FC",
    "GPE": "#B3E5FC",
    "PHONE_NUMBER": "#F8BBD0",
    "EMAIL_ADDRESS": "#E1BEE7",
    "RU_INN": "#FFCCBC",
    "RU_SNILS": "#FFCCBC",
    "RU_PASSPORT": "#FFAB91",
    "RU_DRIVER_LICENSE": "#FFAB91",
    "RU_VEHICLE_PLATE": "#D7CCC8",
    "CREDIT_CARD": "#FFCDD2",
    "RU_ACCOUNT": "#FFCDD2",
    "RU_BIK": "#FFCDD2",
    "IP_ADDRESS": "#B2DFDB",
    "MAC_ADDRESS": "#B2DFDB",
    "GPS_COORDS": "#B2DFDB",
    "TG_CHAT_ID": "#D1C4E9",
    "DATE_TIME": "#CFD8DC",
    "DEFAULT": "#FFF59D",
}


def _fmt(color_hex: str) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setBackground(QColor(color_hex))
    return fmt


def clear_highlights(edit: QTextEdit) -> None:
    cursor = edit.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    cursor.setCharFormat(QTextCharFormat())
    cursor.clearSelection()
    edit.setTextCursor(cursor)


def highlight_entities(
    edit: QTextEdit,
    text: str,
    entities: list[Entity],
) -> None:
    """D3: подсветка найденных span'ов в исходном тексте."""
    edit.setPlainText(text)
    if not entities:
        return

    for entity in sorted(entities, key=lambda e: e.start):
        color = _LABEL_COLORS.get(entity.label, _LABEL_COLORS["DEFAULT"])
        cursor = edit.textCursor()
        cursor.setPosition(entity.start)
        cursor.setPosition(entity.end, QTextCursor.MoveMode.KeepAnchor)
        cursor.mergeCharFormat(_fmt(color))

    # сброс selection
    cursor = edit.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.Start)
    edit.setTextCursor(cursor)


def highlight_anonymized(edit: QTextEdit, text: str) -> None:
    """Подсветка плейсхолдеров ``<...>`` в обезличенном тексте."""
    import re

    edit.setPlainText(text)
    fmt = _fmt("#E0E0E0")
    for m in re.finditer(r"<[A-Za-z0-9_]+>", text):
        cursor = edit.textCursor()
        cursor.setPosition(m.start())
        cursor.setPosition(m.end(), QTextCursor.MoveMode.KeepAnchor)
        cursor.mergeCharFormat(fmt)
    cursor = edit.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.Start)
    edit.setTextCursor(cursor)


def set_document_preview(
    original_edit: QTextEdit,
    anonymized_edit: QTextEdit,
    doc: AnonymizedDocument,
) -> None:
    highlight_entities(original_edit, doc.original_text, doc.entities)
    highlight_anonymized(anonymized_edit, doc.anonymized_text)


def legend_html(entities: list[Entity]) -> str:
    labels = sorted({e.label for e in entities})
    if not labels:
        return ""
    parts = []
    for label in labels:
        color = _LABEL_COLORS.get(label, _LABEL_COLORS["DEFAULT"])
        name = ENTITY_LABELS_RU.get(label, label)
        parts.append(
            f'<span style="background:{color};padding:1px 6px;'
            f'border-radius:3px;margin-right:6px;">{name}</span>'
        )
    return " ".join(parts)
