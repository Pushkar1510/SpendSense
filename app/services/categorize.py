from __future__ import annotations

from pathlib import Path

import yaml

from app.db.connection import get_connection
from app.services import ollama_client

RULES_PATH = Path(__file__).resolve().parents[1] / "rules" / "categories.yaml"


def load_rules() -> tuple[list[str], list[tuple[str, str]]]:
    data = yaml.safe_load(RULES_PATH.read_text())
    categories = list(data["categories"])
    rules = [(r["pattern"].upper(), r["category"]) for r in data["rules"]]
    return categories, rules


def apply_rules(description: str) -> str | None:
    _, rules = load_rules()
    text = description.upper()
    for pattern, category in rules:
        if pattern in text:
            return category
    return None


def _llm_category(description: str, categories: list[str]) -> str | None:
    prompt = (
        "Pick exactly one category for this bank transaction description. "
        f"Allowed: {', '.join(categories)}. "
        f"Description: {description}\n"
        "Reply with only the category name."
    )
    try:
        reply = ollama_client.generate(prompt)
    except Exception:
        return None
    reply_clean = reply.strip().splitlines()[0].strip()
    for cat in categories:
        if cat.lower() == reply_clean.lower():
            return cat
    return None


def categorize_all(db_path: Path | None = None, use_llm: bool = True) -> dict:
    categories, _ = load_rules()
    counts = {"rule": 0, "llm": 0, "unchanged": 0}
    llm_ok = use_llm and ollama_client.is_up()

    conn = get_connection(db_path)
    try:
        rows = [
            {"id": r["id"], "description": r["description"]}
            for r in conn.execute(
                "SELECT id, description FROM transactions WHERE category_source = 'uncategorized'"
            ).fetchall()
        ]
    finally:
        conn.close()

    updates: list[tuple[str, str, int]] = []
    for row in rows:
        cat = apply_rules(row["description"])
        source = "rule"
        # LLM calls happen without an open DB connection (avoids sqlite lock)
        if cat is None and llm_ok:
            cat = _llm_category(row["description"], categories)
            source = "llm"
        if cat is None:
            counts["unchanged"] += 1
            continue
        updates.append((cat, source, row["id"]))
        counts[source] += 1

    if updates:
        conn = get_connection(db_path)
        try:
            conn.executemany(
                "UPDATE transactions SET category = ?, category_source = ? WHERE id = ?",
                updates,
            )
            conn.commit()
        finally:
            conn.close()
    return counts
