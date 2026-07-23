from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class RuAccountRecognizer(PatternRecognizer):
    """Расчётный / корреспондентский счёт РФ (20 цифр)."""

    ENTITY = "RU_ACCOUNT"
    LANGUAGE = "ru"

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="ru_account_20",
                regex=r"\b\d{20}\b",
                score=0.55,
            ),
            Pattern(
                name="ru_account_spaced",
                regex=r"\b\d{5}\s\d{3}\s\d{1}\s\d{4}\s\d{7}\b",
                score=0.7,
            ),
        ]
        context = [
            "р/с",
            "р с",
            "расчетный",
            "расчётный",
            "счет",
            "счёт",
            "к/с",
            "корр",
            "корреспондентский",
            "банковский счет",
            "банковский счёт",
            "account",
        ]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
        )

    def validate_result(self, pattern_text: str) -> float:
        digits = "".join(c for c in pattern_text if c.isdigit())
        if len(digits) != 20:
            return 0.0
        # Типичные балансовые счета начинаются с 4 (р/с юрлиц и т.п.)
        if digits[0] in "123456789":
            return 0.9
        return 0.0


class RuBikRecognizer(PatternRecognizer):
    """БИК банка (9 цифр, часто начинается с 04)."""

    ENTITY = "RU_BIK"
    LANGUAGE = "ru"

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="ru_bik",
                regex=r"\b\d{9}\b",
                score=0.4,
            ),
        ]
        context = [
            "бик",
            "bik",
            "банк",
            "банка",
            "реквизиты",
        ]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
        )

    def validate_result(self, pattern_text: str) -> float:
        digits = pattern_text.strip()
        if not digits.isdigit() or len(digits) != 9:
            return 0.0
        # БИК РФ: 04xxxxxx или 01–02 для ЦБ/особых
        if digits.startswith(("04", "01", "00")):
            return 0.9
        return 0.0
