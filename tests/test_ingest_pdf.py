from pathlib import Path

import pytest

from app.services.ingest_pdf import parse_pdf_text, parse_pdf_bytes


FIXTURE_TXT = Path(__file__).parent / "fixtures" / "sample_statement.txt"


def test_parse_pdf_text_extracts_signed_amounts():
    rows = parse_pdf_text(FIXTURE_TXT.read_text())
    assert len(rows) >= 3
    swiggy = next(r for r in rows if "SWIGGY" in r["description"])
    assert swiggy["amount"] == -450.0
    salary = next(r for r in rows if "SALARY" in r["description"])
    assert salary["amount"] == 75000.0


def test_parse_pdf_bytes_empty_raises():
    # Minimal PDF with no extractable text is hard inline; empty bytes should fail clearly
    with pytest.raises(ValueError, match="CSV"):
        parse_pdf_bytes(b"%PDF-1.4 empty")
