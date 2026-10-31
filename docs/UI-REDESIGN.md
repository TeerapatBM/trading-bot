# Trading Desk — Horizon UI redesign

Scope: replace dashboard presentation and navigation only. Preserve the existing trading API, engine, configuration fields, account restrictions and order semantics. No account actions or live orders during UI QA.

Reference: https://github.com/horizon-ui/horizon-tailwind-react (MIT). Adapt the palette (#F4F7FE, #4318FF, #2B3674), white sidebar with active marker, 20px rounded cards, DM Sans typography and grid composition to the existing buildless frontend. This is an adaptation, not a React dependency or a PRO template copy. Attribution is in `docs/licenses/Horizon-UI-MIT.md`.

Design: white navigation / pale blue workspace / violet bot control card. Four metric cards, primary market chart, recent execution table and current-position card; strategy and daily-limit summaries beneath. Separate hash views for settings, history, alerts and connection guide. Dark theme and mobile drawer. Thai copy uses local Noto Sans Thai; both fonts self-hosted with OFL notices.

Functional UX: all financial values come from the API; empty states remain honest. Targets show only the selected unit mode in settings. Search navigates sections; history search filters actual displayed trades. Chart window selects 60/240 real samples. Start/pause/flatten use original endpoints; no order calls on load. Save feedback retains unsaved edits on failure. Keyboard navigation, reduced-motion handling, contrast, mobile overflow and authentication are verified in browser QA.

Validation: Chrome browser smoke tests cover route navigation, settings save/rejection, history filtering, CSV download, mocked start/pause/flatten, dark-theme persistence, mobile drawer, connection loss/recovery and session locking. All order mutations are intercepted; no real orders or Telegram messages sent. All five views checked at 320, 390, 768, 1024 and 1440px. Axe WCAG A/AA automated checks found zero violations on all desktop views in both themes, dark mobile views, and both mobile login themes. This is automated coverage, not a claim of comprehensive accessibility conformance.

Use `node .qa/ui-smoke.cjs` and `node .qa/accessibility.cjs` with local preview running on port 8901; dependencies live in `.qa/package.json`. UI screenshots in `docs/preview/` use actual paused synthetic paper state, not historical market performance. Existing backend suite remains 35 passing tests.

Runtime handoff: font files now have explicit static routes in `bot/server.py`. A running pre-redesign process needs one restart to load these routes. Automated restart of the existing localhost:8899 server was blocked by tool policy; that process was left unchanged. UI source changes are complete and verified using a separate local preview.
