from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import datetime

import pandas as pd

from app.config import DEFAULT_CURRENCY

DATE_ALIASES = {"date", "txn date", "txn_date", "transaction date", "value date"}
DESC_ALIASES = {
    "description",
    "narration",
    "remarks",
    "particulars",
    "details",
    "name",
    "payee",
    "beneficiary",
    "merchant",
    "transaction details",
    "transaction description",
    "transaction remarks",
}
AMOUNT_ALIASES = {"amount", "txn amount", "transaction amount"}
DEBIT_ALIASES = {"debit", "withdrawal", "dr"}
CREDIT_ALIASES = {"credit", "deposit", "cr"}
DRCR_ALIASES = {"drcr", "dr cr", "dr/cr", "type", "txn type", "transaction type"}
MODE_ALIASES = {"mode", "channel", "payment mode", "txn mode"}


def _norm(col: str) -> str:
    return re.sub(r"\s+", " ", col.strip().lower())


def _find_col(columns: list[str], aliases: set[str]) -> str | None:
    normalized = {_norm(c): c for c in columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    # Longer aliases may appear inside headers like "Transaction Description"
    for alias in sorted(aliases, key=len, reverse=True):
        if len(alias) < 4:
            continue
        for norm, original in normalized.items():
            if alias in norm:
                return original
    return None


def _signed_amount(amount: float, drcr: object | None) -> float:
    if drcr is None or (isinstance(drcr, float) and pd.isna(drcr)):
        return float(amount)
    token = str(drcr).strip().lower()
    if token in {"db", "dr", "debit", "withdrawal", "d"}:
        return -abs(float(amount))
    if token in {"cr", "credit", "deposit", "c"}:
        return abs(float(amount))
    return float(amount)


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
    drcr_col = _find_col(cols, DRCR_ALIASES)
    mode_col = _find_col(cols, MODE_ALIASES)

    missing: list[str] = []
    if not date_col:
        missing.append("date")
    if not desc_col and not mode_col:
        missing.append("description")
    if not amount_col and not (debit_col and credit_col):
        missing.append("amount or debit/credit")
    if missing:
        found = ", ".join(cols)
        raise ValueError(
            f"missing required CSV columns: {', '.join(missing)} "
            f"(found: {found})"
        )

    rows: list[dict] = []
    for record in df.to_dict(orient="records"):
        parts: list[str] = []
        if mode_col:
            mode = str(record.get(mode_col, "")).strip()
            if mode and mode.lower() != "nan":
                parts.append(mode)
        if desc_col:
            desc = str(record.get(desc_col, "")).strip()
            if desc and desc.lower() != "nan":
                parts.append(desc)
        description = " ".join(parts).strip()
        if not description:
            continue
        txn_date = _parse_date(record[date_col])
        if amount_col:
            amount = _signed_amount(
                float(record[amount_col]),
                record.get(drcr_col) if drcr_col else None,
            )
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
