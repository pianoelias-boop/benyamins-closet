"""Write brands.js (window.BRANDS) from build/suggest/brands.json for the "Browse brands" tab.

Run from the repo root:  python3 build/make_brands.py
Each entry: name, site (the store's origin, also used by the sweep and the sale check), link (a specific page
to open, if one was given), what (one line on what they make), status (approved = pieces in the closet,
proposed = on the list, rejected = hidden from the tab).
"""
import json
d = json.load(open('build/suggest/brands.json'))
rows = [dict(name=b['name'], site=b.get('site', ''), link=b.get('link') or b.get('site', ''), what=b.get('what', ''), status=b.get('status', 'proposed'))
        for b in d['brands'] if b.get('status') not in ('rejected', 'archived')]
rows.sort(key=lambda b: b['name'].lower().lstrip("'"))
open('brands.js', 'w').write('// The brand directory behind the "Browse brands" tab. Source: build/suggest/brands.json (python3 build/make_brands.py)\n'
                             'window.BRANDS = ' + json.dumps(rows, ensure_ascii=False, indent=1) + ';\n')
print('brands.js:', len(rows), 'brands')
