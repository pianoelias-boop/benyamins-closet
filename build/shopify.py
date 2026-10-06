"""Polite fetching for store feeds, shared by the sale check, the weekly sweep and the round.

Shopify serves every store through the same edge, and from GitHub's machines it answers overlapping requests
with HTTP 429 ("Too Many Requests"): six workers each pulling 1-10 MB catalogue pages were refused almost
entirely, while one request at a time every 3 s went through 61 of 61 (probes of 2026-10-06). So every
request made through get() here:
  * runs strictly one at a time across all threads (the others wait their turn), and starts at least MIN_GAP
    seconds after the previous one finished, and
  * on 429 or 503 waits (Retry-After if the store gives one, else 20, 40, 80 s ...) and tries again, up to
    TRIES times; timeouts and dropped connections are retried twice.
STATS counts what happened, for the end-of-run report.
"""
import time, threading, urllib.request, urllib.error, ssl, collections

MIN_GAP = 2.5
TRIES = 5
_lock = threading.Lock(); _last = [0.0]
STATS = collections.Counter()
_ctx = ssl.create_default_context(); _ctx.check_hostname = False; _ctx.verify_mode = ssl.CERT_NONE


def get(url, headers=None, timeout=30):
    """Return the response body as bytes, or raise the last error once the retries are used up."""
    with _lock:   # one request in flight at a time, across every thread
        try: return _get(url, headers, timeout)
        finally: _last[0] = time.monotonic()


def _wait_turn():
    gap = _last[0] + MIN_GAP - time.monotonic()
    if gap > 0: time.sleep(gap)


def _get(url, headers, timeout):
    last = None
    for attempt in range(TRIES):
        _wait_turn()
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=timeout, context=_ctx).read()
            STATS['ok'] += 1
            if attempt: STATS['ok after retry'] += 1
            return data
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 503): STATS[f'http {e.code}'] += 1; raise
            STATS[f'http {e.code} (retried)'] += 1
            ra = e.headers.get('Retry-After') if e.headers else None
            wait = float(ra) if ra and ra.replace('.', '', 1).isdigit() else 20 * (2 ** attempt)
            time.sleep(min(wait, 120)); _last[0] = time.monotonic()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e; STATS['network error (retried)'] += 1
            if attempt >= 2: raise
            time.sleep(5)
    STATS['gave up'] += 1
    raise last


def report():
    return ', '.join(f'{k}: {v}' for k, v in sorted(STATS.items())) or 'no requests'
