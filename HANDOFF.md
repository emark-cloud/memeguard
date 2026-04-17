# FourScout — Project Handoff Document

> Last updated: 2026-04-17
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
│   │   ├── position_tracker.py  # PnL tracking + configurable thresholds + AI exit analysis + auto-sell
│   │   ├── avoided_tracker.py   # "What I Avoided" background checker (NOT YET IMPLEMENTED)
│   │   └── agent_identity.py    # ERC-8004 registration (NOT YET IMPLEMENTED)
│   ├── routes/
│   │   ├── tokens.py            # GET /api/tokens, GET /api/tokens/:address
│   │   ├── actions.py           # GET /api/actions/pending, POST /api/actions/approve, POST /api/actions/reject
│   │   ├── positions.py         # GET /api/positions, GET /api/trades/daily
│   │   ├── config_routes.py     # GET /api/config, PUT /api/config, PUT /api/config/bulk
│   │   ├── activity.py          # GET /api/activity
│   │   ├── avoided.py           # GET /api/avoided
│   │   ├── watchlist.py         # GET/POST/DELETE /api/watchlist
│   │   └── chat.py              # POST /api/chat, DELETE /api/chat/history
│   ├── abis/                    # Contract ABIs (JSON, lite versions)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Routes + WagmiProvider + NotificationProvider + useWebSocket
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Live token feed + persona badge + budget bar + stats
│   │   │   ├── OpportunityDetail.jsx  # 8-signal breakdown + rationale + approve/reject + ChatPanel
│   │   │   ├── Positions.jsx    # Active/closed positions with PnL
│   │   │   ├── Avoided.jsx      # Avoided rugs stats + cards
│   │   │   ├── Activity.jsx     # Event feed (polls every 10s)
│   │   │   └── Settings.jsx     # Persona + approval mode + exit strategy + budget caps
│   │   ├── components/
│   │   │   ├── TokenCard.jsx
│   │   │   ├── RiskBadge.jsx
│   │   │   ├── PersonaSelector.jsx
│   │   │   ├── BudgetBar.jsx
│   │   │   ├── ChatPanel.jsx    # Floating AI chat (global + token-scoped)
│   │   │   ├── ToastNotifications.jsx  # Real-time toast alerts from WebSocket events
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
├── .env.example
└── .gitignore
```

---

## 6. Current Status — Phase 3 (Polish & Demo)

**Spec rename:** `Memeguard.md` is now `FourScout.md`. A new §18 "Roadmap: Non-Custodial Session Keys" documents the post-hackathon evolution from single-tenant self-hosted (one `PRIVATE_KEY`) to multi-tenant ERC-4337 session keys. Phase 4 in `TODO.md` tracks that scope as design-only — no implementation in the current branch.

**Phase 2 verified, Phase 3 largely complete.** Avoided tracker is populating live (39+ red-flagged tokens, price history filling naturally over 1h/6h/24h). All UI features Playwright-verified except wallet-gated flows (8004 register tx + trade approve-sign — require MetaMask in browser). Docker self-host artifacts added.

### COMPLETE (committed at `c23acbf`)

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
- AI-driven position monitoring: `analyze_position_exit()` runs every 5 min with drift detection (capped at 3 LLM calls/cycle)

**Exit strategy:**
- Configurable take-profit/stop-loss thresholds (config keys: `take_profit_pct`, `stop_loss_pct`, `auto_sell_enabled`)
- Auto-sell mode: automatic sell execution at thresholds without approval (separate from buy approval_mode)
- Exit Strategy settings UI section with take profit %, stop loss %, auto-sell toggle

**Real-time alerting:**
- 6 WebSocket events: new_token, risk_scored, risk_alert, action_proposed, position_update, trade_executed
- Toast notification system: real-time visual alerts for all important WS events
- Position update toasts filtered to milestones only (50%+, 100%+, -40%+)
- App.jsx restructured: split into App (providers) and AppContent (hooks + NotificationProvider)

### WHAT NEEDS TO BE TESTED

**To finish Phase 2:**
1. Test the sell flow: buy a token → wait for position tracker to propose exit (or manually trigger) → approve → verify position closes, trade recorded, PnL correct
2. Test toast notifications: start frontend, approve a trade, verify toasts appear
3. Test exit strategy settings: change thresholds in Settings, verify position_tracker uses them
4. Test AI monitoring: with Gemini key, hold a position for 5+ minutes, check backend logs for AI analysis

**Phase 3 — Polish & Demo Features (largely complete; see TODO.md):**
- [x] ERC-8004 agent identity registration, "What I Avoided" tracker, risk radar chart, behavioral nudge, watchlist UI, real volume signal, visual polish, README
- [ ] Deployment (Docker artifacts added; Vercel + Railway/Render still to provision)
- [ ] Wallet-gated smoke test (8004 register + trade approve via MetaMask)
- [ ] Demo video + DoraHacks BUIDL submission

**Phase 4 — Non-Custodial Session Keys (roadmap only, not started):**
- Design documented in `FourScout.md` §18. Stack: ZeroDev Kernel v3 + `@zerodev/permissions` + Pimlico on BSC. Introduces a Node.js `session-signer/` sidecar alongside `fourmeme-cli/`. Backend would swap CLI-subprocess signing for bundler userOps while keeping read-only CLI commands unchanged. All persona rules, approval modes, and budget caps preserved — session keys are a signing mechanism swap, not a policy rewrite.

---

## 7. Key Architecture Decisions

1. **Deterministic risk scoring** — AI only explains, never decides. Rules engine + weighted signals.
2. **AI depth over breadth** — LLM for interactive advising (chat), narrative synthesis, escalation analysis, position exit analysis. Not just labeling.
3. **Deterministic-first monitoring** — Numeric thresholds every 60s (cheap). AI analysis every 5 min, only when drift triggers fire. Max 3 LLM calls per cycle.
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
| 6 | Volume consistency | MEDIUM (2) | CLI: fourmeme events (stub — not fully implemented) |
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

---

## 14. Known Issues & Gotchas

1. **CLI only returns `{ txHash }`** — after buy/sell, there's no price or quantity in the response. For buys, we use the pre-buy quote's `estimatedAmount`. For sells, we use the pre-sell quote's `estimatedCost`.

2. **quote-buy parameter order** — `fourmeme quote-buy <token> <amountWei> [fundsWei]`. For funds-based (spend X BNB), pass `0` as amountWei and the funds as second arg. We had a bug where funds was passed as amountWei.

3. **Backend .env loading** — `config.py` loads from `[".env", "../.env"]`. The root `.env` has PRIVATE_KEY and GEMINI_API_KEY. The backend directory may not have its own `.env`.

4. **Pyright warnings** — Several `response.text` warnings about potentially None return from Gemini SDK. These are pre-existing and don't cause runtime issues. Also `risk_percentage` unused in persona_engine.py (intentional, kept for potential future use).

5. **Volume consistency signal** — Currently a stub in risk_engine.py. TODO to replace with real CLI events analysis.

6. **Frontend polls** — Dashboard polls every 15s, Activity/Positions every 10s. WebSocket events exist but most pages don't react to them (they poll instead). The new ToastNotifications component is the first to actually consume WS events.

7. **Position #1 in DB** — From the first buy test before we fixed the executor. Has token_quantity=0 and entry_price=0. Was manually closed (status='closed'). Position #2 is the valid one with correct data.

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
c23acbf Complete sell flow, AI position monitoring, auto-sell, toast notifications, and handoff doc
d5c782b Phase 2: Brain — auto-propose pipeline, trade execution, AI advisor, and position tracking
4a98030 Fix Phase 1 bugs: HTTP status codes, LLM integration, slippage protection, CORS, and daily budget tracking
0df96f3 Integrate competitive analysis: add AI advisor, narrative synthesis, and reprioritized build phases
12a2d2d Update Memeguard.md to reflect current implementation
258c8f7 Fix Web3 token info decoding for V2 tokens and scanner API field mapping
1e4f776 Phase 1: Foundation — full project scaffold with live token feed and risk scoring
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
