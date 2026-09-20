"""Daily sale check -> sales.js (window.SALES).

Two separate signals:
  items  : closet pieces that are actually marked down right now (matched by product handle in the brand's
           Shopify feed; brands without a feed cannot be checked item by item).
  events : brands running a real sale event, judged by a sitewide promotion on the homepage (a percentage
           off with sitewide/everything/event wording) or a large share of the whole catalogue marked down,
           or a clear jump against the brand's own 45-day baseline. A permanent sale rack does not count.
"""
import json, re, ssl, urllib.request, html, os, datetime, statistics, concurrent.futures as cf
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')); os.chdir(ROOT)
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
H = {'User-Agent': UA, 'Accept': 'application/json,text/html,*/*;q=0.8', 'Accept-Language': 'en-US,en;q=0.9'}
TODAY = datetime.date.today().isoformat()
brands = [b for b in json.load(open('build/suggest/brands.json'))['brands'] if b['status'] == 'approved']
def jsload(p): return json.loads(open(p).read().split('= ', 1)[1].rstrip(';\n'))
pieces = jsload('data.js') + (jsload('suggestions.js') if os.path.exists('suggestions.js') else [])
by_handle = {}
for it in pieces:
    m = re.search(r'/products/([^/?#]+)', it['url'])
    if m: by_handle.setdefault(m.group(1).lower(), []).append(it)
def norm(s): return re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower()).split()
def colour_hint(it):
    # the closet item's own colour: the product's colour detail, else the tail of its name after "in", "-", "|"
    tail = re.split(r'\s+(?:in|-|–|—|/|\|)\s+', it['name'], 1)
    return [w for w in norm((it.get('colorDetail') or '') + ' ' + (tail[1] if len(tail) > 1 else '')) if w not in ('print', 'as', 'shown', 'the', 'and')]
def variants_for(it, product):
    # narrow the product's variants to the item's colour: exact variant id from the URL, else a colour option match,
    # else (no colour option) every variant; returns (variants, matched_by)
    vs = [v for v in product.get('variants', []) if v.get('available')]
    m = re.search(r'[?&]variant=(\d+)', it['url'])
    if m:
        exact = [v for v in vs if str(v.get('id')) == m.group(1)]
        if exact: return exact, 'variant'
    names = [o['name'].lower() for o in product.get('options', [])]
    ci = next((i for i, n in enumerate(names) if re.search(r'colou?r|shade|wash|print|pattern', n)), None)
    if ci is None: return vs, 'all'
    hint = colour_hint(it)
    if not hint: return [], 'nohint'
    def val(v): return norm(v.get(f'option{ci + 1}') or '')
    matched = [v for v in vs if val(v) and (set(val(v)) <= set(hint) or set(hint) <= set(val(v)) or (val(v)[0] in hint))]
    return matched, ('colour' if matched else 'nomatch')
HIST_PATH = 'build/sales/history.json'; hist = json.load(open(HIST_PATH)) if os.path.exists(HIST_PATH) else {}
def get(u, timeout=30): return urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=timeout, context=ctx).read().decode('utf-8', 'ignore')
SALE_COLLECTIONS = ('sale', 'mens-sale', 'men-sale', 'mens-clothing-sale', 'sale-mens', 'last-chance', 'outlet', 'final-sale')
def feed(base):
    # The main feed (up to 12 pages) plus the brand's sale collection, because big stores (Boden) keep thousands of
    # products and their marked-down ones can sit beyond the pages we read.
    n = disc = 0; depths = []; items = {}; seen = set()
    def pages():
        for page in range(1, 13):
            prods = json.loads(get(f'{base}/products.json?limit=250&page={page}')).get('products', [])
            if not prods: break
            yield prods
            if len(prods) < 250: break
        for coll in SALE_COLLECTIONS:
            try:
                for page in range(1, 9):
                    prods = json.loads(get(f'{base}/collections/{coll}/products.json?limit=250&page={page}')).get('products', [])
                    if not prods: break
                    yield prods
                    if len(prods) < 250: break
                else: continue
                break
            except Exception: continue
    for prods in pages():
        for p in prods:
            if p['id'] in seen: continue
            seen.add(p['id'])
            vs = [v for v in p.get('variants', []) if v.get('available')]
            if not vs: continue
            n += 1
            def reduced(v): return v.get('compare_at_price') and float(v['compare_at_price']) > float(v['price'])
            sale = [(float(v['price']), float(v['compare_at_price'])) for v in vs if reduced(v)]
            if sale:
                disc += 1; now, was = min(sale); depths.append(1 - now / was)
            for it in by_handle.get(p['handle'].lower(), []):
                cand, how = variants_for(it, p)
                if how in ('nomatch', 'nohint'):            # cannot tell which colour: only flag a product-wide markdown
                    cand = vs if vs and all(reduced(v) for v in vs) else []
                red = [(float(v['price']), float(v['compare_at_price'])) for v in cand if reduced(v)]
                if red:
                    n_, w_ = min(red)
                    items[it['id']] = dict(now=round(n_, 2), was=round(w_, 2), off=int(round((1 - n_ / w_) * 100)), how=how, listed=it.get('price'))
    return dict(kind='feed', products=n, share=round(disc / n, 3) if n else 0, depth=round(statistics.median(depths), 2) if depths else 0, items=items)
NAVISH = r'<(nav|footer|script|style|noscript|select|form|template)\b.*?</\1>'
BAR_TAG = re.compile(r'<(?:div|section|aside|p|span|ul|li|a|header)\b[^>]*\b(?:class|id)="[^"]*(?:announce|promo|marquee|ticker|notification|topbar|top-bar|top_bar|utility|usp|header-?bar|header__message|message-bar|site-message|alert|offer|sale-bar|hero|slideshow)[^"]*"[^>]*>', re.I)
EXCL = r"in[- ]store only|in person|first (?:purchase|order)|newsletter|subscribe|when you (?:sign up|join)|sign(?:ing)? up (?:to|and) (?:save|get|receive|unlock)|join (?:the|our) .{0,20}(?:save|get|receive|for)|text .{0,20}to (?:save|get|receive)|offer is valid|valid (?:from|through|until)"
THIS_YEAR = str(__import__('datetime').date.today().year)
NOT_A_SALE = r"final sale|sale items?|sale exclusions?|excludes? sale|on sale items|sale-priced|sale price|no (?:further )?discount|sale shop|resale|wholesale"
def promo_in(t, require_number=False):
    """Does this bit of homepage text announce a running sale? Judged per phrase: each 'N% off', '$N off' or 'sale'
    is looked at with about 80 characters either side, so a shipping or returns line elsewhere in the same block
    cannot veto it. Returns (percent_or_0, snippet) for the strongest phrase, or None."""
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) < 4: return None
    best = None
    SALE_PHRASE = r"(?:shop (?:the|our)|the|our|big|mid-?season|end[- ]of[- ]season|fall|autumn|spring|summer|winter|holiday|flash|sample|friends (?:&|and) family|anniversary|annual|semi-?annual|labor day|memorial day|black friday|cyber|weekend|warehouse|archive|extra \d+% off|up to \d+% off)\W{0,3}sale\b|\bsale\W{0,3}(?:on now|starts|start|ends|is on|now on|live|event|weekend|up to|extra|continues|alert|preview|final hours|last chance|ends? (?:today|tonight|soon))"
    pats = [r'(\d{2})\s?%\s?off', r'\$\s?\d+\s?off'] + ([] if require_number else [SALE_PHRASE])
    for pat in pats:
        for m in re.finditer(pat, t, re.I):
            win = t[max(0, m.start() - 80): m.end() + 80]
            if re.search(EXCL, win, re.I): continue
            if any(y != THIS_YEAR for y in re.findall(r'\b(20[12]\d)\b', win)): continue      # fine print about an old offer
            if pat is SALE_PHRASE and re.search(NOT_A_SALE, win, re.I): continue
            pct = int(m.group(1)) if m.lastindex else 0
            if m.lastindex and not (20 <= pct <= 90): continue   # 15%-off-with-code is marketing, not a sale
            if best is None or pct > best[0]: best = (pct, win.strip()[:140])
    return best
def homepage(site):
    """Signals of a sale the store is running, as opposed to a permanent sale rack:
       1. a percentage next to sitewide or holiday-event wording anywhere on the page (the original rule);
       2. anything that says sale, N% off or $N off in an announcement bar or hero (containers whose class or id
          says announcement, promo, ticker, hero ...), or in a top-level heading, with navigation, footers, forms and
          menus stripped first so a nav link that just says 'Sale' does not count;
       3. failing any recognisable container, the first lines of visible text (the announcement bar is nearly always there).
       Owner's preference (2026-09-20): better a few false positives than a missed sale."""
    page = html.unescape(get(site))
    body = re.sub(NAVISH, ' ', page, flags=re.S | re.I)
    def strip(h):
        h = h[:h.rfind('<')] if h.count('<') > h.count('>') else h          # drop a tag cut in half at the end of a slice
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', h))
    def menu_like(h): return len(re.findall(r'<a\b', h, re.I)) >= 6            # a block of six or more links is a menu, not an announcement
    text = strip(body)
    SITE = r'sitewide|site-wide|everything|all full[- ]price|entire (?:site|store)|storewide'
    EVENT = r"labor day|memorial day|black friday|cyber monday|presidents'? day|fourth of july|4th of july|end of season|semi-?annual|anniversary sale|friends (?:&|and) family|flash sale|(?:summer|winter|fall|autumn|spring|holiday|mid-?season) sale"
    best = 0; event = None; promo = False; why = None
    for m in re.finditer(r'(\d{2})\s?%\s?off', text, re.I):
        win = text[max(0, m.start() - 90): m.end() + 90]
        if re.search(EXCL, win, re.I): continue
        ev = re.search(EVENT, win, re.I); sw = re.search(SITE, win, re.I)
        if (sw or ev) and int(m.group(1)) >= 15:
            promo = True; best = max(best, int(m.group(1))); why = why or win.strip()[:140]
            if ev: event = ev.group(0).title()
    slices = [body[m.end(): m.end() + 1500] for m in BAR_TAG.finditer(body)][:12]
    cands = [strip(h)[:400] for h in slices if not menu_like(h)]
    cands += [strip(h)[:200] for h in re.findall(r'<h[1-3]\b[^>]*>(.*?)</h[1-3]>', body, flags=re.S | re.I) if not menu_like(h)][:12]
    hits = [h for h in (promo_in(c) for c in cands) if h] + ([promo_in(text[:700], require_number=True)] if promo_in(text[:700], require_number=True) else [])
    if hits:
        promo = True; top = max(hits, key=lambda h: h[0]); best = max(best, top[0]); why = why or top[1]
        if not event: event = 'Announced on the homepage'
    return dict(kind='homepage', maxoff=best, promo=promo, sitewide=promo, event=event, why=why)
def check(b):
    out = {'name': b['name']}
    try:
        f = feed(b['site'])
        if f['products']: out['feed'] = f
    except Exception: pass
    try: out['home'] = homepage(b['site'])
    except Exception as e: out['home_error'] = str(e)[:60]
    return out
if '--test-events' in __import__('sys').argv:
    import time
    for b in brands:
        try: hm = homepage(b['site']); print(f"{b['name']:22s} {'SALE ' if hm['promo'] else '     '} {hm['maxoff'] or '':>3} {hm['event'] or ''} | {hm.get('why') or ''}")
        except Exception as e: print(f"{b['name']:22s} ERR {type(e).__name__} {str(e)[:50]}")
        time.sleep(1.5)
    raise SystemExit
results = list(cf.ThreadPoolExecutor(6).map(check, brands))
items = {}; events = {}; notes = {}
for r in results:
    name = r['name']; f = r.get('feed'); hm = r.get('home', {})
    if f: items.update(f['items'])
    share = f['share'] if f else None
    if share is not None:
        h = hist.setdefault(name, []); h.append([TODAY, share]); del h[:-45]
    base = statistics.median(x[1] for x in hist[name][:-1]) if share is not None and len(hist.get(name, [])) > 7 else None
    promo = bool(hm) and bool(hm.get('promo'))
    jump = base is not None and share >= 0.3 and share >= base * 2
    if promo or jump:
        events[name] = dict(off=hm['maxoff'] if promo and hm['maxoff'] else (int(round(f['depth'] * 100)) if f else 0), event=hm.get('event') if hm else None, why='promo' if promo else 'jump', checked=TODAY, site=next((b['site'] for b in brands if b['name'] == name), None))
    notes[name] = dict(share=share, checked=bool(f), promo=promo)
json.dump(hist, open(HIST_PATH, 'w'))
open('sales.js', 'w').write('window.SALES = ' + json.dumps({'checked': TODAY, 'items': {str(k): v for k, v in items.items()}, 'events': events, 'brands': notes}, separators=(',', ':')) + ';\n')
byb = {}
for iid, v in items.items():
    it = next(i for i in pieces if i['id'] == iid); byb.setdefault(it['brand'], []).append(f"{it['name'][:34]} [{v['how']}] ${v['now']:.0f} was ${v['was']:.0f} (closet ${it.get('price')})")
print(f"closet pieces actually marked down: {len(items)}")
for b, L in sorted(byb.items()): print(f"  {b}: " + '; '.join(L[:4]) + (f" (+{len(L)-4} more)" if len(L) > 4 else ''))
print('sale events:', {k: (v['why'], v['off'], v['event']) for k, v in events.items()} or 'none')
for r in results:
    hm = r.get('home') or {}
    if hm.get('promo'): print(f"  evidence {r['name']}: {hm.get('why')}")
print('brands checked item by item:', sum(1 for n in notes.values() if n['checked']), 'of', len(notes))
