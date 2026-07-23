from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from extractors import extract_text, get_extractor
from extractors.xlsx_extractor import XlsxExtractor


@pytest.fixture
def sample_xlsx(tmp_path: Path) -> Path:
    path = tmp_path / "clients.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Клиенты"
    ws.append(["Компания", "Контакт", "ИНН"])
    ws.append(["ООО «ВекторФуд»", "Егорова Марина Викторовна", "7707083893"])
    ws.append(["ООО «ГастроМаркет»", "Новиков Павел Игоревич", "500100732259"])

    ws2 = wb.create_sheet("Пустой")
    ws2.append([None, None])

    wb.save(path)
    return path


class TestXlsxExtractor:
    def test_can_handle(self) -> None:
        ext = XlsxExtractor()
        assert ext.can_handle(Path("a.xlsx"))
        assert ext.can_handle(Path("a.xlsm"))
        assert not ext.can_handle(Path("a.xls"))
        assert not ext.can_handle(Path("a.docx"))

    def test_factory_picks_xlsx(self, sample_xlsx: Path) -> None:
        extractor = get_extractor(sample_xlsx)
        assert isinstance(extractor, XlsxExtractor)

    def test_extract_content(self, sample_xlsx: Path) -> None:
        result = extract_text(sample_xlsx)
        assert result.source_format == "xlsx"
        assert "=== Клиенты ===" in result.text
        assert "Егорова Марина Викторовна" in result.text
        assert "7707083893" in result.text
        assert " | " in result.text
        assert result.metadata["rows"] == 3
        # empty sheet omitted
        assert "Пустой" not in result.text

    def test_real_test_docs(self) -> None:
        path = Path("test_docs/Клиенты.xlsx")
        if not path.exists():
            pytest.skip("test_docs not present")
        result = extract_text(path)
        assert result.source_format == "xlsx"
        assert len(result.text) > 0
        assert "Контакт" in result.text or "Компания" in result.text
