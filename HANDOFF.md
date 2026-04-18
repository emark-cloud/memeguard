# FourScout — Project Handoff Document

> Last updated: 2026-04-18
> Purpose: Everything a new Claude instance needs to continue building this project.

---

## 1. What Is This Project?

FourScout is a **persona-based AI trading agent** for the **Four.meme** memecoin launchpad on **BNB Chain (BSC)**. It scans new token launches, scores risk using 8 deterministic signals, explains findings via Google Gemini, and executes trades within user-approved limits.

Built for the **Four.Meme AI Sprint hackathon** on DoraHacks ($50K prize pool).

**GitHub:** https://github.com/emark-cloud/fourscout

---

## 2. About the User

- Full-stack developer with Web3 experience (Python/FastAPI, React, Web3/blockchain)
- Building solo with Claude Code as co-pilot
- Has a BSC wallet funded with BNB for testing (PRIVATE_KEY in root `.env`)
- Has GEMINI_API_KEY configured in root `.env`
- **Preference:** Don't emphasize deadlines or time pressure when planning. Frame by impact and quality, not urgency. The user sets their own pace.
- **Preference:** Don't add yourself as a contributor in commits (no Co-Authored-By line)

---

## 3. Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python FastAPI + SQLite + Web3.py |
| Frontend | React + Vite + Tailwind CSS (Binance-inspired dark theme) |
| LLM | Google Gemini 2.5 Flash (`google-genai` SDK) |
| On-chain reads | Web3.py (direct contract calls for risk scoring) |
| Trading | Four.meme CLI (`@four-meme/four-meme-ai`) via subprocess |
| Wallet | wagmi + viem (frontend BSC wallet connection) |
| Deploy target | Vercel (frontend) + Railway / Docker self-host (backend) |
| Future AA | ZeroDev Kernel v3 + `@zerodev/permissions` session keys + Pimlico bundler (see FourScout.md §18) |

---

## 4. Hackathon Judging Criteria

Expert review (70%) + Community voting (30%):
- **Innovation** (30% of expert) — originality and depth of AI application
- **Technical Implementation** (30% of expert) — code quality and demo stability
- **Practical Value** (20% of expert) — user impact or commercial potential
- **Presentation** (20% of expert) — clarity of pitch and execution capability

---

## 5. Project Structure

```
meme-guard/
├── backend/
│   ├── main.py                  # FastAPI app + WebSocket + lifespan (scanner + position tracker tasks)
│   ├── config.py                # Pydantic Settings from .env (loads .env then ../.env)
│   ├── database.py              # SQLite schema + async queries + DEFAULT_CONFIG
│   ├── clients/
│   │   ├── fourmeme_cli.py      # Async subprocess wrapper for @four-meme/four-meme-ai CLI
│   │   ├── fourmeme_api.py      # Four.meme REST API client (httpx)
│   │   ├── bsc_web3.py          # Web3.py direct contract reads (holders, creator, bonding curve)
│   │   └── market_api.py        # CoinGecko + Fear & Greed
│   ├── services/
│   │   ├── scanner.py           # Token discovery (30s API polling + parallel scoring)
│   │   ├── risk_engine.py       # 8-signal deterministic scoring + auto-propose pipeline
│   │   ├── persona_engine.py    # 3 personas → action mapping (default 0.0001 BNB per trade)
│   │   ├── llm_service.py       # Gemini: rationale, narrative synthesis, AMBER deep analysis, position exit analysis
│   │   ├── chat_service.py      # Interactive AI advisor (context-aware conversational chat)
│   │   ├── tx_builder.py        # Quote preview preparation (buy/sell)
│   │   ├── executor.py          # Trade execution via CLI (buy + sell with slippage protection)
│   │   ├── approval_gate.py     # 4 approval modes (approve_each, per_session, budget_threshold, monitor_only)
│   │   ├── position_tracker.py  # PnL tracking + per-position AI cooldown + auto-sell
│   │   ├── avoided_tracker.py   # "What I Avoided" background checker (live — 39+ flagged)
│   │   ├── agent_identity.py    # ERC-8004 registration (live)
│   │   ├── override_stats.py    # Phase 3.5 — override pattern aggregates → persona nudge line
│   │   ├── creator_reputation.py # Phase 3.5 — cached creator score with outcome feedback (60-min TTL)
│   │   └── signal_outcomes.py   # Phase 3.5 — per-token outcome rows + historical summary for rationale
│   ├── routes/
│   │   ├── tokens.py            # GET /api/tokens, GET /api/tokens/:address
│   │   ├── actions.py           # GET /api/actions/pending, POST /api/actions/approve, POST /api/actions/reject
│   │   ├── positions.py         # GET /api/positions, GET /api/trades/daily
│   │   ├── config_routes.py     # GET /api/config, PUT /api/config, PUT /api/config/bulk
│   │   ├── activity.py          # GET /api/activity
│   │   ├── avoided.py           # GET /api/avoided
│   │   ├── watchlist.py         # GET/POST/DELETE /api/watchlist
│   │   ├── agent.py             # ERC-8004 identity endpoints
│   │   └── chat.py              # POST /api/chat, GET/DELETE /api/chat/history (Phase 3.5: scoped by token_address + scope=current|all)
│   ├── abis/                    # Contract ABIs (JSON, lite versions)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # 7 routes + WagmiProvider + NotificationProvider + useWebSocket
│   │   ├── pages/
│   │   │   ├── Landing.jsx      # Public marketing page at / (Scan → Score → Decide → Track)
│   │   │   ├── Dashboard.jsx    # Live token feed + persona badge + budget bar + stats (at /dashboard)
│   │   │   ├── OpportunityDetail.jsx  # 8-signal breakdown + rationale + approve/reject + ChatPanel + RiskRadar
│   │   │   ├── Positions.jsx    # Active/closed positions with PnL
│   │   │   ├── Avoided.jsx      # Avoided rugs stats + cards
│   │   │   ├── Activity.jsx     # Event feed (polls every 10s)
│   │   │   └── Settings.jsx     # Persona + approval mode + exit strategy + budget caps
│   │   ├── components/
│   │   │   ├── TokenCard.jsx
│   │   │   ├── RiskBadge.jsx
│   │   │   ├── RiskRadar.jsx    # 8-signal radar chart visualization
│   │   │   ├── PersonaSelector.jsx
│   │   │   ├── BudgetBar.jsx
│   │   │   ├── ChatPanel.jsx    # Floating AI chat (global + token-scoped)
│   │   │   ├── ToastNotifications.jsx  # Real-time toast alerts from WebSocket events
│   │   │   ├── NotificationBell.jsx    # Navbar bell with notification history dropdown
│   │   │   └── Navbar.jsx
│   │   ├── hooks/
│   │   │   ├── useWallet.js     # wagmi BSC config
│   │   │   └── useWebSocket.js  # Auto-reconnecting WS hook
│   │   └── services/api.js      # Backend REST client
│   ├── package.json
│   └── vite.config.js
├── fourmeme-cli/                # Local npm install of @four-meme/four-meme-ai
├── FourScout.md                 # Full MVP specification (features, flows, architecture, demo script, §18 session-key roadmap)
├── CLAUDE.md                    # Claude Code project instructions
├── TODO.md                      # Build checklist with phase status
├── COMPETITIVE_ANALYSIS.md      # BuildersClaw benchmark analysis
├── HANDOFF.md                   # This file
├── Dockerfile                   # Backend container image
├── docker-compose.yml           # One-command self-host (backend + CLI sidecar)
├── README.md                    # Public README with Docker quickstart
├── .env.example
└── .gitignore
```

---

## 6. Current Status — Phase 3.5 Complete

**Spec rename:** `Memeguard.md` is now `FourScout.md`. A new §18 "Roadmap: Non-Custodial Session Keys" documents the post-hackathon evolution from single-tenant self-hosted (one `PRIVATE_KEY`) to multi-tenant ERC-4337 session keys. Phase 4 in `TODO.md` tracks that scope as design-only — no implementation in the current branch.

**Phase 3 verified + Phase 3.5 complete.** Avoided tracker populating live. Wallet-gated smoke test passed (position_id 4, tx `0x8a9e…dbdb`). Gemini cost-reduction verified live against refreshed key. Phase 3.5 "agent memory & continuity" shipped across seven narrow commits (`1896754..7bcb09a`, A–G) and verified end-to-end via Docker smoketest + Playwright UI pass. Deploy + demo recording are the remaining Phase 3 items.

### COMPLETE (latest commit: `7bcb09a`)

**Buy loop (verified end-to-end with real BNB):**
- Scanner discovers tokens → risk engine scores with 8 signals → persona engine proposes buy → approval gate creates pending_action with CLI quote preview → user approves → executor gets fresh quote with slippage protection → CLI buys on-chain → position recorded with correct token quantity → position tracker monitors PnL every 60s
- Tested: 0.0001 BNB trade executed, tx hash on BSC, position recorded with 17,249 tokens

**Sell flow (implemented, not yet tested):**
- Sell executor with slippage protection (`cli.quote_sell` → `min_funds_wei`)
- Position closure (sets status='closed', exit_price, exit_amount_bnb, pnl_bnb, closed_at)
- Sell trade recorded in trades table
- Broadcasts trade_executed with PnL data

**AI pipeline:**
- Auto-propose pipeline: scanner automatically creates pending buy actions for AMBER/GREEN tokens
- AI chat advisor: context-aware Gemini chat on every page + token-scoped on OpportunityDetail
- Multi-signal narrative synthesis: LLM correlates 8 signals into pattern-detecting narratives
- AMBER escalation: `deep_analyze_amber()` returns lean_buy/lean_skip/watch with confidence
- AI-driven position monitoring: `analyze_position_exit()` runs every `AI_EXIT_INTERVAL_CYCLES` (default 10 min) with drift detection, per-position 15-min cooldown + 3% PnL-delta guard, and a 3-LLM-call-per-cycle cap

**Exit strategy:**
- Configurable take-profit/stop-loss thresholds (config keys: `take_profit_pct`, `stop_loss_pct`, `auto_sell_enabled`)
- Auto-sell mode: automatic sell execution at thresholds without approval (separate from buy approval_mode)
- Exit Strategy settings UI section with take profit %, stop loss %, auto-sell toggle

**Real-time alerting:**
- 7 WebSocket events: new_token, risk_scored, risk_alert, action_proposed, position_update, trade_executed, avoided_update
- Toast notification system: real-time visual alerts for all important WS events (clickable → deep-link to relevant page)
- NotificationBell in Navbar with persistent history dropdown
- Position update toasts filtered to milestones only (50%+, 100%+, -40%+)
- App.jsx restructured: split into App (providers) and AppContent (hooks + NotificationProvider)

**Public surface + cost controls:**
- Landing page at `/` (Scan → Score → Decide → Track four-step flow, closing CTA, GitHub link)
- Dashboard relocated to `/dashboard`; Navbar logo → `/`
- Gemini cost reduction (`f4523b4`): per-position AI cooldown, tighter drift bands, `max_output_tokens` trimmed to realistic caps (200/256/200), chat history window 10→6, TTL-cached config context, orphaned `classify_description()` removed
- Docker self-host: `Dockerfile` + `docker-compose.yml` for one-command deploy

### WHAT NEEDS TO BE TESTED

**Phase 3 — Polish & Demo Features (see TODO.md):**
- [x] ERC-8004 agent identity registration, "What I Avoided" tracker (live, 39+), risk radar chart, behavioral nudge, watchlist UI, real volume signal (wash-trading detection), visual polish, README, landing page
- [x] Wallet-gated smoke test (8004 register + trade approve via MetaMask) — position_id 4, tx `0x8a9e…dbdb`
- [x] Gemini cost-reduction pass (`f4523b4`) + live-LLM verification (2026-04-17, commit `b8ce0a5`)
- [x] Deployment live (2026-04-18): backend on Railway (`https://fourscout-production.up.railway.app`, persistent volume at `/app/data`), frontend on Vercel (`https://four-scout.vercel.app`). CORS + `API_KEY` auth + WSS verified end-to-end.
- [ ] Demo video + DoraHacks BUIDL submission

**Phase 3.5 — Agent Memory & Continuity (COMPLETE, commits `1896754..7bcb09a`):**
Motivated by the Four.meme team AMA guidance on state, continuity, and the `input → reason → act → memory update` loop. Shipped in seven narrow commits (A–G).
- **Persistent interaction memory:** `chat_messages` table (per-token scoped, survives restart) replaces the in-memory list in `chat_service.py`; `pending_actions.rejection_reason` captures *why* users reject; Dashboard surfaces top reject reasons (last 7d) under Override Summary.
- **Closed feedback loops:** override-aware nudge appended to persona-engine rationale (via `services/override_stats.py`); AI exit-check cooldown persisted on the `positions` row (`last_ai_check_at`, `last_ai_pnl_pct`) — restart-storm eliminated.
- **Learning loops:** `creator_reputation` cache table (60-min TTL) with outcome feedback on close + rug confirmation — scoring folds `rugs`, `losing_closes`, `profitable_closes` into the creator signal; `signal_outcomes` tracker paired with backfill migration feeds a one-line historical summary into the rationale on every scan (works in both LLM and deterministic-fallback paths).
- **Verification:** all four demo-visible surfaces verified end-to-end via Docker smoketest + Playwright UI pass on 2026-04-18 (chat persists across `docker restart`; per-token scope isolated; rejection reason surfaces on Dashboard; override nudge appears in rationale).

**Phase 4 — Non-Custodial Session Keys (roadmap only, not started):**
- Design documented in `FourScout.md` §18. Stack: ZeroDev Kernel v3 + `@zerodev/permissions` + Pimlico on BSC. Introduces a Node.js `session-signer/` sidecar alongside `fourmeme-cli/`. Backend would swap CLI-subprocess signing for bundler userOps while keeping read-only CLI commands unchanged. All persona rules, approval modes, and budget caps preserved — session keys are a signing mechanism swap, not a policy rewrite.

---

## 7. Key Architecture Decisions

1. **Deterministic risk scoring** — AI only explains, never decides. Rules engine + weighted signals.
2. **AI depth over breadth** — LLM for interactive advising (chat), narrative synthesis, escalation analysis, position exit analysis. Not just labeling.
3. **Deterministic-first monitoring** — Numeric thresholds every 60s (cheap). AI analysis every `AI_EXIT_INTERVAL_CYCLES` (default 10 min), only when drift triggers fire AND per-position cooldown (15 min / 3% PnL delta) allows. Max 3 LLM calls per cycle.
4. **Human in the loop** — All trades require approval (4 modes with varying autonomy). Auto-sell is a separate opt-in toggle.
5. **Budget caps are hard limits** — Server-side enforcement, never bypassed.
6. **Hybrid Four.meme integration** — CLI for trading, direct Web3.py for risk data the CLI doesn't expose.
7. **Complete pipelines** — Every flow works end-to-end. No dead ends.

---

## 8. Environment Setup

```bash
# Backend
cd backend && pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Four.meme CLI (already installed)
cd fourmeme-cli && npm install
```

### Required `.env` (in project root):
```env
BSC_RPC_URL=https://bsc-dataseed1.binance.org
PRIVATE_KEY=<hex private key for agent wallet>
GEMINI_API_KEY=<from https://aistudio.google.com/apikey>
DATABASE_PATH=./data/fourscout.db
SCAN_INTERVAL_SECONDS=30
```

The backend `config.py` loads from `backend/.env` first, then falls back to `../.env` (root).

---

## 9. Four.meme Platform Details

- **Chain:** BSC only (chainId 56)
- **Tokens:** 1B supply, bonding curve (~18-24 BNB to graduate), contracts end in `4444`
- **Trading fee:** 1% during bonding (min 0.001 BNB), `minTradingFee` is "0" for standard tokens
- **Minimum trade:** 0.0001 BNB works (tested and verified)
- **CLI quote-buy:** `fourmeme quote-buy <token> <amountWei> [fundsWei]` — for funds-based, pass `0` as amountWei and funds as fundsWei
- **CLI buy:** `fourmeme buy <token> funds <fundsWei> <minAmountWei>` — returns only `{ txHash }` (no price/quantity)
- **CLI sell:** `fourmeme sell <token> <amountWei> [minFundsWei]` — returns only `{ txHash }`
- **Only V2 tokens** (TokenManager2) are supported by the CLI

### Key Contract Addresses (BSC Mainnet)
| Contract | Address |
|----------|---------|
| TokenManager2 | `0x5c952063c7fc8610FFDB798152D69F0B9550762b` |
| TokenManagerHelper3 | `0xF251F83e40a78868FcfA3FA4599Dad6494E46034` |
| AgentIdentifier | `0x09B44A633de9F9EBF6FB9Bdd5b5629d3DD2cef13` |
| PancakeSwap Router V2 | `0x10ED43C718714eb63d5aA57B78B54704E256024E` |
| BRC8004 Identity Registry | `0xfA09B3397fAC75424422C4D28b1729E3D4f659D7` |

---

## 10. Risk Scoring Engine (8 Signals)

| # | Signal | Weight | Data Source |
|---|--------|--------|-------------|
| 1 | Creator history | HIGH (3) | Web3.py: TokenManager2 TokenCreate events |
| 2 | Holder concentration | HIGH (3) | Web3.py: ERC20 balanceOf + Transfer events |
| 3 | Bonding curve velocity | HIGH (3) | Web3.py: TokenManagerHelper3.getTokenInfo() |
| 4 | Liquidity depth & age | MEDIUM (2) | Web3.py: getTokenInfo() funds + liquidityAdded |
| 5 | Tax token flags | MEDIUM (2) | CLI: fourmeme tax-info / Web3.py: TaxToken ABI |
| 6 | Volume consistency | MEDIUM (2) | CLI: fourmeme events (wash-trading detection via trade clustering) |
| 7 | Social signal | LOW (1) | Four.meme API + VADER sentiment |
| 8 | Market context | LOW (1) | CoinGecko + Alternative.me Fear & Greed |

Grades: GREEN (>=65%), AMBER (40-65%), RED (<40%)

---

## 11. Three Personas

| Persona | Default BNB | Min Age | Risk Tolerance | Bonding Only |
|---------|-------------|---------|----------------|--------------|
| Conservative | 0.0001 | 10 min | GREEN only | No |
| Momentum | 0.0001 | 3 min | AMBER if momentum strong | No |
| Sniper | 0.0001 | 0 min | AMBER | Yes |

All defaults set to 0.0001 BNB for testing.

---

## 12. Configuration Keys

| Key | Default | Description |
|-----|---------|-------------|
| persona | momentum | Active trading persona |
| approval_mode | approve_each | Buy approval mode (4 options) |
| max_per_trade_bnb | 0.05 | Max BNB per single trade |
| max_per_day_bnb | 0.3 | Daily spending cap |
| max_active_positions | 3 | Max open positions |
| max_slippage_pct | 5.0 | Slippage tolerance % |
| cooldown_seconds | 60 | Cooldown between trades |
| min_liquidity_usd | 500 | Min token liquidity |
| take_profit_pct | 100 | Take profit threshold % |
| stop_loss_pct | -50 | Stop loss threshold % |
| auto_sell_enabled | false | Auto-execute sells at thresholds |

---

## 13. WebSocket Events

| Event | Source | Data |
|-------|--------|------|
| `new_token` | scanner.py | address, name, symbol, progress |
| `risk_scored` | risk_engine.py | address, grade, percentage, primary_risk |
| `risk_alert` | risk_engine.py | address, old_grade, new_grade, reason |
| `action_proposed` | risk_engine.py / position_tracker.py | token_address, action_type, amount_bnb, rationale |
| `position_update` | position_tracker.py | position_id, token_address, current_price, pnl_bnb |
| `trade_executed` | executor.py | token_address, side, tx_hash, amount_bnb, pnl_bnb |
| `avoided_update` | avoided_tracker.py | token_address, price_change_pct, period |

---

## 14. Known Issues & Gotchas

1. **CLI only returns `{ txHash }`** — after buy/sell, there's no price or quantity in the response. For buys, we use the pre-buy quote's `estimatedAmount`. For sells, we use the pre-sell quote's `estimatedCost`.

2. **quote-buy parameter order** — `fourmeme quote-buy <token> <amountWei> [fundsWei]`. For funds-based (spend X BNB), pass `0` as amountWei and the funds as second arg. We had a bug where funds was passed as amountWei.

3. **Backend .env loading** — `config.py` loads from `[".env", "../.env"]`. The root `.env` has PRIVATE_KEY and GEMINI_API_KEY. The backend directory may not have its own `.env`.

4. **Pyright warnings** — Several `response.text` warnings about potentially None return from Gemini SDK. These are pre-existing and don't cause runtime issues. Also `risk_percentage` unused in persona_engine.py (intentional, kept for potential future use).

5. **Frontend polls** — Dashboard polls every 15s, Activity/Positions every 10s. WebSocket events exist but most pages don't react to them (they poll instead). ToastNotifications + NotificationBell consume WS events directly.

6. **Position #1 in DB** — From the first buy test before we fixed the executor. Has token_quantity=0 and entry_price=0. Was manually closed (status='closed'). Position #2+ are the valid ones with correct data.

7. **Gemini cost changes untested against live LLM** — The `f4523b4` commit shipped per-position cooldown + output-token caps + chat history trim. Needs a refreshed Gemini key to verify end-to-end (see TODO Phase 3). Blocks deploy + demo recording.

---

## 15. Competitive Analysis

Full analysis at `COMPETITIVE_ANALYSIS.md`. Key patterns adopted from BuildersClaw (hackathon winner):
- Multi-stage AI pipeline (not single LLM call) → AI Advisor + narrative synthesis
- On-chain identity verification → ERC-8004 promoted to high priority
- Complete end-to-end pipelines → design principle #7
- Real-time typed events → expanded WebSocket system
- Weighted scoring with transparency → risk visualization (Phase 3)

---

## 16. Git History

```
7bcb09a Phase 3.5-G: signal accuracy tracker feeds rationale
59c0a49 Phase 3.5-F: creator reputation cache with outcome feedback
ed43b34 Phase 3.5-E: persist AI exit-check cooldown on positions row
500cada Phase 3.5-D: override-aware nudge in proposal rationale
f194d16 Phase 3.5-C: capture and surface rejection reasons
a4f94ea Phase 3.5-B: persist chat memory per scope
1896754 Phase 3.5-A: schema foundation for agent memory
4d49355 Input hardening + avoided-tracker slot-matching fix
cb1ec66 Perf polish: DB indexes, lower RPC holder cap, TTL-cache config
2506884 Executor: re-validate budget + abort on empty tx_hash
709f954 Fix async/sync boundary: wrap blocking calls with asyncio.to_thread
0280dc4 Deploy hardening: env-driven CORS + shared-secret auth
b8ce0a5 Mark Phase 3 LLM cost-reduction verification complete
cad4928 Plan Phase 3.5: agent memory & continuity (queued behind verify + deploy)
d484910 Update HANDOFF.md: landing page, cost reduction, wallet test, Phase 3 status
5449098 Update FourScout.md: Docker, landing page, cost-reduction cadence, file structure
f4523b4 Reduce Gemini cost: exit-AI cooldown, tighter drift bands, output caps
10b89e8 Add public marketing landing page at /, move Dashboard to /dashboard
7f3edf7 Trim activity feed, add clickable toasts + notification history
```

**All changes are committed and pushed.** No uncommitted work.

---

## 17. Key Files to Read First

For a new Claude instance, start with these:
1. `CLAUDE.md` — project instructions, architecture, design principles
2. `TODO.md` — what's done and what's next
3. `FourScout.md` — full MVP spec (features, flows, demo script); §18 documents the non-custodial session-key roadmap
4. `backend/services/risk_engine.py` — the core scoring + auto-propose pipeline
5. `backend/services/executor.py` — trade execution (buy + sell)
6. `backend/services/position_tracker.py` — position monitoring + AI exit analysis
7. `frontend/src/App.jsx` — app structure and routing
