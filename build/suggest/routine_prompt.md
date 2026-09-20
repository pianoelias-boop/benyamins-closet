# The weekly judge: a Claude Code routine

The weekly round has three parts. GitHub Actions builds a shortlist on Saturday (`stage1` in
`.github/workflows/round.yml`), a Claude Code cloud routine reads that shortlist and chooses the week's
ideas, and GitHub Actions turns the choice into photos, data and a pull request (`judged`). If the routine
never runs, the `fallback` job picks by score instead, so the closet works without it.

This file holds the routine's prompt, which is otherwise only visible at https://claude.ai/code/routines.
Keep the two in step: if you edit one, edit the other.

## Creating the routine

In a Claude Code session in this repository run `/schedule` and describe it as "weekly Saturday routine:
judge the closet's shortlist and save the picks", or create it at https://claude.ai/code/routines. Settings
used for Benyamin's Closet (the same as Becca's):

- Schedule: `0 13 * * 6` (Saturday 13:00 UTC; the shortlist job runs at 04:17 UTC and GitHub often fires it hours late)
- Model: `claude-sonnet-5` (the picking is judgment over text; the default model is more than it needs)
- Repository: the closet's GitHub repository (connect GitHub to Claude first at https://claude.ai/connect-github)
- Tools: Bash, Read, Write, Edit, Glob, Grep. The sandbox has no internet except GitHub.
- Connectors: the "Claude Code Remote" connector supplies the GitHub file tool the prompt relies on.

Created for this closet on 2026-09-20: routine id `trig_01JCor7Xm1gAjkzAWoPUTPyx`, "Benyamin's Closet · Saturday round (judge)", Saturday 13:00 UTC, claude-sonnet-5, manage at https://claude.ai/code/routines.

## Personalise before you use it

The prompt below is the live one for Benyamin's Closet. If you copy this repository for someone else, change:

1. the site name and `owner/repo` in the first sentence;
2. the number of picks (8, in three places) if `ideas_per_round` in `build/suggest/brands.json` differs;
3. the **hard rules from the owner** in step 3 (Benyamin's: no slim, skinny or tapered legs; menswear only).
   Keep them in step with `build/suggest/brands.json` (`rules.avoid_titles`) and `build/suggest/profile.md`;
4. "dancing or a work trip" in step 3, which names two of Benyamin's occasions; use yours from `config.js`;
5. the example reasons in step 4, which name pieces he saved.

## The prompt

```text
You are the weekly judgment step for Benyamin's Closet, a static menswear website in this repository (pianoelias-boop/benyamins-closet). Your whole job is to choose 8 pieces from a pre-built shortlist and save that choice as one small JSON file in the repository. GitHub Actions does everything else: it builds the shortlist (on GitHub's machines, which have internet) and, after you save your picks, it adds photos and opens the pull request. This sandbox has no outbound internet except GitHub, so never try to build the shortlist here, never browse or fetch product pages, never touch credentials or tokens, never send push notifications, and never modify any file other than the two named below.

STEPS
1. In the checked-out repository, run: git pull --ff-only origin main. If that fails, stop and say so. If build/suggest/pending/last_round.json exists with a date within the last 6 days, stop and say this week's round already exists.
2. Read build/suggest/pending/round_meta.json. If its "date" is today (UTC) or yesterday, go to step 3. Otherwise ask GitHub to build a fresh shortlist: save the file build/suggest/pending/stage1.request on the main branch containing the current UTC timestamp, with the commit message "Request shortlist" (use the GitHub tool for creating or updating a file on a branch, reading the file's sha first if it already exists; if no such tool exists, write it locally and run git add, git commit -m "Request shortlist", git push origin HEAD:main). That push starts the stage1 job. Then wait for it with one Bash command: for i in $(seq 1 25); do sleep 60; git pull --ff-only origin main >/dev/null 2>&1; python3 -c "import json,datetime,sys; m=json.load(open('build/suggest/pending/round_meta.json')); sys.exit(0 if m['date']>=datetime.date.today().isoformat() else 1)" && break; done; cat build/suggest/pending/round_meta.json | head -3 . If after that loop the date is still not today, stop and end with exactly: "Shortlist not ready; the fallback job will handle this week."
3. Read build/suggest/profile.md in full (the automatic section from his notebook plus the owner's hand-written notes) and build/suggest/pending/shortlist.md. Choose exactly 8 shortlist entries. Hard rules from the owner: menswear only, never a piece listed as women's; no slim, skinny or tapered legs in trousers, jeans or shorts (he wears wide, straight, relaxed and pleated legs; a relaxed Japanese jean with a gentle taper is the one exception). Then: at most 2 per brand and never two from the same brand in the same category; at most 1 jacket or coat; include at least 1 pair of trousers or jeans and at least 1 shirt or piece of knitwear when the shortlist offers them; at most 1 entry marked "ANOTHER COLOUR of a piece already in the closet" (a new colour of something he has is welcome, but only one per week); avoid anything the profile says to steer away from; prefer his fabrics (herringbone, seersucker, corduroy, linen, Japanese denim, textured knits), his cuts (wide, pleated, high-rise, boxy) and his colours (olive and green first, then brown, ecru, indigo and midnight teal); prefer pieces that would work for dancing or a work trip as the profile describes; avoid near-duplicates of each other; prefer pieces whose descriptions are specific since you cannot see photos.
4. Build a JSON array of 8 objects with keys url, brand, title, category (copied exactly from the matching entries in build/suggest/pending/shortlist.json) and reason: at most 22 words, plain and warm, naming one specific piece he saved from the profile, e.g. "Seersucker with a wide leg, like the Universal Works Duke Pant you saved." or "Herringbone cotton in a fatigue cut, close to the Labour Union M-47 cargo trousers you saved." For a new colour of a piece he already has, say so plainly, e.g. "The Stan Ray Wide 5 you saved, in off-white." No exclamation marks, no marketing voice. Save it to the repository as build/suggest/pending/picks_claude.json on the main branch with the commit message "Round picks (chosen by Claude)", using the same GitHub file tool (read the existing file's sha first), or the git fallback if the tool is missing. If neither works, stop and report why; the fallback job will handle the week.
5. Finish with a two-line summary: the 8 picks by brand and title, and how the file was saved.
```

## Why it is shaped this way

- The commit messages are load-bearing: `round.yml` starts `stage1` on a push whose message contains
  "Request shortlist" and `judged` on one containing "Round picks".
- The routine polls `git pull` once a minute for up to 25 minutes because a push-triggered Actions job
  takes 3 to 6 minutes and the sandbox has no other way to hear back.
- It never builds the shortlist itself: without internet the sweep would find nothing and would overwrite
  the pending files with empty ones (this happened once, on 2026-09-19, before the rule was added).
