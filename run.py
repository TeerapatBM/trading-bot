import os
import secrets
import signal
import threading
from pathlib import Path
from bot.engine import Engine
from bot.notify import Telegram
from bot.server import make_server

ROOT = Path(__file__).resolve().parent


def load_env(path):
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main():
    load_env(ROOT / '.env')
    data = Path(os.environ.get('DATA_DIR', str(ROOT / 'data')))
    data.mkdir(parents=True, exist_ok=True)
    # OS file lock prevents a second worker from trading the same state directory.
    lock_file = (data / 'instance.lock').open('a+b')
    lock_file.seek(0)
    lock_file.write(b'0')
    lock_file.flush()
    lock_file.seek(0)
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit('Trading Desk is already running for this DATA_DIR')
    token_file = data / 'dashboard-token.txt'
    token = os.environ.get('DASHBOARD_TOKEN')
    if not token:
        if not token_file.exists():
            token_file.write_text(secrets.token_urlsafe(32), encoding='utf-8')
        token = token_file.read_text(encoding='utf-8').strip()
    if len(token) < 24:
        raise SystemExit('DASHBOARD_TOKEN must have at least 24 characters')
    engine = Engine(data / 'trading.db', notifier=Telegram())
    stop = threading.Event()

    def worker():
        while not stop.is_set():
            try:
                engine.step()
            except Exception as exc:
                engine.fail(exc)
            stop.wait(1)

    host = os.environ.get('BIND_HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '8899'))
    server = make_server(engine, token, host, port)
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()
    print(f'Trading Desk: http://127.0.0.1:{port}')
    print(f'Dashboard key file: {token_file} (or your DASHBOARD_TOKEN environment setting)')
    print('Startup: PAUSED. Existing positions remain monitored. Press Ctrl+C to stop.')

    def shutdown(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    try:
        server.serve_forever(poll_interval=.5)
    finally:
        stop.set()
        worker_thread.join(timeout=15)
        server.server_close()
        if not worker_thread.is_alive():
            engine.close()
        lock_file.close()


if __name__ == '__main__':
    main()
