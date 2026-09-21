"""Sweep Shopify catalogues of approved/proposed brands into a candidate list under the closet's rules."""
import json, re, ssl, urllib.request, html, sys, time, concurrent.futures as cf
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
H={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36','Accept':'application/json'}
cfg=json.load(open('build/suggest/brands.json')); R=cfg['rules']
def _existing():
    ex=json.load(open('build/items_raw.json'))+json.load(open('build/extras.json'))
    import glob
    for p in glob.glob('build/suggest/round_*.json'):
        if not p.endswith('_raw.json'): ex+=json.load(open(p))
    import os
    if os.path.exists('build/suggest/retired.json'): ex+=json.load(open('build/suggest/retired.json'))
    return ex
existing=_existing()
exist_urls={i['url'].split('?')[0].rstrip('/').lower() for i in existing}
exist_titles={(i['brand'].lower(), re.sub(r'[^a-z0-9]','',i['name'].lower())) for i in existing}
NATURAL={'cotton','linen','wool','silk','cashmere','hemp','ramie','alpaca','mohair','tencel','lyocell','modal','cupro','viscose','rayon','merino','lambswool','flax','jute','yak','camel','ecovero'}
SYN={'polyester','nylon','polyamide','acrylic','elastane','spandex','lycra','polyurethane','pu','pvc','metallic','elastomultiester'}
CAT_RULES=[('Suits & Blazers',r'blazer|\bsuit\b|sport ?coat|waistcoat'),('Jackets & Coats',r'jacket|\bcoat\b|parka|overshirt|shacket|chore|anorak|windcheater|bomber|trucker|\bvest\b|gilet|overcoat|duffle|duffel'),('Shorts & Swim',r'\bshorts?\b(?! sleeve)|swim|trunks?\b'),('Jeans',r'\bjean|denim (pant|trouser)'),('Trousers',r'\bpant|trouser|chino|jogger|sweatpant|fatigue|cargo|hakama'),('Tees & Polos',r'\btee\b|t-shirt|tshirt|\bpolo\b|henley|\btank\b|\btop\b'),('Knitwear',r'sweater|cardigan|jumper|\bknit|pullover|hoodie|sweatshirt|crewneck|fleece|gansey|guernsey'),('Shirts',r'\bshirt|button[- ]?(up|down)|popover|camp collar')]
EXCL=re.compile(r"\bwomen'?s?\b|\bwomens\b|\bladies\b|\bdress(?:es)?\b(?! (?:shirt|pant|trouser))|\bskirt|\bblouse|\bkid|\bbaby|\bgift card|\bcandle|\bmug\b|\bsock|\bshoe|\bboot|\bsandal|\bhat\b|\bcap\b|\bscarf|\bbag\b|\btote|\bbelt\b|\bjewel|\bearring|\bnecklace|\bswim|\bbikini|\bunderwear|\bbra\b|\bpanty|\bbrief|\bpillow|\bblanket|\bhome\b|\bapron|\bdog\b|\bbook\b|\bprint\b(?!ed)|\bposter|\bpin\b|\bpatch\b|\bsticker|\bmask\b|\bbeanie|\bglove|\bmitten|\bpajama|\bpyjama|\bsleep|\brobe\b|\bbeauty|\bperfume|\bsoap|\bcandle", re.I)
def fibres(text):
    t=html.unescape(re.sub(r'<[^>]+>',' ',text or '')).lower().replace('％','%')
    found=re.findall(r'(\d{1,3})\s?%\s?(?:organic |recycled |pima |supima |merino |virgin |italian |european |french |belgian |japanese |regenerative |certified |gots |bci |washed |brushed |mercerized |slub |ring[- ]spun |combed )*([a-z]+)', t)
    nat=syn=0; parts=[]
    for pct,fib in found:
        p=int(pct);
        if p>100: continue
        if fib in NATURAL: nat+=p; parts.append(f'{p}% {fib}')
        elif fib in SYN: syn+=p; parts.append(f'{p}% {fib}')
    if not parts:
        # unquantified but explicit
        m=re.search(r'\b(100% |pure )?(linen|cotton|silk|wool|cashmere|merino|tencel|lyocell)\b', t)
        return (None, m.group(0) if m else None)
    tot=nat+syn
    return (nat/tot if tot else None, ', '.join(parts[:4]))
def category(title, ptype, tags):
    blob=f'{title} {ptype} {" ".join(tags or [])}'.lower()
    if EXCL.search(blob) and not re.search(r'pant|trouser|jean|shirt|sweater|cardigan|jacket|coat|blazer|\btee\b|polo|short|knit', title.lower()): return None
    if re.search(r"\bwomen'?s?\b|\bwomens\b|\bladies\b", blob) and not re.search(r"\bmen'?s?\b|\bmens\b|\bunisex\b", blob): return None
    for cat,pat in CAT_RULES:
        if re.search(pat, title.lower()) or re.search(pat, (ptype or '').lower()): return cat
    return None
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30,context=ctx).read()
def sweep(b):
    base=b['site'].rstrip('/'); out=[]; note=None
    try:
        page=1
        while page<=12:
            data=json.loads(get(f'{base}/products.json?limit=250&page={page}'))
            prods=data.get('products',[])
            if not prods: break
            for p in prods:
                title=p.get('title') or ''; ptype=p.get('product_type') or ''; tags=p.get('tags') or []
                cat=category(title, ptype, tags)
                if not cat: continue
                vs=[v for v in p.get('variants',[]) if v.get('available', True)]
                if not vs: continue
                price=min(float(v['price']) for v in vs)
                comp=[float(v['compare_at_price']) for v in vs if v.get('compare_at_price')]
                lst=max(comp) if comp else price
                if not (R['price_min']<=lst<=R['price_max']): continue
                url=f"{base}/products/{p['handle']}"
                if url.lower() in exist_urls or (b['name'].lower(), re.sub(r'[^a-z0-9]','',title.lower())) in exist_titles: continue
                share,fab=fibres(p.get('body_html'))
                if share is not None and share<R['natural_min_share']: continue
                if share is None and not fab: fabnote='unknown'
                else: fabnote=fab
                img=(p.get('images') or [{}])[0].get('src')
                desc=html.unescape(re.sub(r'<[^>]+>',' ',p.get('body_html') or '')); desc=re.sub(r'\s+',' ',desc).strip()[:600]
                out.append(dict(brand=b['name'], status=b['status'], title=title, category=cat, price=price, list=lst, fabric=fabnote, natural=share, url=url, img=img, tags=tags[:6], desc=desc, published=p.get('published_at','')[:10]))
            page+=1; time.sleep(0.4)
    except Exception as e:
        note=f'{type(e).__name__}: {str(e)[:60]}'
    return b['name'], out, note
def sweep_brands(statuses={'approved'}, workers=6, quiet=False):
    brands=[b for b in cfg['brands'] if b['status'] in statuses and b.get('feed', True) is not False and b.get('site')]   # feed:false marks stockist pages and non-Shopify sites
    allc=[]; report=[]
    with cf.ThreadPoolExecutor(workers) as ex:
        for name,out,note in ex.map(sweep, brands):
            allc+=out; report.append((name,len(out),note))
    if not quiet:
        for name,n,note in sorted(report, key=lambda r:-r[1]): print(f'{name:24s} {n:4d}  {note or ""}')
        print('TOTAL candidates', len(allc))
    return allc, report

if __name__=='__main__':
    statuses=set(sys.argv[1].split(',')) if len(sys.argv)>1 else {'approved','proposed'}
    allc,report=sweep_brands(statuses)
    json.dump(allc, open('build/suggest/candidates.json','w'), indent=0, ensure_ascii=False)
