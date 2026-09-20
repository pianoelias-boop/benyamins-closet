"""Local stand-in for the Apps Script endpoint, for testing the sync client. Same JSON contract."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from closet_config import load as _load_cfg
DEFAULT_KEY = _load_cfg().get('notebookKey') or 'closet'   # the key the site sends is in config.js
from http.server import BaseHTTPRequestHandler, HTTPServer
EVENTS = []
def state(key):
    items = {}
    for ev in EVENTS:
        if ev.get('key') != key: continue
        it = items.setdefault(str(ev['item']), {})
        if ev['kind'] not in it or ev['ts'] > it[ev['kind']]['ts']:
            it[ev['kind']] = {'on': 1 if ev['on'] else 0, 'ts': ev['ts']}
    return items
class H(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query); key = (q.get('key') or [DEFAULT_KEY])[0]
        if urlparse(self.path).path == '/dump': return self._send({'events': EVENTS})
        self._send({'ok': True, 'key': key, 'items': state(key)})
    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0); body = json.loads(self.rfile.read(n) or b'{}')
        evs = body if isinstance(body, list) else body.get('events', [body])
        EVENTS.extend(evs); self._send({'ok': True, 'n': len(evs)})
    def log_message(self, *a): pass
HTTPServer(('127.0.0.1', int(sys.argv[1]) if len(sys.argv) > 1 else 8769), H).serve_forever()
