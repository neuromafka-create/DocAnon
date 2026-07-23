from __future__ import annotations

import json
from pathlib import Path

from core.models import AnonymizedDocument, ENTITY_LABELS_RU
from exporters.base import Exporter


class JsonExporter(Exporter):
    def export(self, doc: AnonymizedDocument, output_path: Path) -> Path:
        output_path = output_path.with_suffix(".json")

        entities_data = []
        for e in doc.entities:
            entities_data.append({
                "text": e.text,
                "label": e.label,
                "label_ru": e.label_ru,
                "start": e.start,
                "end": e.end,
                "confidence": round(e.confidence, 3),
                "placeholder": e.placeholder,
            })

        stats = {}
        for label, count in doc.stats.items():
            label_ru = ENTITY_LABELS_RU.get(label, label)
            stats[label] = {"ru": label_ru, "count": count}

        data = {
            "source_file": doc.source_file,
            "total_entities": doc.total_entities,
            "stats": stats,
            "mapping": doc.mapping,
            "entities": entities_data,
            "anonymized_text": doc.anonymized_text,
        }

        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path
