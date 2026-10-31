"""Official MT5 terminal adapter. No broker password is stored by this app."""
import datetime as dt
import math
import os
import time

MAGIC = 310026


class MT5Broker:
    def __init__(self):
        try:
            import MetaTrader5 as mt
        except ImportError as exc:
            raise ValueError('ติดตั้ง MetaTrader5 ก่อน: .venv\\Scripts\\python -m pip install MetaTrader5') from exc
        self.mt = mt
        path = os.environ.get('MT5_PATH')
        ok = mt.initialize(path) if path else mt.initialize()
        if not ok:
            raise ValueError(f'เชื่อม MT5 ไม่สำเร็จ: {mt.last_error()}')

    def validate_account(self, account):
        if account.trade_mode == self.mt.ACCOUNT_TRADE_MODE_REAL and os.environ.get('ALLOW_LIVE_TRADING', '').lower() != 'true':
            raise ValueError('บัญชีเงินจริง: ตั้ง ALLOW_LIVE_TRADING=true ใน .env ก่อนใช้งาน')

    def conversion(self, cfg, account):
        if account.currency == 'THB':
            return 1.
        if cfg.account_to_thb <= 0:
            raise ValueError(f'กรอกอัตรา 1 {account.currency} เท่ากับกี่ THB ในการตั้งค่า (บัญชี cent ต้องใช้อัตราต่อ cent)')
        return cfg.account_to_thb

    def account(self):
        terminal = self.mt.terminal_info()
        acc = self.mt.account_info()
        if not terminal or not terminal.connected or not acc:
            raise ValueError('MT5 ไม่ได้เชื่อมต่อ: เปิด terminal และล็อกอินใหม่')
        return acc

    def positions(self):
        positions = self.mt.positions_get()
        orders = self.mt.orders_get()
        if positions is None or orders is None:
            raise ValueError('อ่านสถานะ MT5 ไม่สำเร็จ; หยุดเพื่อป้องกันส่งออเดอร์ซ้ำ')
        owned = [p for p in positions if p.magic == MAGIC]
        if len(owned) > 1:
            raise ValueError('พบมากกว่า 1 สถานะของบอต: จัดการใน MT5 ก่อน')
        if any(o.magic == MAGIC for o in orders):
            raise ValueError('มีคำสั่งค้างของบอต: ตรวจ MT5 ก่อนเริ่มใหม่')
        return positions, owned

    def quote(self, symbol):
        if not self.mt.symbol_select(symbol, True):
            raise ValueError(f'ไม่พบ {symbol}; ใช้ชื่อเต็มตาม Market Watch ของ XM')
        info = self.mt.symbol_info(symbol)
        tick = self.mt.symbol_info_tick(symbol)
        if not info or not tick or tick.bid <= 0 or tick.ask <= tick.bid or time.time() - tick.time > 30:
            raise ValueError('ราคาไม่พร้อมหรือเก่ากว่า 30 วินาที (ตลาดอาจปิด)')
        return info, tick

    def poll(self, cfg):
        acc = self.account()
        factor = self.conversion(cfg, acc)
        all_positions, owned = self.positions()
        info, tick = self.quote(cfg.symbol)
        rates = self.mt.copy_rates_from_pos(cfg.symbol, self.mt.TIMEFRAME_M1, 1, 120)
        if rates is None or len(rates) < 50:
            raise ValueError('รอข้อมูลแท่ง M1 ที่ปิดแล้วอย่างน้อย 50 แท่งใน MT5')
        p = owned[0] if owned else None
        if p and p.symbol != cfg.symbol:
            raise ValueError(f'บอตมีสถานะ {p.symbol}; ตั้ง symbol ให้ตรงก่อน')
        position = None if not p else {'id': str(p.ticket), 'symbol': p.symbol,
            'side': 'buy' if p.type == self.mt.POSITION_TYPE_BUY else 'sell',
            'entry': p.price_open, 'volume': p.volume, 'pnl_thb': (p.profit + p.swap) * factor,
            'opened_at': p.time, 'sl': p.sl, 'tp': p.tp}
        if p and (p.sl <= 0 or p.tp <= 0):
            raise ValueError('สถานะของบอตไม่มี SL/TP: ตรวจและปิด/แก้ใน MT5 ก่อน')
        # History is authoritative. Aggregate entry commissions plus exit deals;
        # only journal a position once it is completely closed.
        deals = self.mt.history_deals_get(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30), dt.datetime.now(dt.timezone.utc))
        if deals is None:
            raise ValueError('อ่านประวัติ MT5 ไม่สำเร็จ')
        ids = {d.position_id for d in deals if d.magic == MAGIC}
        groups = {pid: [] for pid in ids}
        for deal in deals:
            if deal.position_id in groups:
                groups[deal.position_id].append(deal)
        open_ids = {p.identifier for p in all_positions}
        trades = []
        for pid, group in groups.items():
            exits = [d for d in group if d.entry in (self.mt.DEAL_ENTRY_OUT, self.mt.DEAL_ENTRY_OUT_BY)]
            entries = [d for d in group if d.entry == self.mt.DEAL_ENTRY_IN]
            if pid in open_ids or not exits or not entries:
                continue
            last = max(exits, key=lambda d: d.time_msc)
            first = min(group, key=lambda d: d.time_msc)
            trades.append({'id': f'mt5-{acc.login}-{acc.server}-{pid}', 'mode': 'mt5',
                'symbol': last.symbol, 'side': 'buy' if first.type == self.mt.DEAL_TYPE_BUY else 'sell',
                'entry': first.price, 'exit': last.price, 'volume': first.volume,
                'opened_at': first.time, 'closed_at': last.time,
                'pnl_thb': sum(d.profit + d.commission + d.swap + d.fee for d in group) * factor,
                'reason': 'broker', 'conversion': factor})
        return {'identity': f'{acc.login}@{acc.server}',
            'account': {'login': acc.login, 'server': acc.server, 'currency': acc.currency,
                        'real': acc.trade_mode == self.mt.ACCOUNT_TRADE_MODE_REAL,
                        'conversion': factor},
            'balance_thb': acc.balance * factor, 'equity_thb': acc.equity * factor,
            'position': position, 'price': (tick.ask + tick.bid) / 2,
            'closes': [float(r['close']) for r in rates], 'trades': trades}

    def levels(self, cfg, info, side, entry, factor):
        action = self.mt.ORDER_TYPE_BUY if side == 'buy' else self.mt.ORDER_TYPE_SELL
        step = info.trade_tick_size or info.point
        unit = self.mt.order_calc_profit(action, cfg.symbol, cfg.volume, entry,
                                         entry + (step if side == 'buy' else -step))
        if unit is None or not math.isfinite(unit) or unit <= 0:
            raise ValueError('คำนวณมูลค่า tick ไม่สำเร็จ')
        tp_money, sl_money = cfg.targets()
        tp_distance = tp_money / (unit * factor) * step
        sl_distance = sl_money / (unit * factor) * step
        minimum = max(info.trade_stops_level * info.point, step)
        if min(tp_distance, sl_distance) < minimum:
            raise ValueError('เป้าเงินเล็กกว่าระยะ SL/TP ขั้นต่ำ: ลด lot หรือเพิ่มเป้าเอง')
        direction = 1 if side == 'buy' else -1
        sl = round(round((entry - direction * sl_distance) / step) * step, info.digits)
        tp = round(round((entry + direction * tp_distance) / step) * step, info.digits)
        return sl, tp

    def filling(self, info):
        # SYMBOL_FILLING_IOC=2, SYMBOL_FILLING_FOK=1. RETURN is unsupported for market execution.
        if info.filling_mode & 2:
            return self.mt.ORDER_FILLING_IOC
        if info.filling_mode & 1:
            return self.mt.ORDER_FILLING_FOK
        return self.mt.ORDER_FILLING_RETURN

    def send_once(self, request):
        check = self.mt.order_check(request)
        if check is None or check.retcode != 0:
            raise ValueError(f'MT5 order_check rejected: {check.comment if check else self.mt.last_error()}')
        result = self.mt.order_send(request)
        if result is None or result.retcode != self.mt.TRADE_RETCODE_DONE:
            raise ValueError(f'MT5 ส่งคำสั่งไม่สำเร็จ/ไม่ชัดเจน ({result.retcode if result else "no result"}); ตรวจ terminal ก่อนกดเริ่มใหม่ ไม่มีการส่งซ้ำอัตโนมัติ')
        return result

    def open(self, cfg, side):
        acc = self.account()
        self.validate_account(acc)
        terminal = self.mt.terminal_info()
        if not terminal.trade_allowed or terminal.tradeapi_disabled or not acc.trade_allowed or not acc.trade_expert:
            raise ValueError('เปิด Algo Trading และอนุญาต external Python API ใน MT5 ก่อน')
        positions, owned = self.positions()
        orders = self.mt.orders_get(symbol=cfg.symbol)
        if orders is None or orders or owned or any(p.symbol == cfg.symbol for p in positions):
            raise ValueError('มีสถานะหรือคำสั่งค้างใน symbol นี้แล้ว; ใช้บัญชีแยกสำหรับบอต')
        info, tick = self.quote(cfg.symbol)
        if (tick.ask - tick.bid) / info.point > cfg.max_spread_points:
            raise ValueError('Spread สูงกว่าเพดาน: พักเปิดคำสั่งใหม่')
        if not info.volume_min <= cfg.volume <= info.volume_max or abs(cfg.volume / info.volume_step - round(cfg.volume / info.volume_step)) > 1e-7:
            raise ValueError(f'lot ไม่ถูกต้อง: min={info.volume_min}, step={info.volume_step}, max={info.volume_max}')
        factor = self.conversion(cfg, acc)
        entry = tick.ask if side == 'buy' else tick.bid
        sl, tp = self.levels(cfg, info, side, entry, factor)
        # A stop loss must also clear the spread measured from the closing quote.
        closing = tick.bid if side == 'buy' else tick.ask
        minimum = max(info.trade_stops_level * info.point, info.trade_tick_size or info.point)
        if (closing - sl if side == 'buy' else sl - closing) < minimum:
            raise ValueError('SL เล็กกว่า spread + ระยะขั้นต่ำ; ลด lot หรือเพิ่มเป้า')
        action = self.mt.ORDER_TYPE_BUY if side == 'buy' else self.mt.ORDER_TYPE_SELL
        margin = self.mt.order_calc_margin(action, cfg.symbol, cfg.volume, entry)
        if margin is None or margin > acc.margin_free:
            raise ValueError('Free margin ไม่เพียงพอ')
        self.send_once({'action': self.mt.TRADE_ACTION_DEAL, 'symbol': cfg.symbol,
            'volume': cfg.volume, 'type': action, 'price': entry, 'sl': sl, 'tp': tp,
            'deviation': 10, 'magic': MAGIC, 'comment': 'TradingDesk',
            'type_time': self.mt.ORDER_TIME_GTC, 'type_filling': self.filling(info)})
        _, owned = self.positions()
        if not owned:
            raise ValueError('ส่งสำเร็จแต่ไม่พบสถานะ: ตรวจประวัติใน MT5 ก่อนเริ่มใหม่')

    def flatten(self, cfg):
        # Closing exposure remains possible even if opening live trading is disabled.
        self.account()
        _, owned = self.positions()
        for p in owned:
            info, tick = self.quote(p.symbol)
            buy = p.type != self.mt.POSITION_TYPE_BUY
            self.send_once({'action': self.mt.TRADE_ACTION_DEAL, 'position': p.ticket,
                'symbol': p.symbol, 'volume': p.volume,
                'type': self.mt.ORDER_TYPE_BUY if buy else self.mt.ORDER_TYPE_SELL,
                'price': tick.ask if buy else tick.bid, 'deviation': 10, 'magic': MAGIC,
                'comment': 'TradingDesk close', 'type_time': self.mt.ORDER_TIME_GTC,
                'type_filling': self.filling(info)})
