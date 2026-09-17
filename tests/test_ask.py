from pathlib import Path

from app.services.ingest import ingest_file
from app.services.categorize import categorize_all
from app.services.ask import ask

FIXTURE = Path(__file__).parent / "fixtures" / "sample_statement.csv"


def test_ask_empty_db(db_path):
    result = ask("How much on food?", db_path=db_path)
    assert "upload" in result["answer"].lower()
    assert result["citations"] == []


def test_ask_food_total(db_path, monkeypatch):
    monkeypatch.setattr("app.services.categorize.ollama_client.is_up", lambda: False)
    monkeypatch.setattr("app.services.ask.ollama_client.is_up", lambda: False)
    ingest_file("sample_statement.csv", FIXTURE.read_bytes(), db_path=db_path)
    categorize_all(db_path=db_path, use_llm=False)
    result = ask("How much did I spend on food in August 2024?", db_path=db_path)
    assert "830" in result["answer"].replace(",", "")
    assert len(result["citations"]) >= 2
