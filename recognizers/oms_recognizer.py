from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class OmsRecognizer(PatternRecognizer):
    """Распознаватель полиса ОМС (16 цифр)."""

    ENTITY = "RU_OMS"
    LANGUAGE = "ru"

    def __init__(self) -> None:
        patterns = [
            Pattern(name="oms_16", regex=r"\b\d{16}\b", score=0.3),
        ]
        context = [
            "омс",
            "полис",
            "страховой",
            "полис омс",
            "медицинское страхование",
        ]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
        )
