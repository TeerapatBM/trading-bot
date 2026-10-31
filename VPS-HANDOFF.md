# Trading Desk — continue on the VPS

Read this first when opening a new Codex session on the Windows VPS.

## Objective and authorization

The owner authorizes installation of this Trading Desk project, Python, MetaTrader 5, startup tasks and HTTPS on their Windows Server 2025 VPS. Stay within this deployment scope. The owner will configure and log in to their XM account themselves. Do not create XM accounts, deposit funds, submit real orders or enable live trading as part of deployment.

Target public IP: `119.10.138.141`.
Dashboard domain: `btxm.sysplatsec.dev` (A record observed pointing to that IP on 2026-10-31).
Default application install root: `C:\Trading-bot`.
The extracted release/installer folder may instead be `C:\TradingDesk-Installer`; do not confuse that source folder with the installed app.

## Exact current status

- App source and Horizon UI redesign are implemented. Backend/API tests: 40 passing. UI browser smoke checks: 59 passing. Automated accessibility checks passed for the tested views/themes.
- MT5 connector exists; no XM login or actual broker execution has been verified.
- The developer session could not control Remote Desktop because its computer-use runtime failed with `failed to write kernel assets`. SSH/WinRM were unreachable from that session.
- Therefore **nothing was installed or changed on the target VPS by that session**. Do not assume deployment succeeded.
- A complete release ZIP was prepared with Python 3.13.17 x64, MetaTrader5 5.0.6231 + matching numpy Windows wheels, official MetaQuotes MT5 setup, Caddy 2.11.7 and app source.
- Vendor Python SHA256 and Caddy published SHA512 were checked. Python and MT5 Authenticode signatures were valid. Package payload hashes were verified. The Caddy configuration template passed actual `caddy validate` locally.
- The full installer has not yet been run on Windows Server 2025. Static syntax/config verification is not an installation acceptance test.

## Continue without repeating design work

1. Confirm you are actually running on the target VPS, inspect OS/user and the extracted release directory, and read `docs/VPS-INSTALL-TH.md` and `deploy/install-vps.ps1`.
2. Inspect current listeners on TCP 80, 443 and 8899, existing `TradingDeskProxy` service, `TradingDesk-Worker`/`TradingDesk-MT5` tasks and `C:\Trading-bot`. Do not stop unrelated applications or overwrite existing trading state.
3. From an elevated PowerShell, run `deploy\install-vps.ps1` from the release folder if its preconditions hold. All files in `deploy\SHA256.json` and `vendor\` must be present. The script checks hashes, publisher signatures and port conflicts before installing.
4. Resolve installation failures by inspecting evidence. MT5 `/auto` still needs internet access to download platform components.
5. Verify the local dashboard, authenticated API, correct fresh paper/paused state, startup tasks and Caddy service. Verify valid public HTTPS at `https://btxm.sysplatsec.dev` without disabling TLS verification. Inspect DNS and provider firewall if certificate issuance is pending.
6. Read `C:\Trading-bot\deployment-report.json` and independently confirm its claims. Hand off the actual dashboard URL, local dashboard-key-file location and MT5 login steps. Do not print keys in chat or logs.

## Intended installed behavior

- Python backend binds only to `127.0.0.1:8899`. Caddy exposes HTTPS on 443 and handles certificate issuance/renewal via 80/443.
- Bot and MT5 run in the same interactive Windows user session. Tasks start at user logon, not before any user has logged in after reboot. No stored Administrator password or automatic Windows login.
- Initial mode is `paper`, new entries paused, `ALLOW_LIVE_TRADING=false`. Starting the app never starts trading automatically.
- The owner must log in to XM, enable MT5 Algo Trading/external Python API, select their exact symbol/volume/THB conversion, and explicitly start the bot when ready.
- Telegram credentials are not supplied/configured yet.
- Paper prices are synthetic. Do not describe them as real market data or strategy performance.
- TradingView Lightweight Charts + XM price data was discussed as a future upgrade; it has **not** been implemented. Do not expand deployment into that feature without a new request.

## Helpful files

`README.md`, `docs/SETUP-TH.md`, `docs/VPS-INSTALL-TH.md`, `deploy/install-vps.ps1`, `deploy/run-worker.ps1`, `run.py`, `bot/mt5.py`.

No VPS password or account authentication state is embedded in this handoff or release. Codex login on this machine is performed by the owner using their own account.
