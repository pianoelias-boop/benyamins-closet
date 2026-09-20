"""Start a fresh closet from this code. Removes the original catalog, its photos, the weekly-idea rounds,
the sale history and the return terms, and leaves the site, the build scripts and the workflows.

    python3 build/reset_closet.py          # dry run: lists what would go and what would be emptied
    python3 build/reset_closet.py --yes    # do it

Run it once, right after copying the repository and before adding your own pieces. It refuses to run
while config.js still carries the original slug "beccas-closet", so personalise config.js first (which is
also the reminder to change the names, the texts and the email address).
"""
import json, os, shutil, sys, glob, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from closet_config import load

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); os.chdir(ROOT)
TODAY = datetime.date.today().isoformat()

REMOVE = [
    'images',                                  # every photo: the catalog, the ideas, the person collage
    'specs',                                   # session handoff notes from the original build
    'build/suggest/pending', 'build/suggest/candidates.json', 'build/suggest/shortlist.json', 'build/suggest/signals.json',
    'build/suggest/retired.json', 'build/suggest/round_1_contact.jpg', 'build/suggest/round_1_raw.json', 'build/suggest/__pycache__',
    'build/sales/__pycache__', 'build/returns/raw', 'build/returns/fetch_log.json',
    # one-off scripts and scraped data from the original catalog; the generic pipeline (extract, fetch_desc, fetch_hires, download) stays
    'build/anthro.json', 'build/browser_desc.json', 'build/browser_results.json', 'build/browser_todo.json', 'build/desc_final.json',
    'build/desc_raw.json', 'build/extra_specs.json', 'build/hires_urls.json', 'build/nasrin_contact.jpg', 'build/nasrin_raw.json',
    'build/nasrin_urls.txt', 'build/oconnells.json', 'build/rl_desc.json', 'build/retailers_seed.json', 'build/occ', 'build/merino',
    'build/shoes', 'build/add_extras.py', 'build/add_merino.py', 'build/add_shoes.py', 'build/rl_parse.py', 'build/merge_desc.py',
] + glob.glob('build/suggest/round_*.json') + glob.glob('build/*_tmp') + ['build/rl_pages', 'build/contact.jpg']   # the last three are local scratch, ignored by git

WRITE = {
    'data.js': 'window.CLOSET = [];\n',
    'suggestions.js': 'window.SUGGESTIONS = [];\n',
    'sales.js': 'window.SALES = {"checked": "", "items": {}, "events": {}};\n',
    'retailers.js': '// Return terms per store. Source: build/returns/retailers.json\nwindow.RETAILERS = {"checked": "", "stores": {}};\n',
    'build/items_raw.json': '[]\n',
    'build/extras.json': '[]\n',
    'build/sales/history.json': '{}\n',
    'build/returns/retailers.json': json.dumps({'checked': TODAY, 'stores': {}}, indent=1) + '\n',
    'build/returns/hashes.json': '{}\n',
    'build/returns/changes.json': '{}\n',
    'build/pieces_to_add.csv': 'url,brand,retailer,name,category,categoryDetail,color,colorDetail,occasions,why,fabric,details,price,img,id\n',
    'build/suggest/profile.md': (
        '# Her taste profile\n\n'
        '<!-- round.py rewrites a block between "auto:start" and "auto:end" markers from the notebook each week, right\n'
        '     below this heading. Everything else in this file is yours: the weekly judge reads all of it. -->\n\n'
        '## Read of the signals\n- What she saves and passes so far: brands, fabrics, shapes, colours, price.\n\n'
        '## Told in person\n- Things she has said she wants.\n\n'
        '## Guidance for rounds\n- Rules from the owner: $50–$400 list, at least 70% natural fibre, reputable brands only.\n'
        '- Anything she cannot or will not wear, stated plainly.\n'),
}


def strip_brand_rules():
    """Keep the brand roster as a starting point; drop the rules written for the original recipient."""
    p = 'build/suggest/brands.json'; cfg = json.load(open(p))
    cfg.get('rules', {}).pop('avoid_titles', None)
    for b in cfg['brands']:
        b.pop('only_titles', None)
        if b.get('note') == 'in the closet': b.pop('note')
    json.dump(cfg, open(p, 'w'), indent=1, ensure_ascii=False); open(p, 'a').write('\n')


def main():
    yes = '--yes' in sys.argv
    slug = load().get('slug')
    if slug == 'beccas-closet':
        sys.exit('config.js still has the original slug "beccas-closet". Personalise config.js first (slug, names, texts, email), then run this again.')
    print(('Removing' if yes else 'Would remove') + ':')
    for p in REMOVE:
        if not os.path.exists(p): continue
        print('  ', p + ('/' if os.path.isdir(p) else ''))
        if yes: shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    print(('Writing' if yes else 'Would write') + ' empty starting files:')
    for p, body in WRITE.items():
        print('  ', p)
        if yes: os.makedirs(os.path.dirname(p) or '.', exist_ok=True); open(p, 'w').write(body)
    print(('Stripping' if yes else 'Would strip') + ' the original recipient\'s rules from build/suggest/brands.json (the roster stays).')
    if yes: strip_brand_rules(); os.makedirs('images/full', exist_ok=True)
    if not yes: print('\nDry run. Add --yes to do it.')
    else: print('\nDone. Next: fill build/pieces_to_add.csv and run  python3 build/add_pieces.py')


if __name__ == '__main__':
    main()
