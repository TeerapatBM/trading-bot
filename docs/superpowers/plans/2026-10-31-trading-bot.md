# Trading bot implementation plan

Goal: unattended single-position trading with a Thai web dashboard, Telegram and an XM MT5 adapter.
Architecture: Python standard-library HTTP server, SQLite state/journal, serialized engine thread, optional official MetaTrader5 package. Local workspace deployment; no hosted Sites deployment because the user will provide a server.
User requests immediate execution and delegates design choices; implement inline.

- [x] Test configuration validation, paper execution including spread, thresholds, pause versus flatten, restart recovery, daily limits and signal warmup.
- [x] Implement engine, persistent state and notifications. Paper quotes are synthetic and explicitly labeled. Never claim profitability from simulation.
- [x] Implement MT5 adapter with broker-side SL/TP, authoritative position reconciliation, account identity pinning, fresh quotes, volume/margin/stops validation, ambiguous-send halt. No automatic order retries.
- [x] Implement authenticated dashboard, controls, settings, trade history and price chart; responsive white/navy/blue control-room design, clear Thai labels and system fonts.
- [x] Test HTTP authentication and validation, broker failure cases. 35 tests pass. Browser QA attempted via CUA and Windows sky; both unavailable due to missing kernel assets. HTTP page/assets/control smoke checks pass; visual verification remains pending.
- [x] Write detailed Thai MT5, Telegram and Windows VPS instructions and startup scripts.

Review rulings: keep deployment local to the user's selected workspace and future Windows VPS. No external hosting, account login or real orders performed. Start paused after restart; unattended operations require a logged-in MT5 session. Native review performed inline; no delegated agents. Port 8765 is denied by Windows here, verified port 8899 and set it as default. Regression tests exposed and resolved conversion settings deadlock, account-switch flatten hazard and paper bankruptcy entry. Historical MT5 trades import silently; only newly closed positions trigger alerts.

Review focus: stale quotes; rejected/ambiguous broker orders; other account positions; THB conversion versus account currency; restart with open trade. Start paused after process restart, keep monitoring existing positions.
