# MemeGuard — Build TODO

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
- [x] LLM service (Gemini 2.0 Flash, provider abstraction, fallback rationale)
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

## Phase 2: The Brain
**Goal:** End-to-end trade loop with AI depth and position tracking.

### Core Pipeline (carry-over)
- [x] Complete risk scoring engine: all 8 signals
- [x] LLM integration (Gemini) for rationale generation
- [x] Opportunity detail page (full risk breakdown + rationale + action)
- [x] Persona action engine (rules that map score + persona → action)
- [x] Approval gate system (4 modes — service exists)
- [x] Trade executor (buy/sell via CLI)
- [x] Activity feed page
- [x] WebSocket for live updates
- [ ] Transaction builder integration: quote via CLI → slippage calc → TxPreview display
- [ ] Approval modal: TX preview with amount, slippage, gas, approve/reject buttons
- [ ] Position tracker background job: update prices, compute PnL, propose exits
- [ ] Auto-propose actions: scanner → score → persona decides → auto-create pending_action + broadcast
- [ ] End-to-end test: scanner → score → persona recommends → approve → execute → track

### AI Depth (competitive edge — targets Innovation criterion)
- [ ] Interactive AI chat advisor: backend `/api/chat` endpoint + frontend chat panel
  - Users ask questions about specific tokens ("Why is this risky?", "Compare to last 5 tokens")
  - Context-aware: pulls token risk data, position history, persona config into prompt
  - Conversational memory within session (last N messages)
- [ ] Multi-signal narrative synthesis: enhanced LLM prompt that correlates signals
  - Cross-signal pattern detection ("creator launched 3 tokens + top holder 40% = pump-and-dump pattern")
  - Replace one-line-per-signal with a cohesive narrative rationale
- [ ] Escalation pipeline: quick deterministic scan for GREEN/RED, deep AI analysis only for AMBER tokens

### Expanded WebSocket Events
- [ ] `action_proposed` — new trade opportunity pending approval
- [ ] `trade_executed` — buy/sell completed with tx details
- [ ] `position_update` — PnL change (periodic)
- [ ] `risk_alert` — token grade changed or rug detected
- [ ] `avoided_update` — "dodged a bullet" notification

### Verify Phase 2
- [ ] **Full trade loop:** find token → score → explain → propose → approve → execute → track position
- [ ] **AI advisor:** ask "why is this token risky?" and get a contextual answer
- [ ] **Live dashboard:** WebSocket events update UI without refresh

## Phase 3: Polish & Demo Features
**Goal:** Demo-ready with killer differentiators and visual polish. Ordered by judging impact.

### High Priority (Differentiators)
- [ ] ERC-8004 agent identity registration (`agent_identity.py` + Settings UI button + on-chain verification)
- [ ] "What I Avoided" background job: check red-flagged token prices at 1h/6h/24h, confirmed rug detection
- [ ] Risk visualization: radar chart or stacked signal bars for 8-signal breakdown (recharts/chart.js)
- [ ] Deployment: Frontend → Vercel, Backend Dockerfile (Python + Node.js) → Railway

### Medium Priority (Completeness)
- [ ] Post-trade monitoring: price alerts, momentum loss detection, exit signals
- [ ] Behavioral nudge: track overrides, show outcome summary on Dashboard ("You overrode 3 red signals, 2 rugged")
- [ ] Watchlist management UI on Settings page
- [ ] Volume consistency signal: replace stub with real implementation (CLI events analysis)

### Demo & Submission
- [ ] Demo seed script (pre-populate avoided rugs for compelling demo)
- [ ] Visual polish: animations, hover effects, pulsing status indicator, responsive layout
- [ ] README.md (architecture diagram, screenshots, setup instructions)
- [ ] Demo video recording (3-5 min, follow script in Memeguard.md Section 12)
- [ ] DoraHacks BUIDL submission (GitHub repo + demo video link)

### Verify Phase 3
- [ ] **Full demo flow:** wallet → 8004 register → persona → live feed → AI advisor chat → approve trade → avoided rugs → behavioral summary
- [ ] **Community voting appeal:** deployed, polished, screenshot-worthy
