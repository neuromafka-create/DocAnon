from __future__ import annotations

"""C3: канонический ключ ФИО для согласованных placeholder'ов.

«Иванов», «Иванову», «ИВАНОВ» → один ключ ``иванов``.
«Егорова Марина» / «Егоровой Марине» → ``егоров марина``.
"""

import re

from core.morpho import _is_name_parse, _morph


def _lemma_token(token: str) -> str:
    token = token.strip(".,;:«»\"'()[]")
    if not token:
        return ""
    # Инициал
    if re.fullmatch(r"[А-ЯA-Z]", token):
        return token[0].upper() + "."

    low = token.lower()
    # Типичные женские фамилии: не схлопывать «Егорова» в «егоров»
    fem_hint = low.endswith(
        ("ова", "ева", "ёва", "ина", "ына", "ая", "яя", "ой", "ей")
    )

    morph = _morph()
    parses = morph.parse(token)
    ranked = sorted(
        parses,
        key=lambda p: (
            0 if _is_name_parse(p.tag) else 1,
            0 if (fem_hint and "femn" in p.tag) else 1,
            0 if "Surn" in p.tag else 1,
            -p.score,
        ),
    )
    for p in ranked[:5]:
        if _is_name_parse(p.tag) or "Surn" in p.tag or p.score >= 0.1:
            try:
                # женский nomn sing, если намекает окончание
                if fem_hint and "femn" in p.tag:
                    nomn = p.inflect({"nomn", "sing"})
                    if nomn is not None:
                        return nomn.word.lower()
                nomn = p.inflect({"nomn"})
                if nomn is not None:
                    word = nomn.word.lower()
                    # если inflect дал мужскую «егоров» из «егоровой»,
                    # оставим fem normal_form
                    if fem_hint and word.endswith("ов") and not word.endswith("ова"):
                        if "femn" in p.tag:
                            return p.normal_form.lower()
                    return word
            except Exception:
                pass
            return p.normal_form.lower()
    return token.lower()


def person_canonical(text: str) -> str:
    """Канонический ключ ФИО (нижний регистр, леммы токенов)."""
    tokens = re.findall(r"[А-Яа-яЁёA-Za-z]+\.?", text.strip())
    if not tokens:
        return text.strip().lower()
    lemmas = [_lemma_token(t) for t in tokens]
    lemmas = [L for L in lemmas if L]
    return " ".join(lemmas)


def surname_key(canon: str) -> str:
    """Первый токен канона (фамилия) для связи partial/full FIO."""
    if not canon:
        return ""
    return canon.split()[0]
