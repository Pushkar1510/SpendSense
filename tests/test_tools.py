from pathlib import Path

from app.services.ingest import ingest_file
from app.services.categorize import categorize_all
from app.services import tools
from app.db.connection import get_connection

FIXTURE = Path(__file__).parent / "fixtures" / "sample_statement.csv"


def _seed(db_path, monkeypatch):
    monkeypatch.setattr("app.services.categorize.ollama_client.is_up", lambda: False)
    ingest_file("sample_statement.csv", FIXTURE.read_bytes(), db_path=db_path)
    categorize_all(db_path=db_path, use_llm=False)


def test_sum_spend_food_august(db_path, monkeypatch):
    _seed(db_path, monkeypatch)
    conn = get_connection(db_path)
    result = tools.sum_spend(
        conn, date_from="2024-08-01", date_to="2024-08-31", category="Food"
    )
    assert result["total"] == 830.0  # 450 + 380
    assert len(result["citations"]) == 2
    conn.close()
