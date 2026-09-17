from __future__ import annotations

import io
import json
import logging
import re
from datetime import datetime

import pdfplumber

from app.config import DEFAULT_CURRENCY
from app.services.ingest_csv import dedupe_hash

logger = logging.getLogger(__name__)

LINE_RE = re.compile(
    r"(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(?P<desc>.+?)\s+(?P<amount>\d+(?:\.\d+)?)\s*(?P<dc>DR|CR|Dr|Cr)?\s*$"
)

OCR_UNAVAILABLE_MSG = (
    "unreadable or scanned PDF; install tesseract-ocr for local OCR, or export CSV"
)
OCR_FAILED_MSG = "unreadable or scanned PDF; OCR found no transactions — export CSV"


def _to_iso(date_str: str) -> str:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"unparseable date: {date_str}")


def parse_pdf_text(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        m = LINE_RE.search(line.strip())
        if not m:
            continue
        amount = float(m.group("amount"))
        dc = (m.group("dc") or "DR").upper()
        if dc == "DR":
            amount = -abs(amount)
        else:
            amount = abs(amount)
        description = m.group("desc").strip()
        txn_date = _to_iso(m.group("date"))
        rows.append(
            {
                "txn_date": txn_date,
                "description": description,
                "amount": amount,
                "currency": DEFAULT_CURRENCY,
                "raw_json": json.dumps({"line": line}),
                "dedupe_hash": dedupe_hash(txn_date, amount, description),
            }
        )
    return rows


def tesseract_available() -> bool:
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_pdf_bytes(data: bytes, *, max_pages: int = 20, dpi_scale: float = 2.0) -> str:
    """Rasterize PDF pages and OCR with local Tesseract. Requires tesseract-ocr installed."""
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image

    if not tesseract_available():
        raise RuntimeError("tesseract binary not available")

    doc = fitz.open(stream=data, filetype="pdf")
    try:
        if doc.page_count == 0:
            return ""
        matrix = fitz.Matrix(dpi_scale, dpi_scale)
        chunks: list[str] = []
        for index, page in enumerate(doc):
            if index >= max_pages:
                break
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            chunks.append(pytesseract.image_to_string(image))
        return "\n".join(chunks)
    finally:
        doc.close()


def _extract_text_pdfplumber(data: bytes) -> str:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def parse_pdf_bytes(data: bytes) -> list[dict]:
    text = ""
    try:
        text = _extract_text_pdfplumber(data)
    except Exception as exc:  # noqa: BLE001 — try OCR next
        logger.debug("pdfplumber failed: %s", exc)

    if text.strip():
        rows = parse_pdf_text(text)
        if rows:
            return rows

    # Scanned / image PDF — optional local Tesseract fallback
    if not tesseract_available():
        raise ValueError(OCR_UNAVAILABLE_MSG)

    try:
        ocr_text = ocr_pdf_bytes(data)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(OCR_FAILED_MSG) from exc

    rows = parse_pdf_text(ocr_text)
    if not rows:
        raise ValueError(OCR_FAILED_MSG)
    return rows
