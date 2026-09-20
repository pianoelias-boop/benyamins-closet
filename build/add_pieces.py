"""Add pieces to the closet from a CSV list. Run from the repo root:

    python3 build/add_pieces.py                 # reads build/pieces_to_add.csv, then rebuilds data.js
    python3 build/add_pieces.py my_list.csv     # another file
    python3 build/add_pieces.py --dry-run       # say what would be added, fetch nothing

Each row is one piece. For a Shopify store (most independent brands; the product URL contains /products/)
only url, brand, category, color and occasions are required: the price, description, fabric line and the
first photo come from the product's JSON. For any other store, also give price and img (a photo URL or a
local file) and as much of the rest as you know. Rows whose url is already in the closet are skipped, so
the file can stay as a record of what was added. Shopify answers a burst of requests with HTTP 429; the
script waits a minute and retries, so a long list simply takes a while.

Columns (header row required, any order)
  url             product page (required)
  brand           the label on the garment (required)
  retailer        the store you buy it from, if different from the brand
  name            display name; default: the store's product title
  category        one of CATEGORIES below (required)
  categoryDetail  the store's own type, e.g. "Cord A-line skirt"
  color           one of COLORS below (required)
  colorDetail     the store's colour name, e.g. "Carbon Black"
  occasions       occasion keys from config.js, separated by ";" e.g. "teaching; hang" (required)
  why             one line on why it earns those occasions; shown in the detail view
  fabric          fibre line, e.g. "100% cotton"; default: parsed from the description
  details         extra bullet points for the detail view, separated by ";"
  price           number in dollars; required when the store is not Shopify
  img             photo URL or local file path; default: the product's first Shopify photo
  id              a fixed id; default: the next free number
"""
import csv, json, ssl, urllib.request, urllib.error, re, html, io, time, sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from closet_config import load, occasion_keys

# Keep these two lists in step with CATEGORY_ORDER and COLOR_ORDER at the top of app.js.
CATEGORIES = ['Shirts', 'Tees & Polos', 'Knitwear', 'Trousers', 'Jeans', 'Shorts & Swim', 'Jackets & Coats', 'Suits & Blazers', 'Shoes', 'Accessories']
COLORS = ['Black', 'Grey', 'White/Ivory', 'Beige/Tan', 'Brown', 'Denim', 'Blue', 'Green', 'Red', 'Pink', 'Purple', 'Orange/Rust', 'Yellow/Gold', 'Multi/Print']

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
H = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1', 'Accept': 'application/json,image/*,*/*'}


def get(u, tries=12):
    for i in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=40, context=ctx).read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1: print(f'  429 from {u.split("/")[2]}, waiting 60s'); time.sleep(60); continue
            raise


def clean(s): return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or ''))).strip()
def split_list(s): return [x.strip() for x in (s or '').split(';') if x.strip()]
def bare(u): return (u or '').split('?')[0].split('#')[0].rstrip('/').lower()


def save_photo(data, path):
    from PIL import Image
    im = Image.open(io.BytesIO(data)); im.load()
    if im.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', im.size, (255, 255, 255)); bg.paste(im.convert('RGBA'), mask=im.convert('RGBA').split()[-1]); im = bg
    else: im = im.convert('RGB')
    im.thumbnail((900, 900)); os.makedirs(os.path.dirname(path), exist_ok=True); im.save(path, 'JPEG', quality=84, optimize=True)
    return im.size


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]; dry = '--dry-run' in sys.argv; build = '--no-build' not in sys.argv
    src = args[0] if args else 'build/pieces_to_add.csv'
    valid_occ = set(occasion_keys(load()))
    extras = json.load(open('build/extras.json')) if os.path.exists('build/extras.json') else []
    raw = json.load(open('build/items_raw.json')) if os.path.exists('build/items_raw.json') else []
    have_urls = {bare(i['url']) for i in extras + raw}
    used_ids = {i['id'] for i in extras + raw}
    next_id = max([i for i in used_ids if i < 5000] + [0]) + 1     # ids 5000+ belong to the weekly ideas
    rows = list(csv.DictReader(open(src, encoding='utf-8-sig')))
    added = 0
    for n, r in enumerate(rows, 2):
        r = {k.strip(): (v or '').strip() for k, v in r.items() if k}
        url = r.get('url')
        if not url: continue
        if bare(url) in have_urls: print(f'row {n}: already in the closet, skipped: {url}'); continue
        problems = [f'missing {k}' for k in ('brand', 'category', 'color', 'occasions') if not r.get(k)]
        occ = split_list(r.get('occasions'))
        bad_occ = [o for o in occ if o not in valid_occ]
        if bad_occ: problems.append(f'occasions not in config.js: {bad_occ} (have {sorted(valid_occ)})')
        if problems: print(f'row {n}: skipped, {"; ".join(problems)}'); continue
        if r['category'] not in CATEGORIES: print(f'row {n}: note, category "{r["category"]}" is not one of {CATEGORIES}')
        if r['color'] not in COLORS: print(f'row {n}: note, color "{r["color"]}" is not one of {COLORS}')
        iid = int(r['id']) if r.get('id') else next_id
        if iid in used_ids: print(f'row {n}: id {iid} is taken, skipped'); continue
        if dry: print(f'row {n}: would add {iid} {r["brand"]} {r.get("name") or url}'); added += 1; continue

        d = None
        if '/products/' in url:
            try: d = json.loads(get(url.split('?')[0] + '.js'))
            except Exception as e: print(f'row {n}: no Shopify data ({str(e)[:60]}), using the row as given')
        name = r.get('name') or (d or {}).get('title')
        price = float(r['price']) if r.get('price') else ((d or {}).get('price') or 0) / 100
        if not name or not price:
            print(f'row {n}: skipped, this store is not Shopify so name and price must be in the CSV'); continue
        full = clean((d or {}).get('description', ''))
        desc = re.split(r'\s###\s|Size & Fit', full)[0].strip()[:600] or None
        details = split_list(r.get('details'))
        for pat in [r'\d{1,3}% [A-Za-z ]+?(?=[,.;]|$)', r'Machine wash[^.]*\.', r'Made in [A-Z][a-z]+']:
            for m in re.findall(pat, full):
                m = m.strip().rstrip('.')
                if m and m not in details and len(details) < 8: details.append(m)
        fabric = r.get('fabric') or next((x for x in details if re.search(r'\d{1,3}%', x)), None)
        path = f'images/full/{iid}.jpg'
        try:
            if r.get('img', '').startswith('http'): size = save_photo(get(r['img']), path)
            elif r.get('img'): size = save_photo(open(r['img'], 'rb').read(), path)
            else:
                imgs = [('https:' + s if s.startswith('//') else s) for s in (d or {}).get('images', [])]
                if not imgs: raise ValueError('no photo: give an img column')
                hint = (r.get('colorDetail') or '').split()[0].lower() if r.get('colorDetail') else ''
                pick = next((s for s in imgs if hint and hint in s.lower()), imgs[0])
                size = save_photo(get(pick.split('?')[0] + '?width=1000'), path)
        except Exception as e:
            print(f'row {n}: skipped, photo failed ({str(e)[:80]})'); continue
        extras.append(dict(id=iid, brand=r['brand'], retailer=r.get('retailer') or r['brand'], name=name, category=r['category'], color=r['color'],
                           occasions=occ, why=r.get('why') or None, price=price, colorDetail=r.get('colorDetail') or None,
                           categoryDetail=r.get('categoryDetail') or (d or {}).get('type') or r['category'], url=url, img=path, hi=True,
                           desc=desc, details=details, fabric=fabric))
        used_ids.add(iid); have_urls.add(bare(url)); next_id = max(next_id, iid + 1); added += 1
        print(f'{iid} {r["brand"]} {name} ${price:g} | photo {size[0]}x{size[1]}')
    if dry: print(f'dry run: {added} rows would be added'); return
    extras.sort(key=lambda e: e['id'])
    json.dump(extras, open('build/extras.json', 'w'), indent=1, ensure_ascii=False)
    print(f'{added} added; build/extras.json now holds {len(extras)} pieces')
    if build and added: subprocess.run([sys.executable, 'build/make_data.py'], check=True)


if __name__ == '__main__':
    main()
