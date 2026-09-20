"""Watch each store's return-policy page for changes.

Fetches every policy URL in build/returns/retailers.json, keeps only the sentences that carry
return terms (days, fees, labels, final sale ...), hashes them, and compares with
build/returns/hashes.json. Prints the stores whose terms changed and writes them to
build/returns/changes.json so the workflow can open an issue. Run with --init to record
the current hashes without reporting.

Pages that block scripted fetches are skipped (listed in SKIP) and must be checked by hand.
"""
import json, re, ssl, sys, hashlib, html, urllib.request

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UAS = ['Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
       'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36']
SKIP = {'J.Crew', 'Madewell', 'Ralph Lauren', 'Converse', 'Abercrombie & Fitch', "O'Connell's"}   # render their policy client-side or block scripts
KEY = re.compile(r'(\b\d{1,3}\s*(?:days?|business days?|working days?)\b|free (?:return|shipping|exchange)|prepaid|return label|shipping label|restocking|deducted|\bfee\b|\$\d|final sale|non-?returnable|store credit|exchange)', re.I)

def fetch(u):
    last = None
    for ua in UAS:
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': ua, 'Accept': 'text/html,*/*', 'Accept-Language': 'en-US,en;q=0.9'}), timeout=40, context=ctx)
            return r.read().decode('utf-8', 'ignore')
        except Exception as e: last = e
    raise last

def terms(h):
    h = re.sub(r'(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>', ' ', h)
    h = re.sub(r'(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>|</tr>', '\n', h)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', h))
    sents = [re.sub(r'\s+', ' ', s).strip() for s in re.split(r'(?<=[.!?])\s+|\n', t)]
    keep = sorted(set(s for s in sents if KEY.search(s) and 20 < len(s) < 400 and not re.search(r'cart|bag|checkout|sign up|subscribe|newsletter|% off|shop now', s, re.I)))
    return keep

def main():
    init = '--init' in sys.argv
    d = json.load(open('build/returns/retailers.json'))
    try: old = json.load(open('build/returns/hashes.json'))
    except Exception: old = {}
    new, changes, errors = {}, [], []
    for name, r in d['stores'].items():
        if name in SKIP: continue
        try:
            keep = terms(fetch(r['policy']))
            if len(keep) < 2: raise RuntimeError(f'only {len(keep)} policy sentences found')
            new[name] = hashlib.sha1('\n'.join(keep).encode()).hexdigest()
            if not init and name in old and old[name] != new[name]: changes.append(name)
        except Exception as e:
            errors.append(f'{name}: {type(e).__name__} {str(e)[:80]}'); new[name] = old.get(name)
    json.dump(new, open('build/returns/hashes.json', 'w'), indent=1, sort_keys=True)
    json.dump({'changed': changes, 'errors': errors, 'checked': d['checked']}, open('build/returns/changes.json', 'w'), indent=1)
    print('recorded' if init else 'checked', len(new), 'stores;', 'changed:', changes or 'none', ';', 'errors:', len(errors))
    for e in errors: print('  !', e)

if __name__ == '__main__': main()
