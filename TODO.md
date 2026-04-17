# FourScout — Build TODO

## Phase 1: Foundation (COMPLETE)
- [x] Project scaffolding: backend (FastAPI + requirements.txt) + frontend (React/Vite + Tailwind)
- [x] Backend config.py (Pydantic Settings, .env loading, contract address constants)
- [x] Database schema (SQLite: tokens, scans, positions, trades, avoided, config, watchlist, activity, token_snapshots)
- [x] .env.example + .gitignore
- [x] Four.meme CLI wrapper (`backend/clients/fourmeme_cli.py` — subprocess around @four-meme/four-meme-ai)
- [x] Install Four.meme CLI locally (`fourmeme-cli/` npm package)
- [x] Contract ABIs (TokenManager2, TokenManagerHelper3, AgentIdentifier, TaxToken, ERC20 — lite versions)
- [x] BSC Web3 client (`backend/clients/bsc_web3.py` — get_token_info, get_holder_balances, get_creator_history, is_tax_token, is_agent)
- [x] Four.meme REST API client (`backend/clients/fourmeme_api.py` — search_tokens, get_token, get_rankings)
- [x] Market context client (`backend/clients/market_api.py` — BNB price, Fear & Greed)
- [x] Scanner service (`backend/services/scanner.py` — 30s polling + event monitoring)
- [x] Risk scoring engine — all 8 signals with weighted aggregation
- [x] LLM service (Gemini 2.5 Flash, provider abstraction, fallback rationale)
- [x] Persona engine (3 personas, decide_action rules)
- [x] Trade executor (buy/sell via CLI, position/trade recording)
- [x] Backend routes: tokens, config, activity, positions, actions, avoided, watchlist
- [x] Frontend: Tailwind dark theme config (Binance-inspired colors)
- [x] Frontend: App.jsx with React Router (6 routes) + WagmiProvider (BSC chain)
- [x] Frontend: Navbar, TokenCard, RiskBadge, PersonaSelector, BudgetBar components
- [x] Frontend: useWallet hook (wagmi BSC), useWebSocket hook
- [x] Frontend: Dashboard page (live token feed + persona badge + budget bar + stats)
- [x] Frontend: Settings page (persona selector + budget caps + approval mode)
- [x] Frontend: OpportunityDetail page (8-signal breakdown + rationale + approve/reject)
- [x] Frontend: Positions, Avoided (stats + cards), Activity feed pages
- [x] Frontend: api.js service (backend REST client)
- [x] WebSocket: auto-reconnecting, live push for new tokens and risk scores
- [x] **Verified:** Scanner discovering and scoring real Four.meme tokens with GREEN/AMBER/RED grades

## Phase 2: The Brain (COMPLETE)
**Goal:** End-to-end trade loop with AI depth and position tracking.

### Core Pipeline (carry-over)
- [x] Complete risk scoring engine: all 8 signals
- [x] LLM integration (Gemini 2.5 Flash) for rationale generation
- [x] Opportunity detail page (full risk breakdown + rationale + action)
- [x] Persona action engine (rules that map score + persona → action)
- [x] Approval gate system (4 modes — `approval_gate.py`)
- [x] Trade executor (buy/sell via CLI, with slippage protection via quote)
- [x] Activity feed page
- [x] WebSocket for live updates
- [x] Transaction builder integration: quote via CLI → slippage calc → TxPreview display (`tx_builder.py`)
- [x] Approval modal: TX preview with amount, slippage, estimated tokens, min tokens, approve/reject
- [x] Position tracker background job: update prices, compute PnL, propose exits (`position_tracker.py`)
- [x] Auto-propose actions: scanner → score → persona decides → approval gate → pending_action + broadcast
- [x] End-to-end buy loop: scanner → score → propose → approve → buy on-chain → position tracked (verified with 0.0001 BNB)

### Sell Flow & Position Management
- [x] Complete sell executor: sell quote for slippage protection, position closure, trade recording, PnL fields
- [x] Configurable take-profit/stop-loss thresholds (user-settable in Settings, replaces hardcoded 100%/-50%)
- [x] Auto-sell mode: automatic execution at thresholds without requiring approval
- [x] AI-driven position monitoring: Gemini analyzes positions every 5 min, proposes exits with reasoning
  - Drift detection: PnL approaching thresholds, stale positions, holder concentration changes
  - Capped at 3 LLM calls per cycle
- [x] Sell action approve/reject UI on Positions page
- [x] End-to-end sell loop: position tracker proposes → approve → execute on-chain → position closed (verified with 0.0001 BNB)

### AI Depth (competitive edge — targets Innovation criterion)
- [x] Interactive AI chat advisor: backend `/api/chat` endpoint + frontend ChatPanel component
  - Context-aware: pulls token risk data, positions, persona config into prompt
  - Conversational memory within session (last N messages)
  - Token-scoped chat on OpportunityDetail page
  - Suggested questions for new users
- [x] Multi-signal narrative synthesis: enhanced LLM prompt that correlates signals
  - Cross-signal pattern detection ("serial creator + high concentration = pump-and-dump setup")
  - Cohesive narrative rationale instead of per-signal summaries
- [x] Escalation pipeline: quick deterministic scan for GREEN/RED, deep AI analysis only for AMBER tokens
  - `deep_analyze_amber()` returns recommendation (lean_buy/lean_skip/watch) with confidence + analysis

### Real-Time Alerting
- [x] Toast notification system: real-time alerts for WebSocket events (trade_executed, action_proposed, risk_alert)
  - Position update toasts filtered to milestones only (50%+, 100%+, -40%+) to prevent spam
  - Max 5 visible, auto-dismiss after 5s, Binance-themed colors
- [x] `action_proposed` — new trade opportunity pending approval
- [x] `trade_executed` — buy/sell completed with tx details
- [x] `position_update` — PnL change (periodic, from position tracker)
- [x] `risk_alert` — token grade changed on rescore
- [x] `avoided_update` — "dodged a bullet" notification (implemented in Phase 3 avoided tracker)

### Verify Phase 2
- [x] **Auto-propose pipeline:** scanner → score → persona → approval gate → pending_action (verified: 10+ pending actions auto-created)
- [x] **Full buy loop:** approve → execute → track position (verified: 0.0001 BNB trade, tx on-chain, position recorded)
- [x] **Full sell loop:** position tracker proposes exit → approve → execute on-chain → position closed (verified with 0.0001 BNB, tx 0x3a7f...6e9f)
- [x] **AI advisor:** chat endpoint + frontend ChatPanel (graceful fallback without Gemini key)
- [x] **Live dashboard:** WebSocket events update UI without refresh
- [x] **Gemini 2.5 Flash migration:** upgraded from deprecated 2.0 Flash, thinking_budget=0 fix, all 6 AI integration points verified

## Phase 3: Polish & Demo Features
**Goal:** Demo-ready with killer differentiators and visual polish. Ordered by judging impact.

### High Priority (Differentiators)
- [x] ERC-8004 agent identity registration (`agent_identity.py` + Settings UI section + on-chain verification)
- [x] "What I Avoided" background job: check red-flagged token prices at 1h/6h/24h, confirmed rug detection, `avoided_update` toast
- [x] Risk visualization: radar chart for 8-signal breakdown (recharts RadarChart on OpportunityDetail)
- [ ] Deployment: Backend `Dockerfile` + `docker-compose.yml` (Python + Node.js for Four.meme CLI, SQLite volume mount) → Railway / Render / self-host; Frontend → Vercel (`VITE_API_BASE` → backend URL). See README "Deployment" section.

### Medium Priority (Completeness)
- [x] Behavioral nudge: track overrides (approve risky / reject safe), show outcome summary on Dashboard
- [x] Watchlist management UI on Settings page (add/remove creator + token addresses)
- [x] Volume consistency signal: real implementation using on-chain Transfer event analysis (wash trading detection)

### Demo & Submission
- [ ] Demo seed script (pre-populate avoided rugs for compelling demo)
- [x] Visual polish: card fade-in animations, hover glow, pulsing scanner dot, responsive grid
- [x] README.md (architecture diagram, feature list, setup instructions)
- [ ] Demo video recording (3-5 min, follow script in FourScout.md Section 12)
- [ ] DoraHacks BUIDL submission (GitHub repo + demo video link)

### Verify Phase 3
- [x] **Playwright UI pass:** dashboard feed, token detail radar + 8 signals + AMBER deep-analysis narrative, avoided stats, settings (8004 card, persona, approval, exit strategy, budget, watchlist), AI chat panel (graceful Gemini-503 fallback) — all render correctly
- [x] **Fixed during verification:** event-loop blocking on sync Web3 calls (commit `3476eb4`); SQLite `database is locked` under concurrent scoring + ghost-token AMBER mis-grading (commit `295bd0f`) — avoided tracker now auto-populates (39+ tokens flagged live)
- [x] **Wallet-gated demo flow:** 8004 register tx (agent wallet `0xECf5…Bb25` registered on BSC mainnet) + trade approve-sign (position_id 4, 13,069 ORDI, entry 0.0001 BNB, tx `0x8a9e876852b6368fbc1a0bb027eddf1b2043f9882af469653112314c2771dbdb`)
- [ ] **Community voting appeal:** deployed, polished, screenshot-worthy

## Phase 4: Non-Custodial Session Keys (Roadmap — post-hackathon)
**Goal:** Evolve from single-tenant self-hosted (one `PRIVATE_KEY` per deployment) to hosted multi-tenant with cryptographically bounded delegation. Design documented in `FourScout.md` §18.

### Stack
- [ ] ZeroDev Kernel v3 smart account on BSC mainnet (chain 56), EntryPoint v0.7
- [ ] `@zerodev/permissions` session-key module with composable policies: `toCallPolicy` (whitelist Four.meme contracts + selectors), `toSpendingLimitPolicy` (max BNB over session), `toRateLimitPolicy` (userOps/hour cap), `toTimestampPolicy` (7-day expiry)
- [ ] Pimlico bundler integration (BSC mainnet)

### Backend
- [ ] `session-signer/` Node.js sidecar (TypeScript) — `POST /userop` endpoint that builds, signs with session key, submits via Pimlico, returns tx hash
- [ ] Python backend refactor: replace `fourmeme buy/sell/8004-register` signing calls with `httpx` calls to session-signer. `fourmeme_cli.py` keeps all read-only commands (quote-buy, quote-sell, tax-info, events, rankings, token-info).
- [ ] Session key storage: encrypted-at-rest in DB (libsodium sealed box for self-host; KMS envelope for hosted)
- [ ] Config schema: add `smart_account_address`, `session_key_policy_hash`, `session_expires_at`; deprecate direct `PRIVATE_KEY` usage for signing

### Frontend (multi-step onboarding wizard)
- [ ] Connect EOA → compute counterfactual Kernel address → show fund-this-address instruction
- [ ] Generate ephemeral session-key keypair in-browser
- [ ] Prompt MetaMask to sign session-key grant with policy constraints pulled from current Budget Caps config
- [ ] POST session key + policy metadata to backend
- [ ] Settings page: session status card (expiry, remaining cap, active validator) + Revoke button (signs `disableValidator` via MetaMask)

### Migration & Ops
- [ ] Dual-mode backend: detect `PRIVATE_KEY` fallback for self-host vs. session-key mode for hosted; swap executor at runtime
- [ ] userOp failure telemetry: distinguish bundler reverts, policy rejections, session expiry from generic tx errors
- [ ] Docs: migration guide for self-hosted users (optional path; `PRIVATE_KEY` mode remains supported)

### Open Questions (resolve during implementation)
- [ ] Policy upgrade UX: does raising `max_per_day_bnb` require a new grant signature, or can the backend layer sub-policies?
- [ ] Session-signer deployment: separate Docker service vs. supervised process inside backend container?
- [ ] Paymaster use: does gasless onboarding (first userOp sponsored) add enough value to justify the integration?
