"""FastAPI backend: JSON endpoints + serves the static dashboard.

Normally you don't run this directly — `python -m app` starts the server AND
the automatic scraper together. But it can be started standalone too:
    uvicorn app.api:app
Then open: http://localhost:8000
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles

from . import db, service

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app):
    # Make sure the schema exists before any request, then kick off the
    # background scraper (scrapes now if data is missing/stale, refreshes on
    # a schedule).
    conn = db.connect()
    db.init(conn)
    conn.close()
    service.start_background()
    yield


app = FastAPI(title="Vienna Supermarket Offers", lifespan=lifespan)


@app.get("/api/offers")
def api_offers(
    retailer: str | None = Query(None, description="Comma-separated retailer names"),
    category: str | None = Query(None, description="Comma-separated category groups"),
    q: str | None = Query(None, description="Free-text search"),
    min_discount: float | None = Query(None, ge=0, le=100),
    active_only: bool = True,
    sort: str = "discount",
    limit: int = Query(500, ge=1, le=2000),
):
    conn = db.connect()
    try:
        rows = db.query_offers(
            conn,
            retailer=retailer,
            category=category,
            q=q,
            min_discount=min_discount,
            active_only=active_only,
            sort=sort,
            limit=limit,
        )
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/retailers")
def api_retailers():
    conn = db.connect()
    try:
        return db.distinct_retailers(conn)
    finally:
        conn.close()


@app.get("/api/categories")
def api_categories():
    conn = db.connect()
    try:
        return db.distinct_category_groups(conn)
    finally:
        conn.close()


@app.get("/api/meta")
def api_meta():
    conn = db.connect()
    try:
        return {
            "last_scrape": db.get_meta(conn, "last_scrape"),
            "active_offers": db.count_offers(conn),
            "scraping": service.STATUS["running"],
            "scrape_error": service.STATUS["last_error"],
        }
    finally:
        conn.close()


# Serve the dashboard (index.html) and its assets at the root.
# Registered last so the /api/* routes above take precedence.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
