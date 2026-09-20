/** @OnlyCurrentDoc */
/**
 * The closet's notebook — Google Apps Script web app.
 * The @OnlyCurrentDoc line above limits the script's permission to this one spreadsheet.
 *
 * Sheets used (created automatically):
 *   events  — one row per heart/pass action, newest at the bottom
 *   latest  — one row per piece currently saved or marked not for me, newest change first
 *
 * Deploy: Extensions → Apps Script → paste this → Deploy → New deployment → Web app,
 *   "Execute as: Me", "Who has access: Anyone" → copy the Web app URL into config.js ("syncUrl").
 * The site sends its list name ("notebookKey" in config.js) with every request; the defaults below only
 *   apply to requests that omit it.
 */
const EVENT_HEADERS = ['ts', 'when', 'key', 'item', 'kind', 'on', 'name', 'brand', 'client', 'received'];

function sheet_(name, headers) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(name);
  if (!sh) { sh = ss.insertSheet(name); sh.appendRow(headers); sh.setFrozenRows(1); }
  return sh;
}

function doGet(e) {
  const key = (e && e.parameter && e.parameter.key) || 'closet';
  return json_({ ok: true, key: key, items: state_(key), serverTime: Date.now() });
}

function doPost(e) {
  let body = {};
  try { body = JSON.parse(e.postData.contents || '{}'); } catch (err) { return json_({ ok: false, error: 'bad json' }); }
  const events = Array.isArray(body) ? body : (body.events || [body]);
  const sh = sheet_('events', EVENT_HEADERS);
  const now = new Date();
  const MAX_ITEM = 100000;   // ignore anything that is not a plausible closet item number
  const rows = events.filter(ev => ev && Number.isInteger(Number(ev.item)) && Number(ev.item) > 0 && Number(ev.item) < MAX_ITEM && (ev.kind === 's' || ev.kind === 'p')).slice(0, 200).map(ev => [
    Number(ev.ts) || Date.now(), new Date(Number(ev.ts) || Date.now()), String(ev.key || 'closet'), Number(ev.item),
    ev.kind, ev.on ? 1 : 0, String(ev.name || ''), String(ev.brand || ''), String(ev.client || ''), now
  ]);
  if (rows.length) {
    const lock = LockService.getScriptLock(); lock.waitLock(10000);
    try {
      sh.getRange(sh.getLastRow() + 1, 1, rows.length, EVENT_HEADERS.length).setValues(rows);
      rebuildLatest_(String((events[0] && events[0].key) || 'closet'));
    } finally { lock.releaseLock(); }
  }
  return json_({ ok: true, n: rows.length });
}

/** Latest on/off per item and kind, newest timestamp wins. */
function state_(key) {
  const sh = sheet_('events', EVENT_HEADERS);
  const last = sh.getLastRow(); if (last < 2) return {};
  const values = sh.getRange(2, 1, last - 1, EVENT_HEADERS.length).getValues();
  const items = {};
  values.forEach(r => {
    const [ts, , k, item, kind, on] = r;
    if (String(k) !== key) return;
    const it = items[item] = items[item] || {};
    if (!it[kind] || Number(ts) > it[kind].ts) it[kind] = { on: Number(on) ? 1 : 0, ts: Number(ts) };
  });
  return items;
}

/** Human-readable summary sheet: one row per item that has ever been touched. */
function rebuildLatest_(key) {
  const sh = sheet_('events', EVENT_HEADERS);
  const last = sh.getLastRow(); if (last < 2) return;
  const values = sh.getRange(2, 1, last - 1, EVENT_HEADERS.length).getValues();
  const rows = {};
  values.forEach(r => {
    const [ts, , k, item, kind, on, name, brand] = r;
    if (String(k) !== key) return;
    const row = rows[item] = rows[item] || { item: item, name: name, brand: brand, saved: '', passed: '', sTs: 0, pTs: 0, lastTs: 0 };
    if (name) row.name = name; if (brand) row.brand = brand;
    if (kind === 's' && ts > row.sTs) { row.sTs = ts; row.saved = Number(on) ? 'yes' : ''; }
    if (kind === 'p' && ts > row.pTs) { row.pTs = ts; row.passed = Number(on) ? 'yes' : ''; }
    if (ts > row.lastTs) row.lastTs = ts;
  });
  const out = sheet_('latest', ['item', 'brand', 'name', 'status', 'since']);
  out.getRange(2, 1, Math.max(out.getLastRow(), 2), 6).clearContent();
  // Only pieces that are currently saved or marked "not for me". Undone actions drop off this tab
  // (they stay in "events").
  const list = Object.values(rows).filter(r => r.saved || r.passed).sort((a, b) => b.lastTs - a.lastTs)
    .map(r => [r.item, r.brand, r.name, r.saved ? 'saved' : 'not for me', new Date(r.lastTs)]);
  if (list.length) out.getRange(2, 1, list.length, 5).setValues(list);
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
