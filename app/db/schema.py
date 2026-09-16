SEED_CATEGORIES = [
    "Food",
    "Rent",
    "Transport",
    "Shopping",
    "Bills",
    "Transfer",
    "Income",
    "Entertainment",
    "Healthcare",
    "Education",
    "Other",
]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS statements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK(file_type IN ('csv', 'pdf')),
    uploaded_at TEXT NOT NULL,
    parse_status TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    storage_path TEXT NOT NULL,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
    txn_date TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    category TEXT NOT NULL DEFAULT 'Other',
    subcategory TEXT,
    merchant TEXT,
    category_source TEXT NOT NULL DEFAULT 'uncategorized'
        CHECK(category_source IN ('rule', 'llm', 'user', 'uncategorized')),
    raw_json TEXT,
    dedupe_hash TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS categories (
    name TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer_summary TEXT NOT NULL,
    tool_trace_json TEXT,
    latency_ms INTEGER,
    created_at TEXT NOT NULL
);
"""
