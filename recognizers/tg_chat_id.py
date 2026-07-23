from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class TgChatIdRecognizer(PatternRecognizer):
    """Telegram Chat / Channel ID.

    Только явные формы ``-100…`` или числа рядом с telegram-контекстом
    (широкий ``\\d{5,15}`` убран — давал FP на ИНН/БИК/КПП).
    """

    ENTITY = "TG_CHAT_ID"
    LANGUAGE = "ru"

    def __init__(self) -> None:
        patterns = [
            Pattern(
                name="tg_channel",
                regex=r"(?<!\d)-100\d{10,}(?!\d)",
                score=0.95,
            ),
            Pattern(
                name="tg_id_labeled",
                # id: 123456789 / chat_id=12345
                regex=r"(?i)(?:chat[_\s-]?id|tg[_\s-]?id|telegram\s*id)\s*[=:]?\s*-?\d{5,15}\b",
                score=0.85,
            ),
        ]
        context = [
            "chat_id",
            "chatid",
            "телеграм",
            "telegram",
            "tg_id",
            "чат",
        ]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
            name="TgChatIdRecognizer",
        )

    def validate_result(self, pattern_text: str) -> float:
        text = pattern_text.strip()
        # извлечь числовую часть
        digits = "".join(c for c in text if c.isdigit() or c == "-")
        if digits.startswith("-100") and len(digits) >= 13:
            return 0.98
        # labeled match — оставить score
        if any(k in text.lower() for k in ("chat", "tg", "telegram", "id")):
            pure = "".join(c for c in text if c.isdigit())
            if 5 <= len(pure) <= 15:
                return 0.9
        return 0.0
