from __future__ import annotations

import logging
from pathlib import Path

from core.analyze import analyze_text
from core.config import AnonymizerConfig
from core.engine import build_analyzer, build_anonymizer, get_operators
from core.mapping import MappingStore
from core.models import AnonymizedDocument, Entity
from extractors import extract_text

logger = logging.getLogger(__name__)


def apply_placeholders(
    text: str,
    entities: list[Entity],
    placeholder_for,
) -> str:
    """Замена span'ов справа налево. ``placeholder_for(original, label) -> str``."""
    if not entities:
        return text
    ordered = sorted(entities, key=lambda e: e.start, reverse=True)
    result = text
    for entity in ordered:
        original = text[entity.start : entity.end]
        placeholder = placeholder_for(original, entity.label)
        result = result[: entity.start] + placeholder + result[entity.end :]
    return result


class AnonymizationPipeline:
    """Единый пайплайн: analyze + replace (single-file).

    Analyzer/config можно переиспользовать в BatchPipeline (D1).
    """

    def __init__(self, config: AnonymizerConfig | None = None) -> None:
        self.config = config or AnonymizerConfig()
        self._analyzer = build_analyzer(self.config)
        self._anonymizer = build_anonymizer()
        self._operators = get_operators(self.config)

    def process_file(self, file_path: Path) -> AnonymizedDocument:
        logger.info("Извлечение текста из %s...", file_path.name)
        extraction = extract_text(file_path)
        doc = self.process_text(
            extraction.text,
            source_file=file_path.name,
            source_path=str(file_path.resolve()),
        )
        # XLSX: mapping должен покрывать отдельные ячейки (не только «A | B»)
        from core.xlsx_enrich import enrich_dict_mapping_from_xlsx, is_xlsx_path

        if is_xlsx_path(file_path):
            doc.mapping = enrich_dict_mapping_from_xlsx(
                file_path,
                self,
                doc.mapping,
                entities=doc.entities,
            )
            # пересобрать anonymized_text с учётом новых ключей (substring)
            from core.xlsx_cells import apply_mapping_to_text

            doc.anonymized_text = apply_mapping_to_text(
                doc.original_text, doc.mapping
            )
        return doc

    def process_text(
        self,
        text: str,
        source_file: str = "",
        source_path: str = "",
    ) -> AnonymizedDocument:
        logger.info("Анализ текста (%d символов)...", len(text))

        entities = self.analyze(text)
        logger.info("Найдено сущностей: %d", len(entities))

        anonymized_text = self.anonymize(text, entities)
        mapping = self.build_mapping(text, entities)

        return AnonymizedDocument(
            original_text=text,
            anonymized_text=anonymized_text,
            entities=entities,
            mapping=mapping,
            source_file=source_file,
            source_path=source_path,
        )

    def analyze(self, text: str) -> list[Entity]:
        """Публичный analyze — общий с batch."""
        return analyze_text(self._analyzer, text, self.config)

    def anonymize(self, text: str, entities: list[Entity]) -> str:
        """Single-file: generic placeholders ``<PERSON>``, ``<INN>``…"""
        from presidio_analyzer import RecognizerResult

        presidio_results = [
            RecognizerResult(
                entity_type=e.label,
                start=e.start,
                end=e.end,
                score=e.confidence,
            )
            for e in entities
        ]
        result = self._anonymizer.anonymize(
            text=text,
            analyzer_results=presidio_results,
            operators=self._operators,
        )
        return result.text

    def anonymize_with_store(
        self,
        text: str,
        entities: list[Entity],
        store: MappingStore,
    ) -> str:
        """Batch: numbered placeholders из MappingStore."""

        def placeholder_for(original: str, label: str) -> str:
            ph = store.get_placeholder(original)
            if ph is None:
                ph = store.register(original, label)
            return ph

        return apply_placeholders(text, entities, placeholder_for)

    @staticmethod
    def build_mapping(text: str, entities: list[Entity]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for entity in entities:
            original = text[entity.start : entity.end]
            if original not in mapping:
                mapping[original] = entity.placeholder
        return mapping

    def register_entities(
        self,
        text: str,
        entities: list[Entity],
        store: MappingStore,
        source_file: str = "",
    ) -> None:
        """Регистрация в store: длинные PERSON раньше (C3 primary)."""
        ordered = sorted(
            entities,
            key=lambda e: (
                0 if e.label == "PERSON" else 1,
                -(e.end - e.start),
                e.start,
            ),
        )
        for entity in ordered:
            original = text[entity.start : entity.end]
            store.register(original, entity.label, source_file=source_file)
