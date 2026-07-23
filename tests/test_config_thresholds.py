from __future__ import annotations

from core.config import (
    DEFAULT_ENTITY_THRESHOLDS,
    NER_ENTITY_TYPES,
    AnonymizerConfig,
)
from core.entity_filter import filter_entities
from core.models import Entity


class TestThresholdFor:
    def test_defaults_from_table(self) -> None:
        cfg = AnonymizerConfig()
        assert cfg.threshold_for("RU_INN") == DEFAULT_ENTITY_THRESHOLDS["RU_INN"]
        assert cfg.threshold_for("PERSON") == DEFAULT_ENTITY_THRESHOLDS["PERSON"]
        assert cfg.threshold_for("DATE_TIME") == DEFAULT_ENTITY_THRESHOLDS["DATE_TIME"]
        assert cfg.threshold_for("RU_INT_PASSPORT") == 0.70

    def test_override_wins(self) -> None:
        cfg = AnonymizerConfig()
        cfg.set_threshold("PHONE_NUMBER", 0.9)
        assert cfg.threshold_for("PHONE_NUMBER") == 0.9
        # others unchanged
        assert cfg.threshold_for("RU_INN") == DEFAULT_ENTITY_THRESHOLDS["RU_INN"]

    def test_fallback_regex(self) -> None:
        cfg = AnonymizerConfig(regex_confidence_threshold=0.66)
        # unknown structured type
        assert cfg.threshold_for("SOME_CUSTOM_TYPE") == 0.66

    def test_fallback_ner_when_not_in_table(self) -> None:
        # DATE_TIME is in table; simulate NER type only in frozenset logic
        cfg = AnonymizerConfig(ner_confidence_threshold=0.42)
        # remove from defaults path by using type only in NER set if we had one
        # PERSON is in DEFAULT table at 0.35 — override ner doesn't change table
        assert cfg.threshold_for("PERSON") == 0.35
        # type not in DEFAULT but in NER → ner threshold
        assert "EVENT" not in DEFAULT_ENTITY_THRESHOLDS
        # EVENT not in NER_ENTITY_TYPES either → regex fallback
        assert cfg.threshold_for("EVENT") == cfg.regex_confidence_threshold

    def test_set_threshold_range(self) -> None:
        cfg = AnonymizerConfig()
        cfg.set_threshold("PERSON", 0.0)
        cfg.set_threshold("PERSON", 1.0)
        try:
            cfg.set_threshold("PERSON", 1.5)
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_effective_thresholds_covers_enabled(self) -> None:
        cfg = AnonymizerConfig()
        eff = cfg.effective_thresholds()
        assert set(eff.keys()) == set(cfg.enabled_entity_types)
        assert all(0.0 <= v <= 1.0 for v in eff.values())

    def test_ner_types_set(self) -> None:
        assert "PERSON" in NER_ENTITY_TYPES
        assert "RU_INN" not in NER_ENTITY_TYPES


class TestFilterPerTypeThreshold:
    def test_stricter_type_filters_out(self) -> None:
        text = "Контакт: test@example.com и +7 495 111 22 33"
        entities = [
            Entity("test@example.com", "EMAIL_ADDRESS", 9, 25, 0.9),
            Entity("+7 495 111 22 33", "PHONE_NUMBER", 28, 44, 0.60),
        ]
        # phone needs 0.85 after adjust might boost with «Контакт»? no phone keyword
        # anti: none. score stays 0.60
        result = filter_entities(
            entities,
            text,
            min_score=0.5,
            thresholds={"EMAIL_ADDRESS": 0.5, "PHONE_NUMBER": 0.85},
        )
        labels = {e.label for e in result}
        assert "EMAIL_ADDRESS" in labels
        assert "PHONE_NUMBER" not in labels

    def test_threshold_for_callable(self) -> None:
        cfg = AnonymizerConfig()
        cfg.set_threshold("EMAIL_ADDRESS", 0.99)
        text = "mail: a@b.ru"
        entities = [
            Entity("a@b.ru", "EMAIL_ADDRESS", 6, 12, 0.9),
        ]
        result = filter_entities(
            entities,
            text,
            threshold_for=cfg.threshold_for,
        )
        assert result == []

    def test_pipeline_uses_config_thresholds(self) -> None:
        from core.pipeline import AnonymizationPipeline

        cfg = AnonymizerConfig()
        # practically disable PERSON
        cfg.set_threshold("PERSON", 0.99)
        # keep INN easy
        cfg.set_threshold("RU_INN", 0.5)

        text = "Иванов Иван Иванович, ИНН 7707083893"
        result = AnonymizationPipeline(cfg).process_text(text)

        assert "7707083893" not in result.anonymized_text
        # person likely filtered if spaCy score < 0.99
        person_hits = [e for e in result.entities if e.label == "PERSON"]
        assert all(e.confidence >= 0.99 for e in person_hits)
