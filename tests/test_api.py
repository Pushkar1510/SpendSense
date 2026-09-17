from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.db.connection import init_db

FIXTURE = Path(__file__).parent / "fixtures" / "sample_statement.csv"


def test_upload_list_categorize_ask(tmp_path, monkeypatch):
    db_path = tmp_path / "api.db"
    init_db(db_path)
    monkeypatch.setenv("SPENDENSE_DB_PATH", str(db_path))
    # Force config DB path if create_app reads env — see implementation note below
    monkeypatch.setattr("app.config.DB_PATH", db_path)
    monkeypatch.setattr("app.services.categorize.ollama_client.is_up", lambda: False)
    monkeypatch.setattr("app.services.ask.ollama_client.is_up", lambda: False)

    app = create_app(db_path=db_path)
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    with FIXTURE.open("rb") as f:
        resp = client.post("/upload", files={"file": ("sample_statement.csv", f, "text/csv")})
    assert resp.status_code == 200
    assert resp.json()["inserted"] == 8

    cat = client.post("/categorize", json={"use_llm": False})
    assert cat.status_code == 200

    txns = client.get("/transactions")
    assert txns.status_code == 200
    assert len(txns.json()) == 8

    asked = client.post("/ask", json={"question": "How much on food in August 2024?"})
    assert asked.status_code == 200
    body = asked.json()
    assert "830" in body["answer"].replace(",", "")
    assert body["citations"]
