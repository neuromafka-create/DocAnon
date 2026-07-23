from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import (
    PhoneRecognizer,
    EmailRecognizer,
    IpRecognizer,
    CreditCardRecognizer,
    IbanRecognizer,
    CryptoRecognizer,
)
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from core.config import AnonymizerConfig
from core.models import ENTITY_PLACEHOLDERS
from core.ner_config import ner_model_configuration_dict
from recognizers.inn_recognizer import InnRecognizer
from recognizers.snils_recognizer import SnilsRecognizer
from recognizers.passport_recognizer import PassportRfRecognizer, ZagranPassportRecognizer
from recognizers.driver_license import DriverLicenseRecognizer
from recognizers.oms_recognizer import OmsRecognizer
from recognizers.vehicle_plate import VehiclePlateRecognizer
from recognizers.tg_chat_id import TgChatIdRecognizer
from recognizers.geo_coords import GeoCoordsRecognizer
from recognizers.phone_recognizer import RuPhoneRecognizer
from recognizers.mac_recognizer import RuMacAddressRecognizer
from recognizers.bank_recognizer import RuAccountRecognizer, RuBikRecognizer

logger = logging.getLogger(__name__)

SPACY_MODEL = "ru_core_news_lg"


def _resource_root() -> Path | None:
    """Корень ресурсов PyInstaller (sys._MEIPASS) или None."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return None


def resolve_spacy_model() -> str:
    """Имя или путь к spaCy-модели (поддержка frozen exe)."""
    # 1) Явный env
    env = os.environ.get("DOCANON_SPACY_MODEL")
    if env:
        return env

    root = _resource_root()
    if root is not None:
        bundled = root / "ru_core_news_lg"
        if bundled.is_dir():
            return str(bundled)
        # иногда кладут в spacy/data
        alt = root / "spacy" / "data" / "ru_core_news_lg"
        if alt.is_dir():
            return str(alt)

    return SPACY_MODEL


def create_nlp_engine(config: AnonymizerConfig | None = None):
    """C1: spaCy NLP engine с явным PER/ORG/LOC → PERSON/ORGANIZATION/LOCATION."""
    if config is None:
        config = AnonymizerConfig()

    model_name = resolve_spacy_model()
    ner_score = config.ner_confidence_threshold
    # default_score для сущностей без score в модели; не ниже 0.5 для стабильности
    default_ner_score = max(0.5, min(0.95, ner_score + 0.5))

    logger.info("spaCy model: %s", model_name)
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "ru", "model_name": model_name}],
        "ner_model_configuration": ner_model_configuration_dict(
            default_score=default_ner_score
        ),
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    return provider.create_engine()


def create_recognizers() -> list:
    return [
        InnRecognizer(),
        SnilsRecognizer(),
        PassportRfRecognizer(),
        ZagranPassportRecognizer(),
        DriverLicenseRecognizer(),
        OmsRecognizer(),
        VehiclePlateRecognizer(),
        TgChatIdRecognizer(),
        GeoCoordsRecognizer(),
        RuPhoneRecognizer(),
        RuMacAddressRecognizer(),
        RuAccountRecognizer(),
        RuBikRecognizer(),
    ]


def build_analyzer(config: AnonymizerConfig | None = None) -> AnalyzerEngine:
    if config is None:
        config = AnonymizerConfig()

    logger.info("Инициализация NLP-движка (spaCy %s)...", SPACY_MODEL)
    nlp_engine = create_nlp_engine(config)

    logger.info("Регистрация распознавателей...")
    registry = RecognizerRegistry(supported_languages=["ru", "en"])
    registry.load_predefined_recognizers(nlp_engine=nlp_engine)

    for recognizer in create_recognizers():
        registry.add_recognizer(recognizer)

    for recognizer_cls in [
        PhoneRecognizer,
        EmailRecognizer,
        IpRecognizer,
        CreditCardRecognizer,
        IbanRecognizer,
        CryptoRecognizer,
    ]:
        registry.add_recognizer(recognizer_cls(supported_language="ru"))

    # C1: mapping PER→PERSON задан в ner_model_configuration;
    # фильтрация NER-типов — в analyze_text (ner_enabled / enabled_entity_types).
    logger.info(
        "NER mapping active (PER/ORG/LOC → PERSON/ORGANIZATION/LOCATION), "
        "ner_enabled=%s",
        config.ner_enabled,
    )

    logger.info("Создание AnalyzerEngine...")
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=nlp_engine,
        supported_languages=["ru", "en"],
    )

    return analyzer


def build_anonymizer() -> AnonymizerEngine:
    return AnonymizerEngine()


def get_operators(
    config: AnonymizerConfig | None = None,
) -> dict[str, OperatorConfig]:
    if config is None:
        config = AnonymizerConfig()

    operators = {}
    for entity_type in config.enabled_entity_types:
        placeholder = ENTITY_PLACEHOLDERS.get(entity_type, f"<{entity_type}>")
        operators[entity_type] = OperatorConfig(
            "replace", {"new_value": placeholder}
        )
    operators["DEFAULT"] = OperatorConfig("replace", {"new_value": "<ANONYMIZED>"})
    return operators
