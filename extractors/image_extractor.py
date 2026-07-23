from __future__ import annotations

from pathlib import Path

import pytesseract
from PIL import Image

from core.models import ExtractionResult
from extractors.base import TextExtractor


class ImageExtractor(TextExtractor):
    def supported_extensions(self) -> list[str]:
        return [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"]

    def extract(self, file_path: Path) -> ExtractionResult:
        image = Image.open(str(file_path))
        text = pytesseract.image_to_string(image, lang="rus+eng")
        return ExtractionResult(
            text=text,
            source_format="image",
            metadata={
                "file_name": file_path.name,
                "width": image.width,
                "height": image.height,
            },
        )
