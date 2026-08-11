"""
db.py — single-file SQLite database using Python's built-in sqlite3 module.
Deliberately no ORM (no SQLAlchemy/SQLModel): for a catalog this small, plain
SQL is fewer moving parts and a smaller dependency footprint, matching the
"leanest Python option" goal.
"""
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "./data/victorlights.db")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug          TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',   -- short blurb shown on the product card
    details       TEXT NOT NULL DEFAULT '',   -- longer copy shown on the product detail view
    images_json   TEXT NOT NULL DEFAULT '[]', -- JSON array of image URLs, first = primary/cover image
    price         INTEGER NOT NULL,        -- KES, integer to avoid float rounding issues
    compare_price INTEGER,                 -- original/"was" price, nullable
    tag           TEXT,                    -- e.g. 'BESTSELLER', nullable
    stock         INTEGER NOT NULL DEFAULT 0,
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number  TEXT UNIQUE NOT NULL,
    customer_name TEXT NOT NULL,
    phone         TEXT NOT NULL,
    address       TEXT,
    items_json    TEXT NOT NULL,   -- snapshot of [{product_id, name, qty, price}], frozen at order time
    total         INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'new',
    notes         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
"""

# Columns added after the initial release. CREATE TABLE IF NOT EXISTS won't add
# these to a database that already exists from before this change, so we check
# for and add them explicitly — this lets you pull this update without having
# to delete and reseed your existing database.
MIGRATIONS = [
    ("products", "details", "TEXT NOT NULL DEFAULT ''"),
    ("products", "images_json", "TEXT NOT NULL DEFAULT '[]'"),
]


def _run_migrations(conn: sqlite3.Connection) -> None:
    for table, column, coltype in MIGRATIONS:
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")  # safer + faster for concurrent reads during a write
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        _run_migrations(conn)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def db_cursor():
    """Yields a cursor; commits on success, rolls back and re-raises on error."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
