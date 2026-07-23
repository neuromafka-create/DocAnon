from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class RuMacAddressRecognizer(PatternRecognizer):
    """MAC-адрес (``00:1A:2B:3C:4D:5E`` / ``00-1A-2B-3C-4D-5E``).

    Имя класса не ``MacAddressRecognizer``, чтобы не конфликтовать
    с predefined-распознавателем Presidio.
    """

    ENTITY = "MAC_ADDRESS"
    LANGUAGE = "ru"

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="mac_colon",
                regex=r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b",
                score=0.9,
            ),
            Pattern(
                name="mac_dash",
                regex=r"\b(?:[0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}\b",
                score=0.9,
            ),
            Pattern(
                name="mac_dot",
                regex=r"\b(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}\b",
                score=0.85,
            ),
        ]
        context = [
            "mac",
            "мак",
            "mac-адрес",
            "mac адрес",
            "физический адрес",
            "hwaddr",
            "ethernet",
        ]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
            name="RuMacAddressRecognizer",
        )
