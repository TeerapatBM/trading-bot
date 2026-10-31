import dataclasses
import datetime as dt
import json
import math
import random
import sqlite3
import threading
import time
from collections import deque


def thai_day():
    # Fixed offset avoids a tzdata dependency on Windows.
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date().isoformat()


@dataclasses.dataclass
class Config:
    mode: str = 'paper'
    symbol: str = 'EURUSD'
    entry_mode: str = 'continuous'
    target_mode: str = 'fixed'
    capital_thb: float = 1000
    take_profit_thb: float = 10
    stop_loss_thb: float = 10
    take_profit_pct: float = 1
    stop_loss_pct: float = 1
    daily_loss_thb: float = 100
    volume: float = 0.01
    max_spread_points: float = 30
    account_to_thb: float = 0

    @classmethod
    def from_dict(cls, values):
        if not isinstance(values, dict):
            raise ValueError('Settings must be an object')
        fields = {f.name: f for f in dataclasses.fields(cls)}
        if set(values) - set(fields):
            raise ValueError('Unknown setting')
        cfg = cls(**values)
        choices = {'mode': ('paper', 'mt5'), 'entry_mode': ('continuous', 'signal'),
                   'target_mode': ('fixed', 'percent')}
        for key, options in choices.items():
            if getattr(cfg, key) not in options:
                raise ValueError(f'Invalid {key}')
        if not isinstance(cfg.symbol, str) or not 1 <= len(cfg.symbol) <= 64 or not all(c.isalnum() or c in '._#-+' for c in cfg.symbol):
            raise ValueError('Invalid symbol')
        for key in fields.keys() - choices.keys() - {'symbol'}:
            val = getattr(cfg, key)
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
                raise ValueError(f'{key} must be a finite number')
            if val < 0 or (val == 0 and key != 'account_to_thb') or val > 1e9:
                raise ValueError(f'{key} outside allowed range')
        return cfg

    def targets(self):
        if self.target_mode == 'percent':
            return self.capital_thb * self.take_profit_pct / 100, self.capital_thb * self.stop_loss_pct / 100
        return self.take_profit_thb, self.stop_loss_thb


def signal(prices):
    if len(prices) < 50:
        return {'side': 'wait', 'reason': 'รอข้อมูลแท่งปิดอย่างน้อย 50 แท่ง', 'fast': None, 'slow': None}
    def ema(period):
        value = prices[0]
        for p in prices[1:]:
            value += (p - value) * 2 / (period + 1)
        return value
    fast, slow = ema(12), ema(26)
    changes = [abs(b - a) for a, b in zip(prices[-15:-1], prices[-14:])]
    volatility = sum(changes) / len(changes)
    side = 'wait' if abs(fast - slow) < max(volatility * .15, 1e-12) else ('buy' if fast > slow else 'sell')
    return {'side': side, 'reason': f'EMA12 {fast:.5f} / EMA26 {slow:.5f}; volatility {volatility:.5f}',
            'fast': fast, 'slow': slow}


class Engine:
    def __init__(self, path, notifier=None, broker_factory=None):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, time REAL, kind TEXT, message TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS trades (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        row = self.db.execute('SELECT payload FROM state WHERE id=1').fetchone()
        self.state = json.loads(row[0]) if row else {
            'config': dataclasses.asdict(Config()), 'balance': 1000., 'position': None,
            'day': thai_day(), 'day_start_equity': 1000., 'paper_seq': 0,
            'account_identity': None, 'broker_day': None, 'broker_day_start': None,
        }
        self.cfg = Config.from_dict(self.state['config'])
        self.running = False
        self.notifier = notifier
        self.broker_factory = broker_factory
        self.broker = None
        self.prices = deque(maxlen=240)
        self.chart = deque(maxlen=240)
        self.analysis = signal([])
        self.price = 100.
        self.error = None
        self.broker_state = None
        self.last_report = time.time()
        self.started_at = time.time()
        self.last_tick = None
        self.save()

    def save(self):
        self.db.execute('INSERT OR REPLACE INTO state VALUES (1, ?)', (json.dumps(self.state),))
        self.db.commit()

    def event(self, kind, message):
        self.db.execute('INSERT INTO events(time,kind,message) VALUES (?,?,?)', (time.time(), kind, message))
        self.db.commit()
        if self.notifier:
            self.notifier.send(f'[{kind}] {message}')

    def close(self):
        with self.lock:
            self.db.close()

    def configure(self, updates):
        with self.lock:
            if self.running or self.state['position'] or (self.broker_state and self.broker_state['position']):
                raise ValueError('พักบอตและปิดสถานะก่อนเปลี่ยนค่า')
            # A disconnected MT5 session must not permit switching away from unknown exposure.
            if self.cfg.mode == 'mt5':
                self.ensure_broker()
                expected = self.state['account_identity']
                if expected:
                    acc = self.broker.account()
                    if expected != f'{acc.login}@{acc.server}':
                        raise ValueError('MT5 account identity changed; reconnect the original account')
                _, owned = self.broker.positions()
                if owned:
                    raise ValueError('MT5 ยังมีสถานะเปิดอยู่')
            cfg = Config.from_dict({**dataclasses.asdict(self.cfg), **updates})
            if cfg.mode != self.cfg.mode or cfg.symbol != self.cfg.symbol:
                self.prices.clear()
                self.chart.clear()
                self.analysis = signal([])
                self.broker_state = None
            self.cfg = cfg
            self.state['config'] = dataclasses.asdict(cfg)
            self.save()
            self.event('settings', 'บันทึกการตั้งค่าแล้ว')

    def ensure_broker(self):
        if not self.broker:
            if self.broker_factory:
                self.broker = self.broker_factory()
            else:
                from bot.mt5 import MT5Broker
                self.broker = MT5Broker()

    def start(self):
        with self.lock:
            if self.cfg.mode == 'mt5':
                self.ensure_broker()
                self.broker_state = self.broker.poll(self.cfg)
                identity = self.broker_state['identity']
                old = self.state['account_identity']
                if old and old != identity:
                    raise ValueError('MT5 account changed; use a separate data directory for another account')
                self.state['account_identity'] = identity
                if self.state['broker_day'] != thai_day():
                    self.state['broker_day'] = thai_day()
                    self.state['broker_day_start'] = self.broker_state['equity_thb']
            else:
                self.roll_day()
                if self.state['balance'] + self.paper_pnl() <= 0:
                    raise ValueError('ทุนจำลองหมดแล้ว')
            self.check_daily()
            if self.daily_pnl() <= -self.cfg.daily_loss_thb:
                raise ValueError('ถึงขีดจำกัดขาดทุนรายวันแล้ว')
            self.running = True
            self.error = None
            self.save()
            self.event('start', f'เริ่ม {self.cfg.mode}: {self.cfg.symbol}')

    def pause(self):
        with self.lock:
            self.running = False
            self.event('pause', 'พักเปิดออเดอร์ใหม่; ยังเฝ้าสถานะที่เปิดอยู่')

    def flatten(self):
        with self.lock:
            self.running = False
            if self.cfg.mode == 'mt5':
                self.ensure_broker()
                acc = self.broker.account()
                expected = self.state['account_identity']
                if expected and expected != f'{acc.login}@{acc.server}':
                    raise ValueError('MT5 account identity changed; cannot close another account')
                self.broker.flatten(self.cfg)
                self.broker_state = self.broker.poll(self.cfg)
            elif self.state['position']:
                self.paper_close('manual')
            self.event('flatten', 'ส่งคำสั่งปิดสถานะและพักบอตแล้ว')

    def paper_pnl(self):
        p = self.state['position']
        if not p:
            return 0.
        # A synthetic unit has 10 THB P/L per price point at the default volume.
        exit_price = self.price - .02 if p['side'] == 'buy' else self.price + .02
        return (exit_price - p['entry']) * (1 if p['side'] == 'buy' else -1) * self.cfg.volume * 1000

    def paper_close(self, reason):
        p = self.state['position']
        pnl = self.paper_pnl()
        trade = {**p, 'closed_at': time.time(), 'exit': self.price,
                 'pnl_thb': pnl, 'reason': reason, 'mode': 'paper'}
        self.state['balance'] += pnl
        self.state['position'] = None
        self.db.execute('INSERT INTO trades VALUES (?,?)', (trade['id'], json.dumps(trade)))
        self.save()
        self.event('trade', f"ปิด {p['side']} {p['symbol']}: {pnl:+.2f} THB ({reason})")

    def roll_day(self):
        if self.state['day'] != thai_day():
            self.state['day'] = thai_day()
            self.state['day_start_equity'] = self.state['balance'] + self.paper_pnl()
            self.save()

    def daily_pnl(self):
        if self.cfg.mode == 'mt5':
            if not self.broker_state or self.state['broker_day_start'] is None:
                return 0.
            return self.broker_state['equity_thb'] - self.state['broker_day_start']
        return self.state['balance'] + self.paper_pnl() - self.state['day_start_equity']

    def check_daily(self):
        if self.daily_pnl() <= -self.cfg.daily_loss_thb:
            if self.running:
                self.event('limit', 'ถึงขีดจำกัดขาดทุนรายวัน: พักเปิดออเดอร์ใหม่')
            self.running = False
            return False
        if self.cfg.mode == 'paper' and self.state['balance'] + self.paper_pnl() <= 0:
            self.running = False
            return False
        return True

    def record_broker_trades(self, trades):
        for t in trades:
            cur = self.db.execute('INSERT OR IGNORE INTO trades VALUES (?,?)', (t['id'], json.dumps(t)))
            if cur.rowcount and t['closed_at'] >= self.started_at:
                self.event('trade', f"MT5 {t['symbol']}: {t['pnl_thb']:+.2f} THB")
        self.db.commit()

    def step(self, price=None):
        with self.lock:
            if self.cfg.mode == 'mt5':
                self.ensure_broker()
                status = self.broker.poll(self.cfg)
                old_identity = self.state['account_identity']
                if old_identity and status['identity'] != old_identity:
                    raise ValueError('MT5 account identity changed')
                self.broker_state = status
                self.price = status['price']
                self.analysis = signal(status['closes'])
                self.record_broker_trades(status['trades'])
                if self.state['broker_day'] != thai_day():
                    self.state['broker_day'] = thai_day()
                    self.state['broker_day_start'] = status['equity_thb']
                    self.save()
                self.check_daily()
                side = self.analysis['side']
                if self.running and not status['position'] and (side != 'wait' or self.cfg.entry_mode == 'continuous'):
                    self.broker.open(self.cfg, side if side != 'wait' else 'buy')
                    self.broker_state = self.broker.poll(self.cfg)
                    self.event('order', f'MT5 ส่งออเดอร์ {self.cfg.symbol} แล้ว')
            else:
                self.price = price if price is not None else max(1, self.price + random.gauss(0, .13))
                if not math.isfinite(self.price) or self.price <= 0:
                    raise ValueError('Invalid price')
                self.prices.append(self.price)
                self.analysis = signal(list(self.prices))
                self.roll_day()
                if self.state['position']:
                    pnl = self.paper_pnl()
                    tp, sl = self.cfg.targets()
                    if pnl >= tp or pnl <= -sl:
                        self.paper_close('take_profit' if pnl >= tp else 'stop_loss')
                self.check_daily()
                if self.running and not self.state['position']:
                    side = self.analysis['side']
                    if side != 'wait' or self.cfg.entry_mode == 'continuous':
                        side = side if side != 'wait' else 'buy'
                        self.state['paper_seq'] += 1
                        self.state['position'] = {
                            'id': f"paper-{self.state['paper_seq']}", 'symbol': self.cfg.symbol,
                            'side': side, 'entry': self.price + (.02 if side == 'buy' else -.02),
                            'opened_at': time.time(), 'volume': self.cfg.volume,
                        }
                        self.event('order', f'จำลองเปิด {side} {self.cfg.symbol}')
                self.save()
            self.last_tick = time.time()
            self.chart.append({'time': self.last_tick, 'price': self.price})
            if time.time() - self.last_report > 3600:
                self.event('report', f'{self.cfg.mode} | วันนี้ {self.daily_pnl():+.2f} THB | ทำงาน {self.running}')
                self.last_report = time.time()

    def fail(self, exc):
        with self.lock:
            self.running = False
            message = str(exc)
            if message != self.error:
                self.event('error', message)
            self.error = message

    def snapshot(self):
        with self.lock:
            position = self.state['position']
            balance = self.state['balance']
            equity = balance + self.paper_pnl()
            if position:
                position = {**position, 'pnl_thb': self.paper_pnl()}
            if self.cfg.mode == 'mt5':
                position = self.broker_state['position'] if self.broker_state else None
                balance = self.broker_state['balance_thb'] if self.broker_state else None
                equity = self.broker_state['equity_thb'] if self.broker_state else None
            trades = [json.loads(r[0]) for r in self.db.execute(
                "SELECT payload FROM trades WHERE json_extract(payload, '$.mode')=? ORDER BY rowid DESC LIMIT 100", (self.cfg.mode,))]
            events = [dict(zip(('time', 'kind', 'message'), r)) for r in self.db.execute('SELECT time,kind,message FROM events ORDER BY id DESC LIMIT 50')]
            return {'config': dataclasses.asdict(self.cfg), 'running': self.running, 'balance': balance,
                    'equity': equity, 'daily_pnl': self.daily_pnl(), 'position': position,
                    'analysis': self.analysis, 'chart': list(self.chart), 'trades': trades,
                    'events': events, 'error': self.error, 'last_tick': self.last_tick,
                    'account': self.broker_state.get('account') if self.broker_state else None,
                    'alerts': self.notifier.status() if self.notifier else {'configured': False},
                    'targets': self.cfg.targets()}
