from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class PassportRfRecognizer(PatternRecognizer):
    """Паспорт РФ: серия 4 цифры + номер 6 цифр.

    Форматы: ``4512 345678``, ``45 12 345678``, ``4512345678``, ``45-12-345678``.
    """

    ENTITY = "RU_PASSPORT"
    LANGUAGE = "ru"

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="passport_spaced_series",
                # 45 12 345678
                regex=r"\b\d{2}\s\d{2}\s\d{6}\b",
                score=0.85,
            ),
            Pattern(
                name="passport_series_dash",
                # 45-12 345678 / 45-12-345678
                regex=r"\b\d{2}[-\s]\d{2}[-\s]?\d{6}\b",
                score=0.8,
            ),
            Pattern(
                name="passport_rf",
                # 4512 345678 / 4512345678
                regex=r"\b\d{4}[\s\-]?\d{6}\b",
                score=0.65,
            ),
        ]
        context = [
            "паспорт",
            "паспорта",
            "паспорту",
            "серия",
            "номер паспорта",
            "паспортные данные",
            "удостоверение личности",
        ]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
        )

    def validate_result(self, pattern_text: str) -> float:
        from recognizers.inn_recognizer import InnRecognizer

        digits = "".join(c for c in pattern_text if c.isdigit())
        if len(digits) != 10:
            return 0.0
        # Отсекаем явно «круглые»/нулевые
        if digits == "0" * 10 or digits[:4] == "0000":
            return 0.0
        # Валидный ИНН по чексумме — не паспорт
        if InnRecognizer._validate_inn(digits):
            return 0.0
        return 0.9


class ZagranPassportRecognizer(PatternRecognizer):
    """Загранпаспорт: 2 цифры серии + 7 цифр номера."""

    ENTITY = "RU_INT_PASSPORT"
    LANGUAGE = "ru"

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="zagran_passport",
                regex=r"\b\d{2}\s?\d{7}\b",
                score=0.45,
            ),
        ]
        context = [
            "загранпаспорт",
            "заграничный паспорт",
            "загран",
            "заграничный",
        ]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
        )
