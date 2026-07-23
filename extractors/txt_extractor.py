from __future__ import annotations

from pathlib import Path

from core.models import ExtractionResult
from extractors.base import TextExtractor


class TxtExtractor(TextExtractor):
    def supported_extensions(self) -> list[str]:
        return [".txt", ".md", ".csv", ".log"]

    def extract(self, file_path: Path) -> ExtractionResult:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return ExtractionResult(
            text=text,
            source_format="txt",
            metadata={"file_name": file_path.name},
        )
