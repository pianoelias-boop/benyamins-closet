"""Read config.js (the site's personal settings) from Python.

config.js is a browser file, but everything after "window.CLOSET_CONFIG =" is strict JSON, so the build
scripts can share it: the occasion tags, the notebook key and URL, the site title.

    from closet_config import load
    cfg = load()                       # dict
    keys = occasion_keys(cfg)          # ['teaching', 'dance', ...]

Run this file directly to check that config.js parses:  python3 build/closet_config.py
"""
import json, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PATH = os.path.join(ROOT, 'config.js')


def load(path=PATH):
    txt = open(path, encoding='utf-8').read()
    m = re.search(r'window\.CLOSET_CONFIG\s*=\s*(\{.*\})\s*;?\s*$', txt, re.S)
    if not m:
        raise SystemExit(f'{path}: expected "window.CLOSET_CONFIG = {{ ... }};" with nothing after it')
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise SystemExit(f'{path}: the part after "window.CLOSET_CONFIG =" must be strict JSON ({e})')


def occasion_keys(cfg):
    return [o['key'] for o in cfg.get('occasions', [])]


def occasions(cfg):
    """The occasion list with its auto-tagging rules, for scripts that classify new pieces."""
    return cfg.get('occasions', [])


if __name__ == '__main__':
    c = load(sys.argv[1] if len(sys.argv) > 1 else PATH)
    missing = [k for k in ('slug', 'siteTitle', 'text', 'occasions', 'email') if k not in c]
    print('config.js parses;', 'site:', c.get('siteTitle'), '| slug:', c.get('slug'), '| notebook key:', c.get('notebookKey'),
          '| sync:', 'set' if c.get('syncUrl') else 'off', '| occasions:', ', '.join(occasion_keys(c)) or 'none',
          '| person photos:', len((c.get('person') or {}).get('photos', [])))
    if missing: print('missing keys:', ', '.join(missing))
