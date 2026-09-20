# Kickoff for a Claude Code session that sets up a new closet

How to use this file: open a new Claude Code session in the folder that contains `Beccas Closet`
(on this machine, `/Users/piano/Documents/Claude Code`), and paste everything below the line as the
first message. The new session does the whole setup, from creating the repository to publishing, and
asks you only for the decisions that are yours: who the closet is for, its name, the look, the pieces.

---

You are setting up a new closet: a copy of Becca's Closet, a static gift site, made for a different
person. Everything below is yours to do. The source is on this machine at
`/Users/piano/Documents/Claude Code/Beccas Closet` (GitHub `pianoelias-boop/beccas-closet`, live at
https://pianoelias-boop.github.io/beccas-closet/). Treat that folder and that repository as read-only:
read anything you like there, never edit, commit or push in it, and never load its live site or its
notebook. The `gh` CLI is signed in as `pianoelias-boop`; use it for everything on GitHub.

## First, read

1. In the source folder: `MAKE-YOUR-OWN.md` (the recipe; you are the one following it), `README.md`,
   `build/suggest/README.md`, `build/suggest/routine_prompt.md`, and the top of `config.js` and `theme.css`.
2. Your memory notes on Becca's Closet and on subagent judgment. They carry the operational lessons:
   Shopify answers a burst of requests from this Mac with HTTP 429 for about half an hour, so add pieces
   in modest batches and run bulk checks on GitHub Actions rather than locally; GitHub fires scheduled
   workflows hours late; the cloud routine's sandbox has no internet except GitHub; a local copy must
   never be pointed at a real notebook; the owner reviews round pull requests and nothing else, so never
   open issues or assign him anything; keep subagents few, well aimed and on cheaper models, never the
   default model, and keep judgment in your own session.

## Then ask, once

Ask all of this in a single round before touching anything, and proceed with the answers (use sensible
defaults where he says "you choose"):

- Who the closet is for and how to name it (site title, the short slug for the repository and the
  address, e.g. `bens-closet`). Whether the repository should be public (needed for free GitHub Pages).
- The email address the saved list should go to, and whether to quietly copy anyone.
- The occasions he wants as filters (four to six short labels), or whether to keep Becca's.
- The look: a palette (or a mood, and you propose one), the two typefaces or "keep them", and the
  emoji for the browser tab.
- Whether he wants an "About her" dialog with photos and a paragraph; if so, where the photos are.
- How he wants to source pieces: URLs he pastes, or store and brand names for you to browse and propose
  in batches for his approval. Which stores and brands, and the price band.
- Whether the closet is menswear (see the section on that below).
- Which automations to switch on now: the daily sale check, return terms, the weekly round of ideas
  with or without the Claude judge, and the notebook.

## Create the repository

1. Copy the source folder's working tree, not its git history, to a sibling folder named after the slug:

   ```bash
   rsync -a --exclude .git --exclude 'build/rl_pages' --exclude 'build/*_tmp' --exclude 'build/contact.jpg' --exclude .DS_Store --exclude __pycache__ "/Users/piano/Documents/Claude Code/Beccas Closet/" "/Users/piano/Documents/Claude Code/<slug>/"
   ```

   A fresh history matters: a plain clone would carry Becca's photos, her email and her notebook URL in
   every old commit of the new repository.
2. In the new folder: `git init -b main`, set the same local git identity the source repository uses
   (`git -C "…/Beccas Closet" config user.name` and `user.email`), commit everything as
   "Start <site title> from Becca's Closet", then create and push the repository in one step:

   ```bash
   gh repo create <slug> --public --source . --remote origin --push
   ```

3. If the app lets you, switch this session's working directory to the new folder; otherwise keep
   using absolute paths.

## Make it his

4. Edit `config.js` from his answers: `slug`, `notebookKey`, `siteTitle`, `description`, `icon`, every
   `text.*` field written for him in the same warm, plain voice, `about`, `person` (or `null`), `email`,
   `occasions` (write `auto` rules for the weekly round from the occasion's meaning; leave `auto` out
   where none makes sense), and `resale`. Check it with `python3 build/closet_config.py`.
5. Edit `theme.css`: the palette by role, including the `-rgb` twins and the three glows, the fonts
   `@import` and stacks, the radius.
6. Now that the slug has changed, empty the copy: `python3 build/reset_closet.py` (dry run), then
   `python3 build/reset_closet.py --yes`. Rewrite the title and first lines of `README.md` for the new
   closet. Commit.

## If the closet is menswear

The page generalises, but the weekly-ideas pipeline and the vocabulary assume womenswear. Before adding
pieces, propose and then make these changes:

- `app.js`: `CATEGORY_ORDER` (for example Shirts, Tees & Polos, Knitwear, Trousers, Jeans, Shorts,
  Jackets & Coats, Suits & Blazers, Shoes, Accessories) and `PRICE_BANDS` if his band differs; mirror the
  category list in `CATEGORIES` in `build/add_pieces.py`.
- `build/suggest/sweep.py`: the `EXCL` pattern drops any title containing "men's" and the `CAT_RULES`
  map titles to the womenswear categories; invert the first, rewrite the second for the new categories.
- `build/suggest/round.py`: the category loop in `stage1` and `need` / `want_one_of` in `fallback`
  (which insists on a dress); replace with the new categories.
- `config.js`: `resale` to eBay category `1059` (men's clothing) and Poshmark department `Men`.
- `build/suggest/brands.json`: prune the roster to brands that make what he wears and add his; the
  status `approved` is what the sale check and the sweep read.

## Add the pieces

7. Put each piece in `build/pieces_to_add.csv` (columns and vocabulary are documented at the top of
   `build/add_pieces.py` and in the guide), then `python3 build/add_pieces.py`. Batches of about twenty,
   and if Shopify answers 429 let the script wait rather than retrying by hand. When you are proposing
   pieces rather than adding a list he gave you, show him each batch with photos (an HTML page is
   fine) and add only what he approves. Commit after each batch.
8. Return terms: for the stores that end up in the closet, write `build/returns/retailers.json` (window,
   who pays return shipping, exceptions, policy URL, `checked` today) from each store's own policy page,
   run `python3 build/returns/make.py`, commit `retailers.js`.

## Look, then publish

9. Preview locally (`python3 -m http.server 8768`, or the `closet` entry in `.claude/launch.json`) and
   check the hero, the dialogs, an item modal, the filters, the saved list and the emailed list. Show
   him screenshots. The notebook is off on localhost by design.
10. Switch on GitHub Pages and give the workflows the permissions they need:

    ```bash
    gh api -X POST repos/pianoelias-boop/<slug>/pages -f "source[branch]=main" -f "source[path]=/"
    ```

    ```bash
    gh api -X PUT repos/pianoelias-boop/<slug>/actions/permissions/workflow -f default_workflow_permissions=write -F can_approve_pull_request_reviews=true
    ```

    Confirm with `curl` that `https://pianoelias-boop.github.io/<slug>/` serves `config.js`. Do not open
    the live site in a browser once a notebook URL is set.

## Optional pieces, only if he asked for them

11. Notebook: the Google steps in `sync/SETUP.md` are his to do (a new Sheet, paste `sync/Code.gs`,
    deploy as a web app); ask him for the `/exec` URL, put it in `config.js` as `syncUrl`, and pick a
    `notebookKey` that is not `becca`. A separate sheet, not Becca's.
12. Daily sale check and return-terms watcher: they run from `.github/workflows/sales.yml` as soon as the
    repository exists and the roster is right. Run it once by hand from the Actions tab with `dry_run`
    set to `true` and read the summary.
13. Weekly round: write `build/suggest/profile.md` (his taste, in the shape the file already has), set
    `rules` in `brands.json` (price band, natural-fibre share, ideas per round, any hard rule about what he
    cannot wear), and check `.github/workflows/round.yml` needs nothing else. For the Claude judge, read
    Becca's routine with the RemoteTrigger tool (`trig_01Hn6GFRvidhjxpDNxCsqDdW`) and create a new one
    for the new repository with the same environment, model (`claude-sonnet-5`), tools and connectors,
    the same schedule, and the prompt from `build/suggest/routine_prompt.md` rewritten for this closet
    (site name, repository, pick count, his hard rules, his occasions, examples of his own). Save the
    rewritten prompt back into that file so the repository and the routine stay in step. Ask him before
    creating the routine; it is billed.

## Ways of working

- Commit as you go with clear messages; push when a step is complete. Tell him before anything that
  publishes for the first time or sends anything.
- Verify what you claim: rebuild and diff, preview and screenshot, `curl` the live site.
- Finish with a short report: the live address, what is switched on and off, and what is left for him
  (the Google steps for the notebook, approving the first round).
