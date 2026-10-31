import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

WEB = Path(__file__).resolve().parent.parent / 'web'


def make_server(engine, token, host='127.0.0.1', port=8765):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, value, mime='application/json; charset=utf-8'):
            data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(data)

        def authenticated(self):
            # No query-string tokens or cookies, hence cross-site forms cannot authorize mutations.
            actual = self.headers.get('Authorization', '').encode()
            return hmac.compare_digest(actual, ('Bearer ' + token).encode())

        def do_GET(self):
            path = urlsplit(self.path).path
            if path.startswith('/api/'):
                if not self.authenticated():
                    return self.reply(401, {'error': 'รหัสเข้าใช้งานไม่ถูกต้อง'})
                if path == '/api/state':
                    return self.reply(200, engine.snapshot())
                if path == '/api/symbols':
                    try:
                        with engine.lock:
                            if engine.cfg.mode == 'mt5':
                                engine.ensure_broker()
                                symbols = engine.broker.mt.symbols_get()
                                if symbols is None:
                                    raise ValueError('อ่านรายการสินทรัพย์ไม่ได้')
                                items = [{'name': s.name, 'description': s.description, 'path': s.path} for s in symbols]
                            else:
                                items = [{'name': n, 'description': 'Synthetic paper market', 'path': 'จำลอง'} for n in ('EURUSD', 'XAUUSD', 'US500', 'AAPL')]
                        return self.reply(200, items)
                    except Exception as exc:
                        return self.reply(400, {'error': str(exc)})
                return self.reply(404, {'error': 'Not found'})
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                     '/style.css': ('style.css', 'text/css; charset=utf-8'),
                     '/assets/dm-sans.ttf': ('assets/dm-sans.ttf', 'font/ttf'),
                     '/assets/noto-sans-thai.ttf': ('assets/noto-sans-thai.ttf', 'font/ttf')}
            if path not in files:
                return self.reply(404, {'error': 'Not found'})
            name, mime = files[path]
            return self.reply(200, (WEB / name).read_bytes(), mime)

        def do_POST(self):
            if not self.authenticated():
                return self.reply(401, {'error': 'รหัสเข้าใช้งานไม่ถูกต้อง'})
            path = urlsplit(self.path).path
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 16384:
                    raise ValueError('Invalid request size')
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError('Expected JSON object')
                if path == '/api/settings':
                    engine.configure(payload)
                elif path == '/api/start':
                    engine.start()
                elif path == '/api/pause':
                    engine.pause()
                elif path == '/api/flatten':
                    engine.flatten()
                elif path == '/api/test-alert':
                    if not engine.notifier or not engine.notifier.status()['configured']:
                        raise ValueError('ตั้ง TELEGRAM_BOT_TOKEN และ TELEGRAM_CHAT_ID ใน .env แล้วรีสตาร์ตก่อน')
                    with engine.lock:
                        engine.event('test', 'Trading Desk: ทดสอบการแจ้งเตือน Telegram')
                else:
                    return self.reply(404, {'error': 'Not found'})
                return self.reply(200, engine.snapshot())
            except (ValueError, UnicodeError) as exc:
                return self.reply(400, {'error': str(exc)})
            except Exception as exc:
                engine.fail(exc)
                return self.reply(503, {'error': str(exc)})

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server
