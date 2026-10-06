"""Polite fetching for store feeds, shared by the sale check, the weekly sweep and the round.

From 2026-09-29 Shopify refused nearly every request from our GitHub jobs with HTTP 429 ("Too Many
Requests"). The cause (probe of 2026-10-06): the Python that actions/setup-python installs. On the same
machine, with the same headers, the operating system's own python3 got 200 on every store while the
setup-python build got 429 at once, so the workflows now run the system python3. As a courtesy, and so a
bad day ends quickly instead of retrying for hours, every request made through get() here:
  * runs strictly one at a time across all threads (the others wait their turn), and starts at least MIN_GAP
    seconds after the previous one finished, and
  * on 429 or 503 waits (Retry-After if the store gives one, else 20, 40, 80 s ...) and tries again, up to
    TRIES times; timeouts and dropped connections are retried twice.
STATS counts what happened, for the end-of-run report.
"""
import time, threading, urllib.request, urllib.error, ssl, collections, os
LOG = os.environ.get('SHOPIFY_LOG') == '1'   # print every request with its status and timing (set in the workflows)
_T0 = time.monotonic()

MIN_GAP = 1.0
TRIES = 3
BREAKER = 12   # this many give-ups in a row with no success in between: stop asking Shopify for the rest of the run
_lock = threading.Lock(); _last = [0.0]; _streak = [0]
STATS = collections.Counter()
_ctx = ssl.create_default_context(); _ctx.check_hostname = False; _ctx.verify_mode = ssl.CERT_NONE


def get(url, headers=None, timeout=30):
    """Return the response body as bytes, or raise the last error once the retries are used up."""
    with _lock:   # one request in flight at a time, across every thread
        if _streak[0] >= BREAKER:
            STATS['skipped (breaker open)'] += 1
            raise urllib.error.URLError('skipped: Shopify kept refusing this run')
        try:
            data = _get(url, headers, timeout); _streak[0] = 0; return data
        except urllib.error.HTTPError as e:
            if e.code in (429, 503): _streak[0] += 1
            raise
        finally: _last[0] = time.monotonic()


def _wait_turn():
    gap = _last[0] + MIN_GAP - time.monotonic()
    if gap > 0: time.sleep(gap)


def _get(url, headers, timeout):
    last = None
    for attempt in range(TRIES):
        _wait_turn()
        t = time.monotonic()
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=timeout, context=_ctx).read()
            if LOG: print(f'  [{t - _T0:6.0f}s] 200 {len(data):>8}B {time.monotonic() - t:4.1f}s {url}', flush=True)
            STATS['ok'] += 1
            if attempt: STATS['ok after retry'] += 1
            return data
        except urllib.error.HTTPError as e:
            last = e
            if LOG: print(f'  [{t - _T0:6.0f}s] {e.code} retry-after={e.headers.get("Retry-After") if e.headers else None} {url}', flush=True)
            if e.code not in (429, 503): STATS[f'http {e.code}'] += 1; raise
            STATS[f'http {e.code} (retried)'] += 1
            ra = e.headers.get('Retry-After') if e.headers else None
            wait = float(ra) if ra and ra.replace('.', '', 1).isdigit() else 15 * (2 ** attempt)
            time.sleep(min(wait, 60)); _last[0] = time.monotonic()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e; STATS['network error (retried)'] += 1
            if attempt >= 2: raise
            time.sleep(5)
    STATS['gave up'] += 1
    raise last


def report():
    return ', '.join(f'{k}: {v}' for k, v in sorted(STATS.items())) or 'no requests'
