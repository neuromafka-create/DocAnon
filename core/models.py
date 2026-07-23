from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EntityType(str, Enum):
    PERSON = "PERSON"
    PHONE = "PHONE_NUMBER"
    EMAIL = "EMAIL_ADDRESS"
    IP = "IP_ADDRESS"
    INN = "RU_INN"
    SNILS = "RU_SNILS"
    PASSPORT = "RU_PASSPORT"
    PASSPORT_INT = "RU_INT_PASSPORT"
    DRIVER_LICENSE = "RU_DRIVER_LICENSE"
    OMS = "RU_OMS"
    VEHICLE_PLATE = "RU_VEHICLE_PLATE"
    TG_CHAT_ID = "TG_CHAT_ID"
    GPS_COORDS = "GPS_COORDS"
    CREDIT_CARD = "CREDIT_CARD"
    IBAN = "IBAN_CODE"
    ACCOUNT = "RU_ACCOUNT"
    BIK = "RU_BIK"
    CRYPTO = "CRYPTO"
    MAC = "MAC_ADDRESS"
    IMEI = "EME_IMEI"
    ORG = "ORGANIZATION"
    LOC = "LOCATION"
    GPE = "GPE"
    DATE = "DATE_TIME"
    NORP = "NORP"


ENTITY_LABELS_RU: dict[str, str] = {
    "PERSON": "ФИО",
    "PHONE_NUMBER": "Телефон",
    "EMAIL_ADDRESS": "Email",
    "IP_ADDRESS": "IP-адрес",
    "RU_INN": "ИНН",
    "RU_SNILS": "СНИЛС",
    "RU_PASSPORT": "Паспорт РФ",
    "RU_INT_PASSPORT": "Загранпаспорт",
    "RU_DRIVER_LICENSE": "Вод. удостоверение",
    "RU_OMS": "Полис ОМС",
    "RU_VEHICLE_PLATE": "Госномер",
    "TG_CHAT_ID": "Telegram ID",
    "GPS_COORDS": "GPS-координаты",
    "CREDIT_CARD": "Кредитная карта",
    "IBAN_CODE": "IBAN",
    "RU_ACCOUNT": "Расчётный счёт",
    "RU_BIK": "БИК",
    "CRYPTO": "Криптокошелёк",
    "MAC_ADDRESS": "MAC-адрес",
    "EME_IMEI": "IMEI",
    "ORGANIZATION": "Организация",
    "LOCATION": "Адрес",
    "GPE": "Город/Страна",
    "DATE_TIME": "Дата",
    "NORP": "Национальность",
}

ENTITY_PLACEHOLDERS: dict[str, str] = {
    "PERSON": "<PERSON>",
    "PHONE_NUMBER": "<PHONE>",
    "EMAIL_ADDRESS": "<EMAIL>",
    "IP_ADDRESS": "<IP>",
    "RU_INN": "<INN>",
    "RU_SNILS": "<SNILS>",
    "RU_PASSPORT": "<PASSPORT_RF>",
    "RU_INT_PASSPORT": "<PASSPORT_INT>",
    "RU_DRIVER_LICENSE": "<DRIVER_LICENSE>",
    "RU_OMS": "<OMS>",
    "RU_VEHICLE_PLATE": "<CAR_PLATE>",
    "TG_CHAT_ID": "<TG_CHAT_ID>",
    "GPS_COORDS": "<GEO>",
    "CREDIT_CARD": "<BANK_CARD>",
    "IBAN_CODE": "<IBAN>",
    "RU_ACCOUNT": "<ACCOUNT>",
    "RU_BIK": "<BIK>",
    "CRYPTO": "<WALLET>",
    "MAC_ADDRESS": "<MAC>",
    "EME_IMEI": "<IMEI>",
    "ORGANIZATION": "<ORG>",
    "LOCATION": "<LOC>",
    "GPE": "<LOC>",
    "DATE_TIME": "<DATE>",
    "NORP": "<GROUP>",
}


@dataclass
class Entity:
    text: str
    label: str
    start: int
    end: int
    confidence: float
    source: str = "presidio"

    @property
    def label_ru(self) -> str:
        return ENTITY_LABELS_RU.get(self.label, self.label)

    @property
    def placeholder(self) -> str:
        return ENTITY_PLACEHOLDERS.get(self.label, f"<{self.label}>")


@dataclass
class ExtractionResult:
    text: str
    source_format: str
    pages: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        if self.pages:
            return "\n\n".join(self.pages)
        return self.text


@dataclass
class AnonymizedDocument:
    original_text: str
    anonymized_text: str
    entities: list[Entity] = field(default_factory=list)
    mapping: dict[str, str] = field(default_factory=dict)
    source_file: str = ""
    source_path: str = ""

    @property
    def stats(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self.entities:
            counts[e.label] = counts.get(e.label, 0) + 1
        return counts

    @property
    def total_entities(self) -> int:
        return len(self.entities)
