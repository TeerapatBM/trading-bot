import tempfile
import unittest
from pathlib import Path
from bot.engine import Config, Engine, signal


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = Engine(Path(self.tmp.name) / 'test.db')

    def tearDown(self):
        self.engine.close()
        self.tmp.cleanup()

    def test_defaults_match_ten_baht_targets(self):
        self.assertEqual(Config().take_profit_thb, 10)
        self.assertEqual(Config().stop_loss_thb, 10)

    def test_reject_bad_settings(self):
        for value in [-1, 0, float('nan'), float('inf'), True, '10']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                Config.from_dict({'stop_loss_thb': value})

    def test_unknown_settings_rejected(self):
        with self.assertRaises(ValueError):
            Config.from_dict({'password': 'bad'})

    def test_signal_requires_warmup(self):
        self.assertEqual(signal([1, 2])['side'], 'wait')

    def test_signal_tracks_trend(self):
        self.assertEqual(signal([1 + i / 1000 for i in range(100)])['side'], 'buy')
        self.assertEqual(signal([2 - i / 1000 for i in range(100)])['side'], 'sell')

    def test_paper_enters_with_spread_cost(self):
        self.engine.start()
        self.engine.step(100)
        state = self.engine.snapshot()
        self.assertEqual(state['position']['side'], 'buy')
        self.assertLess(state['position']['pnl_thb'], 0)

    def test_profit_closes_and_reopens_same_step(self):
        self.engine.start()
        self.engine.step(100)
        self.engine.step(102)
        state = self.engine.snapshot()
        self.assertEqual(len(state['trades']), 1)
        self.assertGreaterEqual(state['trades'][0]['pnl_thb'], 10)
        self.assertIsNotNone(state['position'])

    def test_loss_closes_and_reopens(self):
        self.engine.start()
        self.engine.step(100)
        self.engine.step(98)
        state = self.engine.snapshot()
        self.assertLessEqual(state['trades'][0]['pnl_thb'], -10)
        self.assertIsNotNone(state['position'])

    def test_pause_does_not_abandon_threshold_monitoring(self):
        self.engine.start()
        self.engine.step(100)
        self.engine.pause()
        self.engine.step(102)
        self.assertIsNone(self.engine.snapshot()['position'])
        self.assertEqual(len(self.engine.snapshot()['trades']), 1)

    def test_restart_keeps_position_but_pauses_entries(self):
        self.engine.start()
        self.engine.step(100)
        self.engine.close()
        self.engine = Engine(Path(self.tmp.name) / 'test.db')
        self.assertIsNotNone(self.engine.snapshot()['position'])
        self.assertFalse(self.engine.snapshot()['running'])

    def test_cannot_change_settings_with_open_position(self):
        self.engine.start()
        self.engine.step(100)
        with self.assertRaises(ValueError):
            self.engine.configure({'symbol': 'XAUUSD'})

    def test_daily_loss_limit_stops_new_entries(self):
        self.engine.configure({'daily_loss_thb': 15})
        self.engine.start()
        self.engine.step(100)
        self.engine.step(90)
        state = self.engine.snapshot()
        self.assertFalse(state['running'])
        self.assertIsNone(state['position'])

    def test_flatten_pauses_and_closes(self):
        self.engine.start()
        self.engine.step(100)
        self.engine.flatten()
        self.assertFalse(self.engine.snapshot()['running'])
        self.assertIsNone(self.engine.snapshot()['position'])

    def test_strategy_wait_does_not_force_entry(self):
        self.engine.configure({'entry_mode': 'signal'})
        self.engine.start()
        self.engine.step(100)
        self.assertIsNone(self.engine.snapshot()['position'])

    def test_percent_mode_uses_allocated_capital(self):
        cfg = Config.from_dict({'target_mode': 'percent', 'capital_thb': 2000})
        self.assertEqual(cfg.targets(), (20, 20))

    def test_no_entries_when_paper_balance_exhausted(self):
        self.engine.state['balance'] = -1
        self.engine.state['day_start_equity'] = -1
        with self.assertRaises(ValueError):
            self.engine.start()

    def test_mt5_settings_can_fix_missing_conversion_without_poll(self):
        class Broker:
            def positions(self):
                return [], []
        self.engine.cfg = Config(mode='mt5')
        self.engine.broker = Broker()
        self.engine.configure({'account_to_thb': 35})
        self.assertEqual(self.engine.cfg.account_to_thb, 35)

    def test_account_switch_prevents_flatten(self):
        class Broker:
            def account(self):
                from types import SimpleNamespace
                return SimpleNamespace(login=222, server='new')
            def flatten(self, cfg):
                raise AssertionError('Must not close trades on another account')
        self.engine.cfg = Config(mode='mt5')
        self.engine.broker = Broker()
        self.engine.state['account_identity'] = '111@old'
        with self.assertRaises(ValueError):
            self.engine.flatten()

if __name__ == '__main__':
    unittest.main()
