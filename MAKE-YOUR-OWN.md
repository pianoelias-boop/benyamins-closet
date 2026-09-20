# Make your own closet

This repository is a finished gift site: a curated catalog of clothes with hearts, filters, a saved list
she can email herself, an optional notebook that carries her hearts between phone and laptop, a daily
check for sales at the stores, each store's return terms, and a weekly round of new ideas that you
approve by merging a pull request. None of it needs a server; GitHub Pages hosts it for free.

To make one for someone else you do not rewrite any of that. You change three things:

| What | Where | How long |
|---|---|---|
| Names, every sentence written for her, her email, her photos, the occasion tags | `config.js` | 20 minutes |
| Colours and fonts | `theme.css` | 10 minutes |
| The pieces themselves | `build/pieces_to_add.csv`, then one command | as long as the curating takes |

Everything else (the page, the scripts, the schedules) reads from those.

If Claude Code is doing the setup for you, paste `NEW-CLOSET-KICKOFF.md` into a new session and it will
follow this guide end to end, from creating the repository to publishing.

You need: a GitHub account, Python 3.9 or newer with Pillow (`python3 -m pip install pillow`), and git.
The notebook needs a Google account. The weekly judge needs Claude Code; without it the round still
runs, picked by score instead.

## 1. Get the code

1. On the repository's GitHub page choose **Use this template** if it is offered, otherwise **Fork**, or
   download the zip. Create the copy under your own account with the name you want in the address, for
   example `sams-closet` (the site will live at `https://<you>.github.io/sams-closet/`).
2. Clone it to your computer and open a terminal in that folder. Every command below runs from there.

## 2. Make it hers: `config.js`

Open `config.js`. The part after `window.CLOSET_CONFIG =` is strict JSON: double quotes, no trailing
commas, no comments, nothing after the closing `};`. Check it any time with:

```bash
python3 build/closet_config.py
```

| Field | What it does |
|---|---|
| `slug` | A short id such as `sams-closet`. It names the browser storage that holds her saved list, so choose it once and keep it. |
| `notebookKey` | The name of her list inside the notebook spreadsheet, e.g. `sam`. One notebook can hold several closets. |
| `syncUrl` | The notebook's web-app URL from step 7, or `""` to run without the notebook. |
| `siteTitle`, `description`, `icon` | Browser tab title, search-engine description, and the emoji used as the tab icon. |
| `text.eyebrow`, `text.wordmark`, `text.tagline` | The three lines at the top. `<em>` in the wordmark gives the italic accent word; `{n}` in the tagline becomes the number of pieces. |
| `text.heroNote`, `text.footer` | The note under the heading and the sign-off at the bottom. `<br>` is fine. |
| `text.aboutLink`, `text.aboutTitle`, `about.*` | The "About this closet" dialog: its link and title, the two headline numbers (`considered`, `storefronts`), the paragraphs, and the small print. The other two numbers (labels, pieces) are counted from the catalog. |
| `text.personLink`, `text.personTitle`, `text.personText`, `person.photos` | The "About her" dialog: a collage (six photos look best, two rows of three) and a paragraph. Put the photos anywhere under `images/` and list them with `src` and `alt`. Set `"person": null` to drop this dialog entirely. |
| `text.storesTitle`, `text.storesIntro` | The dialog listing the stores and their return terms; `{date}` becomes the date the terms were last checked. |
| `email.to`, `email.bcc`, `email.subject`, `email.intro` | Where "Email me my list" goes, an optional quiet copy to you, and the wording. |
| `occasions` | The occasion filter, in display order. Each has a `key` (stored on every piece, never shown), a `label`, and optional `auto` rules the weekly round uses to tag new ideas (see below). Becca's are teaching, dancing, friends, hanging out, dressy, outdoors; yours can be anything. |
| `resale` | The eBay category and Poshmark department the "find it secondhand" links search. The defaults are women's clothing. |

**Occasion auto rules.** A new idea from the weekly round is tagged by matching its description:
`categories` (the piece must be in one of these), `any` (a regular expression that must match), `all` (a
list that must all match), `not` (must not match). One occasion may carry `"role": "default"`: it is
added when its `categories` match or when nothing else matched. The one with `"role": "otherwise"` is
added instead when the default did not apply. Pieces you add yourself carry whatever you write in the CSV;
these rules only matter for the automated round. Leave `auto` out to keep an occasion manual.

## 3. Make it hers: `theme.css`

Every colour, both fonts and the corner radius live in `theme.css`, named by role rather than by colour
(`--bg`, `--ink`, `--accent`, `--trim`, `--note-bg`, and so on; each line says where it is used). Change
the values and the whole site follows. The `-rgb` twins hold the same colours as bare channels for
translucent bars and shadows, so update those with their partners. To change the typefaces, replace the
Google Fonts `@import` line and the two font stacks.

## 4. Empty the closet

The copy still holds Becca's 432 pieces, photos, rounds and sale history. Once `config.js` has a new
`slug`, clear them:

```bash
python3 build/reset_closet.py
```

That is a dry run; it lists what would be removed and emptied. Then:

```bash
python3 build/reset_closet.py --yes
```

It removes the photos, the catalog, the weekly-idea rounds, the sale history, the return terms and the
one-off scripts that built the original catalog, and writes empty starting files. It keeps the site, the
generic build scripts, the workflows and the brand roster in `build/suggest/brands.json` (with Becca's
personal rules stripped out). Commit the result.

## 5. Add the pieces

Fill `build/pieces_to_add.csv`, one row per piece, then run:

```bash
python3 build/add_pieces.py
```

For a Shopify store (most independent brands; the product address contains `/products/`) you only need
`url`, `brand`, `category`, `color` and `occasions`: the price, the description, the fabric line and the
first photo come from the store. For any other store also give `price` and `img` (a photo URL or a file
on your disk) and whatever else you know. Rows already in the closet are skipped, so the file can stay
as your record. The script rebuilds `data.js` when it finishes. `--dry-run` checks the file without
fetching anything.

- `category` is one of: Dresses, Skirts, Pants, Jeans, Shirts & Blouses, Tops & Tees, Sweaters & Knitwear,
  Jumpsuits & Rompers, Jackets & Coats, Shoes, Accessories.
- `color` is one of: Black, Grey, White/Ivory, Beige/Tan, Brown, Denim, Blue, Green, Red, Pink, Purple,
  Orange/Rust, Yellow/Gold, Multi/Print. `colorDetail` is the store's own name for it.
- `occasions` are your keys from `config.js`, separated by semicolons. `why` is the one line shown under
  "Why these occasions".
- `brand` is the label; `retailer` the store, if different (a department store, a boutique).
- Shopify answers a burst of requests with "429 Too Many Requests"; the script waits a minute and retries,
  so a long list simply takes a while.

To change a piece later, edit its entry in `build/extras.json` and run `python3 build/make_data.py`. To
remove one, delete the entry and its photo in `images/full/`.

If you already have a big spreadsheet, `build/extract.py` shows how the original 395 pieces were read
from one (columns: retailer, brand, name, category, color, occasions, price, colour detail, category
detail, url, with the photo embedded in the row) into `build/items_raw.json`, and `fetch_hires.py` and
`download.py` how their photos were fetched. Adapt them; the CSV route is the supported one.

## 6. Look at it

```bash
python3 -m http.server 8768
```

Open http://localhost:8768. On localhost the notebook is switched off on purpose, so hearts stay in the
browser and never reach a real spreadsheet while you test.

## 7. Put it online

1. In the repository on GitHub open **Settings → Pages**. Under *Build and deployment* choose **Deploy
   from a branch**, branch `main`, folder `/ (root)`, and save. The site appears at the address shown
   there within a couple of minutes, and every push to `main` republishes it.
2. So the schedules can commit and open pull requests: **Settings → Actions → General → Workflow
   permissions**, choose **Read and write permissions** and tick **Allow GitHub Actions to create and
   approve pull requests**.
3. Send her the link.

## 8. Optional: the notebook (hearts that follow her between devices)

Follow `sync/SETUP.md` (five minutes, a Google Sheet plus a small Apps Script that the folder provides).
Paste the resulting web-app URL into `config.js` as `syncUrl`, commit and push. Without it the site still
works; her list lives in her browser and in the share link.

## 9. Optional: the automation

All three run on GitHub's own machines through `.github/workflows/`; nothing runs on your computer.

**Daily sale check** (`sales.yml`, `build/sales/check.py`). Reads the stores in `build/suggest/brands.json`
whose `status` is `approved`, marks closet pieces that are actually reduced (Shopify stores only) and
stores running a sale event (any store with a homepage), and writes `sales.js`. Edit the roster to match
where your pieces come from: each entry needs `name`, `site` and `status`. Run it by hand from the Actions
tab with `dry_run` set to `true` to see what it would report without publishing.

**Return terms** (`build/returns/`). Write each store's terms into `build/returns/retailers.json` (window,
who pays return shipping, exceptions, policy URL), set `checked` to today, run
`python3 build/returns/make.py` and commit `retailers.js`. The daily workflow then watches each policy
page and records changes in `build/returns/changes.json` for you to look at now and then.

**Weekly round of ideas** (`round.yml`, `build/suggest/`). Saturday morning it reads her notebook,
sweeps the approved and proposed brands, and writes a shortlist. A Claude Code cloud routine then chooses
the week's picks from that shortlist; `build/suggest/routine_prompt.md` holds its prompt and how to create
it. If the routine is not set up, the afternoon fallback picks by score. Either way the result is a pull
request assigned to the repository owner: merge it and the ideas appear in her "Based on your likes" tab;
close it to skip the week. Before the first round, write `build/suggest/profile.md` (what she likes; the
judge reads all of it) and set the rules in `brands.json`: price band, natural-fibre share, ideas per
round, and any hard rule about things she cannot wear (`rules.avoid_titles`; a per-brand `only_titles`
limits a brand to certain pieces). `build/suggest/README.md` explains the pipeline in detail.

## 10. A last look for anything left over

```bash
grep -rn -i "becca" --exclude-dir=.git --exclude-dir=images .
```

After the reset, that should find only prose: this guide, the routine prompt (which shows Becca's rules
as the example to replace), the reset script's safety check, and `README.md`, whose title and first lines
are yours to rewrite. Nothing that runs still carries her name. Also check that the round label colour in `round.yml` (`D4879A`) suits your
palette; it is only the colour of the pull-request label.

## What is deliberately not in config.js

- The **categories, colour families and price bands** are the closet's vocabulary and sit at the top of
  `app.js` (`CATEGORY_ORDER`, `COLOR_ORDER`, `COLOR_SWATCH`, `PRICE_BANDS`). `build/add_pieces.py` mirrors the
  first two lists; keep them in step if you change them.
- The **interface strings** (Search the closet, Filters, Saved, Not for me, Surprise me) are English and
  live in `index.html` and `app.js`.
- The **sale-season nudges** in the banner (`saleSeason` in `app.js`) follow the US retail calendar.
- **Return terms** are described as each store states them for US orders.

## Map of the repository

| Path | Role |
|---|---|
| `index.html`, `app.js`, `styles.css` | the site |
| `config.js`, `theme.css` | the two files that make it personal |
| `data.js` | the catalog, generated by `build/make_data.py` |
| `suggestions.js`, `sales.js`, `retailers.js` | the weekly ideas, the daily sale flags, the return terms; each generated |
| `images/full/` | one photo per piece; `images/ideas/` photos of the weekly ideas |
| `build/pieces_to_add.csv`, `build/add_pieces.py` | how pieces get in |
| `build/extras.json`, `build/items_raw.json` | the catalog's sources (pieces added by CSV; the original spreadsheet, if any) |
| `build/reset_closet.py` | empties a fresh copy |
| `build/closet_config.py` | lets the Python scripts read `config.js` |
| `build/suggest/` | the weekly round: `brands.json` (roster and rules), `profile.md` (her taste), `round.py`, `sweep.py`, `routine_prompt.md` |
| `build/sales/check.py` | the daily sale check |
| `build/returns/` | return terms and their watcher |
| `sync/` | the notebook: `Code.gs` for Google Apps Script and `SETUP.md` |
| `.github/workflows/` | the schedules |
