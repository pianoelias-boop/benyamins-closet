import json, ssl, urllib.request, io, re, sys, concurrent.futures as cf
from PIL import Image
items = json.load(open('build/items_raw.json')); out = json.load(open('build/hires_urls.json'))
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
H = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36','Accept':'image/avif,image/webp,image/apng,image/*,*/*;q=0.8','Accept-Language':'en-US,en;q=0.9','Sec-Fetch-Dest':'image','Sec-Fetch-Mode':'no-cors','Sec-Fetch-Site':'same-origin'}
MAX = 900
def tweak(u):
    u = re.sub(r'wid=\d+&hei=\d+', 'wid=800&hei=1000', u)          # Abercrombie
    u = u.replace('_1024x1024.', '_1200x1200.').replace('_1024x.', '_1200x.')
    u = re.sub(r'-\d+x\d+\.(jpe?g|png)$', r'.\1', u)                 # WP thumbnails
    return u
def work(it):
    u = out[str(it['id'])]['img']
    if not u: return it['id'], None
    dest = f'images/full/{it["id"]:03d}.jpg'
    import os
    if os.path.exists(dest): return it['id'], dest
    err = Exception("too small")
    for cand in [tweak(u), u]:
        try:
            hh = dict(H); hh['Referer'] = re.match(r'https?://[^/]+', cand).group(0) + '/'
            data = urllib.request.urlopen(urllib.request.Request(cand, headers=hh), timeout=25, context=ctx).read()
            im = Image.open(io.BytesIO(data)); im.load()
            if im.mode in ('RGBA','LA','P'):
                bg = Image.new('RGB', im.size, (250,247,242)); bg.paste(im.convert('RGBA'), mask=im.convert('RGBA').split()[-1]); im = bg
            im = im.convert('RGB')
            if max(im.size) < 300: continue
            im.thumbnail((MAX, MAX)); im.save(dest, 'JPEG', quality=82, optimize=True)
            return it['id'], dest
        except Exception as e:
            err = e
    return it['id'], f'ERR {type(err).__name__}'
res = {}
with cf.ThreadPoolExecutor(8) as ex:
    for iid, r in ex.map(work, items): res[iid] = r
ok = [k for k,v in res.items() if v and v.startswith('images')]
bad = {k:v for k,v in res.items() if v and not v.startswith('images')}
print('downloaded', len(ok), 'failed', bad)
import subprocess; print(subprocess.run(['du','-sh','images/full'],capture_output=True,text=True).stdout)
