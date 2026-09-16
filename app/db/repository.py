from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


def create_statement(
    conn: sqlite3.Connection,
    *,
    filename: str,
    file_type: str,
    storage_path: str,
    parse_status: str,
    row_count: int = 0,
    error_message: str | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO statements(filename, file_type, uploaded_at, parse_status, row_count, storage_path, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            filename,
            file_type,
            datetime.now(timezone.utc).isoformat(),
            parse_status,
            row_count,
            storage_path,
            error_message,
        ),
    )
    return int(cur.lastrowid)


def insert_transactions(conn: sqlite3.Connection, statement_id: int, rows: list[dict[str, Any]]) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    for row in rows:
        try:
            conn.execute(
                """
                INSERT INTO transactions(
                    statement_id, txn_date, description, amount, currency,
                    category, category_source, raw_json, dedupe_hash
                ) VALUES (?, ?, ?, ?, ?, 'Other', 'uncategorized', ?, ?)
                """,
                (
                    statement_id,
                    row["txn_date"],
                    row["description"],
                    row["amount"],
                    row.get("currency", "INR"),
                    row.get("raw_json"),
                    row["dedupe_hash"],
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
    return inserted, skipped


def list_transactions(
    conn: sqlite3.Connection,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    merchant: str | None = None,
    limit: int = 100,
) -> list[sqlite3.Row]:
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
        clauses.append("IFNULL(merchant, description) LIKE ?")
        params.append(f"%{merchant}%")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    return list(
        conn.execute(
            f"SELECT * FROM transactions {where} ORDER BY txn_date DESC, id DESC LIMIT ?",
            params,
        )
    )


def get_transaction(conn: sqlite3.Connection, txn_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()


def update_transaction_category(
    conn: sqlite3.Connection, txn_id: int, category: str, source: str = "user"
) -> bool:
    cur = conn.execute(
        "UPDATE transactions SET category = ?, category_source = ? WHERE id = ?",
        (category, source, txn_id),
    )
    return cur.rowcount > 0


def delete_statement(conn: sqlite3.Connection, statement_id: int) -> str | None:
    row = conn.execute(
        "SELECT storage_path FROM statements WHERE id = ?", (statement_id,)
    ).fetchone()
    if row is None:
        return None
    conn.execute("DELETE FROM statements WHERE id = ?", (statement_id,))
    return row["storage_path"]


def count_transactions(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])


def log_query(
    conn: sqlite3.Connection,
    *,
    question: str,
    answer_summary: str,
    tool_trace: dict[str, Any],
    latency_ms: int,
) -> None:
    conn.execute(
        """
        INSERT INTO query_logs(question, answer_summary, tool_trace_json, latency_ms, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            question,
            answer_summary,
            json.dumps(tool_trace),
            latency_ms,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
