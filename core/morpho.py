from __future__ import annotations

import logging
import re
from functools import lru_cache

from core.models import Entity

logger = logging.getLogger(__name__)

# Грамматические падежи для склонения ФИО
_CASES = ("nomn", "gent", "datv", "accs", "ablt", "loct")

# Граница слова (кириллица/латиница)
_WORD_BOUND = r"(?<![А-Яа-яЁёA-Za-z]){0}(?![А-Яа-яЁёA-Za-z])"


@lru_cache(maxsize=1)
def _morph():
    import pymorphy3

    return pymorphy3.MorphAnalyzer()


def _is_name_parse(tag) -> bool:
    return bool(tag.grammemes & {"Name", "Surn", "Patr"})


def is_person_name_token(token: str) -> bool:
    """Токен похож на имя/фамилию/отчество (pymorphy3)."""
    raw = token.strip()
    # Инициалы: А. / А (до strip точек)
    if re.fullmatch(r"[А-ЯA-Z]\.?", raw):
        return True
    token = raw.strip(".,;:«»\"'()[]")
    if len(token) < 2 or not any(c.isalpha() for c in token):
        return False
    if re.fullmatch(r"[А-ЯA-Z]\.?", token):
        return True
    morph = _morph()
    for p in morph.parse(token)[:5]:
        if _is_name_parse(p.tag):
            return True
    # NER уже сказал PERSON — допускаем Capitalized word
    if token[0].isupper() and len(token) >= 3:
        return True
    return False


def generate_name_forms(token: str) -> set[str]:
    """Все разумные словоформы имени/фамилии."""
    token = token.strip(".,;:«»\"'()[]")
    if not token:
        return set()
    if re.fullmatch(r"[А-ЯA-Z]\.?", token):
        base = token[0]
        return {base, base + ".", base.lower(), base.lower() + "."}

    forms: set[str] = {token, token.lower(), token.capitalize()}
    morph = _morph()
    parses = morph.parse(token)
    # предпочитаем разборы Name/Surn/Patr
    ranked = sorted(
        parses,
        key=lambda p: (0 if _is_name_parse(p.tag) else 1, -p.score),
    )
    for p in ranked[:4]:
        forms.add(p.normal_form)
        forms.add(p.normal_form.capitalize())
        if _is_name_parse(p.tag) or p.score >= 0.3:
            for case in _CASES:
                try:
                    inf = p.inflect({case})
                except Exception:
                    inf = None
                if inf is not None:
                    forms.add(inf.word)
                    forms.add(inf.word.capitalize())
                    forms.add(inf.word.lower())
            # полный lexeme — дорого, берём sparingly
            try:
                for form in p.lexeme[:24]:
                    forms.add(form.word)
                    forms.add(form.word.capitalize())
            except Exception:
                pass
    return {f for f in forms if f and len(f) >= 2}


def find_form_spans(text: str, forms: set[str]) -> list[tuple[int, int, str]]:
    """Найти вхождения форм в тексте (длинные первыми)."""
    spans: list[tuple[int, int, str]] = []
    # уникальные по lower, но ищем case-insensitive с сохранением среза
    seen_keys: set[str] = set()
    ordered = sorted(forms, key=len, reverse=True)
    for form in ordered:
        key = form.lower()
        if key in seen_keys or len(form) < 2:
            continue
        seen_keys.add(key)
        try:
            pattern = _WORD_BOUND.format(re.escape(form))
        except re.error:
            continue
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            spans.append((m.start(), m.end(), text[m.start() : m.end()]))
    return spans


def merge_adjacent_persons(
    entities: list[Entity],
    text: str,
    max_gap: int = 2,
) -> list[Entity]:
    """Склеить соседние PERSON (spaCy часто режет ФИО на 2–3 span'а)."""
    persons = sorted(
        [e for e in entities if e.label == "PERSON"],
        key=lambda e: e.start,
    )
    others = [e for e in entities if e.label != "PERSON"]
    if not persons:
        return entities

    merged: list[Entity] = []
    cur = persons[0]
    for nxt in persons[1:]:
        gap = text[cur.end : nxt.start]
        if len(gap) <= max_gap and gap.strip() == "":
            cur = Entity(
                text=text[cur.start : nxt.end],
                label="PERSON",
                start=cur.start,
                end=nxt.end,
                confidence=min(cur.confidence, nxt.confidence),
                source="ner_merged",
            )
        else:
            merged.append(cur)
            cur = nxt
    merged.append(cur)
    return others + merged


def expand_person_morphology(
    text: str,
    entities: list[Entity],
    *,
    min_token_len: int = 3,
) -> list[Entity]:
    """C2: по найденным PERSON добавить вхождения тех же имён в других падежах.

    Также склеивает соседние PERSON-span'ы.
    """
    entities = merge_adjacent_persons(entities, text)

    person_entities = [e for e in entities if e.label == "PERSON"]
    if not person_entities:
        return entities

    # spans, уже занятые (любые сущности)
    occupied: list[tuple[int, int]] = [(e.start, e.end) for e in entities]

    def overlaps(start: int, end: int) -> bool:
        for a, b in occupied:
            if start < b and end > a:
                return True
        return False

    # собрать токены-имена из PERSON
    seed_tokens: list[tuple[str, float]] = []
    for ent in person_entities:
        for raw in re.findall(r"[А-Яа-яЁёA-Za-z]+\.?", ent.text):
            if len(raw.rstrip(".")) < min_token_len and not re.fullmatch(
                r"[А-ЯA-Z]\.?", raw
            ):
                continue
            if is_person_name_token(raw):
                seed_tokens.append((raw, ent.confidence))

    if not seed_tokens:
        return entities

    new_entities: list[Entity] = []
    for token, conf in seed_tokens:
        forms = generate_name_forms(token)
        for start, end, matched in find_form_spans(text, forms):
            if overlaps(start, end):
                continue
            # не раздуваем на союзы/мусор
            if not is_person_name_token(matched) and matched.lower() not in {
                f.lower() for f in forms
            }:
                continue
            ent = Entity(
                text=matched,
                label="PERSON",
                start=start,
                end=end,
                confidence=min(0.9, conf * 0.95),
                source="morpho",
            )
            new_entities.append(ent)
            occupied.append((start, end))

    if new_entities:
        logger.debug(
            "morpho: +%d PERSON spans from %d seed tokens",
            len(new_entities),
            len(seed_tokens),
        )

    combined = entities + new_entities
    # повторный merge (новые формы рядом со старыми не склеиваем — разные offset)
    return combined
