from pathlib import Path

from app.services.ingest_csv import parse_csv_bytes
from app.services.ingest import ingest_file
from app.db.connection import get_connection


FIXTURE = Path(__file__).parent / "fixtures" / "sample_statement.csv"


def test_parse_csv_maps_debit_credit_and_signs():
    rows = parse_csv_bytes(FIXTURE.read_bytes())
    assert len(rows) == 8
    swiggy = next(r for r in rows if "SWIGGY" in r["description"])
    assert swiggy["amount"] == -450.0
    assert swiggy["txn_date"] == "2024-08-01"
    salary = next(r for r in rows if "SALARY" in r["description"])
    assert salary["amount"] == 75000.0


def test_parse_csv_missing_columns_raises():
    bad = b"foo,bar\n1,2\n"
    try:
        parse_csv_bytes(bad)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "date" in str(exc).lower() or "missing" in str(exc).lower()


def test_ingest_file_dedupes_on_reupload(db_path):
    data = FIXTURE.read_bytes()
    first = ingest_file("sample_statement.csv", data, db_path=db_path)
    second = ingest_file("sample_statement.csv", data, db_path=db_path)
    assert first["inserted"] == 8
    assert second["inserted"] == 0
    assert second["skipped_duplicates"] == 8
    conn = get_connection(db_path)
    count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert count == 8
    conn.close()
