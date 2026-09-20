import json, re, ssl, urllib.request, html, concurrent.futures as cf, collections
items = json.load(open('build/items_raw.json'))
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
H = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36',
     'Accept':'text/html,application/xhtml+xml,*/*;q=0.8','Accept-Language':'en-US,en;q=0.9'}
def find_img(page):
    for pat in [r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)']:
        m = re.search(pat, page, re.I)
        if m: return html.unescape(m.group(1))
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S|re.I):
        try:
            d = json.loads(m.group(1))
            objs = d if isinstance(d, list) else [d]
            for o in objs:
                if isinstance(o, dict) and 'image' in o:
                    im = o['image']; im = im[0] if isinstance(im, list) else im
                    if isinstance(im, dict): im = im.get('url') or im.get('contentUrl')
                    if isinstance(im, str): return im
        except Exception: pass
    return None
def work(it):
    try:
        req = urllib.request.Request(it['url'], headers=H)
        page = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode('utf-8','ignore')
        u = find_img(page)
        if u and u.startswith('//'): u = 'https:' + u
        return it['id'], u, None
    except Exception as e:
        return it['id'], None, f'{type(e).__name__}: {str(e)[:60]}'
out = {}
with cf.ThreadPoolExecutor(8) as ex:
    for iid, u, err in ex.map(work, items):
        out[iid] = {'img': u, 'err': err}
json.dump(out, open('build/hires_urls.json','w'), indent=1)
by = collections.defaultdict(lambda:[0,0,collections.Counter()])
for it in items:
    r = out[it['id']]; b = by[it['retailer']]; b[1]+=1
    if r['img']: b[0]+=1
    else: b[2][(r['err'] or 'no-img-tag')[:40]]+=1
for k,(ok,tot,errs) in sorted(by.items()): print(f'{k:22s} {ok:3d}/{tot:<3d}', dict(errs) if ok<tot else '')
print('TOTAL', sum(1 for v in out.values() if v['img']), '/', len(items))
