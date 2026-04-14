# MemeGuard — Four.meme AI Agent Console

## Project Overview

MemeGuard is a persona-based AI trading agent for the **Four.meme** memecoin launchpad on **BNB Chain (BSC)**. It scans new token launches, scores risk, explains findings in plain language, provides an interactive AI advisor for trading decisions, and executes trades within user-approved limits.

Built for the **Four.Meme AI Sprint** hackathon on DoraHacks ($50K prize pool).

## Hackathon Judging Criteria

Expert review (70%) + Community voting (30%):
- **Innovation** (30% of expert) — originality and depth of AI application
- **Technical Implementation** (30% of expert) — code quality and demo stability
- **Practical Value** (20% of expert) — user impact or commercial potential
- **Presentation** (20% of expert) — clarity of pitch and execution capability

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python FastAPI + SQLite + Web3.py |
| Frontend | React + Vite + Tailwind CSS (dark theme) |
| LLM | Google Gemini 2.0 Flash (free tier, `google-genai` SDK) |
| On-chain reads | Web3.py (direct contract calls for risk scoring) |
| Trading | Four.meme CLI (`@four-meme/four-meme-ai`) via subprocess |
| Wallet | wagmi + viem (frontend BSC wallet connection) |
| Deploy | Vercel (frontend) + Railway (backend) |

## Architecture

```
Frontend (React/Vite) <--REST+WebSocket--> Backend (FastAPI)
                                              |
                    ┌─────────────────────────┼─────────────────────────┐
                    |                         |                         |
              Four.meme CLI            Web3.py (BSC)            Google Gemini
           (buy/sell/quotes/          (risk scoring:            (rationale generation,
            events/8004)              holders, creator           AI advisor chat,
                                      history, contracts)        narrative synthesis)
```

**Hybrid integration approach:**
- **Four.meme CLI** for: trading (buy/sell), price quotes, token rankings, ERC-8004 registration, event monitoring
- **Direct Web3.py** for: holder concentration, creator wallet history, bonding curve reads, tax token inspection, liquidity depth — data the CLI doesn't expose
- **Google Gemini** for: rationale generation, interactive AI advisor chat, multi-signal narrative synthesis, AMBER token deep analysis

## Key Contract Addresses (BSC Mainnet)

| Contract | Address |
|----------|---------|
| TokenManager2 | `0x5c952063c7fc8610FFDB798152D69F0B9550762b` |
| TokenManagerHelper3 | `0xF251F83e40a78868FcfA3FA4599Dad6494E46034` |
| AgentIdentifier | `0x09B44A633de9F9EBF6FB9Bdd5b5629d3DD2cef13` |
| PancakeSwap Router V2 | `0x10ED43C718714eb63d5aA57B78B54704E256024E` |
| BRC8004 Identity Registry | `0xfA09B3397fAC75424422C4D28b1729E3D4f659D7` |

## Four.meme API

- Base URL: `https://four.meme/meme-api/v1`
- Token search: `POST /public/token/search`
- Token detail: `GET /private/token/get/v2?address=<addr>`
- Rankings: `POST /public/token/ranking`

## Four.meme CLI Commands

Install: `npm install -g @four-meme/four-meme-ai`

| Command | Purpose |
|---------|---------|
| `fourmeme token-rankings <orderBy>` | Get token rankings |
| `fourmeme token-info <address>` | Token details |
| `fourmeme quote-buy <token> <amountWei>` | Buy price estimate |
| `fourmeme quote-sell <token> <amountWei>` | Sell price estimate |
| `fourmeme buy <token> funds <fundsWei> <minAmountWei>` | Execute buy |
| `fourmeme sell <token> <amountWei> [minFundsWei]` | Execute sell |
| `fourmeme events <fromBlock> [toBlock]` | Block event monitor |
| `fourmeme tax-info <token>` | Tax configuration |
| `fourmeme 8004-register <name> [imageUrl] [desc]` | Register agent identity |
| `fourmeme 8004-balance <owner>` | Check 8004 NFT balance |

Requires `.env` with `PRIVATE_KEY` and optionally `BSC_RPC_URL`.

## Risk Scoring Engine (8 Signals)

All deterministic (no AI). LLM only generates the plain-language explanation.

| # | Signal | Weight | Data Source |
|---|--------|--------|-------------|
| 1 | Creator history | HIGH (3) | Web3.py: TokenManager2 TokenCreate events |
| 2 | Holder concentration | HIGH (3) | Web3.py: ERC20 balanceOf + Transfer events |
| 3 | Bonding curve velocity | HIGH (3) | Web3.py: TokenManagerHelper3.getTokenInfo() |
| 4 | Liquidity depth & age | MEDIUM (2) | Web3.py: getTokenInfo() funds + liquidityAdded |
| 5 | Tax token flags | MEDIUM (2) | CLI: fourmeme tax-info / Web3.py: TaxToken ABI |
| 6 | Volume consistency | MEDIUM (2) | CLI: fourmeme events (TokenPurchase/Sale) |
| 7 | Social signal | LOW (1) | Four.meme API + VADER sentiment |
| 8 | Market context | LOW (1) | CoinGecko + Alternative.me Fear & Greed |

Grades: GREEN (>=65%), AMBER (40-65%), RED (<40%)

## Three Personas

| Persona | Default BNB | Min Age | Risk Tolerance | Bonding Only |
|---------|-------------|---------|----------------|--------------|
| Conservative | 0.02 | 10 min | GREEN only | No |
| Momentum | 0.05 | 3 min | AMBER if momentum strong | No |
| Sniper | 0.01 | 0 min | AMBER | Yes |

## Four Approval Modes

1. **Approve each** — every trade needs explicit approval (Sniper default)
2. **Approve per session** — first trade approved, rest auto within rules
3. **Budget threshold** — auto under threshold, approve above
4. **Monitor only** — no trades, recommendations only

## Budget Caps (hard-enforced server-side)

| Rule | Default |
|------|---------|
| Max per trade | 0.05 BNB |
| Max per day | 0.3 BNB |
| Max active positions | 3 |
| Min liquidity | $500 |
| Max slippage | 5% |
| Cooldown | 60 seconds |

## Project Structure

```
meme-guard/
├── backend/
│   ├── main.py              # FastAPI app + WebSocket + lifespan
│   ├── config.py            # Pydantic Settings from .env
│   ├── database.py          # SQLite schema + async queries
│   ├── clients/
│   │   ├── fourmeme_cli.py  # Subprocess wrapper for @four-meme/four-meme-ai
│   │   ├── fourmeme_api.py  # Four.meme REST API client (httpx)
│   │   ├── bsc_web3.py      # Web3.py direct contract reads
│   │   └── market_api.py    # CoinGecko + Fear & Greed
│   ├── services/
│   │   ├── scanner.py       # Token discovery (API polling + CLI events)
│   │   ├── risk_engine.py   # 8-signal deterministic scoring
│   │   ├── persona_engine.py # Persona rules -> action mapping
│   │   ├── llm_service.py   # Gemini rationale generation (provider abstraction)
│   │   ├── chat_service.py  # Interactive AI advisor (context-aware conversational chat)
│   │   ├── tx_builder.py    # Transaction preview preparation
│   │   ├── executor.py      # Trade execution via CLI
│   │   ├── approval_gate.py # 4 approval modes
│   │   ├── position_tracker.py  # PnL tracking
│   │   ├── avoided_tracker.py   # "What I Avoided" background checker
│   │   └── agent_identity.py    # ERC-8004 registration
│   ├── models/              # Pydantic models / dataclasses
│   ├── routes/              # FastAPI route modules (tokens, actions, positions, avoided, config, watchlist, activity, chat)
│   ├── abis/                # Contract ABIs (JSON)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/           # Dashboard, OpportunityDetail, Positions, Avoided, Activity, Settings
│   │   ├── components/      # TokenCard, RiskBadge, ApprovalModal, PersonaSelector, etc.
│   │   ├── hooks/           # useWallet, useWebSocket, useTokenFeed
│   │   └── services/api.js  # Backend API client
│   ├── package.json
│   └── vite.config.js
├── fourmeme-cli/            # Local npm install of @four-meme/four-meme-ai
├── Memeguard.md             # Full MVP specification
├── CLAUDE.md                # This file
├── .env.example
└── .gitignore
```

## Environment Variables

```env
# BSC
BSC_RPC_URL=https://bsc-dataseed1.binance.org

# Four.meme CLI
PRIVATE_KEY=                  # Hex private key for agent wallet (never main wallet)

# LLM
GEMINI_API_KEY=               # Google Gemini API key (free tier)

# Database
DATABASE_PATH=./data/memeguard.db

# Scanner
SCAN_INTERVAL_SECONDS=30
```

## Development Commands

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Four.meme CLI
cd fourmeme-cli && npm install @four-meme/four-meme-ai
```

## Four.meme Platform Mechanics

- Tokens launch with 1B supply on a bonding curve (~18-24 BNB to graduate)
- 1% trading fee during bonding phase (min 0.001 BNB)
- On graduation: 20% supply pairs with collected tokens on PancakeSwap, LP burned
- All token contracts end in `4444`
- Tax tokens support: 1/3/5/10% fees (burn/dividend/liquidity/founder)
- Launch modes: Normal, X Mode (anti-bot), Alpha, Rush (10min sell lock), AI Agent Mode
- ERC-8004 enables agent wallets to trade during AI Agent Mode exclusive phases

## Key Design Principles

1. **Deterministic risk scoring** — AI only explains, never decides. Rules engine + weighted signals.
2. **AI depth over breadth** — Use the LLM for interactive advising (chat), multi-signal narrative synthesis, and escalation analysis on AMBER tokens — not just labeling. The AI should feel like a knowledgeable trading co-pilot, not a badge generator.
3. **Human in the loop** — All trades require approval (4 modes with varying autonomy).
4. **Budget caps are hard limits** — Server-side enforcement, never bypassed.
5. **Local-first** — SQLite, no external DB dependency.
6. **Provider-agnostic LLM** — Abstraction layer supports Gemini now, Anthropic later.
7. **Complete pipelines** — Every user flow must work end-to-end (discover → score → propose → approve → execute → track). No dead ends.
