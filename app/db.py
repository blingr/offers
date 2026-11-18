"""SQLite storage + queries for offers."""
import sqlite3
from dataclasses import astuple
from datetime import datetime, timezone
from pathlib import Path

from .categories import classify
from .config import DB_PATH
from .normalize import COLUMNS

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    id             INTEGER PRIMARY KEY,
    retailer       TEXT,
    retailer_key   TEXT,
    product_name   TEXT,
    brand          TEXT,
    category       TEXT,
    category_group TEXT,
    description    TEXT,
    price          REAL,
    old_price      REAL,
    discount_pct   REAL,
    reference_price REAL,
    unit           TEXT,
    volume         REAL,
    valid_from     TEXT,
    valid_to       TEXT,
    image_url      TEXT,
    scraped_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_retailer ON offers(retailer);
CREATE INDEX IF NOT EXISTS idx_discount ON offers(discount_pct);
CREATE INDEX IF NOT EXISTS idx_valid_to ON offers(valid_to);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

_SORTS = {
    "discount": "discount_pct DESC NULLS LAST, price ASC",
    "price": "price ASC NULLS LAST",
    "price_desc": "price DESC NULLS LAST",
    "valid_to": "valid_to ASC NULLS LAST",
    "name": "product_name COLLATE NOCASE ASC",
    "scraped": "scraped_at DESC",
}


def now_iso():
    """UTC timestamp in the same format marktguru uses (lexical-comparable)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init(conn):
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate_category_group(conn)
    # Created after the migration so it works on pre-existing databases.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_category_group ON offers(category_group)"
    )
    conn.commit()


def _migrate_category_group(conn):
    """Add + backfill category_group on databases created before it existed."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(offers)").fetchall()]
    if "category_group" in cols:
        return
    conn.execute("ALTER TABLE offers ADD COLUMN category_group TEXT")
    for (cat,) in conn.execute("SELECT DISTINCT category FROM offers").fetchall():
        conn.execute(
            "UPDATE offers SET category_group = ? WHERE category IS ?",
            (classify(cat), cat),
        )
    conn.commit()


def upsert_offers(conn, offers):
    placeholders = ", ".join("?" * len(COLUMNS))
    sql = (
        f"INSERT OR REPLACE INTO offers ({', '.join(COLUMNS)}) "
        f"VALUES ({placeholders})"
    )
    conn.executemany(sql, [astuple(o) for o in offers])
    conn.commit()
    return len(offers)


def prune_expired(conn):
    """Drop offers whose validity window has fully passed."""
    cur = conn.execute(
        "DELETE FROM offers WHERE valid_to IS NOT NULL AND valid_to < ?",
        (now_iso(),),
    )
    conn.commit()
    return cur.rowcount


def set_meta(conn, key, value):
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, str(value))
    )
    conn.commit()


def get_meta(conn, key):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def query_offers(
    conn,
    retailer=None,
    category=None,
    q=None,
    min_discount=None,
    active_only=True,
    sort="discount",
    limit=500,
):
    where, args = [], []

    if retailer:
        names = [r.strip() for r in retailer.split(",") if r.strip()]
        if names:
            where.append(f"retailer IN ({', '.join('?' * len(names))})")
            args += names
    if category:
        groups = [c.strip() for c in category.split(",") if c.strip()]
        if groups:
            where.append(f"category_group IN ({', '.join('?' * len(groups))})")
            args += groups
    if q:
        where.append(
            "(product_name LIKE ? OR brand LIKE ? OR description LIKE ? OR category LIKE ?)"
        )
        like = f"%{q}%"
        args += [like, like, like, like]
    if min_discount:
        where.append("discount_pct >= ?")
        args.append(min_discount)
    if active_only:
        where.append("(valid_to IS NULL OR valid_to >= ?)")
        args.append(now_iso())

    sql = "SELECT * FROM offers"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {_SORTS.get(sort, _SORTS['discount'])} LIMIT ?"
    args.append(limit)

    return conn.execute(sql, args).fetchall()


def distinct_retailers(conn, active_only=True):
    sql = "SELECT retailer, COUNT(*) AS count FROM offers"
    args = []
    if active_only:
        sql += " WHERE (valid_to IS NULL OR valid_to >= ?)"
        args.append(now_iso())
    sql += " GROUP BY retailer ORDER BY count DESC"
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def distinct_category_groups(conn, active_only=True):
    """Category groups with active-offer counts, in canonical display order."""
    from .categories import GROUP_ORDER

    sql = "SELECT category_group AS category, COUNT(*) AS count FROM offers"
    args = []
    if active_only:
        sql += " WHERE (valid_to IS NULL OR valid_to >= ?)"
        args.append(now_iso())
    sql += " GROUP BY category_group"
    counts = {r["category"]: r["count"] for r in conn.execute(sql, args).fetchall()}
    order = {g: i for i, g in enumerate(GROUP_ORDER)}
    return [
        {"category": g, "count": counts[g]}
        for g in sorted(counts, key=lambda g: order.get(g, len(order)))
        if g is not None
    ]


def count_offers(conn, active_only=True):
    sql = "SELECT COUNT(*) AS n FROM offers"
    args = []
    if active_only:
        sql += " WHERE (valid_to IS NULL OR valid_to >= ?)"
        args.append(now_iso())
    return conn.execute(sql, args).fetchone()["n"]
