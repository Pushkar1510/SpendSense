from __future__ import annotations

import io
import json
import re
from datetime import datetime

import pdfplumber

from app.config import DEFAULT_CURRENCY
from app.services.ingest_csv import dedupe_hash

LINE_RE = re.compile(
    r"(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(?P<desc>.+?)\s+(?P<amount>\d+(?:\.\d+)?)\s*(?P<dc>DR|CR|Dr|Cr)?\s*$"
)


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


def parse_pdf_bytes(data: bytes) -> list[dict]:
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    except Exception as exc:  # noqa: BLE001 — surface as unreadable PDF
        raise ValueError("unreadable or scanned PDF; export CSV") from exc
    if not text.strip():
        raise ValueError("unreadable or scanned PDF; export CSV")
    rows = parse_pdf_text(text)
    if not rows:
        raise ValueError("unreadable or scanned PDF; export CSV")
    return rows
