from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class SnilsRecognizer(PatternRecognizer):
    """Распознаватель СНИЛС (XXX-XXX-XXX XX) с валидацией чексумм."""

    ENTITY = "RU_SNILS"
    LANGUAGE = "ru"

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="snils_dashed",
                regex=r"\b\d{3}-\d{3}-\d{3}\s?\d{2}\b",
                score=0.6,
            ),
            Pattern(
                name="snils_plain",
                regex=r"\b\d{11}\b",
                score=0.3,
            ),
        ]
        context = ["СНИЛС", "снилс", "страховой номер"]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
        )

    @staticmethod
    def _validate_snils(snils_digits: str) -> bool:
        if len(snils_digits) != 11:
            return False
        digits = [int(d) for d in snils_digits]
        if digits[9] == 0 and digits[10] == 0:
            return False
        number = digits[:9]
        control = digits[9] * 10 + digits[10]
        if number[0] == number[1] == number[2] == 0:
            return False
        total = 0
        for i, d in enumerate(number):
            weight = 9 - i
            total += d * weight
        remainder = total % 101
        if remainder == 100:
            remainder = 0
        return remainder == control

    def validate_result(self, pattern_text: str) -> float:
        digits = pattern_text.strip().replace("-", "").replace(" ", "")
        if not digits.isdigit():
            return 0.0
        if len(digits) == 11 and self._validate_snils(digits):
            return 0.95
        return 0.0
