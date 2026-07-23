from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class RuPhoneRecognizer(PatternRecognizer):
    """Российские телефонные номера.

    Примеры: ``+7 495 123 45 67``, ``+7(495)123-45-67``, ``8 900 123-45-67``,
    ``89001234567``.
    """

    ENTITY = "PHONE_NUMBER"
    LANGUAGE = "ru"

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="ru_phone_plus7_spaced",
                regex=(
                    r"(?<!\d)\+7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}"
                    r"[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"
                ),
                score=0.9,
            ),
            Pattern(
                name="ru_phone_8_spaced",
                regex=(
                    r"(?<!\d)8[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}"
                    r"[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"
                ),
                score=0.85,
            ),
            Pattern(
                name="ru_phone_compact",
                regex=r"(?<!\d)(?:\+7|8|7)\d{10}(?!\d)",
                score=0.8,
            ),
        ]
        context = [
            "тел",
            "телефон",
            "моб",
            "мобильный",
            "phone",
            "фах",
            "факс",
            "связаться",
            "звоните",
        ]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
        )

    def validate_result(self, pattern_text: str) -> float:
        import re

        from recognizers.inn_recognizer import InnRecognizer
        from recognizers.snils_recognizer import SnilsRecognizer

        text = pattern_text.strip()
        if text.count(".") >= 2:
            return 0.0
        # СНИЛС-формат XXX-XXX-XXX XX — не телефон
        if re.fullmatch(r"\d{3}-\d{3}-\d{3}\s*\d{2}", text):
            return 0.0

        digits = "".join(c for c in text if c.isdigit())
        if len(digits) == 11 and SnilsRecognizer._validate_snils(digits):
            # похож на СНИЛС, если нет телефонного префикса в тексте
            if not text.startswith(("+", "8", "7")):
                return 0.0
        if len(digits) == 10 and InnRecognizer._validate_inn(digits):
            return 0.0
        if len(digits) == 11 and digits[0] in ("7", "8"):
            return 0.95
        if len(digits) == 10 and text.startswith(("+", "8", "7")):
            return 0.85
        # 10 цифр без префикса — не считаем телефоном (часто паспорт/мусор)
        return 0.0
