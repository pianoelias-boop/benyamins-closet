"""Write retailers.js (window.RETAILERS) from build/returns/retailers.json.

Run from the repo root:  python3 build/returns/make.py
The site loads retailers.js with an hourly cache stamp, so no version bump is needed.
"""
import json
d = json.load(open('build/returns/retailers.json'))
assert all(v.get('window') and v.get('ship') and v.get('policy') for v in d['stores'].values()), 'every store needs window, ship, policy'
assert not any('WINDOW_' in v['window'] for v in d['stores'].values()), 'placeholder left in retailers.json'
open('retailers.js', 'w').write('// Return terms per store, as each states them for US orders. Source: build/returns/retailers.json\n'
                                'window.RETAILERS = ' + json.dumps(d, ensure_ascii=False, indent=1) + ';\n')
print('retailers.js:', len(d['stores']), 'stores, checked', d['checked'])
