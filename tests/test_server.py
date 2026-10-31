import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from bot.engine import Engine
from bot.server import make_server


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = Engine(Path(self.tmp.name) / 'state.db')
        self.server = make_server(self.engine, 'test-token', '127.0.0.1', 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.engine.close()
        self.tmp.cleanup()

    def request(self, path, payload=None, token='test-token'):
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        req = urllib.request.Request(self.url + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        return urllib.request.urlopen(req)

    def test_auth_required(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.request('/api/state', token='wrong')
        self.assertEqual(cm.exception.code, 401)

    def test_state(self):
        with self.request('/api/state') as res:
            self.assertEqual(json.load(res)['config']['mode'], 'paper')

    def test_start_pause(self):
        with self.request('/api/start', {}) as res:
            self.assertTrue(json.load(res)['running'])
        with self.request('/api/pause', {}) as res:
            self.assertFalse(json.load(res)['running'])

    def test_invalid_config_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.request('/api/settings', {'volume': -1})
        self.assertEqual(cm.exception.code, 400)

    def test_static_traversal_not_served(self):
        with self.assertRaises(urllib.error.HTTPError):
            self.request('/../.env')

    def test_malformed_json_returns_400(self):
        req = urllib.request.Request(self.url + '/api/start', data=b'{bad', headers={'Authorization': 'Bearer test-token'})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 400)

if __name__ == '__main__':
    unittest.main()
