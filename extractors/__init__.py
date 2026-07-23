from __future__ import annotations

from pathlib import Path

from core.models import ExtractionResult
from extractors.base import TextExtractor
from extractors.txt_extractor import TxtExtractor
from extractors.docx_extractor import DocxExtractor
from extractors.pdf_extractor import PdfExtractor
from extractors.image_extractor import ImageExtractor
from extractors.xlsx_extractor import XlsxExtractor

_EXTRACTORS: list[TextExtractor] = [
    TxtExtractor(),
    DocxExtractor(),
    PdfExtractor(),
    ImageExtractor(),
    XlsxExtractor(),
]


def get_extractor(file_path: Path) -> TextExtractor | None:
    for extractor in _EXTRACTORS:
        if extractor.can_handle(file_path):
            return extractor
    return None


def extract_text(file_path: Path) -> ExtractionResult:
    extractor = get_extractor(file_path)
    if extractor is None:
        raise ValueError(f"Неподдерживаемый формат: {file_path.suffix}")
    return extractor.extract(file_path)
