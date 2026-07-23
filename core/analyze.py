from __future__ import annotations

import logging

from presidio_analyzer import AnalyzerEngine

from core.config import AnonymizerConfig
from core.entity_filter import filter_entities
from core.models import Entity
from core.morpho import expand_person_morphology
from core.ner_config import NER_OUTPUT_TYPES, normalize_entity_label

logger = logging.getLogger(__name__)


def analyze_text(
    analyzer: AnalyzerEngine,
    text: str,
    config: AnonymizerConfig,
) -> list[Entity]:
    """Единый analyze: Presidio → normalize labels → morpho → filter.

    Используется single и batch pipeline.
    """
    supported = config.get_supported_entities()
    if not config.ner_enabled:
        supported = [e for e in supported if e not in NER_OUTPUT_TYPES]

    results = analyzer.analyze(
        text=text,
        language=config.language,
        entities=supported if supported else None,
    )

    entities: list[Entity] = []
    for r in results:
        label = normalize_entity_label(r.entity_type)
        if not config.is_entity_enabled(label):
            continue
        if not config.ner_enabled and label in NER_OUTPUT_TYPES:
            continue
        entities.append(
            Entity(
                text=text[r.start : r.end],
                label=label,
                start=r.start,
                end=r.end,
                confidence=r.score,
                source="presidio",
            )
        )

    if (
        config.morpho_enabled
        and config.is_entity_enabled("PERSON")
        and config.ner_enabled
    ):
        entities = expand_person_morphology(text, entities)

    return filter_entities(
        entities,
        text,
        min_score=config.regex_confidence_threshold,
        threshold_for=config.threshold_for,
    )
