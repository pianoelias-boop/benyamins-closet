"""Weekly round of ideas, no model required.

  python3 build/suggest/round.py stage1              notebook -> profile (auto section), sweep, score, shortlist
  python3 build/suggest/round.py fallback            pick 8 from the shortlist by score -> pending/picks.json
  python3 build/suggest/round.py finalize --by X     picks -> round_N.json + photos + suggestions.js + housekeeping + pr_body.md

The judgment step (a Claude Code routine) reads pending/shortlist.md and writes pending/picks.json in the
same shape the fallback writes, then calls finalize --by claude.
"""
import json, re, os, sys, glob, html, io, ssl, urllib.request, urllib.parse, datetime, collections, subprocess
sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, 'build'))
import closet_config
CFG = closet_config.load(); KEY = CFG.get('notebookKey') or 'closet'; OCCASIONS = closet_config.occasions(CFG)
P = 'build/suggest'; PEND = f'{P}/pending'
os.makedirs(PEND, exist_ok=True); os.makedirs('images/ideas', exist_ok=True)
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
H = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36', 'Accept': 'application/json,image/*,*/*'}
cfg = json.load(open(f'{P}/brands.json')); R = cfg['rules']
NOW = datetime.datetime.now(datetime.timezone.utc); TODAY = NOW.date().isoformat()

def clean(s): return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or ''))).strip()
def jsload(text): return json.loads(text.split('= ', 1)[1].rstrip(';\n'))
def catalogue(): return jsload(open('data.js').read())
def ideas(): return jsload(open('suggestions.js').read()) if os.path.exists('suggestions.js') else []
def round_files(): return sorted(p for p in glob.glob(f'{P}/round_*.json') if not p.endswith('_raw.json'))
def sync_url():
    if CFG.get('syncUrl'): return CFG['syncUrl']
    m = re.search(r'name="closet-sync" content="([^"]*)"', open('index.html').read()); return m.group(1) if m else ''   # older copies kept it in a meta tag
def repo_slug():
    """owner/repo: from GitHub Actions' environment, else from the git remote."""
    if os.environ.get('GITHUB_REPOSITORY'): return os.environ['GITHUB_REPOSITORY']
    try:
        u = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True, check=True).stdout.strip()
        m = re.search(r'github\.com[:/]([^/]+/[^/.]+)', u)
        if m: return m.group(1)
    except Exception: pass
    return 'owner/repo'

# ---------------- signals ----------------
FABRICS = ['corduroy', 'cord', 'twill', 'denim', 'linen', 'cotton', 'wool', 'merino', 'tweed', 'jersey', 'poplin', 'chambray', 'silk', 'viscose', 'cupro', 'tencel', 'lyocell', 'flannel', 'canvas', 'moleskin', 'cashmere', 'velvet', 'seersucker', 'gauze', 'voile', 'rib']
CUTS = ['wide leg', 'wide-leg', 'wide', 'straight leg', 'straight', 'relaxed', 'tapered', 'slim', 'double pleat', 'double-pleat', 'pleated', 'pleat', 'high rise', 'high-rise', 'high waist', 'cargo', 'fatigue', 'utility', 'pocket', 'elastic', 'drawstring', 'button', 'collar', 'camp collar', 'long sleeve', 'short sleeve', 'cropped', 'boxy', 'oversized', 'fitted', 'unstructured', 'raglan', 'cable', 'ribbed', 'rib', 'stripe', 'striped', 'herringbone', 'seersucker', 'patchwork', 'embroidered', 'reversible', 'waxed', 'selvedge', 'hakama']
COLOR_MAP = [('Black', r'\bblack|noir|onyx|jet\b'), ('White/Ivory', r'\bwhite|ivory|cream|ecru|natural|salt|chalk|off-white|oat\b'), ('Grey', r'\bgrey|gray|charcoal|slate|heather|smoke|storm|gunmetal'), ('Beige/Tan', r'\bbeige|tan|sand|dune|khaki|camel|stone|taupe|parchment|almond'), ('Brown', r'\bbrown|cocoa|espresso|java|chocolate|coffee|mocha|walnut|chestnut|tobacco|toast\b|carob'), ('Denim', r'\bdenim|indigo|wash\b'), ('Blue', r'\bblue|navy|midnight|cobalt|sky|teal|petrol|peacock'), ('Green', r'\bgreen|olive|moss|forest|sage|army|evergreen|pine|jade|ivy'), ('Red', r'\bred|burgundy|currant|wine|merlot|oxblood|crimson|cherry|scarlet|rust\b'), ('Pink', r'\bpink|rose|blush|coral|raspberry'), ('Purple', r'\bpurple|plum|fig|mulberry|violet|lilac|lavender|aubergine|wisteria'), ('Orange/Rust', r'\borange|terracotta|clay|apricot|amber|sumac|papaya|copper'), ('Yellow/Gold', r'\byellow|gold|mustard|butter|ochre|honey|saffron'), ('Multi/Print', r'\bprint|floral|stripe|check|plaid|gingham|tartan|pattern|paisley|multi')]
def features(it):
    text = ' '.join([it.get('name', ''), it.get('fabric') or '', ' '.join(it.get('details') or []), it.get('desc') or '', it.get('colorDetail') or '']).lower()
    f = {f'brand:{it["brand"]}', f'cat:{it["category"]}', f'color:{it["color"]}'}
    p = it.get('price') or 0
    f.add('price:' + ('u100' if p < 100 else '100-200' if p < 200 else '200-300' if p < 300 else '300+'))
    for w in FABRICS:
        if re.search(r'\b' + re.escape(w) + r'\b', text): f.add('fab:' + ('cord' if w == 'corduroy' else w))
    for w in CUTS:
        if w in text: f.add('cut:' + w.replace('-', ' '))
    return f
NOTEBOOK_FAILED = False
def notebook():
    u = sync_url()
    if not u: return {}
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u + ('&' if '?' in u else '?') + 'key=' + urllib.parse.quote(KEY), headers=H), timeout=60, context=ctx).read()).get('items', {})
    except Exception as e:
        global NOTEBOOK_FAILED; NOTEBOOK_FAILED = True
        print('notebook unreachable:', e); return {}
def signals():
    nb = notebook(); cat = {i['id']: i for i in catalogue()}; ide = {i['id']: i for i in ideas()}
    for p in round_files():
        for i in json.load(open(p)): ide.setdefault(i['id'], i)
    saved, passed = [], []
    for k, v in nb.items():
        it = cat.get(int(k)) or ide.get(int(k))
        if not it: continue
        for kind, lst in (('s', saved), ('p', passed)):
            e = v.get(kind)
            if e and e.get('on'):
                age = (NOW.timestamp() * 1000 - e['ts']) / 86400000 if e['ts'] > 1 else 999
                lst.append(dict(item=it, ts=e['ts'], age_days=round(age, 1), idea=int(k) >= 5000))
    return saved, passed
def profile_weights(saved, passed):
    w = collections.Counter()
    for s in saved:
        rec = 1.5 if s['age_days'] <= 14 else 1.0
        for f in features(s['item']): w[f] += rec
    for p in passed:
        rec = 1.5 if p['age_days'] <= 14 else 1.0
        for f in features(p['item']): w[f] -= 0.7 * rec
    n = max(1, len(saved))
    return {k: v / n for k, v in w.items()}
def write_profile_auto(saved, passed, w):
    lines = [f'<!-- auto:start (rewritten by round.py, {TODAY}) -->', f'## What the notebook says ({TODAY})', f'- Hearts: {len(saved)}  ·  Not for me: {len(passed)}']
    def top(prefix, n=6):
        xs = sorted(((k[len(prefix):], v) for k, v in w.items() if k.startswith(prefix) and v > 0), key=lambda kv: -kv[1])[:n]
        return ', '.join(f'{k} ({v:.1f})' for k, v in xs) or 'nothing yet'
    lines += [f'- Brands he saves: {top("brand:")}', f'- Categories: {top("cat:")}', f'- Colours: {top("color:")}', f'- Fabrics: {top("fab:")}', f'- Cuts and details: {top("cut:", 10)}', f'- Price bands: {top("price:")}']
    neg = sorted(((k, v) for k, v in w.items() if v < -0.2), key=lambda kv: kv[1])[:8]
    lines.append('- Steer away from: ' + (', '.join(f'{k.split(":",1)[1]}' for k, v in neg) or 'nothing yet'))
    recent = sorted(saved, key=lambda s: -s['ts'])[:8]
    lines.append('- Most recent hearts: ' + '; '.join(f"{s['item']['brand']} {s['item']['name']}" for s in recent))
    lines.append('<!-- auto:end -->')
    block = '\n'.join(lines)
    path = f'{P}/profile.md'; txt = open(path).read()
    if '<!-- auto:start' in txt: txt = re.sub(r'<!-- auto:start.*?<!-- auto:end -->', block, txt, flags=re.S)
    else:   # no markers yet: put the block right after the first heading line
        first, _, rest = txt.partition('\n'); txt = first + '\n\n' + block + '\n' + rest
    open(path, 'w').write(txt)

# ---------------- scoring ----------------
def cand_features(c):
    it = dict(name=c['title'], brand=c['brand'], category=c['category'], color=colour_of(c)[0], price=c['list'], fabric=c.get('fabric') or '', details=[], desc=c.get('desc') or '', colorDetail='')
    return features(it)
def colour_of(c):
    text = (c['title'] + ' ' + (c.get('desc') or '')[:200]).lower()
    tail = re.split(r'\s+(?:in|-|–|—|/|\|)\s+', c['title'], 1)
    detail = tail[1].strip() if len(tail) > 1 else ''
    for name, pat in COLOR_MAP:
        if re.search(pat, (detail or c['title']).lower()): return name, (detail or name)
    for name, pat in COLOR_MAP:
        if re.search(pat, text): return name, (detail or name)
    return 'Multi/Print', (detail or 'As shown')
def score(c, w, closet_share, recent_brands, passed_brands, median_price):
    s = 0.0; fs = cand_features(c); hits = []
    for f in fs:
        v = w.get(f, 0)
        if f.startswith('brand:'): v = max(-1.5, min(v, 1.5))
        if v: s += v; hits.append((f, v))
    if not any(k.startswith('cat:') and v > 0 for k, v in w.items()):  # no signal yet: lean on the closet's mix
        s += closet_share.get(c['category'], 0) * 3
    if c.get('natural') is not None: s += 0.8 * c['natural']
    elif c.get('fabric') and c['fabric'] != 'unknown': s += 0.3
    else: s -= 0.8
    if median_price: s -= abs(c['list'] - median_price) / median_price * 0.6
    if c['brand'] not in recent_brands: s += 0.3
    s -= 0.5 * passed_brands.get(c['brand'], 0)
    if 'final sale' in ' '.join(c.get('tags') or []).lower(): s -= 0.4
    return s, sorted(hits, key=lambda h: -h[1])[:4]
def title_key(c): return (c['brand'], re.sub(r'\s+(?:in|-|–|—|/|\|)\s+.*$', '', c['title'].lower()).strip())
STOP = {'the', 'in', 'and', 'with', 'a', 'of', 'for', 'men', "men's", 'mens', 'pants', 'pant', 'trousers', 'trouser', 'jean', 'jeans', 'short', 'shorts', 'tee', 'shirt', 'jacket', 'coat', 'sweater', 'cardigan'}
def sim_key(c):  # same brand + same descriptive words, ignoring colour and order -> colourways collapse together
    words = sorted(set(re.findall(r'[a-z]+', title_key(c)[1])) - STOP); return (c['brand'], c['category'], ' '.join(words))
GENERIC = {'fab:cotton', 'cut:pocket', 'cut:button', 'cut:elastic'}
COLOR_WORDS = set(w for _, pat in COLOR_MAP for w in re.findall(r'[a-z]{3,}', pat)) | {'washed', 'wash', 'dark', 'light', 'deep', 'pale', 'heather', 'used', 'vintage'}
def garment_key(brand, name):
    base = re.split(r'\s+(?:in|-|–|—|/|\|)\s+', name.lower(), 1)[0]
    words = sorted(set(re.findall(r'[a-z]+', base)) - STOP - COLOR_WORDS - {'organic', 'womens', 'w', 's', 'wide', 'leg'} )
    return (brand.lower(), ' '.join(words))
def existing_garments():
    keys = set()
    for it in catalogue(): keys.add(garment_key(it['brand'], it['name']))
    for p in round_files():
        for it in json.load(open(p)): keys.add(garment_key(it['brand'], it['name']))
    if os.path.exists(f'{P}/retired.json'):
        for it in json.load(open(f'{P}/retired.json')): keys.add(garment_key(it['brand'], it['name']))
    return keys

def stage1():
    import sweep, sys
    saved, passed = signals()
    if NOTEBOOK_FAILED:
        print('stage1 aborted: the notebook could not be read, so nothing was rewritten.'); sys.exit(2)
    cands_probe, report_probe = sweep.sweep_brands({'approved'}, quiet=True)
    if not cands_probe:
        print('stage1 aborted: no brand feed could be read (network blocked?), so nothing was rewritten.'); sys.exit(2)
    w = profile_weights(saved, passed); write_profile_auto(saved, passed, w)
    json.dump({'saved': [dict(id=s['item']['id'], name=s['item']['name'], brand=s['item']['brand'], age_days=s['age_days']) for s in saved], 'passed': [dict(id=p['item']['id'], name=p['item']['name'], brand=p['item']['brand']) for p in passed], 'weights': w, 'fetched': NOW.isoformat()}, open(f'{PEND}/signals.json', 'w'), indent=1)
    cands, report = cands_probe, report_probe
    data = catalogue(); n = len(data); closet_share = {k: v / n for k, v in collections.Counter(i['category'] for i in data).items()}
    hearted_prices = sorted(s['item']['price'] for s in saved if s['item'].get('price')); median_price = hearted_prices[len(hearted_prices) // 2] if hearted_prices else 200
    recent_brands = set(); passed_brands = collections.Counter()
    for p in round_files()[-3:]: recent_brands |= {i['brand'] for i in json.load(open(p))}
    for p in passed:
        if p['idea']: passed_brands[p['item']['brand']] += 1
    have = existing_garments()
    AVOID = re.compile(R['avoid_titles']['pattern'], re.I) if R.get('avoid_titles') else None; AVOID_CATS = set(R.get('avoid_titles', {}).get('categories', []))
    ONLY = {x['name']: re.compile(x['only_titles'], re.I) for x in cfg['brands'] if x.get('only_titles')}   # e.g. 18 East: shirts and overshirts only
    seen = set(); scored = []; dropped = collections.Counter()
    for c in cands:
        k = title_key(c)
        if k in seen: continue
        if AVOID and c['category'] in AVOID_CATS and AVOID.search(c['title'] + ' ' + (c.get('desc') or '')[:300]): dropped['tapered'] += 1; continue
        only = ONLY.get(c['brand'])
        if only and not only.search(c['title']): dropped[c['brand']] += 1; continue
        seen.add(k); sc, hits = score(c, w, closet_share, recent_brands, passed_brands, median_price); c['score'] = round(sc, 2); c['hits'] = hits
        c['recolour'] = garment_key(c['brand'], c['title']) in have   # another colour of something already in the closet or a past round
        scored.append(c)
    scored.sort(key=lambda c: -c['score'])
    per_brand = collections.Counter(); per_cat = collections.Counter(); short = []; keys = set()
    def take(c):
        per_brand[c['brand']] += 1; per_cat[c['category']] += 1; short.append(c); keys.add(sim_key(c))
    for cat in ('Trousers', 'Jeans', 'Shirts', 'Knitwear', 'Tees & Polos', 'Jackets & Coats', 'Suits & Blazers', 'Shorts & Swim'):
        for c in [x for x in scored if x['category'] == cat][:3]:
            if sim_key(c) not in keys: take(c)
    for c in scored:
        if len(short) >= 36: break
        if c in short or sim_key(c) in keys or per_brand[c['brand']] >= 4 or per_cat[c['category']] >= 8: continue
        take(c)
    short.sort(key=lambda c: -c['score'])
    json.dump(short, open(f'{PEND}/shortlist.json', 'w'), indent=0, ensure_ascii=False)
    with open(f'{PEND}/shortlist.md', 'w') as f:
        f.write(f'# Shortlist for the round of {TODAY}\n\nHearts: {len(saved)} · Not for me: {len(passed)} · candidates swept: {len(cands)} from {sum(1 for r in report if r[1])} brands.\n\n')
        for i, c in enumerate(short, 1):
            f.write(f"{i}. [{c['brand']}] {c['title']} — {c['category']} — ${c['price']:.0f}" + (f" (list ${c['list']:.0f})" if c['list'] != c['price'] else '') + f" — {c.get('fabric') or 'fibre not stated'} — score {c['score']}" + (" — ANOTHER COLOUR of a piece already in the closet" if c.get('recolour') else '') + f"\n   {(c.get('desc') or '')[:220]}\n   {c['url']}\n")
    json.dump({'date': TODAY, 'stage1': NOW.isoformat(), 'brands_ok': [r[0] for r in report if r[1]], 'brands_failed': [r[0] for r in report if r[2]]}, open(f'{PEND}/round_meta.json', 'w'), indent=1)
    print(f'stage1 done: {len(saved)} hearts, {len(passed)} passes, {len(cands)} candidates, shortlist {len(short)}; dropped by rule: {dict(dropped)}; feeds failed: {[r[0] for r in report if r[2]]}')

def fallback():
    short = json.load(open(f'{PEND}/shortlist.json')); sig = json.load(open(f'{PEND}/signals.json'))
    picks = []; per_brand = collections.Counter(); cats = collections.Counter()
    need = {'Trousers': 1}; want_one_of = {'Shirts', 'Knitwear'}
    for c in short:                       # first satisfy the quotas (with pieces that are new to him)
        if c.get('recolour'): continue
        if c['category'] in need and cats[c['category']] < need[c['category']]: picks.append(c); per_brand[c['brand']] += 1; cats[c['category']] += 1
    if not any(p['category'] in want_one_of for p in picks):
        for c in short:
            if c['category'] in want_one_of and c not in picks: picks.append(c); per_brand[c['brand']] += 1; cats[c['category']] += 1; break
    bc = collections.Counter((p['brand'], p['category']) for p in picks)
    recolours = sum(1 for p in picks if p.get('recolour'))
    for c in short:
        if len(picks) >= R['ideas_per_round']: break
        if c in picks or per_brand[c['brand']] >= 2 or cats[c['category']] >= 3 or bc[(c['brand'], c['category'])] >= 1: continue
        if c['category'] == 'Jackets & Coats' and cats['Jackets & Coats'] >= 1: continue
        if c.get('recolour') and recolours >= 1: continue          # one new colour of something he has, at most
        picks.append(c); per_brand[c['brand']] += 1; cats[c['category']] += 1; bc[(c['brand'], c['category'])] += 1; recolours += c.get('recolour', False)
    saved_items, _ = signals()
    out = []
    for c in picks:
        cf_ = cand_features(c) - GENERIC
        best, best_n = None, 0
        for s_ in saved_items:
            shared = (cf_ & features(s_['item'])) - GENERIC
            n_ = sum(2 if f.startswith('fab:') else 1 for f in shared if not f.startswith(('price:', 'brand:')))
            if n_ > best_n: best, best_n = s_, n_
        words = [f.split(':', 1)[1] for f in sorted(cf_, key=lambda f: (not f.startswith('fab:'), f)) if f.startswith(('fab:', 'cut:'))][:3]
        phrase = (', '.join(words[:-1]) + ' and ' + words[-1]) if len(words) > 1 else (words[0] if words else c['category'].lower())
        if best and best_n >= 2: reason = f"{phrase.capitalize()}, like the {best['item']['brand']} {best['item']['name']} you saved."
        elif best: reason = f"{phrase.capitalize()}, close to the {best['item']['brand']} {best['item']['name']} you saved."
        else: reason = f"{phrase.capitalize()} from {c['brand']}, in the fabrics and colours you keep coming back to."
        out.append(dict(url=c['url'], brand=c['brand'], title=c['title'], category=c['category'], reason=reason))
    json.dump(out, open(f'{PEND}/picks.json', 'w'), indent=1, ensure_ascii=False)
    print('fallback picks:', [(p['brand'], p['title'][:30]) for p in out])

# ---------------- finalize ----------------
SPEC = re.compile(r'(\d{1,3}\s?%|^(fabric|material|composition|care|fit|made in|machine wash|hand wash|dry clean|inseam|rise|length|pockets?|zip|button|pull-?on|elastic|stretch|lined|unlined|relaxed|slim|oversized|cropped|high[- ]rise|wide[- ]leg|a-line|midi|maxi)\b)', re.I)
def parse_desc(body, brand):
    lines = [l.strip(' -•·*') for l in re.split(r'\n+|(?<=[.!?])\s+(?=[A-Z])', html.unescape(re.sub(r'<br\s*/?>|</p>|</li>|</div>|</h\d>', '\n', body or ''))) if l.strip()]
    lines = [clean(l) for l in lines if clean(l)]
    prose, det = [], []
    for l in lines:
        low = l.lower()
        if re.search(r'model|wearing size|measurements|size chart|^size|height:|bust:|waist:|hips?:|shipping|returns|designer\'s note|the details:', low): continue
        if re.search(r'founded|our story|since \d{4}|the brand', low): continue
        if (len(l) < 75 and SPEC.search(l)) or (re.search(r'\d{1,3}\s?%', l) and len(l) < 120): det.append(l.rstrip('.'))
        elif len(l) > 40: prose.append(l)
    desc = ' '.join(prose)
    if len(desc) > 600: cut = desc[:600]; desc = cut[:cut.rfind('. ') + 1] if '. ' in cut[250:] else cut + '…'
    seen = set(); dd = []
    for d in det:
        if d.lower() in seen or d.lower() in ('imported', 'machine wash', 'hand wash', 'dry clean'): continue
        seen.add(d.lower()); dd.append(d)
    pct = [d for d in dd if re.search(r'\d{1,3}\s?%', d) and len(d) < 90]
    fabric = min(pct, key=len) if pct else next((d for d in dd if re.search(r'\b(' + '|'.join(FABRICS) + r')\b', d.lower()) and len(d) < 60), None)
    if fabric:
        fabric = re.sub(r'^(?:Machine|Hand) wash[^.]*\.\s*', '', fabric); fabric = re.sub(r'^(?:Main|Body|Shell|Fabric|Composition|Material)\s*:\s*', '', fabric, flags=re.I)
        m = re.search(r'\d{1,3}\s?%.*', fabric); fabric = m.group(0) if m else fabric
    return desc or None, dd[:8], fabric
def occasions_for(text, category):
    """Tag a new piece with occasions, using the "auto" rules each occasion carries in config.js:
    categories (the piece's category must be one of them), any (regex the text must match), all (list of
    regexes that must all match), not (regex that must not match). One occasion may have role "default":
    it is added when its categories match or when nothing else matched; the one with role "otherwise" is
    added instead when the default did not apply. At most three tags, in config order."""
    t = text.lower(); tags = []; default = otherwise = None
    for o in OCCASIONS:
        a = o.get('auto') or {}
        if a.get('role') == 'default': default = (o['key'], a); continue
        if a.get('role') == 'otherwise': otherwise = o['key']; continue
        if not a: continue
        if a.get('categories') and category not in a['categories']: continue
        if a.get('any') and not re.search(a['any'], t): continue
        if a.get('all') and not all(re.search(r, t) for r in a['all']): continue
        if a.get('not') and re.search(a['not'], t): continue
        tags.append(o['key'])
    if default:
        key, a = default
        tags.append(key if category in a.get('categories', []) or not tags else (otherwise or key))
    seen = set(); return [x for x in tags if not (x in seen or seen.add(x))][:3]
def next_id():
    ids = [i['id'] for p in round_files() for i in json.load(open(p))] + [i['id'] for i in ideas()]
    if os.path.exists(f'{P}/retired.json'): ids += [i['id'] for i in json.load(open(f'{P}/retired.json'))]
    ids += [i['id'] for i in json.load(open('build/extras.json')) if i['id'] >= 5000]
    return max(ids + [5010]) + 1
def fetch_pick(pk, iid):
    d = json.loads(urllib.request.urlopen(urllib.request.Request(pk['url'].split('?')[0] + '.js', headers=H), timeout=40, context=ctx).read())
    body = d.get('description') or ''; desc, det, fabric = parse_desc(body, pk['brand'])
    if not fabric:
        m = re.search(r'\b(\d{1,2}[- ]wale )?(cotton )?(corduroy|cord|linen|denim|twill|wool|merino|tweed|flannel|canvas|moleskin|jersey|poplin|chambray|silk|cashmere)\b[^|,-]*', d['title'], re.I)
        if m: fabric = m.group(0).strip().capitalize()
    vs = d.get('variants', []); cents = all(isinstance(v['price'], int) for v in vs)
    avail = [v for v in vs if v.get('available')] or vs
    price = min(float(v['price']) for v in avail) / (100 if cents else 1); comp = [float(v['compare_at_price']) for v in avail if v.get('compare_at_price')]
    lst = (max(comp) / (100 if cents else 1)) if comp else price
    color, cdetail = colour_of({'title': d['title'], 'desc': clean(body)})
    for o in d.get('options', []):
        if re.search(r'colou?r', o['name'], re.I) and len(o['values']) == 1: cdetail = o['values'][0]; color = colour_of({'title': 'x in ' + cdetail, 'desc': ''})[0]
    imgs = [('https:' + s if s.startswith('//') else s) for s in d.get('images', [])]
    pick_img = next((s for s in imgs if cdetail and re.search(re.escape(cdetail.split()[0].lower()), s.lower())), imgs[0] if imgs else None)
    img_path = f'images/ideas/{iid}.jpg'
    if pick_img:
        from PIL import Image
        im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(pick_img.split('?')[0] + '?width=1000', headers=H), timeout=40, context=ctx).read())).convert('RGB'); im.thumbnail((900, 900)); im.save(img_path, 'JPEG', quality=82, optimize=True)
    if color == 'Multi/Print' and cdetail in ('As shown', '') and pick_img:
        try:
            from PIL import Image
            im = Image.open(img_path).convert('RGB'); w_, h_ = im.size; c = im.crop((int(w_*0.4), int(h_*0.35), int(w_*0.6), int(h_*0.6))).resize((8, 8))
            import colorsys
            hs = [colorsys.rgb_to_hsv(*(x/255 for x in p)) for p in c.getdata()]; hue = sum(h[0] for h in hs)/64; sat = sum(h[1] for h in hs)/64; val = sum(h[2] for h in hs)/64
            if val < 0.22: color = 'Black'
            elif sat < 0.12: color = 'White/Ivory' if val > 0.8 else 'Grey'
            elif hue < 0.05 or hue > 0.93: color = 'Red'
            elif hue < 0.11: color = 'Brown' if val < 0.6 else 'Orange/Rust'
            elif hue < 0.2: color = 'Yellow/Gold' if val > 0.6 else 'Beige/Tan'
            elif hue < 0.45: color = 'Green'
            elif hue < 0.7: color = 'Denim' if sat < 0.5 else 'Blue'
            elif hue < 0.85: color = 'Purple'
            else: color = 'Pink'
            cdetail = 'As shown'
        except Exception: pass
    if lst > price: det.append(f'On sale, was ${lst:.0f}')
    text = ' '.join([d['title'], desc or '', ' '.join(det), fabric or ''])
    occ = occasions_for(text, pk['category'])
    why = ', '.join([x for x in [fabric.lower() if fabric else None, next((w for w in CUTS if w in text.lower()), None), color.lower()] if x])
    closet_brands = {i['brand'] for i in catalogue()} | {i['retailer'] for i in catalogue()}
    return dict(id=iid, brand=pk['brand'], retailer=pk['brand'], name=d['title'], category=pk['category'], color=color, colorDetail=cdetail, categoryDetail=d.get('type') or pk['category'], price=price, list=lst,
                url=pk['url'], img=img_path, hi=bool(pick_img), desc=desc, details=det, fabric=fabric, occasions=occ, why=why, reason=pk['reason'], newBrand=pk['brand'] not in closet_brands)
def housekeeping():
    nb = notebook(); ex = json.load(open('build/extras.json')); retired = json.load(open(f'{P}/retired.json')) if os.path.exists(f'{P}/retired.json') else []
    ex_ids = {e['id'] for e in ex}; moved = passed = stale = 0
    for p in round_files():
        keep = []
        for i in json.load(open(p)):
            e = nb.get(str(i['id']), {})
            if e.get('s', {}).get('on') and i['id'] not in ex_ids:
                rec = dict(i); rec.pop('reason', None); rec.pop('newBrand', None); rec.pop('round', None); rec['img'] = f"images/full/{i['id']}.jpg"
                if os.path.exists(i['img']): os.replace(i['img'], rec['img'])
                ex.append(rec); ex_ids.add(i['id']); moved += 1; continue
            if e.get('p', {}).get('on'): retired.append(dict(id=i['id'], brand=i['brand'], name=i['name'], url=i['url'], why='passed', date=TODAY)); passed += 1; continue
            added = datetime.date.fromisoformat(i.get('added', TODAY))
            if (NOW.date() - added).days > 21: retired.append(dict(id=i['id'], brand=i['brand'], name=i['name'], url=i['url'], why='stale', date=TODAY)); stale += 1; continue
            keep.append(i)
        json.dump(keep, open(p, 'w'), indent=1, ensure_ascii=False)
    json.dump(ex, open('build/extras.json', 'w'), indent=1, ensure_ascii=False); json.dump(retired, open(f'{P}/retired.json', 'w'), indent=1, ensure_ascii=False)
    print(f'housekeeping: {moved} added to the closet, {passed} retired as passed, {stale} retired as stale')
def finalize(by):
    picks = json.load(open(f'{PEND}/picks.json')); housekeeping()
    n = len(round_files()) + 1; iid = next_id(); out = []
    for pk in picks:
        try: rec = fetch_pick(pk, iid); rec.update(round=n, added=TODAY, by=by); out.append(rec); iid += 1
        except Exception as e: print('skip', pk['brand'], pk['title'][:30], str(e)[:60])
    json.dump(out, open(f'{P}/round_{n}.json', 'w'), indent=1, ensure_ascii=False)
    subprocess.run([sys.executable, f'{P}/make_suggestions.py'], check=True); subprocess.run([sys.executable, 'build/make_data.py'], check=True)
    branch = os.environ.get('ROUND_BRANCH', 'main'); repo = repo_slug(); owner = os.environ.get('GITHUB_REPOSITORY_OWNER') or repo.split('/')[0]
    with open(f'{PEND}/pr_body.md', 'w') as f:
        f.write(f"## Round {n} · {TODAY} · {'chosen by Claude' if by == 'claude' else 'chosen by score (no model)'}\n\n@{owner} — {len(out)} ideas for **Based on your likes**. Merge to publish; close to skip this week.\n\n")
        for r in out:
            f.write(f"### {r['brand']} — {r['name']} · ${r['price']:.0f}\n<img src=\"https://raw.githubusercontent.com/{repo}/{branch}/{r['img']}\" width=\"220\">\n\n{r['reason']}  \n*{r['fabric'] or 'fibre not stated'} · {', '.join(r['occasions'])}* · [product page]({r['url']})\n\n")
    json.dump({'round': n, 'by': by, 'date': TODAY, 'ids': [r['id'] for r in out]}, open(f'{PEND}/last_round.json', 'w'))
    print(f'round {n} written: {len(out)} ideas by {by}')

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'stage1'
    if cmd == 'stage1': stage1()
    elif cmd == 'fallback': fallback()
    elif cmd == 'finalize': finalize(sys.argv[sys.argv.index('--by') + 1] if '--by' in sys.argv else 'score')
    elif cmd == 'signals':
        s, p = signals(); print('saved', [(x['item']['brand'], x['item']['name'][:30], x['age_days']) for x in s]); print('passed', [(x['item']['brand'], x['item']['name'][:30]) for x in p])
    else: print(__doc__)
