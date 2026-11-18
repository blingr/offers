"""Scrape marktguru offers into SQLite.

Usage:
    python -m app.scrape                 # full sweep of all configured terms
    python -m app.scrape --limit-terms 5 # quick test with the first 5 terms
    python -m app.scrape --zip 1100      # override zip code(s), comma-separated
"""
import argparse
import logging

from . import db
from .config import SEARCH_TERMS, ZIP_CODES
from .marktguru import MarktguruClient
from .normalize import normalize

log = logging.getLogger("scrape")


def run(terms, zips):
    scraped_at = db.now_iso()
    conn = db.connect()
    db.init(conn)

    seen = {}  # offer id -> Offer (dedupe across overlapping terms/zips)
    with MarktguruClient() as client:
        for zip_code in zips:
            for i, term in enumerate(terms, 1):
                count = 0
                for raw in client.search_offers(term, zip_code):
                    offer = normalize(raw, scraped_at)
                    if offer:
                        seen[offer.id] = offer
                    count += 1
                log.info(
                    "[%s] %d/%d '%s': %d offers (%d unique total)",
                    zip_code, i, len(terms), term, count, len(seen),
                )

    offers = list(seen.values())
    db.upsert_offers(conn, offers)
    pruned = db.prune_expired(conn)
    db.set_meta(conn, "last_scrape", scraped_at)
    db.set_meta(conn, "offer_count", db.count_offers(conn))

    retailers = db.distinct_retailers(conn)
    conn.close()

    log.info("Stored %d unique offers this run; pruned %d expired.", len(offers), pruned)
    log.info(
        "Active offers by retailer: %s",
        ", ".join(f"{r['retailer']}={r['count']}" for r in retailers[:12]),
    )


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Scrape marktguru offers into SQLite.")
    parser.add_argument(
        "--limit-terms", type=int, default=None,
        help="Only use the first N search terms (for quick tests).",
    )
    parser.add_argument(
        "--zip", default=None,
        help="Comma-separated zip code(s) to override config (e.g. 1010,1100).",
    )
    args = parser.parse_args()

    terms = SEARCH_TERMS[: args.limit_terms] if args.limit_terms else SEARCH_TERMS
    zips = [z.strip() for z in args.zip.split(",")] if args.zip else ZIP_CODES
    run(terms, zips)


if __name__ == "__main__":
    main()
