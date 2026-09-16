from pathlib import Path

import pytest

from app.db.connection import init_db, get_connection


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


@pytest.fixture
def conn(db_path: Path):
    connection = get_connection(db_path)
    yield connection
    connection.close()
