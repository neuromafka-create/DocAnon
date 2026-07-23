from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.config import AnonymizerConfig
from core.golden import GoldCase, list_gold_cases, run_gold_case
from core.metrics import GoldSpan, evaluate
from core.models import Entity
from core.pipeline import AnonymizationPipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_DIR = Path(__file__).resolve().parent / "fixtures" / "gold"

# skip if gold dir empty
_GOLD_FILES = list_gold_cases(GOLD_DIR)


@pytest.fixture(scope="module")
def pipeline() -> AnonymizationPipeline:
    return AnonymizationPipeline(AnonymizerConfig())


class TestMetricsUnit:
    def test_perfect_label_text(self) -> None:
        gold = [
            GoldSpan("RU_INN", "7707083893"),
            GoldSpan("PERSON", "Иванов"),
        ]
        pred = [
            Entity("7707083893", "RU_INN", 0, 10, 0.9),
            Entity("Иванов", "PERSON", 11, 17, 0.9),
        ]
        m = evaluate(gold, pred, mode="label_text")
        assert m.overall.f1 == 1.0
        assert m.overall.precision == 1.0
        assert m.overall.recall == 1.0

    def test_false_positive_lowers_precision(self) -> None:
        gold = [GoldSpan("RU_INN", "7707083893")]
        pred = [
            Entity("7707083893", "RU_INN", 0, 10, 0.9),
            Entity("мусор", "PERSON", 11, 16, 0.5),
        ]
        m = evaluate(gold, pred, mode="label_text", labels={"RU_INN", "PERSON"})
        assert m.overall.tp == 1
        assert m.overall.fp == 1
        assert m.overall.precision == pytest.approx(0.5)

    def test_false_negative_lowers_recall(self) -> None:
        gold = [
            GoldSpan("RU_INN", "7707083893"),
            GoldSpan("EMAIL_ADDRESS", "a@b.ru"),
        ]
        pred = [Entity("7707083893", "RU_INN", 0, 10, 0.9)]
        m = evaluate(gold, pred, mode="label_text")
        assert m.overall.fn == 1
        assert m.overall.recall == pytest.approx(0.5)

    def test_exact_mode(self) -> None:
        gold = [GoldSpan("RU_INN", "7707083893", start=5, end=15)]
        pred_ok = [Entity("7707083893", "RU_INN", 5, 15, 0.9)]
        pred_bad = [Entity("7707083893", "RU_INN", 0, 10, 0.9)]
        assert evaluate(gold, pred_ok, mode="exact").overall.f1 == 1.0
        assert evaluate(gold, pred_bad, mode="exact").overall.f1 == 0.0

    def test_overlap_mode(self) -> None:
        gold = [GoldSpan("PERSON", "Иванов Иван", start=0, end=11)]
        pred = [Entity("Иванов", "PERSON", 0, 6, 0.9)]
        # IoU = 6/11 ≈ 0.55
        m = evaluate(gold, pred, mode="overlap", iou_threshold=0.5)
        assert m.overall.tp == 1


class TestGoldenRegression:
    """E1+E3: регрессия по golden fixtures."""

    @pytest.mark.parametrize(
        "gold_path",
        _GOLD_FILES,
        ids=lambda p: p.stem,
    )
    def test_gold_case_thresholds(
        self, pipeline: AnonymizationPipeline, gold_path: Path
    ) -> None:
        if not gold_path.exists():
            pytest.skip(f"missing {gold_path}")

        case = GoldCase.load(gold_path)
        try:
            _, metrics = run_gold_case(
                case, pipeline, project_root=PROJECT_ROOT
            )
        except FileNotFoundError as e:
            pytest.skip(str(e))

        assert metrics.overall.recall >= case.min_recall, (
            f"{case.id}: recall {metrics.overall.recall:.3f} "
            f"< min {case.min_recall}; FN={metrics.unmatched_gold}"
        )
        assert metrics.overall.precision >= case.min_precision, (
            f"{case.id}: precision {metrics.overall.precision:.3f} "
            f"< min {case.min_precision}; FP={[e.text for e in metrics.unmatched_pred]}"
        )
        assert metrics.overall.f1 >= case.min_f1, (
            f"{case.id}: f1 {metrics.overall.f1:.3f} < min {case.min_f1}; "
            f"metrics={metrics.overall.to_dict()}"
        )

    def test_contract_required_labels_present(
        self, pipeline: AnonymizationPipeline
    ) -> None:
        """Жёсткая проверка ключевых structured-типов на contract."""
        path = GOLD_DIR / "test_contract.json"
        case = GoldCase.load(path)
        entities, metrics = run_gold_case(
            case, pipeline, project_root=PROJECT_ROOT
        )
        pred_labels = {e.label for e in entities}
        required = {
            "RU_INN",
            "RU_SNILS",
            "PHONE_NUMBER",
            "EMAIL_ADDRESS",
            "RU_PASSPORT",
            "MAC_ADDRESS",
            "RU_ACCOUNT",
            "RU_BIK",
        }
        missing = required - pred_labels
        assert not missing, f"missing labels: {missing}"
        assert metrics.overall.recall >= 0.95

    def test_gold_files_valid_json(self) -> None:
        assert _GOLD_FILES, "no gold fixtures found"
        for path in _GOLD_FILES:
            data = json.loads(path.read_text(encoding="utf-8"))
            assert "id" in data
            assert "entities" in data
            assert len(data["entities"]) > 0
