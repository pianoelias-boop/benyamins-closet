"""Home-screen icons and the web app manifest, from config.js (the emoji) and theme.css (the colours).

Run from the repo root:  python3 build/make_icons.py
Writes icons/apple-touch-icon.png (180), icons/icon-192.png, icons/icon-512.png and manifest.json, so the site
can be added to an iPhone or Android home screen as an app with its own icon and no browser bars.
"""
import json, re, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from closet_config import load
from PIL import Image, ImageDraw, ImageFont
cfg = load(); theme = open('theme.css').read()
def var(name, default): m = re.search(r'--' + name + r':\s*(#[0-9a-fA-F]{6})', theme); return m.group(1) if m else default
bg, accent = var('bg', '#FFFFFF'), var('accent-tint', '#EEEEEE')
icon = cfg.get('icon') or '♥'
FONT = '/System/Library/Fonts/Apple Color Emoji.ttc'
os.makedirs('icons', exist_ok=True)
def render(size, path, pad=0.18):
    im = Image.new('RGBA', (size, size), bg)
    d = ImageDraw.Draw(im)
    r = int(size * 0.42); c = size // 2
    d.ellipse((c - r, c - r, c + r, c + r), fill=accent)                     # a soft disc behind the emoji
    try:   # Apple's emoji font only renders at fixed bitmap sizes, so draw it at 160 px and scale the glyph
        f = ImageFont.truetype(FONT, 160)
        layer = Image.new('RGBA', (240, 240), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
        ld.text((40, 40), icon, font=f, embedded_color=True)
        layer = layer.crop(layer.getbbox())
        target = int(size * (1 - 2 * pad) * 0.72)
        layer = layer.resize((target, int(target * layer.height / layer.width)), Image.LANCZOS)
        im.alpha_composite(layer, (c - layer.width // 2, c - layer.height // 2))
    except Exception as e:
        print('emoji font failed, drawing a plain disc:', e)
    im.convert('RGB').save(path, 'PNG', optimize=True)
render(180, 'icons/apple-touch-icon.png'); render(192, 'icons/icon-192.png'); render(512, 'icons/icon-512.png')
title = cfg.get('siteTitle', 'Closet'); short = 'Closet' if len(title) > 12 else title
json.dump({
    'name': title, 'short_name': short, 'description': cfg.get('description', ''),
    'start_url': './', 'scope': './', 'display': 'standalone', 'background_color': bg, 'theme_color': bg,
    'icons': [{'src': 'icons/icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
              {'src': 'icons/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'}],
}, open('manifest.json', 'w'), indent=1)
print('icons and manifest.json written for', title)
