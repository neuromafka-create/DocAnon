from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class GeoCoordsRecognizer(PatternRecognizer):
    """Распознаватель GPS-координат."""

    ENTITY = "GPS_COORDS"
    LANGUAGE = "ru"

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="geo_coords",
                regex=r"\b-?\d{1,3}\.\d{3,10}[,\s]+-?\d{1,3}\.\d{3,10}\b",
                score=0.5,
            ),
        ]
        context = [
            "gps",
            "координаты",
            "широта",
            "долгота",
            "location",
            "местоположение",
        ]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
        )
