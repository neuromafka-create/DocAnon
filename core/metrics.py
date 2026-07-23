from __future__ import annotations

"""E2: precision / recall / F1 для детекции ПДн (span-level)."""

from dataclasses import dataclass, field
from typing import Iterable, Literal

from core.models import Entity

MatchMode = Literal["exact", "label_text", "overlap"]


@dataclass(frozen=True)
class GoldSpan:
    label: str
    text: str
    start: int | None = None
    end: int | None = None

    @classmethod
    def from_dict(cls, d: dict) -> GoldSpan:
        return cls(
            label=d["label"],
            text=d.get("text", ""),
            start=d.get("start"),
            end=d.get("end"),
        )

    def to_dict(self) -> dict:
        out: dict = {"label": self.label, "text": self.text}
        if self.start is not None:
            out["start"] = self.start
        if self.end is not None:
            out["end"] = self.end
        return out


@dataclass
class PRF:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int
    support_gold: int = 0
    support_pred: int = 0

    def to_dict(self) -> dict:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "support_gold": self.support_gold,
            "support_pred": self.support_pred,
        }


@dataclass
class EvaluationResult:
    overall: PRF
    by_label: dict[str, PRF] = field(default_factory=dict)
    mode: str = "label_text"
    unmatched_gold: list[GoldSpan] = field(default_factory=list)
    unmatched_pred: list[Entity] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "overall": self.overall.to_dict(),
            "by_label": {k: v.to_dict() for k, v in sorted(self.by_label.items())},
            "unmatched_gold": [g.to_dict() for g in self.unmatched_gold],
            "unmatched_pred": [
                {"label": e.label, "text": e.text, "start": e.start, "end": e.end}
                for e in self.unmatched_pred
            ],
        }


def _prf(tp: int, fp: int, fn: int, support_gold: int = 0, support_pred: int = 0) -> PRF:
    precision = tp / (tp + fp) if (tp + fp) else (1.0 if support_gold == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) else (1.0 if support_pred == 0 else 0.0)
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return PRF(
        precision=precision,
        recall=recall,
        f1=f1,
        tp=tp,
        fp=fp,
        fn=fn,
        support_gold=support_gold,
        support_pred=support_pred,
    )


def _norm_text(text: str) -> str:
    return " ".join(text.strip().split()).casefold()


def _key_exact(label: str, start: int, end: int) -> tuple:
    return ("exact", label, start, end)


def _key_label_text(label: str, text: str) -> tuple:
    return ("lt", label, _norm_text(text))


def _iou(a0: int, a1: int, b0: int, b1: int) -> float:
    inter = max(0, min(a1, b1) - max(a0, b0))
    if inter == 0:
        return 0.0
    union = (a1 - a0) + (b1 - b0) - inter
    return inter / union if union else 0.0


def _match_overlap(
    gold: list[GoldSpan],
    pred: list[Entity],
    iou_threshold: float,
) -> tuple[int, list[int], list[int]]:
    """Greedy match by IoU + same label. Returns tp, unmatched gold idx, unmatched pred idx."""
    used_p: set[int] = set()
    used_g: set[int] = set()
    tp = 0
    # pairs sorted by iou desc
    pairs: list[tuple[float, int, int]] = []
    for gi, g in enumerate(gold):
        if g.start is None or g.end is None:
            continue
        for pi, p in enumerate(pred):
            if p.label != g.label:
                continue
            score = _iou(g.start, g.end, p.start, p.end)
            if score >= iou_threshold:
                pairs.append((score, gi, pi))
    pairs.sort(reverse=True)
    for _, gi, pi in pairs:
        if gi in used_g or pi in used_p:
            continue
        used_g.add(gi)
        used_p.add(pi)
        tp += 1

    # gold without offsets: fallback label_text
    for gi, g in enumerate(gold):
        if gi in used_g:
            continue
        if g.start is not None and g.end is not None:
            continue
        gkey = _norm_text(g.text)
        for pi, p in enumerate(pred):
            if pi in used_p:
                continue
            if p.label == g.label and _norm_text(p.text) == gkey:
                used_g.add(gi)
                used_p.add(pi)
                tp += 1
                break

    unmatched_g = [i for i in range(len(gold)) if i not in used_g]
    unmatched_p = [i for i in range(len(pred)) if i not in used_p]
    return tp, unmatched_g, unmatched_p


def evaluate(
    gold: Iterable[GoldSpan | dict],
    predicted: Iterable[Entity],
    *,
    mode: MatchMode = "label_text",
    labels: set[str] | None = None,
    iou_threshold: float = 0.5,
) -> EvaluationResult:
    """Сравнить gold и predicted entities.

    Modes:
      - exact: (start, end, label) — нужны offsets в gold
      - label_text: (label, normalized text) — устойчиво к границам NER
      - overlap: same label + IoU >= threshold
    """
    gold_list = [
        g if isinstance(g, GoldSpan) else GoldSpan.from_dict(g) for g in gold
    ]
    pred_list = list(predicted)

    if labels is not None:
        gold_list = [g for g in gold_list if g.label in labels]
        pred_list = [p for p in pred_list if p.label in labels]

    if mode == "overlap":
        tp, ug, up = _match_overlap(gold_list, pred_list, iou_threshold)
        unmatched_gold = [gold_list[i] for i in ug]
        unmatched_pred = [pred_list[i] for i in up]
        overall = _prf(
            tp,
            len(unmatched_pred),
            len(unmatched_gold),
            support_gold=len(gold_list),
            support_pred=len(pred_list),
        )
        # by label
        by_label: dict[str, PRF] = {}
        all_labels = {g.label for g in gold_list} | {p.label for p in pred_list}
        for lab in sorted(all_labels):
            g_sub = [g for g in gold_list if g.label == lab]
            p_sub = [p for p in pred_list if p.label == lab]
            tp_l, ug_l, up_l = _match_overlap(g_sub, p_sub, iou_threshold)
            by_label[lab] = _prf(
                tp_l, len(up_l), len(ug_l), len(g_sub), len(p_sub)
            )
        return EvaluationResult(
            overall=overall,
            by_label=by_label,
            mode=mode,
            unmatched_gold=unmatched_gold,
            unmatched_pred=unmatched_pred,
        )

    if mode == "exact":
        from collections import Counter

        def gold_key(g: GoldSpan) -> tuple:
            if g.start is None or g.end is None:
                return _key_label_text(g.label, g.text)
            return _key_exact(g.label, g.start, g.end)

        def pred_key(p: Entity) -> tuple:
            return _key_exact(p.label, p.start, p.end)

        gold_keys = Counter(gold_key(g) for g in gold_list)
        pred_keys = Counter(pred_key(p) for p in pred_list)
        tp = sum(min(gold_keys[k], pred_keys.get(k, 0)) for k in gold_keys)
        fp = sum(pred_keys.values()) - tp
        fn = sum(gold_keys.values()) - tp
        overall = _prf(tp, fp, fn, len(gold_list), len(pred_list))
        by_label: dict[str, PRF] = {}
        all_labels = {g.label for g in gold_list} | {p.label for p in pred_list}
        for lab in sorted(all_labels):
            gk = Counter(gold_key(g) for g in gold_list if g.label == lab)
            pk = Counter(pred_key(p) for p in pred_list if p.label == lab)
            tp_l = sum(min(gk[k], pk.get(k, 0)) for k in gk)
            by_label[lab] = _prf(
                tp_l,
                sum(pk.values()) - tp_l,
                sum(gk.values()) - tp_l,
                sum(1 for g in gold_list if g.label == lab),
                sum(1 for p in pred_list if p.label == lab),
            )
        unmatched_gold = []
        rem_p = pred_keys.copy()
        for g in gold_list:
            k = gold_key(g)
            if rem_p.get(k, 0) > 0:
                rem_p[k] -= 1
            else:
                unmatched_gold.append(g)
        unmatched_pred = []
        rem_g = gold_keys.copy()
        for p in pred_list:
            k = pred_key(p)
            if rem_g.get(k, 0) > 0:
                rem_g[k] -= 1
            else:
                unmatched_pred.append(p)
        return EvaluationResult(
            overall=overall,
            by_label=by_label,
            mode=mode,
            unmatched_gold=unmatched_gold,
            unmatched_pred=unmatched_pred,
        )

    # label_text: exact norm match or containment (устойчиво к NER/контексту)
    return _evaluate_label_text(gold_list, pred_list, mode)


def _texts_match(gold_text: str, pred_text: str) -> bool:
    g = _norm_text(gold_text)
    p = _norm_text(pred_text)
    if not g or not p:
        return False
    if g == p:
        return True
    # containment: gold in pred or pred in gold (min 4 chars to avoid noise)
    if len(g) >= 4 and g in p:
        return True
    if len(p) >= 4 and p in g:
        return True
    # digit-core match (TG id inside "Chat ID: -100…")
    g_digits = "".join(c for c in g if c.isdigit() or c == "-")
    p_digits = "".join(c for c in p if c.isdigit() or c == "-")
    if len(g_digits) >= 8 and g_digits in p_digits:
        return True
    if len(p_digits) >= 8 and p_digits in g_digits:
        return True
    return False


def _evaluate_label_text(
    gold_list: list[GoldSpan],
    pred_list: list[Entity],
    mode: str,
) -> EvaluationResult:
    used_p: set[int] = set()
    used_g: set[int] = set()

    # prefer longer gold first
    order = sorted(
        range(len(gold_list)),
        key=lambda i: len(gold_list[i].text),
        reverse=True,
    )
    for gi in order:
        g = gold_list[gi]
        best_pi = None
        best_len = -1
        for pi, p in enumerate(pred_list):
            if pi in used_p or p.label != g.label:
                continue
            if _texts_match(g.text, p.text):
                if len(p.text) > best_len:
                    best_len = len(p.text)
                    best_pi = pi
        if best_pi is not None:
            used_g.add(gi)
            used_p.add(best_pi)

    tp = len(used_g)
    unmatched_gold = [gold_list[i] for i in range(len(gold_list)) if i not in used_g]
    unmatched_pred = [pred_list[i] for i in range(len(pred_list)) if i not in used_p]
    fp = len(unmatched_pred)
    fn = len(unmatched_gold)
    overall = _prf(tp, fp, fn, len(gold_list), len(pred_list))

    by_label: dict[str, PRF] = {}
    all_labels = {g.label for g in gold_list} | {p.label for p in pred_list}
    for lab in sorted(all_labels):
        g_idx = [i for i, g in enumerate(gold_list) if g.label == lab]
        p_idx = [i for i, p in enumerate(pred_list) if p.label == lab]
        tp_l = sum(1 for i in g_idx if i in used_g)
        fn_l = sum(1 for i in g_idx if i not in used_g)
        fp_l = sum(1 for i in p_idx if i not in used_p)
        by_label[lab] = _prf(tp_l, fp_l, fn_l, len(g_idx), len(p_idx))

    return EvaluationResult(
        overall=overall,
        by_label=by_label,
        mode=mode,
        unmatched_gold=unmatched_gold,
        unmatched_pred=unmatched_pred,
    )
