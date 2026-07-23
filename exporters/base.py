from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from core.models import AnonymizedDocument


class Exporter(ABC):
    @abstractmethod
    def export(self, doc: AnonymizedDocument, output_path: Path) -> Path:
        ...
