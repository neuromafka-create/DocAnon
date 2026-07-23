from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# Типы, которые в основном даёт spaCy NER (ниже типичный score)
NER_ENTITY_TYPES: frozenset[str] = frozenset({
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "GPE",
    "NORP",
    "DATE_TIME",
})

# Пороги по умолчанию: выше = строже (меньше recall, меньше FP)
# Не указанные типы → regex_confidence_threshold или ner_confidence_threshold
DEFAULT_ENTITY_THRESHOLDS: dict[str, float] = {
    # Structured + validators (можно чуть ниже — чексумма режет FP)
    "RU_INN": 0.50,
    "RU_SNILS": 0.50,
    "EMAIL_ADDRESS": 0.50,
    "CREDIT_CARD": 0.50,
    "MAC_ADDRESS": 0.50,
    "IP_ADDRESS": 0.50,
    "GPS_COORDS": 0.50,
    "CRYPTO": 0.50,
    "IBAN_CODE": 0.50,
    "RU_VEHICLE_PLATE": 0.50,
    "RU_DRIVER_LICENSE": 0.55,
    "RU_OMS": 0.60,
    # Контекстно-зависимые / коллизии с другими ID
    "RU_PASSPORT": 0.55,
    "RU_INT_PASSPORT": 0.70,
    "PHONE_NUMBER": 0.55,
    "RU_ACCOUNT": 0.55,
    "RU_BIK": 0.55,
    "TG_CHAT_ID": 0.60,
    "EME_IMEI": 0.60,
    # NER (spaCy часто даёт 0.4–0.85)
    "PERSON": 0.35,
    "ORGANIZATION": 0.40,
    "LOCATION": 0.40,
    "GPE": 0.40,
    "NORP": 0.50,
    # Даты часто шумят в договорах
    "DATE_TIME": 0.65,
}


@dataclass
class AnonymizerConfig:
    enabled_entity_types: list[str] = field(default_factory=lambda: [
        "PERSON",
        "PHONE_NUMBER",
        "EMAIL_ADDRESS",
        "RU_INN",
        "RU_SNILS",
        "RU_PASSPORT",
        "RU_INT_PASSPORT",
        "RU_DRIVER_LICENSE",
        "RU_OMS",
        "RU_VEHICLE_PLATE",
        "IP_ADDRESS",
        "CREDIT_CARD",
        "IBAN_CODE",
        "RU_ACCOUNT",
        "RU_BIK",
        "CRYPTO",
        "LOCATION",
        "GPE",
        "ORGANIZATION",
        "DATE_TIME",
        "GPS_COORDS",
        "MAC_ADDRESS",
        "EME_IMEI",
        "TG_CHAT_ID",
        "NORP",
    ])

    ner_enabled: bool = True
    # C2: pymorphy3 — поиск ФИО в других падежах после NER
    morpho_enabled: bool = True
    # C3: один placeholder на канон ФИО (словоформы / partial) в batch
    person_canonical_mapping: bool = True
    # Глобальные fallback-пороги
    ner_confidence_threshold: float = 0.35
    regex_confidence_threshold: float = 0.5
    # Переопределения: entity_type → min score (поверх DEFAULT_ENTITY_THRESHOLDS)
    entity_thresholds: dict[str, float] = field(default_factory=dict)

    placeholder_format: str = "<{label}>"

    language: str = "ru"

    def get_supported_entities(self) -> list[str]:
        return list(self.enabled_entity_types)

    def is_entity_enabled(self, entity_type: str) -> bool:
        return entity_type in self.enabled_entity_types

    def disable_entity(self, entity_type: str) -> None:
        if entity_type in self.enabled_entity_types:
            self.enabled_entity_types.remove(entity_type)

    def enable_entity(self, entity_type: str) -> None:
        if entity_type not in self.enabled_entity_types:
            self.enabled_entity_types.append(entity_type)

    def set_threshold(self, entity_type: str, threshold: float) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Порог должен быть в [0, 1], получено {threshold}")
        self.entity_thresholds[entity_type] = threshold

    def threshold_for(self, entity_type: str) -> float:
        """Минимальный confidence для принятия сущности данного типа."""
        if entity_type in self.entity_thresholds:
            return self.entity_thresholds[entity_type]
        if entity_type in DEFAULT_ENTITY_THRESHOLDS:
            return DEFAULT_ENTITY_THRESHOLDS[entity_type]
        if entity_type in NER_ENTITY_TYPES:
            return self.ner_confidence_threshold
        return self.regex_confidence_threshold

    def effective_thresholds(self) -> dict[str, float]:
        """Сводка порогов для всех включённых типов (для отладки/GUI)."""
        return {et: self.threshold_for(et) for et in self.enabled_entity_types}

    def score_gate(self) -> Callable[[str], float]:
        """Callable label → threshold для filter_entities."""
        return self.threshold_for
