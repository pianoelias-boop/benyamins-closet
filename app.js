/* A tiny static shop with no backend. Everything personal (names, texts, email, occasions, notebook)
   comes from config.js; colours and fonts from theme.css; the pieces from data.js.
   Saved list: localStorage + the URL hash (#saved=…), so a link IS the list. */
(() => {
  'use strict';

  // ---------- config (see config.js) ----------
  const CFG = window.CLOSET_CONFIG || {};
  const SLUG = CFG.slug || 'closet';                        // prefixes this browser's storage keys; changing it forgets saved lists
  const MAIL = CFG.email || {};
  const HER_EMAIL = MAIL.to || '';                           // where "Email me my list" goes
  const BCC_EMAIL = MAIL.bcc || '';                          // optional: an address to quietly copy on every emailed list
  const STORAGE_KEY = `${SLUG}-saved-v1`;
  const PASSED_KEY = `${SLUG}-passed-v1`;
  const META_KEY = `${SLUG}-meta-v1`;                        // per-item timestamps, for cross-device merging
  const QUEUE_KEY = `${SLUG}-queue-v1`;                      // events not yet delivered to the notebook
  const CLIENT_KEY = `${SLUG}-client`;
  const SEEN_KEY = `${SLUG}-ideas-seen`;
  const CLOSET_KEY = CFG.notebookKey || 'closet';            // one shared list per closet in the notebook
  let SYNC_URL = CFG.syncUrl || (document.querySelector('meta[name="closet-sync"]') || {}).content || '';
  // Never let a local copy of the site write into the real notebook: on localhost only a local endpoint counts.
  if (/^(localhost|127\.0\.0\.1)$/.test(location.hostname) && !/localhost|127\.0\.0\.1/.test(SYNC_URL)) SYNC_URL = '';

  const OCCASIONS = CFG.occasions || [];
  const OCC_LABEL = Object.fromEntries(OCCASIONS.map(o => [o.key, o.label]));
  const OCC_ORDER = OCCASIONS.map(o => o.key);
  const RESALE = CFG.resale || {};
  const COLOR_SWATCH = {
    'Black': '#2b2226', 'Grey': '#9a9598', 'White/Ivory': '#f6f1e6', 'Beige/Tan': '#d9c3a3', 'Brown': '#7a5238',
    'Denim': '#4f6a8f', 'Blue': '#5b7fc4', 'Green': '#6f8f6a', 'Red': '#b8404a', 'Pink': '#e9a3b6', 'Purple': '#8b6aa8',
    'Orange/Rust': '#c96f3e', 'Yellow/Gold': '#e0b84c', 'Multi/Print': 'linear-gradient(135deg,#e9a3b6,#e0b84c,#6f8f6a,#5b7fc4)'
  };
  const COLOR_ORDER = ['Black', 'Grey', 'White/Ivory', 'Beige/Tan', 'Brown', 'Denim', 'Blue', 'Green', 'Red', 'Pink', 'Purple', 'Orange/Rust', 'Yellow/Gold', 'Multi/Print'];
  const CATEGORY_ORDER = ['Shirts', 'Tees & Polos', 'Knitwear', 'Trousers', 'Jeans', 'Shorts & Swim', 'Jackets & Coats', 'Suits & Blazers', 'Shoes', 'Accessories'];
  const PRICE_BANDS = [
    { key: 'u100', label: 'Under $100', test: p => p < 100 },
    { key: '100-200', label: '$100 – $200', test: p => p >= 100 && p < 200 },
    { key: '200-350', label: '$200 – $350', test: p => p >= 200 && p < 350 },
    { key: '350+', label: '$350 and up', test: p => p >= 350 },
  ];

  const ITEMS = window.CLOSET;
  const IDEAS = (window.SUGGESTIONS || []).map(i => Object.assign({ idea: true }, i));
  const byId = new Map(ITEMS.concat(IDEAS).map(i => [i.id, i]));
  const isIdea = id => { const it = byId.get(id); return !!(it && it.idea); };
  // ---------- sales: brand flags from the daily check, plus calendar nudges ----------
  const SALE_ITEMS = (window.SALES && window.SALES.items) || {};     // pieces actually marked down, by id
  const SALE_EVENTS = (window.SALES && window.SALES.events) || {};   // brands running a real sale event
  const salesFresh = (() => { const d = window.SALES && window.SALES.checked; return d ? (Date.now() - new Date(d + 'T12:00:00Z').getTime()) < 3 * 86400000 : false; })();
  const onSale = it => salesFresh && (!!SALE_ITEMS[String(it.id)] || !!(SALE_EVENTS[it.retailer] || SALE_EVENTS[it.brand]));
  const verifiedSale = it => salesFresh && !!SALE_ITEMS[String(it.id)];
  const saleInfo = it => SALE_ITEMS[String(it.id)];
  const brandEvent = it => salesFresh ? (SALE_EVENTS[it.retailer] || SALE_EVENTS[it.brand]) : null;
  const RET = (window.RETAILERS && window.RETAILERS.stores) || {};
  const RET_CHECKED = (window.RETAILERS && window.RETAILERS.checked) || '';
  const retFor = it => RET[it.retailer] || RET[it.brand] || null;
  const retLine = it => { const r = retFor(it); if (!r) return ''; return `<p class="returns-line"><span>Returns at ${esc(it.retailer)}</span> ${esc(r.window)} · ${esc(r.ship)}${r.note ? '. ' + esc(r.note) : ''}. <a href="${esc(r.policy)}" target="_blank" rel="noopener">Their policy</a></p>`; };
  function renderStores() {
    const counts = new Map(); ITEMS.forEach(i => counts.set(i.retailer, (counts.get(i.retailer) || 0) + 1));
    const names = Object.keys(RET).sort((a, b) => a.localeCompare(b));
    $('#stores-list').innerHTML = names.map(n => { const r = RET[n]; const c = counts.get(n) || 0; return `<div class="store"><div class="store-head"><a href="${esc(r.site)}" target="_blank" rel="noopener">${esc(n)}</a><span>${c} ${c === 1 ? 'piece' : 'pieces'}</span></div><p>${esc(r.window)} · ${esc(r.ship)}${r.note ? '. ' + esc(r.note) : ''}. <a class="pol" href="${esc(r.policy)}" target="_blank" rel="noopener">Their policy</a></p></div>`; }).join('');
    const sc = $('#stores-checked'); if (sc) sc.textContent = RET_CHECKED ? new Date(RET_CHECKED + 'T12:00:00Z').toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) : 'an unknown date';
  }
  const asOfLabel = () => new Date(window.SALES.checked + 'T12:00:00Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  function saleSeason() {
    const d = new Date(), y = d.getFullYear(), m = d.getMonth(), day = d.getDate(), dow = d.getDay();
    const nth = (mo, n, wd) => { const first = new Date(y, mo, 1).getDay(); return 1 + ((wd - first + 7) % 7) + (n - 1) * 7; };
    const lastMon = (mo) => { const last = new Date(y, mo + 1, 0); return last.getDate() - ((last.getDay() + 6) % 7); };
    const within = (mo, dd, before, after) => { const t = new Date(y, mo, dd), diff = (d - t) / 86400000; return diff >= -before && diff <= after; };
    if (within(1, nth(1, 3, 1), 3, 1)) return 'Presidents\u2019 Day weekend';
    if (within(4, lastMon(4), 4, 1)) return 'Memorial Day weekend';
    if (within(6, 4, 3, 2)) return 'the Fourth of July';
    if (within(8, nth(8, 1, 1), 4, 1)) return 'Labor Day weekend';
    const tg = nth(10, 4, 4); if (within(10, tg, 2, 5)) return 'Black Friday and Cyber Monday';
    if ((m === 11 && day >= 26) || (m === 0 && day <= 2)) return 'the after-Christmas sales';
    if ((m === 0 && day >= 20) || (m === 6 && day >= 20)) return 'end-of-season sales';
    return null;
  }

  // ---------- state ----------
  const state = {
    q: '', sort: 'default',
    category: new Set(), color: new Set(), brand: new Set(), occasion: new Set(), price: new Set(),
    saved: new Set(), passed: new Set(), showPassed: false, onlySale: false, meta: {}, shuffleOrder: null, view: [], modalIndex: -1, tab: 'closet',
  };

  // ---------- persistence ----------
  function readList(key, hashName) {
    const ids = new Set();
    try { (JSON.parse(localStorage.getItem(key) || '[]')).forEach(n => byId.has(n) && ids.add(n)); } catch (e) { }
    const m = location.hash.match(new RegExp(hashName + '=([\\d.,]+)'));
    if (m) m[1].split(/[.,]/).map(Number).forEach(n => byId.has(n) && ids.add(n));
    return ids;
  }
  function loadLists() {
    state.saved = readList(STORAGE_KEY, 'saved');
    state.passed = readList(PASSED_KEY, 'passed');
    state.passed.forEach(id => state.saved.delete(id));
    try { state.meta = JSON.parse(localStorage.getItem(META_KEY) || '{}'); } catch (e) { state.meta = {}; }
  }
  function hashFor() {
    const parts = [];
    if (state.saved.size) parts.push('saved=' + [...state.saved].join('.'));
    if (state.passed.size) parts.push('passed=' + [...state.passed].join('.'));
    return parts.length ? '#' + parts.join('&') : '';
  }
  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...state.saved]));
      localStorage.setItem(PASSED_KEY, JSON.stringify([...state.passed]));
      localStorage.setItem(META_KEY, JSON.stringify(state.meta));
    } catch (e) { }
    history.replaceState(null, '', location.pathname + location.search + hashFor());
  }
  function shareLink() { return location.origin + location.pathname + hashFor(); }

  // ---------- the notebook (optional Google Sheet sync) ----------
  // Each heart/pass is stamped with a time. On load we fetch the notebook's view of every item and keep,
  // per item and per kind, whichever side is newer. Local storage stays the instant source of truth, so the
  // page works fully without the notebook; the notebook only makes lists follow her between devices.
  const CLIENT_ID = (() => { try { let c = localStorage.getItem(CLIENT_KEY); if (!c) { c = Math.random().toString(36).slice(2, 10); localStorage.setItem(CLIENT_KEY, c); } return c; } catch (e) { return 'anon'; } })();
  function stamp(id, kind, on) {
    const m = state.meta[id] = state.meta[id] || {};
    m[kind] = { on: on ? 1 : 0, ts: Date.now() };
    const it = byId.get(id);
    enqueue({ key: CLOSET_KEY, item: id, kind, on: on ? 1 : 0, ts: m[kind].ts, name: it ? it.name : '', brand: it ? it.brand : '', client: CLIENT_ID });
  }
  function readQueue() { try { return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]'); } catch (e) { return []; } }
  function writeQueue(q) { try { localStorage.setItem(QUEUE_KEY, JSON.stringify(q)); } catch (e) { } }
  let flushTimer = null;
  function enqueue(ev) {
    if (!SYNC_URL) return;
    const q = readQueue(); q.push(ev); writeQueue(q);
    clearTimeout(flushTimer); flushTimer = setTimeout(flushQueue, 600);   // batch rapid taps
  }
  async function flushQueue() {
    if (!SYNC_URL || !navigator.onLine) return;
    const q = readQueue(); if (!q.length) return;
    try {
      const r = await fetch(SYNC_URL, { method: 'POST', body: JSON.stringify({ events: q }), redirect: 'follow' });
      if (!r.ok) throw new Error('status ' + r.status);
      const rest = readQueue().slice(q.length); writeQueue(rest);   // drop only what we sent
    } catch (e) { /* keep the queue; retried on the next load or when back online */ }
  }
  async function pullNotebook() {
    if (!SYNC_URL) return;
    try {
      const r = await fetch(SYNC_URL + (SYNC_URL.includes('?') ? '&' : '?') + 'key=' + encodeURIComponent(CLOSET_KEY), { redirect: 'follow' });
      if (!r.ok) throw new Error('status ' + r.status);
      const data = await r.json();
      const items = data.items || {};
      let changed = false;
      const pushBack = [];
      // Hearts and passes made before the notebook existed carry no timestamp. Give them a very old one,
      // so they reach the notebook but any newer decision made elsewhere wins over them.
      state.saved.forEach(id => { const m = state.meta[id] = state.meta[id] || {}; if (!m.s) m.s = { on: 1, ts: 1 }; });
      state.passed.forEach(id => { const m = state.meta[id] = state.meta[id] || {}; if (!m.p) m.p = { on: 1, ts: 1 }; });
      const allIds = new Set([...Object.keys(items), ...Object.keys(state.meta)]);
      for (const idStr of allIds) {
        const id = Number(idStr); if (!byId.has(id)) continue;
        for (const kind of ['s', 'p']) {
          const remote = items[idStr] && items[idStr][kind];
          const local = state.meta[id] && state.meta[id][kind];
          if (remote && (!local || remote.ts > local.ts)) {
            (state.meta[id] = state.meta[id] || {})[kind] = { on: remote.on ? 1 : 0, ts: remote.ts };
            const set = kind === 's' ? state.saved : state.passed;
            const had = set.has(id);
            remote.on ? set.add(id) : set.delete(id);
            if (had !== set.has(id)) changed = true;
          } else if (local && (!remote || local.ts > remote.ts) && !(remote && remote.on === local.on)) {
            const it = byId.get(id);
            pushBack.push({ key: CLOSET_KEY, item: id, kind, on: local.on, ts: local.ts, name: it.name, brand: it.brand, client: CLIENT_ID });
          }
        }
      }
      state.passed.forEach(id => { if (state.saved.has(id)) { const sm = state.meta[id]; if (sm && sm.p && sm.s && sm.p.ts >= sm.s.ts) state.saved.delete(id); else state.passed.delete(id); changed = true; } });
      if (pushBack.length) { const q = readQueue(); writeQueue(q.concat(pushBack)); }
      persist();
      if (changed) { updateSavedUi(); render(); if ($('#drawer').classList.contains('open')) renderDrawer(); }
      flushQueue();
    } catch (e) { /* notebook unreachable: carry on from local storage */ }
  }
  window.addEventListener('online', flushQueue);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') pullNotebook(); });

  // ---------- helpers ----------
  const $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const money = n => n == null ? 'Sold out' : '$' + (Number.isInteger(n) ? n.toLocaleString() : n.toFixed(2));
  const P = n => n == null ? Infinity : n;   // unpriced (sold-out) pieces sort last
  const heartSvg = '<svg><use href="#i-heart"/></svg>';
  let toastTimer, toastAction = null;
  function toast(msg, actionLabel, action) {
    const t = $('#toast'); $('#toast-msg').textContent = msg;
    const b = $('#toast-action'); toastAction = action || null;
    b.hidden = !actionLabel; b.textContent = actionLabel || '';
    t.classList.add('show');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.classList.remove('show'); toastAction = null; }, actionLabel ? 4500 : 1800);
  }
  function searchUrl(site, item) {
    const q = encodeURIComponent(`${item.brand} ${item.name}`);
    return site === 'ebay' ? `https://www.ebay.com/sch/i.html?_nkw=${q}&_sacat=${encodeURIComponent(RESALE.ebayCategory || '15724')}`
      : `https://poshmark.com/search?query=${q}&department=${encodeURIComponent(RESALE.poshmarkDepartment || 'Women')}`;
  }

  // ---------- filtering ----------
  function pool() {
    return state.tab === 'ideas' ? IDEAS.filter(i => !state.saved.has(i.id)) : ITEMS.concat(IDEAS.filter(i => state.saved.has(i.id)));
  }
  function matches(item) {
    if (!state.showPassed && state.passed.has(item.id)) return false;
    if (state.onlySale && !onSale(item)) return false;
    if (state.category.size && !state.category.has(item.category)) return false;
    if (state.color.size && !state.color.has(item.color)) return false;
    if (state.brand.size && !state.brand.has(item.brand)) return false;
    if (state.occasion.size && !item.occasions.some(o => state.occasion.has(o))) return false;
    if (state.price.size && (item.price == null || ![...state.price].some(k => PRICE_BANDS.find(b => b.key === k).test(item.price)))) return false;
    if (state.q) {
      const hay = `${item.brand} ${item.name} ${item.colorDetail || ''} ${item.categoryDetail || ''} ${item.retailer} ${item.color}`.toLowerCase();
      if (!state.q.split(/\s+/).every(w => hay.includes(w))) return false;
    }
    return true;
  }
  function sorted(list) {
    const l = list.slice();
    switch (state.sort) {
      case 'price-asc': l.sort((a, b) => P(a.price) - P(b.price) || a.id - b.id); break;
      case 'price-desc': l.sort((a, b) => P(b.price) - P(a.price) || a.id - b.id); break;
      case 'brand': l.sort((a, b) => a.brand.localeCompare(b.brand) || a.name.localeCompare(b.name)); break;
      case 'shuffle': {
        if (!state.shuffleOrder) reshuffle();
        const pos = state.shuffleOrder; l.sort((a, b) => pos.get(a.id) - pos.get(b.id)); break;
      }
      default: {
        if (state.tab === 'ideas') { l.sort((a, b) => (b.round - a.round) || (a.id - b.id)); break; }
        const pos = defaultOrder(); l.sort((a, b) => (pos.has(a.id) ? pos.get(a.id) : -1) - (pos.has(b.id) ? pos.get(b.id) : -1)); break;
      }
    }
    return l;
  }
  // A fixed, seeded shuffle: looks mixed, but identical on every visit.
  const DEFAULT_SEED = 54;
  let _defaultOrder = null;
  function defaultOrder() {
    if (_defaultOrder) return _defaultOrder;
    let t = DEFAULT_SEED >>> 0;
    const rnd = () => { t = (t + 0x6D2B79F5) >>> 0; let r = Math.imul(t ^ (t >>> 15), 1 | t); r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r; return ((r ^ (r >>> 14)) >>> 0) / 4294967296; };
    const ids = ITEMS.map(i => i.id);
    for (let i = ids.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [ids[i], ids[j]] = [ids[j], ids[i]]; }
    _defaultOrder = new Map(ids.map((id, k) => [id, k]));
    return _defaultOrder;
  }
  function reshuffle() {
    const ids = ITEMS.map(i => i.id);
    for (let i = ids.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1));[ids[i], ids[j]] = [ids[j], ids[i]]; }
    state.shuffleOrder = new Map(ids.map((id, k) => [id, k]));
  }
  function activeFilterCount() { return state.category.size + state.color.size + state.brand.size + state.occasion.size + state.price.size; }

  // ---------- facets ----------
  const pool_ = () => pool();
  function countBy(key, values, getter) {
    // counts respect every OTHER active facet, so numbers stay honest as you refine
    const saved = new Set(state[key]); state[key].clear();
    const pool = pool_().filter(matches); state[key] = saved;
    const c = new Map(values.map(v => [v, 0]));
    pool.forEach(it => getter(it).forEach(v => c.has(v) && c.set(v, c.get(v) + 1)));
    return c;
  }
  function renderFacets() {
    const brands = [...new Set(pool().map(i => i.brand))].sort((a, b) => a.localeCompare(b));
    const cCat = countBy('category', CATEGORY_ORDER, i => [i.category]);
    const cCol = countBy('color', COLOR_ORDER, i => [i.color]);
    const cOcc = countBy('occasion', OCC_ORDER, i => i.occasions);
    const cBrand = countBy('brand', brands, i => [i.brand]);
    const cPrice = countBy('price', PRICE_BANDS.map(b => b.key), i => i.price == null ? [] : PRICE_BANDS.filter(b => b.test(i.price)).map(b => b.key));

    const opt = (key, v, label, cnt, extra = '') =>
      `<label class="opt"><input type="checkbox" data-facet="${key}" value="${esc(v)}" ${state[key].has(v) ? 'checked' : ''}><span class="box"></span>${extra}<span class="lbl">${esc(label)}</span><span class="cnt">${cnt}</span></label>`;
    const pill = (key, v, label) =>
      `<label class="pill"><input type="checkbox" data-facet="${key}" value="${esc(v)}" ${state[key].has(v) ? 'checked' : ''}>${esc(label)}</label>`;
    const facet = (title, key, body, open = true) =>
      `<details class="facet" ${open ? 'open' : ''}><summary>${title}${state[key].size ? `<span class="n">${state[key].size}</span>` : ''}</summary><div class="facet-body ${key === 'occasion' || key === 'price' ? 'wrap' : ''}">${body}</div></details>`;

    $('#facets').innerHTML =
      facet('Occasion', 'occasion', OCC_ORDER.map(o => pill('occasion', o, OCC_LABEL[o])).join('')) +
      facet('Category', 'category', CATEGORY_ORDER.map(c => opt('category', c, c, cCat.get(c))).join('')) +
      facet('Color', 'color', COLOR_ORDER.map(c => opt('color', c, c, cCol.get(c), `<span class="sw" style="background:${COLOR_SWATCH[c]}"></span>`)).join('')) +
      facet('Price', 'price', PRICE_BANDS.map(b => pill('price', b.key, b.label)).join('')) +
      facet('Brand', 'brand', `<input class="facet-search" id="brand-q" type="search" placeholder="Find a brand…" autocomplete="off"><div class="brand-list" id="brand-list">${brands.map(b => opt('brand', b, b, cBrand.get(b), salesFresh && SALE_EVENTS[b] ? '<span class="sale-dot" title="Running a sale event"></span>' : '')).join('')}</div>`, state.brand.size > 0);
    const saleN = pool().filter(i => onSale(i) && !state.passed.has(i.id)).length;
    $('#sale-toggle').hidden = saleN === 0 && !state.onlySale; $('#sale-count').textContent = saleN; $('#only-sale').checked = state.onlySale;
  }

  // ---------- grid ----------
  function cardHtml(it) {
    const on = state.saved.has(it.id), passed = state.passed.has(it.id);
    const ribbon = it.idea ? (state.tab === 'ideas' ? (it.newBrand ? 'New label' : '') : 'New idea') : '';
    return `<article class="card ${passed ? 'is-passed' : ''} ${it.idea ? 'is-idea' : ''}" data-id="${it.id}">
      ${ribbon ? `<span class="ribbon">${ribbon}</span>` : ''}
      <button class="heart ${on ? 'on' : ''}" type="button" aria-label="${on ? 'Remove from saved' : 'Save'}" aria-pressed="${on}">${heartSvg}</button>
      <button class="pass" type="button" aria-label="${passed ? 'Bring back' : 'Not for me'}" title="${passed ? 'Bring back' : 'Not for me'}"><svg><use href="#i-x"/></svg></button>
      <div class="frame" data-open="${it.id}"><img loading="lazy" src="${it.img}" alt="${esc(it.name)}" ${it.hi ? '' : 'class="soft"'}>${verifiedSale(it) ? `<span class="sale">On sale · ${Math.abs((it.price || 0) - saleInfo(it).now) < 1 ? 'was ' + money(saleInfo(it).was) : 'now ' + money(saleInfo(it).now)}</span>` : (onSale(it) ? `<span class="sale event">Sale event</span>` : '')}</div>
      <div class="meta" data-open="${it.id}">
        <p class="brand">${esc(it.brand)}</p>
        <h3 class="name">${esc(it.name)}</h3>
        <div class="price ${it.price == null ? 'soldout' : ''}">${it.price == null ? 'Sold out · hunt secondhand' : money(it.price)}</div>
      </div></article>`;
  }
  function render() {
    document.body.classList.toggle('tab-ideas', state.tab === 'ideas');
    const season = saleSeason();
    const closetBrands = new Set(ITEMS.map(i => i.retailer).concat(ITEMS.map(i => i.brand)));
    const events = salesFresh ? Object.keys(SALE_EVENTS).filter(b => closetBrands.has(b)).sort() : [];
    const reduced = salesFresh ? ITEMS.filter(i => onSale(i) && !state.passed.has(i.id)).length : 0;
    const banner = $('#sale-banner');
    if ((season || events.length || reduced) && state.tab === 'closet') {
      const brandLink = b => SALE_EVENTS[b].site ? `<a class="bl" href="${esc(SALE_EVENTS[b].site)}" target="_blank" rel="noopener">${esc(b)}</a>` : esc(b);
      const names = events.map(brandLink);
      const list = names.length <= 1 ? names.join('') : names.slice(0, -1).join(', ') + ' and ' + names[names.length - 1];
      banner.hidden = false;
      banner.innerHTML = `<svg class="bh" viewBox="0 0 24 24"><use href="#i-heart"/></svg><span>` +
        (season ? `It\u2019s ${season}, when most of these brands mark things down. ` : '') +
        (events.length ? `${list} ${events.length === 1 ? 'is' : 'are'} running a sale event as of ${esc(asOfLabel())}. ` : '') +
        (reduced ? (events.length ? `That puts ${reduced} piece${reduced === 1 ? '' : 's'} in the closet possibly on sale right now. ` : `${reduced} piece${reduced === 1 ? '' : 's'} in the closet ${reduced === 1 ? 'is' : 'are'} on sale right now. `) : '') +
        (reduced && !state.onlySale ? `<button class="link" type="button" id="see-sale">See them</button>` : '') + `</span>`;
    } else banner.hidden = true;
    $('#ideas-intro').hidden = state.tab !== 'ideas';
    const all = pool();
    state.view = sorted(all.filter(matches));
    const n = state.view.length;
    const total = all.length - (state.showPassed ? 0 : all.filter(i => state.passed.has(i.id)).length);
    const noun = state.tab === 'ideas' ? 'suggestion' : 'piece';
    $('#grid').innerHTML = state.view.map(cardHtml).join('');
    $('#empty').hidden = n > 0;
    if (state.tab === 'ideas' && total === 0) $('#results-count').innerHTML = 'Nothing waiting. Anything you added is in the closet.';
    else $('#results-count').innerHTML = n === total ? `All <b>${n}</b> ${noun}${n === 1 ? '' : 's'}` : `<b>${n}</b> of ${total} ${noun}s`;
    $('#apply-count').textContent = `${n} piece${n === 1 ? '' : 's'}`;
    const fc = activeFilterCount();
    $('#filter-count').textContent = fc ? String(fc) : '';
    $('#filter-count').hidden = !fc;
    renderChips();
    renderFacets();
    renderPassed();
    renderIdeas();
  }
  function renderChips() {
    const chips = [];
    const add = (key, v, label) => chips.push(`<button class="chip" type="button" data-chip="${key}" data-value="${esc(v)}">${esc(label)} <svg><use href="#i-x"/></svg></button>`);
    state.occasion.forEach(v => add('occasion', v, OCC_LABEL[v]));
    state.category.forEach(v => add('category', v, v));
    state.color.forEach(v => add('color', v, v));
    state.price.forEach(v => add('price', v, PRICE_BANDS.find(b => b.key === v).label));
    state.brand.forEach(v => add('brand', v, v));
    if (state.q) add('q', state.q, `“${state.q}”`);
    if (state.onlySale) add('sale', 'sale', 'On sale now');
    const html = chips.join('') + (chips.length > 1 ? `<button class="link" type="button" data-chip="all">Clear all</button>` : '');
    $('#chips').innerHTML = html; $('#chips-m').innerHTML = html;
  }

  // ---------- saved ----------
  function toggleSaved(id, sourceBtn) {
    const was = state.saved.has(id);
    was ? state.saved.delete(id) : state.saved.add(id);
    stamp(id, 's', !was);
    if (!was && state.passed.has(id)) { state.passed.delete(id); stamp(id, 'p', false); persist(); render(); }
    persist(); updateSavedUi();
    if (isIdea(id)) render();   // an idea joins or leaves the grid when hearted or un-hearted
    document.querySelectorAll(`.card[data-id="${id}"] .heart, .modal-heart[data-id="${id}"]`).forEach(b => {
      b.classList.toggle('on', !was); b.setAttribute('aria-pressed', String(!was)); b.setAttribute('aria-label', !was ? 'Remove from saved' : 'Save');
      if (!was) { b.classList.remove('pop'); void b.offsetWidth; b.classList.add('pop'); }
    });
    toast(was ? (isIdea(id) ? 'Back in suggestions' : 'Taken out of your saved pieces') : (isIdea(id) ? 'Added to your closet ♥' : 'Tucked away ♥'));
    if ($('#drawer').classList.contains('open')) renderDrawer();
  }
  function updateSavedUi() {
    const n = state.saved.size;
    $('#saved-count').textContent = n;
  }
  function togglePassed(id) {
    const was = state.passed.has(id);
    if (was) {
      state.passed.delete(id); stamp(id, 'p', false); persist(); render();
      toast('Brought back');
    } else {
      state.passed.add(id); stamp(id, 'p', true);
      if (state.saved.has(id)) { state.saved.delete(id); stamp(id, 's', false); updateSavedUi(); }
      persist();
      const card = document.querySelector(`.card[data-id="${id}"]`);
      if (card && !state.showPassed) { card.classList.add('leaving'); setTimeout(render, 360); } else render();
      if ($('#modal').open) $('#modal').close();
      toast('Tucked out of sight', 'Undo', () => togglePassed(id));
    }
    if ($('#drawer').classList.contains('open')) renderDrawer();
  }
  function renderIdeas() {
    const open = IDEAS.filter(i => !state.saved.has(i.id) && !state.passed.has(i.id));
    $('#tabs').hidden = IDEAS.length === 0;
    $('#ideas-count').textContent = open.length;
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.tab === state.tab));
    let seen = []; try { seen = JSON.parse(localStorage.getItem(SEEN_KEY) || '[]'); } catch (e) { }
    const unseen = state.tab !== 'ideas' && open.some(i => !seen.includes(i.id));
    const tab = document.querySelector('.tab[data-tab="ideas"]'); let dot = tab.querySelector('.dot');
    if (unseen && !dot) { dot = document.createElement('span'); dot.className = 'dot'; tab.appendChild(dot); }
    if (!unseen && dot) dot.remove();
  }
  function markIdeasSeen() {
    try { localStorage.setItem(SEEN_KEY, JSON.stringify(IDEAS.map(i => i.id))); } catch (e) { }
  }
  function switchTab(tab) {
    state.tab = tab;
    if (tab === 'ideas') markIdeasSeen();
    if ($('#modal').open) $('#modal').close();
    render();
    window.scrollTo({ top: $('#topbar').offsetTop, behavior: 'smooth' });
  }
  function renderPassed() {
    const items = [...state.passed].map(id => byId.get(id)).filter(Boolean);
    const facet = $('#passed-facet');
    facet.hidden = items.length === 0;
    $('#passed-count').textContent = items.length;
    $('#show-passed').checked = state.showPassed;
    $('#passed-list').innerHTML = items.map(it => `<div class="passed-row"><img src="${it.img}" alt="" data-open="${it.id}"><span class="nm">${esc(it.name)}</span><button class="link" type="button" data-unpass="${it.id}">Bring back</button></div>`).join('');
  }
  function savedItems() { return [...state.saved].map(id => byId.get(id)).filter(Boolean); }
  function renderDrawer() {
    const items = savedItems();
    const body = $('#drawer-body'), foot = $('#drawer-foot');
    if (!items.length) {
      body.innerHTML = `<div class="drawer-empty">${heartSvg}<p class="big">Nothing tucked away yet.</p><p>Tap the heart on anything that catches your eye and it will wait for you here.</p></div>`;
      foot.innerHTML = '';
      return;
    }
    body.innerHTML = items.map(it => `<div class="saved-item" data-id="${it.id}">
        <img src="${it.img}" alt="" data-open="${it.id}">
        <div><p class="brand">${esc(it.brand)}</p><div class="nm" data-open="${it.id}">${esc(it.name)}</div><div class="pr">${it.price == null ? 'Sold out' : money(it.price)} · ${esc(it.color)}</div></div>
        <button class="icon-btn rm" type="button" data-remove="${it.id}" aria-label="Remove"><svg width="18" height="18"><use href="#i-x"/></svg></button>
      </div>`).join('');
    const total = items.reduce((s, i) => s + (i.price || 0), 0);
    const unpriced = items.filter(i => i.price == null).length;
    foot.innerHTML = `<div class="total"><span>${items.length} piece${items.length === 1 ? '' : 's'} saved</span></div>
      <div class="drawer-actions">
        <a class="btn rose full" id="mail-list" href="${mailtoHref(items, total)}">Email me my list</a>
        <button class="btn" id="copy-link" type="button">Copy share link</button>
        <button class="btn ghost" id="clear-saved" type="button">Clear list</button>
      </div>
      <p class="tiny">Your list is saved in this browser and inside the share link.</p>`;
  }
  function mailtoHref(items, total) {
    const link = shareLink();
    let lines = items.map(i => `♥ ${i.brand} — ${i.name} (${i.color}) — ${money(i.price)}\n   ${i.url}`);
    let body;
    for (; ;) {
      body = `${MAIL.intro || 'My saved pieces from ' + (CFG.siteTitle || 'the closet') + ':'}\n\n${lines.join('\n\n')}\n\nOpen the list anytime: ${link}\n`;
      if (encodeURIComponent(body).length < 1800 || lines.length <= 1) break;   // keep the mailto short enough for every mail app
      lines = items.slice(0, Math.max(1, lines.length - 1)).map(i => `♥ ${i.brand} — ${i.name} — ${money(i.price)}`);
      if (lines.length < items.length) lines.push(`…and ${items.length - lines.length} more, all in the link below.`);
    }
    const params = new URLSearchParams({ subject: MAIL.subject || 'My picks from ' + (CFG.siteTitle || 'the closet'), body });
    if (BCC_EMAIL) params.set('bcc', BCC_EMAIL);
    return `mailto:${HER_EMAIL}?${params.toString().replace(/\+/g, '%20')}`;
  }
  async function copyShareLink() {
    const link = shareLink();
    try { await navigator.clipboard.writeText(link); toast('Link copied'); }
    catch (e) { prompt('Copy this link:', link); }
  }

  // ---------- modal ----------
  function openModal(id) {
    const idx = state.view.findIndex(i => i.id === id);
    state.modalIndex = idx >= 0 ? idx : -1;
    const it = byId.get(id);
    const on = state.saved.has(id);
    $('#modal-inner').innerHTML = `
      <div class="modal-media">
        <img src="${it.img}" alt="${esc(it.name)}">
        <div class="arch"></div>
        <button class="heart modal-heart ${on ? 'on' : ''}" type="button" data-id="${it.id}" aria-pressed="${on}" aria-label="${on ? 'Remove from saved' : 'Save'}">${heartSvg}</button>
        ${it.idea && !on ? `<button class="modal-add" type="button" data-add="${it.id}"><svg><use href="#i-heart"/></svg> Add to my closet</button>` : `<button class="modal-pass ${state.passed.has(id) ? 'on' : ''}" type="button" data-pass="${it.id}"><svg><use href="#i-x"/></svg> ${state.passed.has(id) ? 'Bring back' : 'Not for me'}</button>`}
        ${state.modalIndex >= 0 && state.view.length > 1 ? `<div class="modal-nav"><button type="button" data-nav="-1" aria-label="Previous"><svg><use href="#i-arrow"/></svg></button><button type="button" data-nav="1" aria-label="Next"><svg><use href="#i-arrow"/></svg></button></div>` : ''}
      </div>
      <div class="modal-body">
        <button class="icon-btn modal-close" type="button" data-close aria-label="Close"><svg width="20" height="20"><use href="#i-x"/></svg></button>
        <p class="brand">${esc(it.brand)}${it.retailer !== it.brand ? ` · at ${esc(it.retailer)}` : ''}</p>
        <h2>${esc(it.name)}</h2>
        <div class="price">${it.price == null ? 'Sold out at ' + esc(it.retailer) + ' · worth a secondhand hunt' : money(it.price)}</div>
        <div class="tags">
          <span class="tag">${esc(it.category)}</span>
          <span class="tag col">${esc(it.colorDetail || it.color)}</span>
          ${it.occasions.map(o => `<span class="tag occ">${OCC_LABEL[o] || o}</span>`).join('')}
        </div>
        ${verifiedSale(it) ? `<p class="sale-line">${Math.abs((it.price || 0) - saleInfo(it).now) < 1 ? `Marked down at ${esc(it.retailer)} from ${money(saleInfo(it).was)} to ${money(saleInfo(it).now)}, as of ${esc(asOfLabel())}.` : `Marked down at ${esc(it.retailer)} right now: ${money(saleInfo(it).now)}, was ${money(saleInfo(it).was)}, as of ${esc(asOfLabel())}.`}</p>` : (brandEvent(it) ? `<p class="sale-line">${brandEvent(it).site ? `<a href="${esc(brandEvent(it).site)}" target="_blank" rel="noopener">${esc(it.retailer)}</a>` : esc(it.retailer)} is running a sale event right now${brandEvent(it).off ? ', ' + brandEvent(it).off + '% off' : ''}, as of ${esc(asOfLabel())}. This piece is possibly on sale; check the product page.</p>` : '')}
        ${it.fabric ? `<p class="fabric-line">${esc(it.fabric)}</p>` : ''}
        ${it.desc ? `<div class="about"><h3>About this piece</h3><p>${esc(it.desc)}</p></div>` : ''}
        ${it.details && it.details.length ? `<div class="about"><h3>Cut, fabric &amp; care</h3><ul class="details">${it.details.map(d => `<li>${esc(d)}</li>`).join('')}</ul></div>` : ''}
        ${!it.desc && !(it.details && it.details.length) ? `<p class="lowres-note">${esc(it.retailer)} keeps its details behind a login wall, so the full description lives on their site.</p>` : ''}
        ${it.idea && it.reason ? `<div class="idea-why"><b>Why this idea</b>${esc(it.reason)}</div>` : ''}
        ${it.idea && !on ? `<p class="detail-row"><button class="link" type="button" data-pass="${it.id}">Not for me</button></p>` : ''}
        ${it.why ? `<p class="why"><span>Why these occasions</span> ${esc(it.why)}</p>` : ''}
        ${it.categoryDetail && it.categoryDetail !== it.category ? `<p class="detail-row">Listed as <b>${esc(it.categoryDetail)}</b></p>` : ''}
        ${retLine(it)}
        <div class="links">
          <a href="${esc(it.url)}" target="_blank" rel="noopener"><span>See it at ${esc(it.retailer)} <small>· original listing</small></span><svg><use href="#i-arrow"/></svg></a>
          <a href="${searchUrl('ebay', it)}" target="_blank" rel="noopener"><span>Find it on eBay <small>· search</small></span><svg><use href="#i-arrow"/></svg></a>
          <a href="${searchUrl('posh', it)}" target="_blank" rel="noopener"><span>Find it on Poshmark <small>· search</small></span><svg><use href="#i-arrow"/></svg></a>
        </div>
      </div>`;
    const m = $('#modal');
    if (!m.open) m.showModal();
    m.querySelector('.modal-body').scrollTop = 0;
  }
  function navModal(dir) {
    if (state.modalIndex < 0) return;
    const n = state.view.length;
    const next = state.view[(state.modalIndex + dir + n) % n];
    openModal(next.id);
  }

  // ---------- panels ----------
  function openPanel(which) {
    closePanels();
    $('#scrim').hidden = false;
    $(which).classList.add('open'); $(which).setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    if (which === '#drawer') renderDrawer();
  }
  function closePanels() {
    $('#scrim').hidden = true;
    ['#drawer', '#filters'].forEach(s => { $(s).classList.remove('open'); $(s).setAttribute('aria-hidden', $(s).id === 'filters' ? 'false' : 'true'); });
    document.body.style.overflow = '';
  }

  // ---------- events ----------
  document.addEventListener('click', e => {
    const t = e.target.closest('button, a, .frame, .meta, [data-open]');
    if (!t) return;
    if (t.classList.contains('heart')) { e.preventDefault(); toggleSaved(Number(t.dataset.id || t.closest('.card').dataset.id), t); return; }
    if (t.classList.contains('pass')) { e.preventDefault(); togglePassed(Number(t.closest('.card').dataset.id)); return; }
    if (t.dataset.pass) { togglePassed(Number(t.dataset.pass)); return; }
    if (t.dataset.add) { const id = Number(t.dataset.add); if (!state.saved.has(id)) toggleSaved(id); $('#modal').close(); toast('Added to your closet ♥'); return; }
    if (t.dataset.tab) { switchTab(t.dataset.tab); return; }
    if (t.dataset.unpass) { togglePassed(Number(t.dataset.unpass)); return; }
    if (t.id === 'toast-action') { const fn = toastAction; toastAction = null; $('#toast').classList.remove('show'); if (fn) fn(); return; }
    if (t.dataset.open) { openModal(Number(t.dataset.open)); return; }
    if (t.dataset.remove) { toggleSaved(Number(t.dataset.remove)); return; }
    if (t.dataset.nav) { navModal(Number(t.dataset.nav)); return; }
    if (t.hasAttribute('data-close')) { const d = t.closest('dialog'); if (d) d.close(); return; }
    if (t.dataset.chip) {
      if (t.dataset.chip === 'all') clearAll();
      else if (t.dataset.chip === 'q') { state.q = ''; $('#q').value = ''; }
      else if (t.dataset.chip === 'sale') { state.onlySale = false; }
      else state[t.dataset.chip].delete(t.dataset.value);
      render(); return;
    }
    switch (t.id) {
      case 'open-saved': openPanel('#drawer'); break;
      case 'open-about': $('#about').showModal(); break;
      case 'open-stores': renderStores(); $('#stores').showModal(); break;
      case 'see-sale': state.onlySale = true; state.tab = 'closet'; render(); window.scrollTo({ top: $('#topbar').offsetTop, behavior: 'smooth' }); break;
      case 'open-person': $('#person').showModal(); break;
      case 'open-filters': openPanel('#filters'); break;
      case 'close-drawer': case 'close-filters': case 'apply-filters': closePanels(); break;
      case 'surprise': reshuffle(); state.sort = 'shuffle'; $('#sort').value = 'shuffle'; render(); window.scrollTo({ top: $('#topbar').offsetTop, behavior: 'smooth' }); toast('Shuffled ✨'); break;
      case 'clear-all': case 'empty-clear': clearAll(); render(); break;
      case 'copy-link': copyShareLink(); break;
      case 'clear-saved': if (confirm('Clear your whole saved list?')) { state.saved.clear(); persist(); updateSavedUi(); render(); renderDrawer(); } break;
      case 'mail-list': setTimeout(() => toast('Opening your mail app…'), 50); break;
    }
  });
  $('#scrim').addEventListener('click', closePanels);
  $('#show-passed').addEventListener('change', e => { state.showPassed = e.target.checked; render(); });
  $('#only-sale').addEventListener('change', e => { state.onlySale = e.target.checked; render(); });
  $('#facets').addEventListener('change', e => {
    const cb = e.target; if (!cb.dataset.facet) return;
    cb.checked ? state[cb.dataset.facet].add(cb.value) : state[cb.dataset.facet].delete(cb.value);
    const bq = $('#brand-q') ? $('#brand-q').value : '';
    render();
    if (bq) { $('#brand-q').value = bq; filterBrandList(bq); }
  });
  $('#facets').addEventListener('input', e => { if (e.target.id === 'brand-q') filterBrandList(e.target.value); });
  function filterBrandList(q) {
    q = q.trim().toLowerCase();
    $('#brand-list').querySelectorAll('.opt').forEach(o => { o.style.display = !q || o.textContent.toLowerCase().includes(q) ? '' : 'none'; });
  }
  let qTimer;
  $('#q').addEventListener('input', e => { clearTimeout(qTimer); qTimer = setTimeout(() => { state.q = e.target.value.trim().toLowerCase(); render(); }, 120); });
  $('#sort').addEventListener('change', e => { state.sort = e.target.value; if (state.sort === 'shuffle') reshuffle(); render(); });
  document.addEventListener('keydown', e => {
    if ($('#modal').open) { if (e.key === 'ArrowRight') navModal(1); if (e.key === 'ArrowLeft') navModal(-1); return; }
    if (e.key === 'Escape') closePanels();
  });
  ['#modal', '#about', '#person', '#stores'].forEach(sel => $(sel).addEventListener('click', e => { if (e.target === e.currentTarget) e.currentTarget.close(); }));
  window.addEventListener('hashchange', () => { const s = readList(STORAGE_KEY, 'saved'), p = readList(PASSED_KEY, 'passed'); s.forEach(id => state.saved.add(id)); p.forEach(id => { state.passed.add(id); state.saved.delete(id); }); persist(); updateSavedUi(); render(); });
  function clearAll() { ['category', 'color', 'brand', 'occasion', 'price'].forEach(k => state[k].clear()); state.q = ''; $('#q').value = ''; state.onlySale = false; }

  // ---------- the personal parts of the page (config.js) ----------
  // Plain text fields are filled by the small script in index.html; this builds the parts with structure.
  function applyConfig() {
    const set = (sel, v) => { const el = $(sel); if (el && v != null) el.textContent = v; };
    const about = CFG.about || {};
    set('#about-considered', about.considered); set('#about-storefronts', about.storefronts);
    $('#about-body').innerHTML = (about.paragraphs || []).map(p => `<p>${p}</p>`).join('') + (about.fine || []).map(p => `<p class="fine">${p}</p>`).join('');
    const person = CFG.person;
    if (person && (person.photos || []).length) $('#person-collage').innerHTML = person.photos.map(p => `<img src="${esc(p.src)}" alt="${esc(p.alt || '')}" loading="lazy">`).join('');
    if (!person) { $('#open-person').hidden = true; $('#person-dot').hidden = true; }   // no "About her" page at all
  }

  // ---------- go ----------
  applyConfig();
  loadLists(); persist();
  const heroCount = $('#hero-count'); if (heroCount) heroCount.textContent = ITEMS.length;
  $('#about-count').textContent = ITEMS.length;
  $('#about-brands').textContent = new Set(ITEMS.map(i => i.brand)).size;
  updateSavedUi();
  render();
  pullNotebook();
})();
