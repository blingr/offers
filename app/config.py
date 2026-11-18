"""Configuration for the marktguru-based offers scraper.

All values are plain data so they can be tuned without touching logic.
The marktguru API keys are NOT stored here on purpose — they rotate and are
scraped fresh from the homepage at runtime (see marktguru.py).
"""
from pathlib import Path

# --- marktguru endpoints -----------------------------------------------------
MARKTGURU_HOME = "https://www.marktguru.at/"
API_BASE = "https://api.marktguru.at/api/v1"
# Offer image CDN. Verified pattern: sizes small|medium|large.
IMAGE_CDN = "https://mgat.b-cdn.net/api/v1/offers/{id}/images/default/0/{size}.jpg"

# --- scrape scope ------------------------------------------------------------
# Vienna postal codes to sweep. 1010 = city centre; add more districts for
# fuller regional coverage (offers can differ slightly by area).
ZIP_CODES = ["1010"]

# The offers endpoint is query-based, so we sweep a broad list of common
# grocery terms and dedupe by offer id. Add/remove terms to taste.
SEARCH_TERMS = [
    # dairy & eggs
    "milch", "butter", "käse", "joghurt", "topfen", "sahne", "obers", "ei", "eier",
    # bakery
    "brot", "semmel", "gebäck", "toast", "croissant",
    # pantry
    "mehl", "zucker", "nudeln", "pasta", "reis", "müsli", "cornflakes",
    "marmelade", "honig", "öl", "olivenöl", "essig", "salz", "gewürz",
    "sauce", "ketchup", "senf", "konserve", "suppe",
    # meat & fish
    "fleisch", "huhn", "hühnerfilet", "faschiertes", "schnitzel", "steak",
    "wurst", "schinken", "speck", "leberkäse", "fisch", "lachs", "thunfisch",
    # fruit & veg
    "obst", "apfel", "banane", "orange", "erdbeere", "trauben", "zitrone",
    "gemüse", "tomate", "gurke", "salat", "kartoffel", "zwiebel", "paprika",
    "karotte", "champignon", "avocado",
    # drinks
    "kaffee", "tee", "kakao", "wasser", "saft", "cola", "limonade", "energy",
    "bier", "wein", "sekt", "spirituosen",
    # sweets & snacks
    "schokolade", "keks", "chips", "eis", "snack", "nüsse", "gummibärchen",
    # frozen & convenience
    "pizza", "tiefkühl", "pommes", "fertiggericht",
    # household & drugstore
    "waschmittel", "spülmittel", "klopapier", "küchenrolle", "windel",
    "shampoo", "duschgel", "seife", "zahnpasta", "deo",
    # pets
    "katzenfutter", "hundefutter",
]

# --- HTTP behaviour ----------------------------------------------------------
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
PAGE_LIMIT = 100          # results per API page (keeps pagination shallow)
REQUEST_DELAY = 0.7       # polite pause between requests, seconds
MAX_RETRIES = 4           # retries on network errors / 429 / 5xx
HTTP_TIMEOUT = 45.0

# --- storage -----------------------------------------------------------------
DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "offers.db")

# --- auto-scrape (used when running `python -m app`) -------------------------
# The server scrapes on startup if data is missing/older than this, then
# refreshes on the interval below while it keeps running.
STALE_HOURS = 12
RESCRAPE_INTERVAL_SECONDS = 12 * 3600

# --- server ------------------------------------------------------------------
HOST = "127.0.0.1"
PORT = 8000
