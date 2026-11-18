# Wiener Supermarkt-Angebote 🛒

Scrapes weekly discount offers from Viennese supermarkets and shows them in a
filterable web dashboard.

Covered retailers: **Billa, Billa Plus, Spar, Interspar, Eurospar, Hofer,
Lidl, Penny** (plus dm, Bipa, Metro and others that appear in the feed).

## How it works

All offer data comes from **[marktguru.at](https://www.marktguru.at/)**, which
aggregates the weekly leaflets ("Flugblätter") of Austrian retailers into a
single JSON API. This avoids scraping each chain individually — most of them
sit behind bot protection (Akamai/Cloudflare) or publish image-only flyers that
would need OCR.

```
python -m app   ─┬─►  scraper: marktguru API ──► normalize ──► SQLite (data/offers.db)
                 └─►  web server: SQLite ──► JSON endpoints ──► dashboard
```

The server scrapes automatically — you never run the scraper by hand.

The API requires two request keys (`x-apikey`, `x-clientkey`) that are embedded
in the marktguru homepage and rotate over time. The scraper **scrapes them
fresh on every run** — nothing is hardcoded.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Usage

**One command starts everything:**

```bash
.venv/bin/python -m app
```

Then open <http://localhost:8000>.

On first launch (empty database) it scrapes automatically — takes a few
seconds, and the page fills in on its own. After that it re-scrapes on startup
if the data is older than 12 hours, and refreshes every 12 hours while running.

In the dashboard: browse **Aktuelle Aktionen** (a highlights strip of the
biggest current discounts, ≥25 %, with a Pickerl-style −X% sticker), tick
**category** and **retailer** chips, search by product, set a minimum discount,
and sort by discount % / price / validity. All filters combine, and the
Aktionen strip follows whatever categories/retailers you tick.

> Note: Austrian store-wide "−25 % Pickerl" promotions aren't published as
> structured data anywhere (marktguru has no vouchers/coupons feed), so
> "Aktuelle Aktionen" surfaces the strongest *product-level* percentage deals
> instead — which is where the −25 %/−50 % offers actually live.

> **Tip:** don't paste `#` comments after the command — in zsh they're not
> treated as comments and the script will reject them as arguments. Just run
> the bare command above.

### Manual scrape (optional)

You normally don't need this, but you can force a scrape without the server:

```bash
.venv/bin/python -m app.scrape                 # full sweep (~90 grocery terms)
.venv/bin/python -m app.scrape --limit-terms 8 # quick test
.venv/bin/python -m app.scrape --zip 1010,1100 # override zip code(s)
```

## Project layout

```
app/
  config.py      zip codes, search terms, endpoints, HTTP tuning
  marktguru.py   key scraping + API client (retry/backoff, pagination)
  normalize.py   raw API offer -> flat Offer record (computes discount %)
  db.py          SQLite schema, upsert, queries
  scrape.py      CLI: sweep terms -> dedupe -> store
  api.py         FastAPI JSON endpoints + serves the dashboard
static/          index.html + app.js + style.css (vanilla, no build step)
data/offers.db   SQLite database (gitignored)
```

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/offers?q=&retailer=&min_discount=&sort=&active_only=` | filtered offers |
| `GET /api/retailers` | retailers with active-offer counts |
| `GET /api/meta` | last scrape time + active offer count |

`sort` accepts: `discount` (default), `price`, `price_desc`, `valid_to`,
`name`. `retailer` accepts a comma-separated list.

## Scheduling a daily scrape

Only needed if you want scraping to run **without keeping the server open** —
while `python -m app` is running it already refreshes itself every 12 hours.

**macOS (launchd)** — create
`~/Library/LaunchAgents/at.offers.scrape.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>at.offers.scrape</string>
  <key>ProgramArguments</key><array>
    <string>/path/to/offers/.venv/bin/python</string>
    <string>-m</string><string>app.scrape</string>
  </array>
  <key>WorkingDirectory</key><string>/path/to/offers</string>
  <key>StartCalendarInterval</key><dict>
    <key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer>
  </dict>
</dict></plist>
```

Then: `launchctl load ~/Library/LaunchAgents/at.offers.scrape.plist`

**cron** alternative:

```
0 7 * * * cd /path/to/offers && .venv/bin/python -m app.scrape
```

## Notes & limitations

- **Promo-only data.** These are leaflet offers, not the retailers' full
  catalogs. If you later want a complete assortment for a specific chain, Billa
  (`shop.billa.at`) and Lidl (`lidl.at/q/api/search`) expose their own product
  APIs and could be added as extra adapters in `app/`.
- **Fragile by nature.** marktguru's embedded keys and endpoint have changed
  before. The scraper refreshes keys each run; if scraping ever breaks, check
  the regexes in `marktguru.py` and the endpoint in `config.py`.
- **Be polite.** The client sends a browser User-Agent, throttles requests
  (`REQUEST_DELAY`), and retries with backoff. Intended for personal use.
