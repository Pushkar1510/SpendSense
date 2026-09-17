from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.api.routes import router
from app.db.connection import init_db


def create_app(db_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="SpendSense", version="0.1.0")
    app.state.db_path = db_path

    @app.on_event("startup")
    def _startup():
        init_db(db_path)

    app.include_router(router)
    return app


app = create_app()
