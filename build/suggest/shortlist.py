"""Score the sweep against the closet's taste (his own saves for now, his hearts/passes once the notebook fills)."""
import json, re, collections, sys
cands=json.load(open('build/suggest/candidates.json'))
closet=json.load(open('data.js').read().split('=',1)[1].rstrip(';\n')) if False else None
import subprocess
data=json.loads(open('data.js').read().split('= ',1)[1].rstrip(';\n'))
# ---- taste profile from the closet (proxy until he has hearted things) ----
cat_share=collections.Counter(i['category'] for i in data); n=len(data)
price_med=sorted(i['price'] for i in data if i['price'])[n//2]
LIKE=re.compile(r'wide[- ]leg|pleat|high[- ]rise|relaxed|linen|seersucker|herringbone|corduroy|cord\b|selvedge|japanese|denim|cotton|wool|merino|mohair|alpaca|cardigan|cable|stripe|patchwork|embroider|pocket|cargo|fatigue|camp collar', re.I)
DISLIKE=re.compile(r'bodycon|mini(?!mal)|crop(ped)? (top|tee|tank)|sheer|mesh|sequin|strapless|tube|cut-?out|bralette|bikini|micro|thong|lingerie|corset|lace-up|latex|faux leather|pleather|vegan leather', re.I)
DANCE=re.compile(r'jersey|wrap|a-line|tiered|circle|swing|stretch|knit|wide[- ]leg|linen|cotton', re.I)
def score(c):
    s=0.0
    s+=2.0*cat_share[c['category']]/n*10          # categories the closet already leans to
    if c['natural'] is not None: s+=1.5*c['natural']
    elif c['fabric']: s+=0.6
    else: s-=1.5
    s-=abs(c['list']-price_med)/price_med*0.8
    blob=f"{c['title']} {c['desc']}"
    s+=0.35*min(len(LIKE.findall(blob)),6)
    s-=1.2*len(DISLIKE.findall(blob))
    if DANCE.search(blob): s+=0.3
    if 'final sale' in ' '.join(c['tags']).lower(): s-=0.5
    if c['status']=='proposed': s+=0.2
    return s
for c in cands: c['score']=round(score(c),2)
# collapse colourways: same brand + title stripped of " in <colour>" / " - colour"
def key(c): return (c['brand'], re.sub(r'\s+(in|-|–|—|/)\s+.*$','',c['title'].lower()).strip())
best={}
for c in sorted(cands, key=lambda c:-c['score']):
    k=key(c)
    if k not in best: best[k]=c
uniq=list(best.values())
# balanced shortlist: top N per category, split approved/proposed
QUOTA={'Trousers':16,'Jeans':8,'Shirts':10,'Knitwear':10,'Tees & Polos':6,'Jackets & Coats':8,'Suits & Blazers':4,'Shorts & Swim':4}
short=[]
for cat,q in QUOTA.items():
    pool=[c for c in uniq if c['category']==cat]
    appr=[c for c in pool if c['status']=='approved'][:q//2+1]; prop=[c for c in pool if c['status']=='proposed'][:q//2+1]
    short+=appr+prop
json.dump(short, open('build/suggest/shortlist.json','w'), indent=0, ensure_ascii=False)
print('unique products', len(uniq), '| shortlist', len(short))
for c in short:
    print(f"[{c['status'][0]}] {c['brand']} | {c['title'][:48]} | {c['category'][:8]} | ${c['price']:.0f}" + (f" (list ${c['list']:.0f})" if c['list']!=c['price'] else '') + f" | {c['fabric'] or 'fibre?'} | {c['score']} | {c['url']}")
print('\n=== proposed-brand summaries ===')
by=collections.defaultdict(list)
for c in cands:
    if c['status']=='proposed': by[c['brand']].append(c)
for b,cs in sorted(by.items(), key=lambda kv:-len(kv[1])):
    prices=sorted(c['list'] for c in cs); nat=[c['natural'] for c in cs if c['natural'] is not None]
    cats=collections.Counter(c['category'] for c in cs).most_common(3)
    print(f"{b:22s} {len(cs):4d} pieces in range | ${prices[len(prices)//10]:.0f}–${prices[len(prices)*9//10]:.0f} typical | fibre stated on {len(nat)}/{len(cs)}, natural share {sum(nat)/len(nat):.0%} avg | {', '.join(f'{k} {v}' for k,v in cats)}" if nat else f"{b:22s} {len(cs):4d} pieces | ${prices[0]:.0f}–${prices[-1]:.0f} | fibre rarely stated")
