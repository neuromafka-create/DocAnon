from __future__ import annotations

import re

from presidio_analyzer import Pattern, PatternRecognizer


class InnRecognizer(PatternRecognizer):
    """Распознаватель ИНН (10/12 цифр) с валидацией чексумм."""

    ENTITY = "RU_INN"
    LANGUAGE = "ru"

    WEIGHTS_10 = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    WEIGHTS_12_C1 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    WEIGHTS_12_C2 = (2, 4, 10, 3, 5, 9, 4, 6, 8, 10)

    def __init__(self) -> None:
        patterns = [
            Pattern(name="inn_10", regex=r"\b\d{10}\b", score=0.5),
            Pattern(name="inn_12", regex=r"\b\d{12}\b", score=0.4),
        ]
        context = ["ИНН", "инн", "идентификационный номер налогоплательщика"]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
        )

    @staticmethod
    def _validate_inn(inn: str) -> bool:
        if not inn.isdigit():
            return False
        if len(inn) == 10:
            checksum = sum(int(inn[i]) * InnRecognizer.WEIGHTS_10[i] for i in range(9))
            return checksum % 11 % 10 == int(inn[9])
        if len(inn) == 12:
            c1 = sum(int(inn[i]) * InnRecognizer.WEIGHTS_12_C1[i] for i in range(10))
            c2 = sum(int(inn[i]) * InnRecognizer.WEIGHTS_12_C2[i - 1] for i in range(1, 11))
            return c1 % 11 % 10 == int(inn[10]) and c2 % 11 % 10 == int(inn[11])
        return False

    def validate_result(self, pattern_text: str) -> float:
        inn = pattern_text.strip().replace(" ", "")
        if len(inn) not in (10, 12):
            return 0.0
        if self._validate_inn(inn):
            return 0.95
        return 0.0
