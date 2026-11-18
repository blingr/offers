"""marktguru.at API client.

marktguru aggregates weekly leaflet ("Flugblatt") offers from Austrian
retailers (Billa, Spar, Hofer, Lidl, Penny, ...) as structured JSON.

Two request headers are required: `x-apikey` and `x-clientkey`. Their values
are embedded in the marktguru.at homepage HTML and rotate over time, so we
scrape them fresh at runtime instead of hardcoding.
"""
import logging
import re
import time

import httpx

from .config import (
    API_BASE,
    HTTP_TIMEOUT,
    MARKTGURU_HOME,
    MAX_RETRIES,
    PAGE_LIMIT,
    REQUEST_DELAY,
    USER_AGENT,
)

log = logging.getLogger(__name__)

_RE_API_KEY = re.compile(r'"apiKey"\s*:\s*"([^"]+)"')
_RE_CLIENT_KEY = re.compile(r'"clientKey"\s*:\s*"([^"]+)"')

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class MarktguruClient:
    """Thin, polite client over the marktguru offers API."""

    def __init__(self):
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
        )
        self._apikey = None
        self._clientkey = None

    # -- auth -----------------------------------------------------------------
    def _ensure_keys(self):
        if self._apikey and self._clientkey:
            return
        r = self._get(MARKTGURU_HOME)
        html = r.text
        m, c = _RE_API_KEY.search(html), _RE_CLIENT_KEY.search(html)
        if not (m and c):
            raise RuntimeError(
                "Could not extract marktguru apiKey/clientKey from the homepage. "
                "The site markup may have changed — update the regexes in marktguru.py."
            )
        self._apikey, self._clientkey = m.group(1), c.group(1)
        log.info("Acquired marktguru API keys (apiKey %s…)", self._apikey[:8])

    # -- low-level HTTP with retry/backoff ------------------------------------
    def _get(self, url, params=None, auth=False):
        headers = {}
        if auth:
            self._ensure_keys()
            headers = {"x-apikey": self._apikey, "x-clientkey": self._clientkey}

        last_exc = None
        for attempt in range(MAX_RETRIES):
            try:
                r = self._client.get(url, params=params, headers=headers)
            except (httpx.TransportError, httpx.TimeoutException) as e:
                last_exc = e
            else:
                if r.status_code not in _RETRYABLE_STATUS:
                    r.raise_for_status()
                    return r
                last_exc = httpx.HTTPStatusError(
                    f"retryable status {r.status_code}",
                    request=r.request,
                    response=r,
                )
            wait = REQUEST_DELAY * (2 ** attempt) + 0.5
            log.warning(
                "GET %s failed (%s); retry %d/%d in %.1fs",
                url, last_exc, attempt + 1, MAX_RETRIES, wait,
            )
            time.sleep(wait)
        raise last_exc

    # -- public API -----------------------------------------------------------
    def search_offers(self, term, zip_code, page_limit=PAGE_LIMIT):
        """Yield raw offer dicts for one search term at one zip code.

        Handles pagination transparently.
        """
        self._ensure_keys()
        offset = 0
        while True:
            r = self._get(
                f"{API_BASE}/offers/search",
                params={
                    "as": "web",
                    "q": term,
                    "limit": page_limit,
                    "offset": offset,
                    "zipCode": zip_code,
                },
                auth=True,
            )
            data = r.json()
            results = data.get("results") or []
            for offer in results:
                yield offer

            total = data.get("totalResults") or 0
            offset += page_limit
            if not results or offset >= total:
                break
            time.sleep(REQUEST_DELAY)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
