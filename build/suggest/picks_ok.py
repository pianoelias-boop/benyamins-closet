"""Check (and if needed repair) the judge's picks before the round is built. Run from the repo root:

    python3 build/suggest/picks_ok.py      exit 0: build/suggest/pending/picks_claude.json is a valid list of picks
                                            exit 1: it cannot be trusted; leave the week to the score-based fallback

The judge saves its picks through a GitHub file tool, and on 2026-10-10 it passed that tool base64 text (with
part of the JSON double-escaped), so the repository received a scrambled file and the round crashed. This
script accepts plain JSON, base64 of JSON, and JSON whose newlines and quotes were escaped one level too
many; rewrites the file as plain JSON when it had to repair it; and checks that every pick is on this week's
shortlist with the same title and category, with no duplicates.
"""
import base64, binascii, json, os, sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pending')
PICKS, SHORT = os.path.join(P, 'picks_claude.json'), os.path.join(P, 'shortlist.json')


def candidates(text):
    yield text
    t = text.strip()
    try: yield base64.b64decode(t, validate=False).decode('utf-8')
    except (binascii.Error, UnicodeDecodeError, ValueError): pass


def parse(text):
    for c in candidates(text):
        for v in (c, c.replace('\\n', '\n').replace('\\"', '"')):
            try:
                d = json.loads(v)
                if isinstance(d, str): d = json.loads(d)   # JSON that was itself wrapped in a JSON string
                return d
            except (json.JSONDecodeError, TypeError): continue
    return None


def main():
    raw = open(PICKS, encoding='utf-8').read()
    picks = parse(raw)
    if not isinstance(picks, list) or not picks:
        print('picks: unreadable, leaving the week to the fallback', file=sys.stderr); return 1
    short = {x['url']: x for x in json.load(open(SHORT, encoding='utf-8'))}
    bad = [p.get('url') for p in picks if not isinstance(p, dict) or p.get('url') not in short
           or short[p['url']]['title'] != p.get('title') or short[p['url']]['category'] != p.get('category') or not p.get('reason')]
    dupes = len(picks) != len({p.get('url') for p in picks if isinstance(p, dict)})
    if bad or dupes:
        print(f'picks: {len(bad)} not on the shortlist as written{", duplicates" if dupes else ""}: {bad[:3]}', file=sys.stderr); return 1
    clean = json.dumps(picks, indent=1, ensure_ascii=False) + '\n'
    try: plain = json.loads(raw) == picks
    except json.JSONDecodeError: plain = False
    if not plain:
        open(PICKS, 'w', encoding='utf-8').write(clean); print('picks: repaired to plain JSON', file=sys.stderr)
    print(f'picks: {len(picks)} valid', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
