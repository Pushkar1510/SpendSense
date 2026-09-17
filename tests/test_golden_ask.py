from pathlib import Path

import pytest

from app.services.ingest import ingest_file
from app.services.categorize import categorize_all
from app.services.ask import ask

FIXTURE = Path(__file__).parent / "fixtures" / "sample_statement.csv"

GOLDEN = [
    ("How much on food in August 2024?", 830.0),
    ("How much on transport in August 2024?", 220.5),
    ("What was my income in August 2024?", 75000.0),
]


@pytest.fixture
def seeded(db_path, monkeypatch):
    monkeypatch.setattr("app.services.categorize.ollama_client.is_up", lambda: False)
    monkeypatch.setattr("app.services.ask.ollama_client.is_up", lambda: False)
    ingest_file("sample_statement.csv", FIXTURE.read_bytes(), db_path=db_path)
    categorize_all(db_path=db_path, use_llm=False)
    return db_path


@pytest.mark.parametrize("question,expected", GOLDEN)
def test_golden_questions(seeded, question, expected):
    result = ask(question, db_path=seeded)
    # Answer must contain the expected number
    compact = result["answer"].replace(",", "")
    assert str(int(expected)) in compact or f"{expected:.1f}" in compact or f"{expected:.2f}" in compact
