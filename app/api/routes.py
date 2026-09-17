from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.api.schemas import AskRequest, CategorizeRequest, CategoryUpdate
from app.db.connection import get_connection
from app.db import repository as repo
from app.services.ingest import IngestError, ingest_file
from app.services.categorize import categorize_all
from app.services.ask import ask
from app.services import ollama_client

router = APIRouter()


def _db(request: Request) -> Path | None:
    return getattr(request.app.state, "db_path", None)


@router.get("/health")
def health():
    return {"status": "ok", "ollama": "up" if ollama_client.is_up() else "down"}


@router.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    data = await file.read()
    try:
        return ingest_file(file.filename or "upload.bin", data, db_path=_db(request))
    except IngestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/transactions")
def transactions(
    request: Request,
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    merchant: str | None = None,
    limit: int = 100,
):
    conn = get_connection(_db(request))
    try:
        rows = repo.list_transactions(
            conn,
            date_from=date_from,
            date_to=date_to,
            category=category,
            merchant=merchant,
            limit=limit,
        )
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/categorize")
def categorize(request: Request, body: CategorizeRequest):
    return categorize_all(db_path=_db(request), use_llm=body.use_llm)


@router.patch("/transactions/{txn_id}")
def patch_transaction(request: Request, txn_id: int, body: CategoryUpdate):
    conn = get_connection(_db(request))
    try:
        ok = repo.update_transaction_category(conn, txn_id, body.category, source="user")
        conn.commit()
        if not ok:
            raise HTTPException(status_code=404, detail="transaction not found")
        return dict(repo.get_transaction(conn, txn_id))
    finally:
        conn.close()


@router.post("/ask")
def ask_route(request: Request, body: AskRequest):
    return ask(body.question, db_path=_db(request))


@router.delete("/statements/{statement_id}")
def delete_statement(request: Request, statement_id: int):
    conn = get_connection(_db(request))
    try:
        path = repo.delete_statement(conn, statement_id)
        if path is None:
            raise HTTPException(status_code=404, detail="statement not found")
        conn.commit()
        p = Path(path)
        if p.exists():
            p.unlink()
        return {"deleted": statement_id}
    finally:
        conn.close()
