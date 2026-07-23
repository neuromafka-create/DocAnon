from __future__ import annotations

import re
from collections.abc import Callable
from typing import Iterable

from core.models import Entity
from recognizers.inn_recognizer import InnRecognizer
from recognizers.snils_recognizer import SnilsRecognizer

# Выше = важнее при пересечении span'ов (при близком score)
ENTITY_PRIORITY: dict[str, int] = {
    "EMAIL_ADDRESS": 100,
    "CREDIT_CARD": 98,
    "MAC_ADDRESS": 96,
    "IP_ADDRESS": 94,
    "GPS_COORDS": 93,
    "RU_SNILS": 90,
    "RU_INN": 88,
    "RU_ACCOUNT": 86,
    "RU_OMS": 85,
    "RU_BIK": 84,
    "RU_VEHICLE_PLATE": 83,
    "RU_DRIVER_LICENSE": 82,
    "CRYPTO": 80,
    "IBAN_CODE": 79,
    "RU_PASSPORT": 70,
    "RU_INT_PASSPORT": 55,
    "PHONE_NUMBER": 60,
    "TG_CHAT_ID": 58,
    "PERSON": 50,
    "ORGANIZATION": 48,
    "LOCATION": 45,
    "GPE": 44,
    "DATE_TIME": 30,
    "NORP": 25,
    "EME_IMEI": 75,
}

# Ключевые слова рядом (±окно) повышают score
CONTEXT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "RU_PASSPORT": (
        "паспорт", "паспорта", "паспорту", "паспортные", "серия и номер",
    ),
    "RU_INT_PASSPORT": (
        "загран", "заграничн", "загранпаспорт",
    ),
    "PHONE_NUMBER": (
        "тел", "телефон", "моб", "мобильн", "phone", "факс", "звон",
    ),
    "RU_INN": ("инн", "идентификационн"),
    "RU_SNILS": ("снилс", "страховой номер"),
    "RU_BIK": ("бик", "банк"),
    "RU_ACCOUNT": (
        "р/с", "р.\\с", "расчётн", "расчетн", "счёт", "счет", "к/с", "корр",
    ),
    "RU_DRIVER_LICENSE": (
        "водительск", "в/у", "права", "удостоверен",
    ),
    "RU_VEHICLE_PLATE": (
        "госномер", "гос. номер", "грз", "автомоб", "машин", "номерной знак",
    ),
    "MAC_ADDRESS": ("mac", "мак-адрес", "мак адрес", "физический адрес"),
    "TG_CHAT_ID": (
        "telegram", "телеграм", "chat_id", "chatid", "tg_id", "tg id",
    ),
    "RU_OMS": ("омс", "полис"),
    "GPS_COORDS": ("gps", "координат", "широт", "долгот"),
}

# Анти-контекст: рядом эти слова → понижаем score
ANTI_CONTEXT: dict[str, tuple[str, ...]] = {
    "RU_PASSPORT": ("инн", "снилс", "бик", "р/с", "кпп"),
    "RU_INT_PASSPORT": ("инн", "кпп", "бик", "снилс", "телефон"),
    "PHONE_NUMBER": (
        "инн", "снилс", "паспорт", "бик", "р/с", "ip", "mac", "счёт", "счет",
    ),
    "TG_CHAT_ID": (
        "инн", "снилс", "паспорт", "бик", "телефон", "тел.", "ip", "кпп",
    ),
    "DATE_TIME": ("инн", "паспорт", "снилс"),
}

_IP_RE = re.compile(
    r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
)
_SNILS_FMT_RE = re.compile(r"^\d{3}-\d{3}-\d{3}\s*\d{2}$")
_MAC_RE = re.compile(
    r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$"
)
_TG_CHANNEL_RE = re.compile(r"^-100\d{10,}$")
_PHONE_PREFIX_RE = re.compile(
    r"^(?:\+?7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$"
    r"|^(?:\+?7|8)\d{10}$"
)


def _digits(text: str) -> str:
    return "".join(c for c in text if c.isdigit())


def _window(text: str, start: int, end: int, size: int = 48) -> str:
    return text[max(0, start - size) : min(len(text), end + size)].lower()


def _has_any(haystack: str, needles: Iterable[str]) -> bool:
    return any(n in haystack for n in needles)


def should_reject(entity: Entity, text: str) -> bool:
    """Структурные правила отсечения FP до/после score."""
    frag = entity.text.strip()
    label = entity.label
    digs = _digits(frag)
    ctx = _window(text, entity.start, entity.end)

    # служебные маркеры extract (xlsx sheet headers)
    if frag.startswith("===") or "\n===" in entity.text:
        return True
    if label in ("PERSON", "ORGANIZATION", "LOCATION") and "\n" in entity.text:
        return True

    if label == "RU_PASSPORT":
        # 10 цифр с валидной чексуммой ИНН → это ИНН, не паспорт
        if len(digs) == 10 and InnRecognizer._validate_inn(digs):
            return True
        # без намёка на паспорт и рядом «инн» — отбрасываем
        if not _has_any(ctx, CONTEXT_KEYWORDS["RU_PASSPORT"]):
            if _has_any(ctx, ANTI_CONTEXT["RU_PASSPORT"]):
                return True

    if label == "RU_INT_PASSPORT":
        # загран только с явным контекстом
        if not _has_any(ctx, CONTEXT_KEYWORDS["RU_INT_PASSPORT"]):
            return True
        if len(digs) == 9 and digs.startswith(("04", "01", "00")):
            # похоже на БИК
            if "бик" in ctx or "инн" in ctx or "кпп" in ctx:
                return True

    if label == "PHONE_NUMBER":
        if _IP_RE.match(frag) or _MAC_RE.match(frag):
            return True
        if _SNILS_FMT_RE.match(frag):
            return True
        if len(digs) == 11 and SnilsRecognizer._validate_snils(digs):
            # голый снилс без разделителей
            if "снилс" in ctx or not _PHONE_PREFIX_RE.match(frag.replace(" ", "")):
                if not frag.strip().startswith(("+", "8", "7")):
                    return True
        if len(digs) == 10 and InnRecognizer._validate_inn(digs):
            return True
        if len(digs) == 9:
            return True
        # 10 цифр без телефонного префикса/формата — часто паспорт/мусор
        if len(digs) == 10 and not _PHONE_PREFIX_RE.match(
            re.sub(r"[\s\-()]", "", frag)
        ):
            if not frag.strip().startswith(("+", "8", "7")):
                return True
        # IP-подобные куски
        if frag.count(".") >= 2:
            return True

    if label == "TG_CHAT_ID":
        if _TG_CHANNEL_RE.match(frag.replace(" ", "")):
            return False
        # произвольные числа — только с telegram-контекстом
        if not _has_any(ctx, CONTEXT_KEYWORDS["TG_CHAT_ID"]):
            return True
        if len(digs) in (9, 10, 11, 12) and (
            InnRecognizer._validate_inn(digs)
            if len(digs) in (10, 12)
            else False
        ):
            return True
        if len(digs) == 11 and SnilsRecognizer._validate_snils(digs):
            return True

    if label == "RU_INN":
        if not InnRecognizer._validate_inn(digs):
            return True

    if label == "RU_SNILS":
        if len(digs) != 11 or not SnilsRecognizer._validate_snils(digs):
            return True

    if label == "RU_DRIVER_LICENSE":
        letters = "".join(c for c in frag if c.isalpha())
        if len(letters) < 2 or len(digs) != 8:
            return True
        # 10 цифр без букв = не ВУ
        if not letters:
            return True

    if label == "DATE_TIME":
        # не маскируем чистые идентификаторы как даты
        if digs and len(digs) in (9, 10, 11, 12) and frag.replace(" ", "").isdigit():
            return True

    return False


def adjust_confidence(entity: Entity, text: str) -> float:
    """Context boost / penalty."""
    score = entity.confidence
    label = entity.label
    ctx = _window(text, entity.start, entity.end)

    keywords = CONTEXT_KEYWORDS.get(label)
    if keywords and _has_any(ctx, keywords):
        score = min(1.0, score + 0.15)

    anti = ANTI_CONTEXT.get(label)
    if anti and _has_any(ctx, anti):
        # не штрафуем, если одновременно есть позитивный контекст сильнее
        if not (keywords and _has_any(ctx, keywords)):
            score = max(0.0, score - 0.25)

    # TG channel id — всегда высокий
    if label == "TG_CHAT_ID" and _TG_CHANNEL_RE.match(entity.text.strip()):
        score = max(score, 0.95)

    return score


def _priority(label: str) -> int:
    return ENTITY_PRIORITY.get(label, 10)


def deduplicate_entities(entities: list[Entity]) -> list[Entity]:
    """Пересекающиеся span'ы: приоритет типа → confidence → длина."""
    if not entities:
        return entities

    def sort_key(e: Entity) -> tuple:
        return (
            e.start,
            -_priority(e.label),
            -e.confidence,
            -(e.end - e.start),
        )

    ordered = sorted(entities, key=sort_key)
    kept: list[Entity] = []

    for entity in ordered:
        conflict = False
        for i, existing in enumerate(kept):
            if entity.start < existing.end and entity.end > existing.start:
                conflict = True
                # решить, кто остаётся
                prefer_new = (
                    _priority(entity.label),
                    entity.confidence,
                    entity.end - entity.start,
                ) > (
                    _priority(existing.label),
                    existing.confidence,
                    existing.end - existing.start,
                )
                if prefer_new:
                    kept[i] = entity
                break
        if not conflict:
            kept.append(entity)

    kept.sort(key=lambda e: e.start)
    return kept


def filter_entities(
    entities: list[Entity],
    text: str,
    min_score: float = 0.5,
    threshold_for: Callable[[str], float] | None = None,
    thresholds: dict[str, float] | None = None,
) -> list[Entity]:
    """Полный post-process: reject → adjust score → per-type threshold → dedup.

    Порядок выбора порога для label:
    1. ``threshold_for(label)`` если передан (AnonymizerConfig.threshold_for)
    2. ``thresholds[label]`` если есть в dict
    3. иначе ``min_score`` (глобальный fallback)
    """
    refined: list[Entity] = []
    for entity in entities:
        if should_reject(entity, text):
            continue
        score = adjust_confidence(entity, text)

        if threshold_for is not None:
            threshold = threshold_for(entity.label)
        elif thresholds is not None and entity.label in thresholds:
            threshold = thresholds[entity.label]
        elif thresholds is not None:
            threshold = thresholds.get(entity.label, min_score)
        else:
            threshold = min_score

        if score < threshold:
            continue
        refined.append(
            Entity(
                text=entity.text,
                label=entity.label,
                start=entity.start,
                end=entity.end,
                confidence=score,
                source=entity.source,
            )
        )
    return deduplicate_entities(refined)
