from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from core.models import ExtractionResult


class TextExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: Path) -> ExtractionResult:
        ...

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        ...

    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions()
