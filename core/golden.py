from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from core.config import AnonymizerConfig
from core.metrics import EvaluationResult, GoldSpan, evaluate
from core.models import Entity
from core.pipeline import AnonymizationPipeline
from extractors import extract_text

GOLD_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "gold"


@dataclass
class GoldCase:
    id: str
    description: str
    entities: list[GoldSpan]
    match_mode: str = "label_text"
    min_recall: float = 0.8
    min_precision: float = 0.5
    min_f1: float = 0.6
    source: str | None = None
    source_type: str = "file"
    text: str | None = None
    notes: str = ""
    raw: dict | None = None

    @classmethod
    def load(cls, path: Path) -> GoldCase:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            id=data["id"],
            description=data.get("description", ""),
            entities=[GoldSpan.from_dict(e) for e in data.get("entities", [])],
            match_mode=data.get("match_mode", "label_text"),
            min_recall=float(data.get("min_recall", 0.8)),
            min_precision=float(data.get("min_precision", 0.5)),
            min_f1=float(data.get("min_f1", 0.6)),
            source=data.get("source"),
            source_type=data.get("source_type", "file"),
            text=data.get("text"),
            notes=data.get("notes", ""),
            raw=data,
        )

    def load_text(self, root: Path | None = None) -> str:
        if self.source_type == "inline" and self.text is not None:
            return self.text
        if not self.source:
            raise ValueError(f"Gold case {self.id}: no source/text")
        path = Path(self.source)
        if root is not None and not path.is_absolute():
            # try relative to project root
            candidate = root / path
            if candidate.exists():
                path = candidate
        if not path.exists():
            # relative to CWD
            path = Path(self.source)
        if not path.exists():
            raise FileNotFoundError(f"Gold source not found: {self.source}")
        if path.suffix.lower() in {".txt", ".md", ".csv", ".log"}:
            return path.read_text(encoding="utf-8")
        return extract_text(path).text


def list_gold_cases(gold_dir: Path | None = None) -> list[Path]:
    d = gold_dir or GOLD_DIR
    if not d.exists():
        return []
    return sorted(d.glob("*.json"))


def run_gold_case(
    case: GoldCase,
    pipeline: AnonymizationPipeline | None = None,
    *,
    project_root: Path | None = None,
) -> tuple[list[Entity], EvaluationResult]:
    pipe = pipeline or AnonymizationPipeline(AnonymizerConfig())
    root = project_root or Path.cwd()
    text = case.load_text(root)
    result = pipe.process_text(text, source_file=case.id)
    labels = {e.label for e in case.entities}
    metrics = evaluate(
        case.entities,
        result.entities,
        mode=case.match_mode,  # type: ignore[arg-type]
        labels=labels,
    )
    return result.entities, metrics
