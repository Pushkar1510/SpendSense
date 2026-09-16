from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import datetime

import pandas as pd

from app.config import DEFAULT_CURRENCY

DATE_ALIASES = {"date", "txn date", "txn_date", "transaction date", "value date"}
DESC_ALIASES = {"description", "narration", "remarks", "particulars", "details"}
AMOUNT_ALIASES = {"amount", "txn amount", "transaction amount"}
DEBIT_ALIASES = {"debit", "withdrawal", "dr"}
CREDIT_ALIASES = {"credit", "deposit", "cr"}


def _norm(col: str) -> str:
    return re.sub(r"\s+", " ", col.strip().lower())


def _find_col(columns: list[str], aliases: set[str]) -> str | None:
    normalized = {_norm(c): c for c in columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    return None


def dedupe_hash(txn_date: str, amount: float, description: str) -> str:
    desc = re.sub(r"\s+", " ", description.strip().upper())
    payload = f"{txn_date}|{amount:.2f}|{desc}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_date(value: object) -> str:
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    ts = pd.to_datetime(value, dayfirst=True, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"unparseable date: {value!r}")
    return ts.strftime("%Y-%m-%d")


def parse_csv_bytes(data: bytes) -> list[dict]:
    df = pd.read_csv(io.BytesIO(data))
    if df.empty:
        return []
    cols = list(df.columns)
    date_col = _find_col(cols, DATE_ALIASES)
    desc_col = _find_col(cols, DESC_ALIASES)
    amount_col = _find_col(cols, AMOUNT_ALIASES)
    debit_col = _find_col(cols, DEBIT_ALIASES)
    credit_col = _find_col(cols, CREDIT_ALIASES)

    missing: list[str] = []
    if not date_col:
        missing.append("date")
    if not desc_col:
        missing.append("description")
    if not amount_col and not (debit_col and credit_col):
        missing.append("amount or debit/credit")
    if missing:
        raise ValueError(f"missing required CSV columns: {', '.join(missing)}")

    rows: list[dict] = []
    for record in df.to_dict(orient="records"):
        description = str(record[desc_col]).strip()
        if not description or description.lower() == "nan":
            continue
        txn_date = _parse_date(record[date_col])
        if amount_col:
            amount = float(record[amount_col])
        else:
            debit = record.get(debit_col)
            credit = record.get(credit_col)
            debit_v = float(debit) if pd.notna(debit) and str(debit).strip() != "" else 0.0
            credit_v = float(credit) if pd.notna(credit) and str(credit).strip() != "" else 0.0
            amount = credit_v - debit_v
        item = {
            "txn_date": txn_date,
            "description": description,
            "amount": float(amount),
            "currency": DEFAULT_CURRENCY,
            "raw_json": json.dumps(record, default=str),
        }
        item["dedupe_hash"] = dedupe_hash(item["txn_date"], item["amount"], item["description"])
        rows.append(item)
    return rows
