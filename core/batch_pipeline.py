from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from core.config import AnonymizerConfig
from core.mapping import MappingStore
from core.models import AnonymizedDocument
from core.pipeline import AnonymizationPipeline
from core.xlsx_enrich import enrich_store_from_xlsx, is_xlsx_path
from extractors import extract_text

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    documents: list[AnonymizedDocument]
    mapping: MappingStore
    total_entities: int


class BatchPipeline:
    """Пакетная обработка с общим MappingStore.

    D1: переиспользует AnonymizationPipeline (один analyzer/config).
    """

    def __init__(
        self,
        config: AnonymizerConfig | None = None,
        pipeline: AnonymizationPipeline | None = None,
    ) -> None:
        if pipeline is not None:
            self._pipeline = pipeline
            self.config = pipeline.config
        else:
            self.config = config or AnonymizerConfig()
            self._pipeline = AnonymizationPipeline(self.config)

    def process_batch(self, files: list[Path]) -> BatchResult:
        store = MappingStore(
            person_canonical_mapping=self.config.person_canonical_mapping,
        )
        documents: list[AnonymizedDocument] = []
        total_entities = 0

        for file_path in files:
            logger.info("Обработка: %s", file_path.name)

            extraction = extract_text(file_path)
            entities = self._pipeline.analyze(extraction.text)

            self._pipeline.register_entities(
                extraction.text,
                entities,
                store,
                source_file=file_path.name,
            )

            # XLSX: ячейки ≠ flattened «A | B» — добираем PERSON/ORG по ячейкам
            # (только в store; не в entities — у cell-entity другие offset'ы)
            if is_xlsx_path(file_path):
                extra = enrich_store_from_xlsx(
                    file_path,
                    self._pipeline,
                    store,
                    entities=entities,
                    source_file=file_path.name,
                )
                if extra:
                    logger.info(
                        "XLSX enrich %s: +%d cell surfaces in mapping",
                        file_path.name,
                        len(extra),
                    )

            anonymized_text = self._pipeline.anonymize_with_store(
                extraction.text, entities, store
            )
            # после store-enrich: доп. substring-replace по всему mapping
            if is_xlsx_path(file_path):
                from core.xlsx_cells import apply_mapping_to_text

                anonymized_text = apply_mapping_to_text(
                    extraction.text, store.to_mapping_dict()
                )

            doc = AnonymizedDocument(
                original_text=extraction.text,
                anonymized_text=anonymized_text,
                entities=entities,
                mapping=store.to_mapping_dict(),
                source_file=file_path.name,
                source_path=str(file_path.resolve()),
            )
            documents.append(doc)
            total_entities += len(entities)

        return BatchResult(
            documents=documents,
            mapping=store,
            total_entities=total_entities,
        )
