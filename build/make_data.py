"""Build data.js (window.CLOSET) from the catalog sources. Run from the repo root: python3 build/make_data.py

Sources, all optional except the first:
  build/items_raw.json   the original catalog (from a spreadsheet via extract.py, or [] for a closet built piece by piece)
  build/desc_final.json  scraped descriptions for those items, keyed by id
  build/occ/out_*.json   occasion re-tagging for those items, keyed by id
  build/extras.json      pieces added later (add_pieces.py); these carry everything they need, including the photo path
Occasion tags are validated against the list in config.js.
"""
import json, os, glob, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from closet_config import load, occasion_keys

VALID = set(occasion_keys(load()))
items = json.load(open('build/items_raw.json')) if os.path.exists('build/items_raw.json') else []
desc = json.load(open('build/desc_final.json')) if os.path.exists('build/desc_final.json') else {}
occ = {}
for p in sorted(glob.glob('build/occ/out_*.json')):
    try: occ.update(json.load(open(p)))
    except Exception as e: print('bad occ file', p, e)
DROP = {294, 295}   # two spreadsheet rows that were duplicates in the original catalog
out = []; retagged = 0
for it in items:
    if it['id'] in DROP: continue
    full = f'images/full/{it["id"]:03d}.jpg'
    hi = os.path.exists(full)
    d = desc.get(str(it['id']), {})
    o = occ.get(str(it['id']))
    tags = [t for t in (o or {}).get('tags', []) if t in VALID]
    if tags: retagged += 1
    else: tags = [t for t in it['occasions'] if t in VALID]
    out.append(dict(id=it['id'], brand=it['brand'], retailer=it['retailer'], name=it['name'],
        category=it['category'], color=it['color'], occasions=tags, why=(o or {}).get('why'), price=it['price'],
        colorDetail=it['colorDetail'], categoryDetail=it['categoryDetail'], url=it['url'],
        img=full if hi else it['thumb'], hi=hi,
        desc=d.get('desc'), details=d.get('details') or [], fabric=d.get('fabric')))
if os.path.exists('build/extras.json'):
    extras = json.load(open('build/extras.json'))
    bad = [(e['id'], t) for e in extras for t in e.get('occasions', []) if t not in VALID]
    if bad: print('warning: occasion tags not in config.js:', bad[:10])
    out.extend(e for e in extras if os.path.exists(e['img']))
    print('added', len(extras), 'extra items')
with open('data.js', 'w') as f:
    f.write('window.CLOSET = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(len(out), 'items,', sum(1 for o in out if o['hi']), 'hi-res,', sum(1 for o in out if not o['hi']), 'thumbnail-only,', retagged, 'retagged,', sum(1 for o in out if o['desc']), 'with description')
print('thumb-only by retailer', dict(collections.Counter(o['retailer'] for o in out if not o['hi'])))
print('tag counts', dict(collections.Counter(t for o in out for t in o['occasions'])))
