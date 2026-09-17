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


def test_parse_pdf_bytes_no_text_without_tesseract_raises(monkeypatch):
    class FakePage:
        def extract_text(self):
            return ""

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("app.services.ingest_pdf.pdfplumber.open", lambda *_a, **_k: FakePdf())
    monkeypatch.setattr("app.services.ingest_pdf.tesseract_available", lambda: False)
    with pytest.raises(ValueError, match="tesseract-ocr|CSV"):
        parse_pdf_bytes(b"fake")


def test_parse_pdf_bytes_ocr_fallback(monkeypatch):
    class FakePage:
        def extract_text(self):
            return ""

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("app.services.ingest_pdf.pdfplumber.open", lambda *_a, **_k: FakePdf())
    monkeypatch.setattr("app.services.ingest_pdf.tesseract_available", lambda: True)
    monkeypatch.setattr(
        "app.services.ingest_pdf.ocr_pdf_bytes",
        lambda *_a, **_k: FIXTURE_TXT.read_text(),
    )
    rows = parse_pdf_bytes(b"fake-scanned")
    assert len(rows) >= 3
    assert any("SWIGGY" in r["description"] for r in rows)


def test_parse_pdf_bytes_ocr_no_rows_raises(monkeypatch):
    class FakePage:
        def extract_text(self):
            return ""

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("app.services.ingest_pdf.pdfplumber.open", lambda *_a, **_k: FakePdf())
    monkeypatch.setattr("app.services.ingest_pdf.tesseract_available", lambda: True)
    monkeypatch.setattr("app.services.ingest_pdf.ocr_pdf_bytes", lambda *_a, **_k: "noise only")
    with pytest.raises(ValueError, match="CSV"):
        parse_pdf_bytes(b"fake")
