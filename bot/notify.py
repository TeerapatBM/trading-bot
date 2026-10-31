import json
import os
import queue
import threading
import urllib.request


class Telegram:
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        self.chat = os.environ.get('TELEGRAM_CHAT_ID', '')
        self.queue = queue.Queue(maxsize=200)
        self.last_error = None
        self.sent = 0
        threading.Thread(target=self.worker, daemon=True).start()

    def status(self):
        return {'configured': bool(self.token and self.chat), 'sent': self.sent, 'error': self.last_error}

    def send(self, message):
        if self.token and self.chat:
            try:
                self.queue.put_nowait(message[:3500])
            except queue.Full:
                self.last_error = 'Telegram queue full; messages dropped'

    def worker(self):
        while True:
            message = self.queue.get()
            try:
                req = urllib.request.Request(f'https://api.telegram.org/bot{self.token}/sendMessage',
                    data=json.dumps({'chat_id': self.chat, 'text': message}).encode(),
                    headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    result = json.load(response)
                    if not result.get('ok'):
                        raise RuntimeError('Telegram rejected message')
                self.sent += 1
                self.last_error = None
            except Exception:
                # Never expose exception URLs: Telegram credentials are in the URL.
                self.last_error = 'ส่ง Telegram ไม่สำเร็จ: ตรวจ token, chat ID และอินเทอร์เน็ต'
            finally:
                self.queue.task_done()
