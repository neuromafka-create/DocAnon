from __future__ import annotations

"""C1: явное соответствие меток spaCy → типы DocAnon / Presidio.

ru_core_news_lg даёт PER / ORG / LOC. Presidio и наш pipeline работают
с PERSON / ORGANIZATION / LOCATION.
"""

# spaCy (и синонимы) → entity type в DocAnon
SPACY_TO_PRESIDIO: dict[str, str] = {
    "PER": "PERSON",
    "PERSON": "PERSON",
    "ORG": "ORGANIZATION",
    "ORGANIZATION": "ORGANIZATION",
    "LOC": "LOCATION",
    "LOCATION": "LOCATION",
    "GPE": "LOCATION",  # geo-political → адрес/локация
    "DATE": "DATE_TIME",
    "TIME": "DATE_TIME",
    "NORP": "NORP",
    "NRP": "NORP",  # Presidio legacy alias
}

# Типы, которые считаем результатом NER (для ner_enabled / порогов)
NER_OUTPUT_TYPES: frozenset[str] = frozenset({
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "GPE",
    "DATE_TIME",
    "NORP",
})

# Что запрашиваем у Analyzer, когда ner_enabled=True
DEFAULT_NER_ENTITIES: tuple[str, ...] = (
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "DATE_TIME",
    "NORP",
)


def ner_model_configuration_dict(default_score: float = 0.85) -> dict:
    """Конфиг для NlpEngineProvider / NerModelConfiguration.from_dict."""
    return {
        "model_to_presidio_entity_mapping": dict(SPACY_TO_PRESIDIO),
        "default_score": default_score,
        "labels_to_ignore": [],
        "low_score_entity_names": [],
        "low_confidence_score_multiplier": 0.4,
        "aggregation_strategy": "max",
        "alignment_mode": "expand",
    }


def normalize_entity_label(label: str) -> str:
    """Нормализация метки (NRP→NORP, PER→PERSON, …)."""
    return SPACY_TO_PRESIDIO.get(label, label)
