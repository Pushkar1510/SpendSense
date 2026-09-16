from app.db.connection import get_connection, init_db
from app.db.schema import SEED_CATEGORIES


def test_init_db_creates_tables_and_seed_categories(db_path):
    conn = get_connection(db_path)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"statements", "transactions", "categories", "query_logs"} <= tables
    cats = [r[0] for r in conn.execute("SELECT name FROM categories ORDER BY name").fetchall()]
    assert set(SEED_CATEGORIES) == set(cats)
    conn.close()


def test_init_db_is_idempotent(db_path):
    init_db(db_path)
    init_db(db_path)
    conn = get_connection(db_path)
    count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    assert count == len(set(__import__("app.db.schema", fromlist=["SEED_CATEGORIES"]).SEED_CATEGORIES))
    conn.close()
