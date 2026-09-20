# Running a round of ideas

A round proposes a handful of pieces from beyond the closet. It runs in a Claude Code session, on
request or on a schedule, and costs one session, never anything per visitor.

1. **Read her signals.** Pull the notebook sheet (`latest` tab, or `GET <syncUrl>?key=<notebookKey>`, both from `config.js`) and
   update `profile.md` with what she saves and passes: brands, silhouettes, colours, fabrics, price band.
   While the notebook is empty the closet itself (`data.js`) stands in for her taste.
2. **Sweep.** `python3 build/suggest/sweep.py approved,proposed` reads every brand in `brands.json` with a
   Shopify feed and writes `candidates.json` under the rules in that file (price, natural fibre share).
   `python3 build/suggest/shortlist.py` scores and balances them into `shortlist.json` (~90 pieces).
3. **Judge.** Read the shortlist against the profile and pick `ideas_per_round` pieces: two thirds from
   approved brands, the rest from proposed ones (max `new_brands_per_round` new labels). For each pick
   fetch `<url>.js`, download the first photo to `images/ideas/<id>.jpg` (ids 5001+, never reused), and
   write a `round_N.json` entry with desc, details, fabric, occasions + why, and a `reason` that names
   something already in the closet.
4. **Brand cards.** For each new label used, give the owner a short card (what they make, price range,
   fibres, where based, sizes) and set its status in `brands.json` to `approved` or `rejected` on their answer.
5. **Publish.** `python3 build/suggest/make_suggestions.py`, verify locally, commit, push.
6. **Fold.** Ideas she has hearted (kind `s` on a 5000+ id in the notebook) can be moved into
   `build/extras.json` permanently; ideas she passed stay out and count against the brand next round.
   Remove folded or stale ideas from `round_N.json` and rebuild.

Discovery of brand candidates: multi-brand boutiques with Shopify feeds, "brands like X" searches from
her profile, and labels carried by stores she already hearts. Vet before proposing: real product pages,
women's clothing, fibre content published, prices overlapping the range, a physical home and returns policy.

## If the shortlist is missing when the judge runs

The judgment routine (Anthropic scheduler, Saturday 13:00 UTC) does not trust GitHub's cron: if `pending/round_meta.json` is older than a day it commits `pending/stage1.request` to main with the message "Request shortlist", which triggers the `stage1` job here (GitHub's machines have internet; the routine's sandbox does not), then pulls every minute until a fresh `round_meta.json` appears and picks from it. Crons are set off the hour (04:17 and 17:23 UTC) because GitHub fires top-of-hour schedules hours late.
