from __future__ import annotations

import sqlite3
from typing import Any


def _filters(
    date_from: str | None,
    date_to: str | None,
    category: str | None,
    merchant: str | None,
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if date_from:
        clauses.append("txn_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("txn_date <= ?")
        params.append(date_to)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if merchant:
        clauses.append("(IFNULL(merchant, '') || ' ' || description) LIKE ?")
        params.append(f"%{merchant}%")
    where = (" AND ".join(clauses)) if clauses else "1=1"
    return where, params


def _citation(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "txn_date": row["txn_date"],
        "description": row["description"],
        "amount": row["amount"],
        "category": row["category"],
    }


def sum_spend(
    conn: sqlite3.Connection,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    merchant: str | None = None,
    limit_citations: int = 20,
) -> dict:
    where, params = _filters(date_from, date_to, category, merchant)
    total = conn.execute(
        f"SELECT COALESCE(ABS(SUM(amount)), 0) FROM transactions WHERE amount < 0 AND {where}",
        params,
    ).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM transactions WHERE amount < 0 AND {where} ORDER BY txn_date DESC LIMIT ?",
        [*params, limit_citations],
    ).fetchall()
    return {"total": float(total), "citations": [_citation(r) for r in rows]}


def sum_income(
    conn: sqlite3.Connection,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    merchant: str | None = None,
    limit_citations: int = 20,
) -> dict:
    where, params = _filters(date_from, date_to, category, merchant)
    total = conn.execute(
        f"SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE amount > 0 AND {where}",
        params,
    ).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM transactions WHERE amount > 0 AND {where} ORDER BY txn_date DESC LIMIT ?",
        [*params, limit_citations],
    ).fetchall()
    return {"total": float(total), "citations": [_citation(r) for r in rows]}


def list_transactions_tool(
    conn: sqlite3.Connection,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    merchant: str | None = None,
    limit: int = 20,
) -> dict:
    where, params = _filters(date_from, date_to, category, merchant)
    rows = conn.execute(
        f"SELECT * FROM transactions WHERE {where} ORDER BY txn_date DESC LIMIT ?",
        [*params, limit],
    ).fetchall()
    return {"items": [_citation(r) for r in rows]}


def breakdown_by_category(
    conn: sqlite3.Connection,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    where, params = _filters(date_from, date_to, None, None)
    rows = conn.execute(
        f"""
        SELECT category, COALESCE(ABS(SUM(amount)), 0) AS total
        FROM transactions
        WHERE amount < 0 AND {where}
        GROUP BY category
        ORDER BY total DESC
        """,
        params,
    ).fetchall()
    return {"breakdown": [{"category": r["category"], "total": float(r["total"])} for r in rows]}
