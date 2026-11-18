"""Background scrape service.

Lets the app run from a single command: the server scrapes automatically on
startup (if data is missing or stale) and refreshes on a schedule, so the user
never has to run the scraper by hand.
"""
import logging
import threading
import time
from datetime import datetime, timezone

from . import db
from . import scrape as scrape_mod
from .config import RESCRAPE_INTERVAL_SECONDS, SEARCH_TERMS, STALE_HOURS, ZIP_CODES

log = logging.getLogger("service")

# In-memory status, surfaced via /api/meta so the dashboard can show progress.
STATUS = {"running": False, "last_error": None, "last_finished": None}

_lock = threading.Lock()


def _last_scrape_age_seconds():
    conn = db.connect()
    db.init(conn)
    try:
        if db.count_offers(conn) == 0:
            return None  # nothing stored yet
        last = db.get_meta(conn, "last_scrape")
    finally:
        conn.close()
    if not last:
        return None
    try:
        dt = datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds()


def is_stale():
    age = _last_scrape_age_seconds()
    return age is None or age > STALE_HOURS * 3600


def run_scrape():
    """Run one scrape, guarded so only one runs at a time."""
    if not _lock.acquire(blocking=False):
        log.info("Scrape already running; skipping.")
        return
    STATUS["running"] = True
    STATUS["last_error"] = None
    try:
        log.info("Auto-scrape started…")
        scrape_mod.run(SEARCH_TERMS, ZIP_CODES)
        STATUS["last_finished"] = db.now_iso()
        log.info("Auto-scrape finished.")
    except Exception as e:  # keep the server alive even if a scrape fails
        STATUS["last_error"] = str(e)
        log.exception("Auto-scrape failed: %s", e)
    finally:
        STATUS["running"] = False
        _lock.release()


def _worker():
    conn = db.connect()
    db.init(conn)
    conn.close()
    if is_stale():
        run_scrape()
    while True:
        time.sleep(RESCRAPE_INTERVAL_SECONDS)
        run_scrape()


def start_background():
    """Start the scrape worker as a daemon thread."""
    threading.Thread(target=_worker, name="scrape-worker", daemon=True).start()
