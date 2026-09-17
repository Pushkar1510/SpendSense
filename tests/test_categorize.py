from pathlib import Path

from app.services.ingest import ingest_file
from app.services.categorize import apply_rules, categorize_all
from app.db.connection import get_connection

FIXTURE = Path(__file__).parent / "fixtures" / "sample_statement.csv"


def test_apply_rules_swiggy_food():
    assert apply_rules("UPI-SWIGGY-BANGALORE") == "Food"
    assert apply_rules("UNKNOWN MERCHANT XYZ") is None


def test_categorize_all_rules_without_llm(db_path, monkeypatch):
    monkeypatch.setattr("app.services.categorize.ollama_client.is_up", lambda: False)
    ingest_file("sample_statement.csv", FIXTURE.read_bytes(), db_path=db_path)
    result = categorize_all(db_path=db_path, use_llm=True)
    assert result["rule"] >= 5
    conn = get_connection(db_path)
    food = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE category='Food'"
    ).fetchone()[0]
    assert food >= 2
    conn.close()
