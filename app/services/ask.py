from __future__ import annotations

import re
import time
from pathlib import Path

from app.db.connection import get_connection
from app.db import repository as repo
from app.db.schema import SEED_CATEGORIES
from app.services import ollama_client, tools

MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}


def _parse_intent(question: str) -> dict:
    q = question.lower()
    intent = "sum_spend"
    if "income" in q or "salary" in q or "earned" in q:
        intent = "sum_income"
    elif "breakdown" in q or "by category" in q or "split" in q:
        intent = "breakdown_by_category"
    elif "list" in q or "show" in q or "which" in q:
        intent = "list_transactions"

    category = None
    for cat in SEED_CATEGORIES:
        if cat.lower() in q:
            category = cat
            break

    date_from = date_to = None
    year_match = re.search(r"(20\d{2})", q)
    year = year_match.group(1) if year_match else None
    for name, num in MONTHS.items():
        if name in q:
            y = year or "2024"
            date_from = f"{y}-{num}-01"
            # simple month end
            if num in {"01", "03", "05", "07", "08", "10", "12"}:
                date_to = f"{y}-{num}-31"
            elif num == "02":
                date_to = f"{y}-{num}-28"
            else:
                date_to = f"{y}-{num}-30"
            break

    return {
        "intent": intent,
        "category": category,
        "date_from": date_from,
        "date_to": date_to,
        "merchant": None,
    }


def ask(question: str, db_path: Path | None = None) -> dict:
    started = time.perf_counter()
    conn = get_connection(db_path)
    try:
        if repo.count_transactions(conn) == 0:
            return {
                "answer": "Upload a statement first.",
                "citations": [],
                "tool_trace": {"intent": None},
            }

        intent = _parse_intent(question)
        citations: list[dict] = []
        tool_name = intent["intent"]
        filters = {
            "date_from": intent["date_from"],
            "date_to": intent["date_to"],
            "category": intent["category"],
            "merchant": intent["merchant"],
        }

        if tool_name == "sum_income":
            result = tools.sum_income(conn, **filters)
            total = result["total"]
            citations = result["citations"]
            base = f"Income total: ₹{total:.2f}."
        elif tool_name == "breakdown_by_category":
            result = tools.breakdown_by_category(
                conn, date_from=filters["date_from"], date_to=filters["date_to"]
            )
            parts = [f"{b['category']}: ₹{b['total']:.2f}" for b in result["breakdown"]]
            base = "Spend breakdown — " + "; ".join(parts) if parts else "No matching expenses."
        elif tool_name == "list_transactions":
            result = tools.list_transactions_tool(conn, **filters)
            citations = result["items"]
            base = f"Found {len(citations)} transaction(s)."
        else:
            result = tools.sum_spend(conn, **filters)
            total = result["total"]
            citations = result["citations"]
            cat = filters["category"] or "all categories"
            base = f"Spent ₹{total:.2f} on {cat}."
            if not citations:
                base = "No matching expenses for that query."
    finally:
        conn.close()

    # Do not hold the SQLite lock while waiting on Ollama
    answer = base
    if ollama_client.is_up() and citations is not None:
        try:
            phrased = ollama_client.generate(
                "Rephrase this finance answer in one short sentence. "
                "Do not change any numbers.\n"
                f"Answer: {base}"
            )
            if phrased:
                answer = phrased.splitlines()[0].strip()
                if "₹" in base and "₹" not in answer:
                    answer = base
        except Exception:
            answer = base

    trace = {"intent": intent, "tool": tool_name, "filters": filters}
    latency_ms = int((time.perf_counter() - started) * 1000)
    conn = get_connection(db_path)
    try:
        repo.log_query(
            conn,
            question=question,
            answer_summary=answer,
            tool_trace=trace,
            latency_ms=latency_ms,
        )
        conn.commit()
    finally:
        conn.close()
    return {"answer": answer, "citations": citations, "tool_trace": trace}
