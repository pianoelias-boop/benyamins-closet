// The one file to personalise. Names, the recipient's email, every sentence written for him, the photos,
// the occasion tags and the notebook settings all live here; colours and fonts live in theme.css.
// Everything after "window.CLOSET_CONFIG =" must stay strict JSON (double quotes, no trailing commas,
// no comments, nothing after the closing "};") because the build scripts read this file too.
// Field guide: MAKE-YOUR-OWN.md. In text fields, {n} becomes the number of pieces and {date} the date
// the return terms were last checked; a little HTML such as <em> or <br> is fine.
window.CLOSET_CONFIG = {
 "slug": "benyamins-closet",
 "notebookKey": "benyamin",
 "syncUrl": "https://script.google.com/macros/s/AKfycbwQjmEeX99EVBaFZqXHTSdfFV8meXq5uFyeYC4CAMJlb5GQIBOzharnK4THG5WcE8YX/exec",
 "siteTitle": "Benyamin's Closet",
 "description": "The pieces Benyamin has his eye on, in one place.",
 "icon": "🌿",
 "text": {
  "eyebrow": "Welcome to",
  "wordmark": "Benyamin’s <em>Closet</em>",
  "tagline": "{n} pieces worth keeping an eye on",
  "heroNote": "Tap a heart to tuck something away. Your saved list lives right here in this browser, and you can email it to yourself whenever you like. The ✕ on a card tucks a piece out of sight.",
  "aboutLink": "About this closet",
  "aboutTitle": "What this closet is",
  "personLink": "",
  "personTitle": "",
  "personText": "",
  "storesTitle": "Where the closet shops",
  "storesIntro": "Every store listed here has at least one piece in the closet. Return terms are as each store states them for US orders, checked on {date}. The policy link is the source of truth.",
  "footer": "Everything here is something you already liked once.<br>Wear it well, Benyamin."
 },
 "about": {
  "considered": "1,000+",
  "storefronts": 39,
  "paragraphs": [
   "Every piece here is one Benyamin saved himself while browsing: wide legs and double pleats, seersucker and herringbone, Japanese denim, knits with a pattern, and shoes that might actually be comfortable. The closet keeps them in one place, with the photo, the price and the note on why each one earned its spot.",
   "Plenty of these are waiting on a sale or a restock, so the closet checks the stores every morning and marks what is reduced right now. Tap through to the store to buy, or to eBay and Poshmark to find it secondhand."
  ],
  "fine": [
   "Wondering about returns? Tap the storefront count above for every store’s return terms.",
   "Hearts and “not for me” marks are kept in a little notebook so your list follows you between your phone and laptop."
  ]
 },
 "person": null,
 "email": {
  "to": "benyamin.elias@gmail.com",
  "bcc": "",
  "subject": "My picks from Benyamin’s Closet",
  "intro": "My saved pieces from Benyamin's Closet:"
 },
 "occasions": [
  {"key": "work", "label": "For work trips",
   "auto": {"categories": ["Shirts", "Knitwear", "Trousers", "Jackets & Coats", "Suits & Blazers", "Shoes"], "not": "swim|board short|sweatpant|hoodie|jogger|trail|running|distressed|graphic|logo"}},
  {"key": "dance", "label": "For dancing with friends",
   "auto": {"all": ["cotton|linen|merino|wool|tencel|lyocell|hemp|rayon|silk|seersucker|khadi", "linen|seersucker|poplin|broadcloth|lightweight|light[- ]weight|wide[- ]leg|pleat|relaxed|open weave|open-weave|airy|breathable|stretch|knit|jersey|drape|featherweight"], "not": "jacket|coat|blazer|parka|waxed|\\bdown\\b|boot|heavyweight|heavy[- ]weight|1[4-9] ?oz|2[0-9] ?oz"}},
  {"key": "hang", "label": "Hanging out",
   "auto": {"categories": ["Tees & Polos", "Jeans", "Shorts & Swim", "Knitwear", "Trousers", "Shoes"], "not": "blazer|suit|tailored|dress shirt"}},
  {"key": "dressy", "label": "Dressy",
   "auto": {"any": "blazer|\\bsuit\\b|loafer|wool|cashmere|mohair|silk|tailored|dress (pant|trouser|shirt)|oxford|tweed|donegal|flannel trouser|sport ?coat"}},
  {"key": "exercise", "label": "For exercise",
   "auto": {"any": "merino|sweatpant|sweatshirt|track|running|trail|hik(e|ing)|athletic|performance|quick[- ]dry|technical|\\bgym\\b|swim|stadium|sneaker|trainer|runner"}}
 ],
 "resale": {"ebayCategory": "1059", "poshmarkDepartment": "Men"}
};
