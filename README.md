# FourScout — AI Trading Agent for Four.meme

FourScout is a persona-based AI trading agent console for the [Four.meme](https://four.meme) memecoin launchpad on BNB Chain (BSC). It scans new token launches in real time, scores risk across 8 deterministic signals, explains findings with AI-generated narratives, provides an interactive AI trading advisor, and executes trades within user-approved limits.

Built for the **Four.Meme AI Sprint** hackathon on DoraHacks.

## Architecture

```
Frontend (React/Vite) <---REST + WebSocket---> Backend (FastAPI)
                                                    |
                     ┌──────────────────────────────┼──────────────────────────────┐
                     |                              |                              |
               Four.meme CLI                  Web3.py (BSC)                 Google Gemini
            (buy/sell/quotes/               (risk scoring:                  (rationale generation,
             events/ERC-8004)               holders, creator                AI advisor chat,
                                            history, contracts)             narrative synthesis)
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3 + FastAPI + SQLite (aiosqlite) + Web3.py |
| Frontend | React 18 + Vite + Tailwind CSS v4 (dark theme) |
| AI/LLM | Google Gemini 2.5 Flash |
| On-chain | Web3.py direct contract calls + Four.meme CLI |
| Trading | `@four-meme/four-meme-ai` CLI via subprocess |
| Wallet | wagmi + viem (BSC wallet connection) |
| Charts | Recharts (risk radar chart) |

## Features

### Risk Scoring Engine (8 Signals)

All scoring is deterministic -- AI only generates the explanation, never the score.

| Signal | Weight | Source |
|--------|--------|--------|
| Creator history | HIGH | Web3.py: TokenManager2 TokenCreate events |
| Holder concentration | HIGH | Web3.py: ERC20 balanceOf + Transfer events |
| Bonding curve velocity | HIGH | Web3.py: TokenManagerHelper3.getTokenInfo() |
| Liquidity depth & age | MEDIUM | Web3.py: getTokenInfo() funds + liquidityAdded |
| Tax token flags | MEDIUM | Web3.py: TaxToken ABI feeRate inspection |
| Volume consistency | MEDIUM | Web3.py: Transfer event pattern analysis |
| Social signal | LOW | Four.meme API + VADER sentiment |
| Market context | LOW | CoinGecko + Fear & Greed Index |

Grades: **GREEN** (>=65%) | **AMBER** (40-65%) | **RED** (<40%)

### Three Trading Personas

| Persona | Style | Risk Tolerance |
|---------|-------|----------------|
| Conservative | Small positions, aged tokens only | GREEN only |
| Momentum | Moderate positions, follows trends | AMBER if momentum strong |
| Sniper | Tiny positions, new launches | AMBER, bonding-only |

### AI-Powered Features

- **Interactive AI Advisor** -- context-aware chat that knows your positions, risk data, and persona config
- **Multi-signal Narrative Synthesis** -- correlates signals into coherent stories ("serial creator + high concentration = pump-and-dump setup")
- **AMBER Escalation Pipeline** -- deep AI analysis only for ambiguous tokens, with lean_buy/lean_skip/watch recommendations
- **AI-driven Position Monitoring** -- Gemini analyzes positions every 5 min when drift triggers fire
- **"What I Avoided" Tracker** -- background job checks red-flagged token prices at 1h/6h/24h, confirms rugs, calculates savings

### Safety & Controls

- **4 Approval Modes**: approve each, per session, budget threshold, monitor only
- **Budget Caps**: max per trade, max per day, max positions, slippage limits (server-side enforced)
- **Behavioral Nudge**: tracks when you override the agent, shows outcomes on Dashboard
- **ERC-8004 Agent Identity**: on-chain registration for AI Agent Mode token launches

### UI

- Dark theme (Binance-inspired)
- Live WebSocket feed with toast notifications
- Risk radar chart (8-signal spider graph)
- Watchlist management
- Real-time position PnL tracking

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- BSC RPC endpoint

### Environment

Copy `.env.example` to `.env` and fill in:

```env
PRIVATE_KEY=           # Hex private key for agent wallet (use a dedicated wallet, never your main)
GEMINI_API_KEY=        # Google Gemini API key
BSC_RPC_URL=https://bsc-dataseed1.binance.org
```

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Four.meme CLI

```bash
cd fourmeme-cli
npm install
```

## Deployment

FourScout ships as a **self-hosted single-tenant** application. Each user runs their own instance with their own agent wallet. This is an explicit design choice — see the Security Model section below and [FourScout.md §18](./FourScout.md#18-roadmap-non-custodial-session-keys) for the non-custodial multi-tenant roadmap.

### Backend — Docker (recommended for self-host)

```bash
cp .env.example .env   # fill in PRIVATE_KEY, GEMINI_API_KEY, BSC_RPC_URL
docker compose up -d
```

The backend listens on port 8000. The SQLite database persists to `./data/fourscout.db` via a volume mount, so restarts and image rebuilds preserve your history, positions, and avoided-token log.

### Backend — Railway / Render

The Dockerfile is deploy-platform-agnostic. On Railway:

1. New project → Deploy from GitHub repo.
2. Set env vars from `.env.example`.
3. Attach a persistent volume mounted at `/app/data` for the SQLite file.

### Frontend — Vercel

```bash
cd frontend
vercel --prod
```

Set `VITE_API_BASE` to your deployed backend URL in the Vercel dashboard. The frontend is a static SPA and does not need any server-side runtime.

## Security Model

FourScout is **single-tenant by design**. Each deployment uses one `PRIVATE_KEY` in `.env` that signs every trade via the Four.meme CLI subprocess. That private key is the agent wallet — it should be a **dedicated wallet**, never your main holdings wallet, and it should only hold the amount of BNB you're comfortable letting the agent trade with.

Why this model:

- **No custody risk.** We never hold your keys on a shared server. If you self-host, only you hold them.
- **No regulatory surface.** Self-hosting keeps the operator out of money-transmitter territory.
- **Honest scope for a hackathon MVP.** Shipping a working agent matters more than a multi-user backend.

The next step toward a hosted, multi-user product is **non-custodial session keys** via ERC-4337 account abstraction (ZeroDev Kernel + Pimlico bundler on BSC). That architecture is documented in full at [FourScout.md §18](./FourScout.md#18-roadmap-non-custodial-session-keys). It is design-only today — not built into the MVP.

**Budget caps are enforced server-side regardless of deployment model** — max per trade, max per day, max active positions, slippage, cooldown. The `PRIVATE_KEY` can only spend what the rest of the stack authorizes.

## Project Structure

```
meme-guard/
├── backend/
│   ├── main.py                  # FastAPI app + WebSocket + background tasks
│   ├── config.py                # Pydantic Settings
│   ├── database.py              # SQLite schema + queries
│   ├── clients/                 # External service wrappers
│   │   ├── fourmeme_cli.py      # Four.meme CLI subprocess wrapper
│   │   ├── fourmeme_api.py      # Four.meme REST API
│   │   ├── bsc_web3.py          # Web3.py contract reads
│   │   └── market_api.py        # CoinGecko + Fear & Greed
│   ├── services/                # Business logic
│   │   ├── scanner.py           # Token discovery (30s polling)
│   │   ├── risk_engine.py       # 8-signal scoring + auto-propose
│   │   ├── persona_engine.py    # Persona rules
│   │   ├── llm_service.py       # Gemini 2.5 Flash integration
│   │   ├── chat_service.py      # AI advisor chat
│   │   ├── executor.py          # Trade execution via CLI
│   │   ├── approval_gate.py     # 4 approval modes
│   │   ├── position_tracker.py  # PnL + AI exit analysis + auto-sell
│   │   ├── avoided_tracker.py   # Price tracking for red-flagged tokens
│   │   └── agent_identity.py    # ERC-8004 registration
│   └── routes/                  # API endpoints
├── frontend/
│   ├── src/
│   │   ├── pages/               # Dashboard, OpportunityDetail, Positions, etc.
│   │   ├── components/          # TokenCard, RiskBadge, RiskRadar, ChatPanel, etc.
│   │   ├── hooks/               # useWallet, useWebSocket
│   │   └── services/api.js      # Backend REST client
│   └── package.json
└── fourmeme-cli/                # Local Four.meme CLI install
```

## Key Design Principles

1. **Deterministic risk scoring** -- AI explains, never decides
2. **AI depth over breadth** -- interactive advisor, narrative synthesis, escalation analysis
3. **Human in the loop** -- all trades require approval (configurable autonomy)
4. **Budget caps are hard limits** -- server-side enforcement, never bypassed
5. **Complete pipelines** -- every flow works end-to-end with no dead ends

## License

MIT
