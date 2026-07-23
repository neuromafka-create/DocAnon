from __future__ import annotations

from pathlib import Path

import pdfplumber

from core.models import ExtractionResult
from extractors.base import TextExtractor


class PdfExtractor(TextExtractor):
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def extract(self, file_path: Path) -> ExtractionResult:
        pages: list[str] = []
        with pdfplumber.open(str(file_path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        cells = [str(c).strip() for c in row if c]
                        if cells:
                            pages.append(" | ".join(cells))

        full_text = "\n\n".join(pages)
        return ExtractionResult(
            text=full_text,
            source_format="pdf",
            pages=pages,
            metadata={"file_name": file_path.name, "total_pages": len(pages)},
        )
