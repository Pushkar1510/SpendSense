from __future__ import annotations

from pathlib import Path

from app.config import UPLOAD_DIR
from app.db.connection import get_connection
from app.db import repository as repo
from app.services.ingest_csv import parse_csv_bytes


class IngestError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def ingest_file(filename: str, data: bytes, db_path: Path | None = None) -> dict:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        file_type = "csv"
        try:
            rows = parse_csv_bytes(data)
        except ValueError as exc:
            raise IngestError(str(exc), status_code=400) from exc
    elif suffix == ".pdf":
        from app.services.ingest_pdf import parse_pdf_bytes

        file_type = "pdf"
        try:
            rows = parse_pdf_bytes(data)
        except ValueError as exc:
            raise IngestError(str(exc), status_code=422) from exc
    else:
        raise IngestError("unsupported file type; upload CSV or PDF", status_code=400)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / filename
    dest.write_bytes(data)

    conn = get_connection(db_path)
    try:
        statement_id = repo.create_statement(
            conn,
            filename=filename,
            file_type=file_type,
            storage_path=str(dest),
            parse_status="ok",
            row_count=0,
        )
        inserted, skipped = repo.insert_transactions(conn, statement_id, rows)
        conn.execute(
            "UPDATE statements SET row_count = ? WHERE id = ?",
            (inserted, statement_id),
        )
        conn.commit()
        return {
            "statement_id": statement_id,
            "file_type": file_type,
            "inserted": inserted,
            "skipped_duplicates": skipped,
            "parsed": len(rows),
        }
    finally:
        conn.close()
