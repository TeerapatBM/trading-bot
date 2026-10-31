import os
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
from bot.engine import Config
from bot.mt5 import MT5Broker


class BrokerTests(unittest.TestCase):
    def broker(self):
        broker = MT5Broker.__new__(MT5Broker)
        broker.mt = NS(ORDER_TYPE_BUY=0, ORDER_TYPE_SELL=1,
                      order_calc_profit=lambda side, sym, vol, entry, end: (end-entry)*(1 if side == 0 else -1)*100000*vol)
        return broker

    def test_money_levels_buy(self):
        broker = self.broker()
        info = NS(trade_tick_size=.00001, point=.00001, trade_stops_level=1, digits=5)
        sl, tp = broker.levels(Config(), info, 'buy', 1.1, 35)
        self.assertLess(sl, 1.1)
        self.assertGreater(tp, 1.1)
        self.assertAlmostEqual((tp-1.1)*1000*35, 10, delta=.36)

    def test_money_levels_sell(self):
        info = NS(trade_tick_size=.00001, point=.00001, trade_stops_level=1, digits=5)
        sl, tp = self.broker().levels(Config(), info, 'sell', 1.1, 35)
        self.assertGreater(sl, 1.1)
        self.assertLess(tp, 1.1)

    def test_too_small_target_rejected_not_widened(self):
        info = NS(trade_tick_size=.00001, point=.00001, trade_stops_level=100, digits=5)
        with self.assertRaises(ValueError):
            self.broker().levels(Config(), info, 'buy', 1.1, 35)

    def test_real_account_requires_local_enable(self):
        b = self.broker()
        b.mt.ACCOUNT_TRADE_MODE_REAL = 2
        with patch.dict(os.environ, {'ALLOW_LIVE_TRADING': 'false'}), self.assertRaises(ValueError):
            b.validate_account(NS(trade_mode=2))

    def test_missing_conversion_rejected(self):
        with self.assertRaises(ValueError):
            self.broker().conversion(Config(), NS(currency='USD'))

    def test_thb_account_needs_no_conversion(self):
        self.assertEqual(self.broker().conversion(Config(), NS(currency='THB')), 1)

    def test_ambiguous_send_is_never_retried(self):
        b = self.broker()
        calls = []
        b.mt.order_check = lambda req: NS(retcode=0)
        b.mt.order_send = lambda req: calls.append(req)
        b.mt.TRADE_RETCODE_DONE = 10009
        with self.assertRaises(ValueError):
            b.send_once({'symbol': 'EURUSD'})
        self.assertEqual(len(calls), 1)

    def test_partial_fill_halts_instead_of_retrying(self):
        b = self.broker()
        calls = []
        b.mt.order_check = lambda req: NS(retcode=0)
        def send(req):
            calls.append(req)
            return NS(retcode=10010)
        b.mt.order_send = send
        b.mt.TRADE_RETCODE_DONE = 10009
        with self.assertRaises(ValueError):
            b.send_once({})
        self.assertEqual(len(calls), 1)

    def test_rejected_order_check_does_not_send(self):
        b = self.broker()
        b.mt.order_check = lambda req: NS(retcode=10019, comment='No money')
        b.mt.order_send = lambda req: self.fail('Rejected order must not be sent')
        with self.assertRaises(ValueError):
            b.send_once({})

    def test_unknown_positions_halts(self):
        b = self.broker()
        b.mt.positions_get = lambda: None
        b.mt.orders_get = lambda: ()
        with self.assertRaises(ValueError):
            b.positions()

    def test_stale_tick_halts(self):
        b = self.broker()
        b.mt.symbol_select = lambda *args: True
        b.mt.symbol_info = lambda *args: NS()
        b.mt.symbol_info_tick = lambda *args: NS(bid=1, ask=1.01, time=0)
        with self.assertRaises(ValueError):
            b.quote('EURUSD')

if __name__ == '__main__':
    unittest.main()
