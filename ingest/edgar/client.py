"""
Shared client for SEC EDGAR.

Everything that talks to sec.gov goes through here, for three reasons:

    Rate limiting. The SEC asks for no more than 10 requests/second and will
    block a source that ignores it. The original per-script `time.sleep(0.4)`
    calls were fine for one company but do not compose - five collectors each
    sleeping independently can still burst past the limit. This module holds a
    single process-wide limiter that every caller shares.

    Identification. The SEC requires a User-Agent naming the requester. That
    was hardcoded to one personal email; as a product it has to be
    configurable, so it reads SEC_USER_AGENT from the environment.

    Caching. Filing documents are large and immutable once filed. Anything
    fetched is cached to disk and never re-fetched.
"""

import json
import os
import threading
import time

import requests

CACHE_DIR = os.environ.get("SEC_CACHE_DIR", "sec_cache")

# The SEC's published ceiling is 10 requests/second. We sit well under it -
# nothing here is latency-sensitive, and being a good citizen of a free public
# API costs us nothing.
MIN_INTERVAL = 0.15

DEFAULT_USER_AGENT = "RWT Employer Intelligence contact@example.com"


class RateLimiter:
    """Process-wide minimum spacing between requests, safe across threads."""

    def __init__(self, min_interval):
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self):
        with self._lock:
            elapsed = time.monotonic() - self._last
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last = time.monotonic()


_limiter = RateLimiter(MIN_INTERVAL)


def user_agent():
    """Identify ourselves to the SEC, as they require.

    Set SEC_USER_AGENT to something like "Your Name you@example.com". The SEC
    may throttle or block requests carrying an unhelpful default.
    """
    return os.environ.get("SEC_USER_AGENT", DEFAULT_USER_AGENT)


def get(url, timeout=180):
    """Rate-limited GET with the required identifying header."""
    _limiter.wait()
    response = requests.get(url, headers={"User-Agent": user_agent()}, timeout=timeout)
    response.raise_for_status()
    return response


def cached_get(url, cache_name, binary=False, timeout=180):
    """GET a URL once and reuse the local copy forever after.

    Only safe for immutable resources - filed documents never change. Do not
    use this for the submissions feed, which gains a row on every new filing.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, cache_name)
    if os.path.exists(path):
        return path, False

    response = get(url, timeout=timeout)
    mode = "wb" if binary else "w"
    payload = response.content if binary else response.text
    with open(path, mode) as handle:
        handle.write(payload)
    return path, True


# ---------------------------------------------------------------------------
# Company identity
# ---------------------------------------------------------------------------


_ticker_map = None


def ticker_to_cik(ticker):
    """Resolve a ticker symbol to a zero-padded 10-digit CIK.

    Backed by the SEC's own company_tickers.json - about 10,400 companies in a
    single 777 KB file, which is what makes "any public company on demand"
    practical. Fetched once per process.
    """
    global _ticker_map
    if _ticker_map is None:
        response = get("https://www.sec.gov/files/company_tickers.json", timeout=60)
        _ticker_map = {
            entry["ticker"].upper(): (str(entry["cik_str"]).zfill(10), entry["title"])
            for entry in response.json().values()
        }

    key = ticker.upper()
    if key not in _ticker_map:
        raise KeyError(f"Ticker {ticker!r} not found in the SEC ticker map")
    return _ticker_map[key]


def submissions(cik):
    """Fetch a company's filing index.

    Deliberately not cached to disk: this feed gains a row every time the
    company files, and a stale copy would silently hide the very filing we are
    looking for.
    """
    return get(f"https://data.sec.gov/submissions/CIK{cik}.json", timeout=60).json()


def filings(cik, forms=None, since=None):
    """Yield filings as dicts, newest first.

    `forms` filters by type ({"10-Q", "10-K"}); `since` is an ISO date string.
    The `items` field is only populated for 8-Ks - it carries the item codes
    that make the restructuring signal possible.
    """
    recent = submissions(cik)["filings"]["recent"]
    count = len(recent["accessionNumber"])
    items = recent.get("items", [""] * count)

    for index in range(count):
        form = recent["form"][index]
        filed = recent["filingDate"][index]
        if forms and form not in forms:
            continue
        if since and filed < since:
            continue
        yield {
            "accession": recent["accessionNumber"][index],
            "filed": filed,
            "period": recent["reportDate"][index],
            "form": form,
            "primary_document": recent["primaryDocument"][index],
            "items": items[index],
        }


def archive_url(cik, accession, filename):
    """URL of one document inside a filing."""
    return (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
        f"{accession.replace('-', '')}/{filename}"
    )
