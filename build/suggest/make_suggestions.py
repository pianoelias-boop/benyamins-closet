"""Concatenate build/suggest/round_*.json into suggestions.js (ideas shown in the New ideas section)."""
import json, glob, os
items=[]
for p in sorted(glob.glob('build/suggest/round_*.json')):
    if p.endswith('_raw.json'): continue
    items += [i for i in json.load(open(p)) if os.path.exists(i['img'])]
open('suggestions.js','w').write('window.SUGGESTIONS = ' + json.dumps(items, ensure_ascii=False, separators=(',',':')) + ';\n')
print(len(items), 'ideas in suggestions.js')
