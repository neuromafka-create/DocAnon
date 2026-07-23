from __future__ import annotations

from core.entity_filter import (
    adjust_confidence,
    deduplicate_entities,
    filter_entities,
    should_reject,
)
from core.models import Entity


def _e(text: str, label: str, start: int, end: int, conf: float = 0.7) -> Entity:
    return Entity(text=text, label=label, start=start, end=end, confidence=conf)


class TestShouldReject:
    def test_passport_that_is_valid_inn(self) -> None:
        text = "ИНН 7707083893"
        ent = _e("7707083893", "RU_PASSPORT", 4, 14, 0.9)
        assert should_reject(ent, text) is True

    def test_real_passport_kept(self) -> None:
        text = "Паспорт: 45 12 345678"
        ent = _e("45 12 345678", "RU_PASSPORT", 9, 21, 0.85)
        assert should_reject(ent, text) is False

    def test_phone_ip_rejected(self) -> None:
        text = "IP-адрес: 192.168.1.100"
        ent = _e("192.168.1.100", "PHONE_NUMBER", 10, 23, 0.6)
        assert should_reject(ent, text) is True

    def test_phone_snils_format_rejected(self) -> None:
        text = "СНИЛС: 123-456-789 64"
        ent = _e("123-456-789 64", "PHONE_NUMBER", 7, 21, 0.6)
        assert should_reject(ent, text) is True

    def test_tg_random_digits_without_context(self) -> None:
        text = "КПП 770701001"
        ent = _e("770701001", "TG_CHAT_ID", 4, 13, 0.6)
        assert should_reject(ent, text) is True

    def test_tg_channel_kept(self) -> None:
        text = "Telegram Chat ID: -1001234567890"
        ent = _e("-1001234567890", "TG_CHAT_ID", 18, 32, 0.95)
        assert should_reject(ent, text) is False

    def test_zagran_without_context_rejected(self) -> None:
        text = "БИК 044525225"
        ent = _e("044525225", "RU_INT_PASSPORT", 4, 13, 0.6)
        assert should_reject(ent, text) is True


class TestPriorityDedup:
    def test_inn_wins_over_passport_same_span(self) -> None:
        text = "ИНН 7707083893"
        entities = [
            _e("7707083893", "RU_PASSPORT", 4, 14, 0.9),
            _e("7707083893", "RU_INN", 4, 14, 0.95),
        ]
        # after reject passport-as-inn
        result = filter_entities(entities, text, min_score=0.5)
        assert len(result) == 1
        assert result[0].label == "RU_INN"

    def test_priority_when_both_pass(self) -> None:
        # overlapping different labels — higher priority wins
        entities = [
            _e("test@mail.ru", "EMAIL_ADDRESS", 0, 12, 0.8),
            _e("test@mail.ru", "PERSON", 0, 12, 0.99),
        ]
        text = "test@mail.ru"
        result = deduplicate_entities(entities)
        assert len(result) == 1
        assert result[0].label == "EMAIL_ADDRESS"


class TestContextBoost:
    def test_boost_with_keyword(self) -> None:
        text = "Телефон: +7 495 123 45 67"
        ent = _e("+7 495 123 45 67", "PHONE_NUMBER", 9, 26, 0.5)
        boosted = adjust_confidence(ent, text)
        assert boosted > ent.confidence

    def test_penalty_anti_context(self) -> None:
        text = "ИНН организации 4512345678"
        # not valid inn checksum necessarily — still anti-context for passport
        ent = _e("4512345678", "RU_PASSPORT", 16, 26, 0.8)
        score = adjust_confidence(ent, text)
        assert score < ent.confidence


class TestFilterIntegration:
    def test_contract_no_inn_as_passport(self) -> None:
        from pathlib import Path
        from core.config import AnonymizerConfig
        from core.pipeline import AnonymizationPipeline

        text = Path("tests/fixtures/test_contract.txt").read_text(encoding="utf-8")
        result = AnonymizationPipeline(AnonymizerConfig()).process_text(text)

        # ИНН не должен уйти в PASSPORT
        for e in result.entities:
            if e.text in ("7707083893", "500100732259"):
                assert e.label == "RU_INN"

        # КПП / БИК не телефон и не TG
        for e in result.entities:
            if e.text in ("770701001", "044525225"):
                assert e.label not in ("PHONE_NUMBER", "TG_CHAT_ID", "RU_PASSPORT")

        # SNILS format not phone
        assert not any(
            e.label == "PHONE_NUMBER" and "123-456-789" in e.text
            for e in result.entities
        )

        # still catch real PII
        labels = {e.label for e in result.entities}
        assert "RU_PASSPORT" in labels
        assert "PHONE_NUMBER" in labels
        assert "MAC_ADDRESS" in labels
        assert "RU_VEHICLE_PLATE" in labels
