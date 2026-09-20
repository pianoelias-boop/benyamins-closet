import json, re, ssl, urllib.request, html, concurrent.futures as cf, collections
items = json.load(open('build/items_raw.json'))
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
H = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36',
     'Accept':'text/html,application/json,*/*;q=0.8','Accept-Language':'en-US,en;q=0.9'}
FAB = re.compile(r'([^.<>\n]{0,80}\b(?:\d{1,3}\s?%\s?(?:organic |recycled |pima |supima |merino |lambs?wool |virgin )?(?:cotton|linen|wool|cashmere|silk|viscose|rayon|lyocell|tencel|modal|polyester|nylon|elastane|spandex|lycra|polyamide|acrylic|alpaca|mohair|hemp|ramie|cupro|leather)\b[^.<>\n]{0,80}))', re.I)
def clean(s):
    s = re.sub(r'<br\s*/?>|</p>|</li>|</div>', '\n', s or '')
    s = re.sub(r'<[^>]+>', ' ', s); s = html.unescape(s)
    s = re.sub(r'[ \t\r\f\v]+', ' ', s); s = re.sub(r'\s*\n\s*', '\n', s)
    return s.strip()
def get(u, timeout=25):
    return urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=timeout, context=ctx).read().decode('utf-8','ignore')
def ldjson(page):
    out=[]
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S|re.I):
        try:
            d=json.loads(m.group(1)); out += d if isinstance(d,list) else [d]
        except Exception: pass
    return out
def work(it):
    u = it['url']; res = {'id': it['id'], 'desc': None, 'fabric': [], 'images': [], 'source': None, 'err': None}
    try:
        base = u.split('?')[0]
        if '/products/' in base:
            try:
                d = json.loads(get(base + '.js'))
                res['desc'] = clean(d.get('description')); res['source'] = 'shopify'
                res['images'] = [('https:' + s if s.startswith('//') else s) for s in d.get('images', [])][:6]
            except Exception as e:
                res['err'] = 'shopify:' + str(e)[:40]
        if not res['desc']:
            page = get(u)
            parts = []
            for o in ldjson(page):
                if isinstance(o, dict) and o.get('@type') in ('Product', ['Product']) and o.get('description'):
                    parts.append(clean(o['description'])); break
            m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', page, re.I) or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']', page, re.I)
            meta = clean(m.group(1)) if m else ''
            if meta and not any(meta[:60] in p for p in parts): parts.append(meta)
            res['desc'] = '\n'.join(p for p in parts if p) or None
            res['source'] = 'html'
            text = clean(page)
            res['fabric'] = list(dict.fromkeys(x.strip() for x in FAB.findall(text)))[:6]
        if res['desc']:
            res['fabric'] = list(dict.fromkeys(res['fabric'] + [x.strip() for x in FAB.findall(res['desc'])]))[:6]
    except Exception as e:
        res['err'] = f'{type(e).__name__}: {str(e)[:60]}'
    return res
out = {}
with cf.ThreadPoolExecutor(8) as ex:
    for r in ex.map(work, items): out[r['id']] = r
json.dump(out, open('build/desc_raw.json','w'), indent=1, ensure_ascii=False)
by = collections.defaultdict(lambda: [0,0])
for it in items:
    b = by[it['retailer']]; b[1]+=1
    if out[it['id']]['desc']: b[0]+=1
for k,(ok,tot) in sorted(by.items()): print(f'{k:22s} {ok:3d}/{tot}')
print('TOTAL with desc', sum(1 for v in out.values() if v['desc']), '/', len(items))
