from __future__ import annotations

from pathlib import Path

from core.models import AnonymizedDocument
from exporters.base import Exporter


class TxtExporter(Exporter):
    def export(self, doc: AnonymizedDocument, output_path: Path) -> Path:
        output_path = output_path.with_suffix(".txt")
        output_path.write_text(doc.anonymized_text, encoding="utf-8")
        return output_path
