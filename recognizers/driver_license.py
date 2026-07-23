from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class DriverLicenseRecognizer(PatternRecognizer):
    """Водительское удостоверение РФ.

    Форматы: ``77 АВ 123456``, ``77АВ123456``, ``77 AB 123456``.
    """

    ENTITY = "RU_DRIVER_LICENSE"
    LANGUAGE = "ru"

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="driver_license_spaced",
                regex=r"\b\d{2}\s+[А-Яа-яA-Za-z]{2}\s+\d{6}\b",
                score=0.85,
            ),
            Pattern(
                name="driver_license_compact",
                regex=r"\b\d{2}\s*[А-Яа-яA-Za-z]{2}\s*\d{6}\b",
                score=0.7,
            ),
        ]
        context = [
            "водительское",
            "права",
            "в/у",
            "ву",
            "удостоверение",
            "водительское удостоверение",
            "водительские права",
        ]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
        )

    def validate_result(self, pattern_text: str) -> float:
        digits = "".join(c for c in pattern_text if c.isdigit())
        letters = "".join(c for c in pattern_text if c.isalpha())
        if len(digits) != 8 or len(letters) != 2:
            return 0.0
        # Не путать с голым 10-значным ИНН без букв
        return 0.9
