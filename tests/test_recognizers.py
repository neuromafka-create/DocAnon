from __future__ import annotations

import pytest

from recognizers.inn_recognizer import InnRecognizer
from recognizers.snils_recognizer import SnilsRecognizer
from recognizers.passport_recognizer import PassportRfRecognizer
from recognizers.driver_license import DriverLicenseRecognizer
from recognizers.vehicle_plate import VehiclePlateRecognizer
from recognizers.phone_recognizer import RuPhoneRecognizer
from recognizers.bank_recognizer import RuAccountRecognizer, RuBikRecognizer


class TestInnRecognizer:
    def test_validate_inn_10_valid(self) -> None:
        assert InnRecognizer._validate_inn("7707083893") is True

    def test_validate_inn_10_invalid(self) -> None:
        assert InnRecognizer._validate_inn("1234567890") is False

    def test_validate_inn_12_valid(self) -> None:
        assert InnRecognizer._validate_inn("500100732259") is True

    def test_validate_inn_12_invalid(self) -> None:
        assert InnRecognizer._validate_inn("123456789012") is False

    def test_validate_inn_wrong_length(self) -> None:
        assert InnRecognizer._validate_inn("12345") is False

    def test_validate_inn_non_digit(self) -> None:
        assert InnRecognizer._validate_inn("abcde") is False


class TestSnilsRecognizer:
    def test_validate_snils_valid(self) -> None:
        assert SnilsRecognizer._validate_snils("12345678964") is True

    def test_validate_snils_zeroes(self) -> None:
        assert SnilsRecognizer._validate_snils("00000000000") is False

    def test_validate_snils_wrong_length(self) -> None:
        assert SnilsRecognizer._validate_snils("12345") is False


class TestPassportRecognizer:
    def setup_method(self) -> None:
        self.r = PassportRfRecognizer()

    def test_validate_ok(self) -> None:
        assert self.r.validate_result("45 12 345678") >= 0.9
        assert self.r.validate_result("4512345678") >= 0.9

    def test_validate_bad(self) -> None:
        assert self.r.validate_result("123") == 0.0


class TestDriverLicense:
    def setup_method(self) -> None:
        self.r = DriverLicenseRecognizer()

    def test_validate_ok(self) -> None:
        assert self.r.validate_result("77 АВ 123456") >= 0.9

    def test_validate_inn_not_license(self) -> None:
        assert self.r.validate_result("7707083893") == 0.0


class TestPhoneRecognizer:
    def setup_method(self) -> None:
        self.r = RuPhoneRecognizer()

    def test_validate_plus7(self) -> None:
        assert self.r.validate_result("+7 495 123 45 67") >= 0.9

    def test_validate_8(self) -> None:
        assert self.r.validate_result("8 900 123-45-67") >= 0.9

    def test_validate_short(self) -> None:
        assert self.r.validate_result("12345") == 0.0


class TestBankRecognizers:
    def test_account_ok(self) -> None:
        r = RuAccountRecognizer()
        assert r.validate_result("40702810400000000001") >= 0.9

    def test_account_bad_len(self) -> None:
        r = RuAccountRecognizer()
        assert r.validate_result("123") == 0.0

    def test_bik_ok(self) -> None:
        r = RuBikRecognizer()
        assert r.validate_result("044525225") >= 0.9

    def test_bik_reject_random(self) -> None:
        r = RuBikRecognizer()
        assert r.validate_result("123456789") == 0.0


@pytest.fixture(scope="module")
def contract_result():
    from pathlib import Path
    from core.config import AnonymizerConfig
    from core.pipeline import AnonymizationPipeline

    text = Path("tests/fixtures/test_contract.txt").read_text(encoding="utf-8")
    return AnonymizationPipeline(AnonymizerConfig()).process_text(text)


class TestPipelineContract:
    """Интеграция: fixture test_contract — structured PII (B1)."""

    def test_pipeline_basic(self) -> None:
        from core.config import AnonymizerConfig
        from core.pipeline import AnonymizationPipeline

        text = (
            "Контактное лицо: Иванов Иван Иванович, "
            "ИНН 7707083893, тел. +7 495 123 45 67"
        )
        result = AnonymizationPipeline(AnonymizerConfig()).process_text(text)
        assert result.total_entities > 0
        assert "7707083893" not in result.anonymized_text
        assert "+7 495 123 45 67" not in result.anonymized_text

    def test_contract_inn_snils_email(self, contract_result) -> None:
        anon = contract_result.anonymized_text
        assert "7707083893" not in anon
        assert "500100732259" not in anon
        assert "123-456-789 64" not in anon
        assert "ivanov@rogaikopyta.ru" not in anon

    def test_contract_passport(self, contract_result) -> None:
        assert "45 12 345678" not in contract_result.anonymized_text
        assert any(e.label == "RU_PASSPORT" for e in contract_result.entities)

    def test_contract_phone(self, contract_result) -> None:
        assert "+7 495 123 45 67" not in contract_result.anonymized_text
        assert any(e.label == "PHONE_NUMBER" for e in contract_result.entities)

    def test_contract_vehicle_plate(self, contract_result) -> None:
        assert "А123БВ 777" not in contract_result.anonymized_text
        assert any(e.label == "RU_VEHICLE_PLATE" for e in contract_result.entities)

    def test_contract_driver_license(self, contract_result) -> None:
        assert "77 АВ 123456" not in contract_result.anonymized_text
        assert any(e.label == "RU_DRIVER_LICENSE" for e in contract_result.entities)

    def test_contract_mac(self, contract_result) -> None:
        assert "00:1A:2B:3C:4D:5E" not in contract_result.anonymized_text
        assert any(e.label == "MAC_ADDRESS" for e in contract_result.entities)

    def test_contract_bank(self, contract_result) -> None:
        assert "40702810400000000001" not in contract_result.anonymized_text
        assert "044525225" not in contract_result.anonymized_text
        labels = {e.label for e in contract_result.entities}
        assert "RU_ACCOUNT" in labels
        assert "RU_BIK" in labels

    def test_contract_card_ip_geo_tg(self, contract_result) -> None:
        anon = contract_result.anonymized_text
        assert "4111 1111 1111 1111" not in anon
        assert "192.168.1.100" not in anon
        assert "55.7558, 37.6173" not in anon
        assert "-1001234567890" not in anon
