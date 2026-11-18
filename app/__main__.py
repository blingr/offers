"""Single-command entry point: `python -m app`.

Starts the web server, which in turn auto-scrapes offers on startup (if the
database is empty or stale) and refreshes them on a schedule. No separate
scrape command needed.
"""
import logging

import uvicorn

from .config import HOST, PORT


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    print(f"\n  🛒 Wiener Supermarkt-Angebote → http://{HOST}:{PORT}\n")
    print("  First launch scrapes offers automatically (~1 min). The page")
    print("  fills in as soon as data arrives. Press Ctrl+C to stop.\n")
    uvicorn.run("app.api:app", host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
