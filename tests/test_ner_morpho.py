from __future__ import annotations

from core.config import AnonymizerConfig
from core.models import Entity
from core.morpho import (
    expand_person_morphology,
    generate_name_forms,
    is_person_name_token,
    merge_adjacent_persons,
)
from core.ner_config import (
    SPACY_TO_PRESIDIO,
    normalize_entity_label,
    ner_model_configuration_dict,
)


class TestNerConfigC1:
    def test_spacy_label_map(self) -> None:
        assert SPACY_TO_PRESIDIO["PER"] == "PERSON"
        assert SPACY_TO_PRESIDIO["ORG"] == "ORGANIZATION"
        assert SPACY_TO_PRESIDIO["LOC"] == "LOCATION"
        assert SPACY_TO_PRESIDIO["GPE"] == "LOCATION"
        assert SPACY_TO_PRESIDIO["NRP"] == "NORP"

    def test_normalize_entity_label(self) -> None:
        assert normalize_entity_label("PER") == "PERSON"
        assert normalize_entity_label("NRP") == "NORP"
        assert normalize_entity_label("RU_INN") == "RU_INN"

    def test_ner_model_configuration_dict(self) -> None:
        d = ner_model_configuration_dict(0.85)
        assert d["model_to_presidio_entity_mapping"]["PER"] == "PERSON"
        assert d["default_score"] == 0.85

    def test_pipeline_emits_person_not_per(self) -> None:
        from core.pipeline import AnonymizationPipeline

        text = "Контакт: Егорова Марина Викторовна, ООО «ВекторФуд», г. Москва"
        result = AnonymizationPipeline(AnonymizerConfig()).process_text(text)
        labels = {e.label for e in result.entities}
        assert "PER" not in labels
        assert "ORG" not in labels
        assert "LOC" not in labels
        # mapped types
        assert labels & {"PERSON", "ORGANIZATION", "LOCATION"}

    def test_ner_disabled_skips_person_org(self) -> None:
        from core.pipeline import AnonymizationPipeline

        cfg = AnonymizerConfig(ner_enabled=False)
        text = "Контакт: Егорова Марина Викторовна, тел. +7 916 412 58 31"
        result = AnonymizationPipeline(cfg).process_text(text)
        labels = {e.label for e in result.entities}
        assert "PERSON" not in labels
        assert "ORGANIZATION" not in labels
        # structured still works
        assert "PHONE_NUMBER" in labels or "+7" not in result.anonymized_text


class TestMorphoC2:
    def test_is_person_name_token(self) -> None:
        assert is_person_name_token("Иванов")
        assert is_person_name_token("Егоровой")
        assert is_person_name_token("А.")

    def test_generate_name_forms_includes_cases(self) -> None:
        forms = {f.lower() for f in generate_name_forms("Иванов")}
        assert "иванов" in forms
        # dative / other cases often present
        assert any(f.startswith("иванов") for f in forms)
        assert "иванову" in forms or "иванова" in forms

    def test_merge_adjacent_persons(self) -> None:
        text = "Егорова Марина Викторовна"
        entities = [
            Entity("Егорова", "PERSON", 0, 7, 0.85),
            Entity("Марина Викторовна", "PERSON", 8, 25, 0.85),
        ]
        merged = merge_adjacent_persons(entities, text)
        persons = [e for e in merged if e.label == "PERSON"]
        assert len(persons) == 1
        assert persons[0].text == "Егорова Марина Викторовна"
        assert persons[0].source == "ner_merged"

    def test_expand_other_case(self) -> None:
        text = (
            "Сотрудник Иванов подписал акт. "
            "Документы передать Иванову в отдел."
        )
        # только номинатив от «NER»
        seed = [
            Entity("Иванов", "PERSON", text.index("Иванов"), text.index("Иванов") + 6, 0.85),
        ]
        expanded = expand_person_morphology(text, seed)
        person_texts = {e.text for e in expanded if e.label == "PERSON"}
        assert "Иванов" in person_texts
        assert "Иванову" in person_texts
        assert any(e.source == "morpho" for e in expanded)

    def test_pipeline_masks_dative_name(self) -> None:
        from core.pipeline import AnonymizationPipeline

        text = (
            "Ответственный: Петров Пётр. "
            "Акт передать Петрову Петру лично."
        )
        result = AnonymizationPipeline(AnonymizerConfig()).process_text(text)
        # dative form should not remain if morpho works
        assert "Петрову" not in result.anonymized_text or any(
            e.text == "Петрову" for e in result.entities
        )
        # at least nominative person detected
        assert any(e.label == "PERSON" for e in result.entities)

    def test_morpho_disabled(self) -> None:
        from core.pipeline import AnonymizationPipeline

        cfg = AnonymizerConfig(morpho_enabled=False)
        text = "Иванов и снова Иванову письмо."
        # without morpho, dative may survive if NER only hits nominative once
        result = AnonymizationPipeline(cfg).process_text(text)
        assert result.total_entities >= 0  # smoke: no crash
