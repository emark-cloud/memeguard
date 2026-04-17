# FourScout — Four.meme AI Agent Console

## Synthesized MVP Specification

**Hackathon:** Four.Meme AI Sprint (DoraHacks, $50K pool, deadline April 30 2026)
**Builder:** Solo + Claude Code
**Chain:** BNB Chain (BSC)
**Submission requires:** GitHub repo + demo video

---

## 1. What This Is

FourScout is a persona-based AI trading agent for Four.meme that scans new token launches, scores them for risk and opportunity in plain language, and executes trades only within user-approved limits.

**Core loop:**

```
detect opportunity → score risk → explain in plain language → persona filters → prepare transaction → user approves → execute
```

**Three things it does well:**

1. **Monitor** new Four.meme launches and BNB/PancakeSwap market context in real time
2. **Score and explain** risk, momentum, and rug signals using on-chain + sentiment signals
3. **Execute trades** through approval gates, under hard budget caps, filtered by a chosen persona

---

## 2. Target User

**Primary:** Existing memecoin trader on Four.meme who is tired of manually vetting hundreds of launches and wants an AI co-pilot that flags opportunity and danger.

**Secondary:** Token creator who wants to monitor their own token's health after launch.

---

## 3. Personas

Three presets. No freeform customization in v1.

### Conservative

- Low trade frequency
- Smaller position sizes (default 0.02 BNB)
- Requires green risk score + strong volume confirmation
- Avoids tokens under 10 minutes old
- Skips anything with holder concentration >40%
- **Best for:** users who want fewer trades and more safety

### Momentum

- Watches volume spikes, social momentum, and liquidity changes
- Enters faster than Conservative (default 0.05 BNB)
- Will trade amber-scored tokens if momentum is strong
- Still respects all budget caps and approval gates
- **Best for:** traders who want speed without full automation

### Sniper

- Reacts to new listings and strong launch signals within minutes
- Highest risk tolerance
- Smallest default size (0.01 BNB) as counterbalance
- Strictest approval mode (approve-each by default)
- Only enters during bonding curve phase
- **Best for:** advanced users who want launch-speed execution

---

## 4. Features

### A. Opportunity Scanner

The agent monitors in real time:

- New Four.meme token launches (via Four.meme public API)
- Token migration / graduation events (bonding curve → PancakeSwap listing)
- Liquidity additions and removals
- Price and volume spikes
- PancakeSwap trading activity on graduated tokens
- Basic social sentiment from linked Twitter/Telegram (lightweight — not a full suite)

**Output per opportunity:**

- What happened (one-line summary)
- Why it matters (plain-language rationale, LLM-generated)
- Risk score (green / amber / red)
- What the selected persona would do (buy / skip / monitor)

### B. Risk Scoring Engine

Concrete signals, not abstract AI. Each scored independently, combined into an overall green/amber/red grade.

| # | Signal | What It Checks | Weight | Data Source |
|---|--------|----------------|--------|-------------|
| 1 | **Creator history** | Has this wallet launched tokens before? Did those tokens dump? How many prior launches? | HIGH (3) | Web3.py: TokenManager2 TokenCreate events |
| 2 | **Holder concentration** | Top 5 wallets holding >X% of supply. Single wallet >20% = red flag. Unique holder count. | HIGH (3) | Web3.py: ERC20 Transfer events + balanceOf |
| 3 | **Bonding curve velocity** | Is the curve filling unusually fast (suggesting coordinated/bot buying)? BNB/min fill rate. | HIGH (3) | Web3.py: TokenManagerHelper3.getTokenInfo() |
| 4 | **Liquidity depth & age** | Is there enough liquidity to exit? Has liquidity been present for <5 minutes? USD value. | MEDIUM (2) | Web3.py: getTokenInfo() funds + liquidityAdded |
| 5 | **Tax token flags** | Does the token use Four.meme's TaxToken contract? What are the fee parameters? | MEDIUM (2) | Web3.py: TaxToken ABI (feeRate, allocation rates) |
| 6 | **Volume consistency** | Is volume real or wash-traded? Look for suspiciously regular buy patterns. | MEDIUM (2) | Four.meme CLI: events (TokenPurchase/Sale) |
| 7 | **Social signal** | Does the token have linked social accounts? Description sentiment analysis. | LOW (1) | Four.meme API + VADER sentiment |
| 8 | **Market context** | Fear & Greed Index, BNB 24h trend. Bear market = higher bar for entry. | LOW (1) | CoinGecko + Alternative.me Fear & Greed |

**Scoring:**

- Each signal scores 0–10, multiplied by weight (1–3)
- Weighted percentage: `sum(score * weight) / sum(10 * weight) * 100`
- Grades: **GREEN** (>=65%), **AMBER** (40–65%), **RED** (<40%)
- One-line explanation per signal, plus optional LLM-generated rationale
- Primary risk factor highlighted

### C. Persona-Based Action Engine

Based on the selected persona, the agent proposes exactly one of:

- **Buy** — with exact amount and slippage
- **Skip** — with reason
- **Monitor** — add to watchlist, check again in N minutes
- **Take profit** — partial or full exit
- **Exit** — sell entire position
- **Reduce exposure** — sell partial position

No complex portfolio theory. One action, one reason, one approval button.

### D. Approval Gates

Four modes, user-selectable:

| Mode | Behavior |
|------|----------|
| **Approve each** | Every trade requires explicit approval (default for Sniper) |
| **Approve per session** | First trade of each session requires approval, rest auto-execute within rules |
| **Budget threshold** | Auto-execute small trades, require approval when cumulative spend crosses a threshold |
| **Monitor only** | Agent scores and recommends, never prepares transactions. User trades manually. |

### E. Budget-Limited Autonomy

Hard caps that cannot be exceeded regardless of approval mode:

| Rule | Default | Configurable |
|------|---------|-------------|
| Max per trade | 0.05 BNB | Yes |
| Max per day | 0.3 BNB | Yes |
| Max active positions | 3 | Yes |
| Max trades per token | 1 entry | Yes |
| Min liquidity threshold | $500 | Yes |
| Max slippage | 5% | Yes |
| Cooldown between trades | 60 seconds | Yes |

### F. Wallet & Execution

- Connect existing BSC wallet via wagmi + viem (MetaMask, injected wallets)
- Agent uses a dedicated hot wallet (PRIVATE_KEY in .env) for trade execution via Four.meme CLI
- Prepare swap transactions with full preview (token, amount, slippage, estimated output)
- User approves via frontend → backend executes via CLI subprocess
- Optionally register agent wallet as ERC-8004 via Four.meme CLI (`fourmeme 8004-register`)

### G. "What I Avoided" Log

This is the demo killer feature.

- Every token the agent scores red gets logged with a timestamp
- A background job checks each red-scored token 1h, 6h, and 24h later
- If the token dropped >70% or liquidity was pulled: confirmed rug
- Dashboard shows: "Avoided 8 rugs this week — estimated savings: 0.4 BNB"
- Visual feed of avoided tokens with before/after price

### H. Behavioral Nudge

When a user overrides the agent's recommendation:

- Log the override (user approved a red-scored token, or skipped a green one)
- Track the outcome
- Show a periodic summary: "You overrode 3 Danger signals this week. 2 of those tokens dropped 80%+"
- Lightweight — not a coaching system, just a feedback mirror

### I. Watchlist

Users can manually add:

- Specific tokens to monitor
- Specific creator wallets to track
- Launch patterns to flag (e.g., "alert me on any token with 'AI' in the name")

### J. Interactive AI Advisor

**Targets: Innovation criterion (30% of expert score)**

A conversational chat interface that transforms the LLM from a label-generator into an interactive trading co-pilot.

- Users ask questions about specific tokens: "Why is this risky?", "Should I buy despite amber?", "Compare this to the last 5 tokens"
- Context-aware: automatically pulls token risk data, position history, persona config, and market context into the prompt
- Session-scoped conversational memory (last N messages)
- Available as a chat panel on the Dashboard and OpportunityDetail pages
- Backend: `POST /api/chat` with `{ message, token_address (optional), conversation_id }`

This is not a general chatbot — it's scoped to trading decisions, risk analysis, and token comparison. The agent has access to all 8 risk signals, the persona's reasoning, and the user's trade history.

### K. Multi-Signal Narrative Synthesis

**Targets: Innovation criterion (30% of expert score)**

Instead of generating one-line explanations per signal, the LLM synthesizes all 8 signals into a correlated narrative that reveals patterns.

Example output:
> "This creator launched 3 tokens in the last hour, and the top wallet already holds 38% of supply. This combination is a strong pump-and-dump indicator — historically, tokens with both rapid creator cycling AND concentrated holdings rug within 2 hours. The bonding curve is filling at 2.1 BNB/min, suggesting coordinated bot buying rather than organic interest. Despite the Fear & Greed index showing 'Greed', the on-chain signals override market sentiment here."

This replaces the existing per-signal one-liner with a cohesive, actionable narrative. The LLM prompt explicitly instructs correlation detection across signals.

### L. Risk Visualization

**Targets: Presentation criterion (20% of expert score) + Community Voting (30% of total)**

A radar chart or stacked signal bar visualization for the 8-signal breakdown on the OpportunityDetail page.

- Each of the 8 signals plotted on a radar chart (recharts or Chart.js)
- Color-coded by signal weight (HIGH = red axis, MEDIUM = amber, LOW = green)
- Instant visual comparison between tokens
- Screenshot-worthy for community voting

### M. AI-Driven Position Monitoring

**Targets: Innovation criterion (30% of expert score)**

Continuous AI-powered position analysis that goes beyond simple price-based stop-loss/take-profit. The system combines deterministic threshold checks with selective AI analysis.

- **Deterministic layer (every 60s):** Checks positions against user-configurable take-profit/stop-loss thresholds. Fast, cheap, no LLM cost.
- **AI layer (every 5 min, selective):** Calls Gemini to analyze positions where drift triggers fire:
  - PnL approaching stop-loss (-30% to threshold) or take-profit (50% to threshold)
  - Holder concentration changed significantly since entry
  - Position stale (>30 min, <5% price movement)
- AI returns structured `{ recommendation: hold|exit, confidence: 0-100, reasoning }` — proposes exit with natural-language rationale if confidence >= 70
- Capped at 3 LLM calls per cycle to stay within Gemini free-tier (15 RPM)

### N. Configurable Auto-Sell

**Targets: Practical Value criterion (20% of expert score)**

User-configurable exit strategy with optional automatic execution:

- **Take-profit threshold** (default 100%): position tracker proposes sell when PnL exceeds this
- **Stop-loss threshold** (default -50%): position tracker proposes sell when PnL drops below this
- **Auto-sell toggle** (default off): when enabled, sells execute immediately at thresholds without user approval — separate from the buy approval mode, since users may want auto-protection even in approve_each mode
- Settings UI: "Exit Strategy" section with numeric inputs + toggle switch

### O. Real-Time Toast Notifications

**Targets: Presentation criterion (20% of expert score) + Practical Value (20%)**

Real-time visual alerts for important events, powered by the existing WebSocket infrastructure:

- Toast notifications appear top-right, auto-dismiss after 5 seconds
- Event-specific styling: trade executed (green), action proposed (gold), risk alert (red)
- Position update toasts filtered to milestones only (50%+, 100%+, -40%+) to prevent spam
- Max 5 visible toasts, click to dismiss early
- Binance-themed color coding matching the dark UI

---

## 5. Non-Goals (v1)

Do NOT build:

- Full portfolio management / rebalancing
- Full social media intelligence suite
- Full creator analytics dashboard
- Arbitrary DeFi strategy backtesting
- Cross-chain support (BSC only)
- Freeform persona customization
- Autonomous trading without caps
- Token creation features (separate agent — don't dilute)
- Mobile app
- User accounts / auth system (wallet = identity)

---

## 6. User Flows

### Flow 1: First-Time Setup

```
Connect wallet
    → Pick persona (Conservative / Momentum / Sniper)
    → Set budget cap (or accept defaults)
    → Choose approval mode
    → Optional: register as ERC-8004 agent wallet
    → Land on scanner dashboard
```

### Flow 2: Finding a Trade

```
Agent detects new token or market signal
    → Scores risk (green / amber / red)
    → Generates plain-language rationale
    → Applies persona filter (buy / skip / monitor)
    → If buy: prepares transaction payload
    → Shows opportunity card with approve/reject buttons
    → User approves → agent executes
    → User rejects → agent logs and moves on
```

### Flow 3: Post-Trade Monitoring

```
Agent watches active position (60s cycle)
    → Checks PnL against user-configured take-profit / stop-loss thresholds
    → Every 5 min: AI analyzes drift triggers (approaching thresholds, stale positions, holder changes)
    → Proposes exit with rationale (numeric or AI-generated)
    → If auto-sell enabled: executes immediately
    → If auto-sell disabled: user approves the exit via toast notification
    → Position closed, PnL recorded
```

### Flow 4: Reviewing Avoided Risks

```
User opens "What I Avoided" tab
    → Sees tokens agent flagged red
    → Each shows current price vs. price at flag time
    → Confirmed rugs highlighted
    → Running tally of estimated savings
```

---

## 7. Web App Pages

### Dashboard (Home)

- Active persona badge + budget remaining
- Live opportunity feed (new launches, scored and ranked)
- Current positions with unrealized PnL
- Agent status indicator (scanning / idle / proposing)
- Quick stats: trades today, avoided rugs, budget used

### Opportunity Detail

- Token name, symbol, contract address, launch time
- Bonding curve progress (visual bar)
- Risk score breakdown (each signal scored)
- LLM-generated rationale (2-3 sentences)
- Creator wallet history (prior launches, outcomes)
- Recommended action from persona
- Approve / Reject buttons
- Transaction preview (amount, slippage, gas estimate)

### Positions

- Active positions with entry price, current price, PnL
- Agent's recommendation for each (hold / trim / exit)
- Approve action buttons per position

### What I Avoided

- Feed of red-scored tokens with timestamps
- Current status: price now vs. price at flag time
- Confirmed rug indicators
- Cumulative savings estimate

### Activity Feed

- Chronological log of:
  - Scans performed
  - Opportunities scored
  - Trades proposed
  - Trades approved / rejected
  - Trades executed
  - Alerts raised
  - User overrides (with outcome tracking)

### Settings

- Persona selection (switch anytime)
- Budget caps (all configurable)
- Approval mode
- Exit strategy: take-profit %, stop-loss %, auto-sell toggle
- Wallet management
- Agent wallet ERC-8004 registration
- Watchlist management
- Slippage / cooldown preferences

---

## 8. Architecture

### System Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite + Tailwind)              │
│  Dashboard │ Opportunity Detail │ Positions │ Avoided │ Settings │
│                                                                  │
│  Wallet Connection (wagmi + viem)                                │
│  Approval Modal → Approve/Reject → WebSocket Live Updates        │
└──────────────────────────┬───────────────────────────────────────┘
                           │ REST API + WebSocket (live feed)
┌──────────────────────────▼───────────────────────────────────────┐
│                      FastAPI Backend                              │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐      │
│  │ Scanner      │  │ Risk Scoring │  │ Persona Action     │      │
│  │ Service      │──│ Engine       │──│ Engine             │      │
│  │ (30s poll)   │  │ (8 signals)  │  │ (Consv/Mom/Snipe)  │      │
│  └──────┬──────┘  └──────┬───────┘  └────────┬───────────┘      │
│         │                │                    │                   │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌────────▼───────────┐      │
│  │ Four.meme   │  │ LLM Service  │  │ Trade Executor      │      │
│  │ REST Client │  │ (Gemini)     │  │ (via CLI subprocess) │      │
│  └─────────────┘  └──────────────┘  └────────────────────┘      │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐      │
│  │ BSC Web3.py │  │ Avoided Log  │  │ Override Tracker    │      │
│  │ (on-chain)  │  │ Service      │  │ (Behavioral Nudge)  │      │
│  └─────────────┘  └──────────────┘  └────────────────────┘      │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐      │
│  │ Market API  │  │ Four.meme    │  │ Approval Gate       │      │
│  │ (CoinGecko) │  │ CLI Wrapper  │  │ (4 modes)           │      │
│  └─────────────┘  └──────────────┘  └────────────────────┘      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐      │
│  │              SQLite (local-first, aiosqlite)            │      │
│  │  tokens │ scans │ positions │ trades │ avoided │ config │      │
│  │  activity │ token_snapshots │ overrides │ pending_actions│     │
│  └────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   Four.meme CLI     Web3.py (BSC)    Four.meme REST API
   (buy/sell/         (risk scoring:   (token search,
    quotes/8004)      holders,creator  rankings, metadata)
                      history,contracts)
          │                │
          └────────┬───────┘
              BSC (BNB Chain)
    TokenManager2 │ TokenManagerHelper3 │ AgentIdentifier
    TaxToken │ ERC20 │ PancakeSwap Router
```

### Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React + Vite + Tailwind CSS | Fast build, polished output, dark Binance-inspired theme |
| Backend | Python FastAPI | Best Web3.py + LLM SDK access, async-native |
| Database | SQLite (aiosqlite) | Local-first, zero config, sufficient for MVP |
| On-chain reads | Web3.py | Direct contract calls for risk scoring (TokenManagerHelper3, TokenManager2, TaxToken, ERC20) |
| Trading | Four.meme CLI (`@four-meme/four-meme-ai`) | Buy/sell execution, price quotes, ERC-8004 registration via subprocess |
| AI/LLM | Google Gemini 2.5 Flash (`google-genai` SDK) | Rationale generation, token description analysis, sentiment |
| Wallet | wagmi + viem (frontend) | Standard BSC wallet connection |
| Market Data | Four.meme API + CoinGecko + Alternative.me | Token feeds, BNB price, Fear & Greed index |
| Deploy | Vercel (frontend) + Railway (backend) | Free tier sufficient for demo |

### Four.meme Integration Points

**Hybrid integration:** CLI for trading actions, Web3.py for on-chain reads, REST API for token discovery.

| Integration | Method | Purpose |
|-------------|--------|---------|
| New token feed | Four.meme REST API (`POST /public/token/search`) | Discover launches in real time (30s polling) |
| Token metadata | Four.meme REST API (`GET /private/token/get/v2`) | Name, symbol, description, creator, image |
| Token rankings | Four.meme REST API (`POST /public/token/ranking`) | Trending/hot tokens |
| Bonding curve state | Web3.py (`TokenManagerHelper3.getTokenInfo()`) | Progress, funds, max funds, graduation status |
| Holder concentration | Web3.py (ERC20 Transfer events + `balanceOf`) | Top holder %, distribution analysis |
| Creator history | Web3.py (`TokenManager2` TokenCreate events) | Prior launches by creator wallet |
| Tax token inspection | Web3.py (`TaxToken` ABI: `feeRate`, allocation rates) | Check fee parameters for risk scoring |
| Buy/sell execution | Four.meme CLI (`fourmeme buy`, `fourmeme sell`) | Trade on bonding curve via subprocess |
| Price quotes | Four.meme CLI (`fourmeme quote-buy`, `fourmeme quote-sell`) | Pre-trade price estimates |
| Agent identity | Four.meme CLI (`fourmeme 8004-register`) + Web3.py (`AgentIdentifier.isAgent`) | Register and verify ERC-8004 agent wallet |
| Block events | Four.meme CLI (`fourmeme events`) | TokenPurchase, TokenSale, LiquidityAdded events |

### AI Orchestration

Use AI where it adds judgment. Use deterministic logic where it doesn't.

| Task | Method |
|------|--------|
| Risk signal computation | Deterministic (Web3.py reads + math) |
| Score aggregation | Rules engine (weighted scoring, 8 signals) |
| Rationale generation | LLM (Google Gemini 2.5 Flash) — multi-signal narrative synthesis |
| Token description analysis | LLM (classify as legit/scam/hype) |
| Interactive AI advisor | LLM (Gemini) — context-aware conversational chat about tokens, risks, decisions |
| Social sentiment | VADER (lightweight, no API key needed) |
| Persona action decision | Rules engine (persona config → action) |
| AMBER token deep analysis | LLM escalation pipeline (only for uncertain tokens where AI adds value) |
| Transaction building | Four.meme CLI (subprocess) |
| Override tracking | Deterministic (log + compare) |
| Market context | CoinGecko (BNB price) + Alternative.me (Fear & Greed) |

**Agent orchestration pattern:**

```
1. Scanner polls Four.meme REST API for new tokens (30s interval)
2. New tokens stored in SQLite, broadcast via WebSocket
3. Unscored tokens queued for risk engine (10 per cycle)
4. Risk engine computes all 8 signals (Web3.py + API + VADER)
5. Weighted aggregation → GREEN/AMBER/RED grade
6. LLM generates plain-language rationale (Gemini, async)
7. Persona engine applies rules → buy/skip/monitor action
8. If buy: prepare TX via CLI quote, push to approval gate
9. User approves → CLI executes trade → position tracked
```

---

## 9. Database Schema

```sql
-- Token discoveries
CREATE TABLE tokens (
    address TEXT PRIMARY KEY,
    name TEXT,
    symbol TEXT,
    creator_address TEXT,
    launch_time TEXT,
    risk_score TEXT,           -- green / amber / red
    risk_detail TEXT,          -- JSON: individual signal scores
    risk_rationale TEXT,       -- LLM-generated explanation
    bonding_curve_progress REAL,
    graduated INTEGER DEFAULT 0,
    is_tax_token INTEGER DEFAULT 0,
    last_checked TEXT,
    created_at TEXT
);

-- Scan events
CREATE TABLE scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    scan_type TEXT,            -- new_launch / price_spike / volume_spike / graduation
    risk_score TEXT,
    persona_action TEXT,       -- buy / skip / monitor / exit
    rationale TEXT,
    created_at TEXT
);

-- Active and closed positions
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    entry_price REAL,
    entry_amount_bnb REAL,
    token_quantity REAL,
    current_price REAL,
    status TEXT,               -- active / closed / stopped_out
    exit_price REAL,
    exit_amount_bnb REAL,
    pnl_bnb REAL,
    entry_risk_score TEXT,
    opened_at TEXT,
    closed_at TEXT
);

-- Trade execution log
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER,
    token_address TEXT,
    side TEXT,                 -- buy / sell
    amount_bnb REAL,
    token_quantity REAL,
    price REAL,
    tx_hash TEXT,
    slippage REAL,
    gas_used REAL,
    approval_mode TEXT,        -- manual / auto / threshold
    was_override INTEGER DEFAULT 0,  -- did user override agent recommendation?
    executed_at TEXT
);

-- What I Avoided log
CREATE TABLE avoided (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    token_name TEXT,
    risk_score TEXT,
    risk_rationale TEXT,
    price_at_flag REAL,
    price_1h_later REAL,
    price_6h_later REAL,
    price_24h_later REAL,
    confirmed_rug INTEGER DEFAULT 0,
    estimated_savings_bnb REAL,
    flagged_at TEXT
);

-- User configuration
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Watchlist
CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type TEXT,            -- token / creator / pattern
    value TEXT,
    label TEXT,
    created_at TEXT
);

-- Activity feed
CREATE TABLE activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT,            -- new_token / risk_scored / trade_executed / override / etc.
    token_address TEXT,
    detail TEXT,                -- JSON payload
    created_at TEXT
);

-- Token snapshots (for velocity tracking)
CREATE TABLE token_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    funds_wei TEXT,
    offers TEXT,
    holder_count INTEGER,
    snapshot_at TEXT
);

-- User overrides (behavioral nudge)
CREATE TABLE overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    override_type TEXT,         -- approved_red / rejected_green
    risk_score TEXT,
    outcome_checked INTEGER DEFAULT 0,
    outcome_detail TEXT,
    created_at TEXT
);

-- Pending actions (approval queue)
CREATE TABLE pending_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    action TEXT,                -- buy / sell
    amount_bnb REAL,
    slippage REAL,
    persona TEXT,
    risk_score TEXT,
    rationale TEXT,
    status TEXT DEFAULT 'pending',  -- pending / approved / rejected / expired
    created_at TEXT,
    resolved_at TEXT
);

-- Indexes
CREATE INDEX idx_tokens_creator ON tokens (creator_address);
CREATE INDEX idx_tokens_risk ON tokens (risk_score);
CREATE INDEX idx_scans_token ON scans (token_address);
CREATE INDEX idx_positions_status ON positions (status);
CREATE INDEX idx_avoided_flagged ON avoided (flagged_at);
CREATE INDEX idx_activity_type ON activity (event_type);
CREATE INDEX idx_activity_token ON activity (token_address);
```

---

## 10. Trust & Safety Controls

| Control | Implementation |
|---------|---------------|
| Spend caps | Hard-coded max per trade / per day / active positions — enforced server-side |
| Token denylist | User can block specific tokens or creators |
| Min liquidity threshold | Agent skips tokens with <$500 liquidity |
| Max slippage guard | Transaction reverts if slippage exceeds user setting |
| Cooldown | Minimum 60s between trades (configurable) |
| Confirm before execution | Always shows full TX preview before signature |
| Session timeout | Auto-lock after 30 min inactivity |
| Private key safety | Never stored in plaintext; encrypted local storage or wallet provider |
| Read-only fallback | Monitor-only mode requires zero on-chain permissions |
| Agent wallet separation | Recommend using a dedicated hot wallet, not main holdings |

---

## 11. Build Order

### Phase 1 — Foundation (COMPLETE)

**Goal:** Working dashboard that shows live Four.meme launches with risk scores.

- [x] Project scaffolding: FastAPI backend + React/Vite frontend + SQLite (aiosqlite)
- [x] BSC Web3 provider setup (Web3.py with POA middleware, V1+V2 token struct decode)
- [x] Four.meme REST API client (httpx): search, get, rankings
- [x] Four.meme CLI wrapper (async subprocess): buy/sell/quotes/events/8004
- [x] Market context client: CoinGecko BNB price + Alternative.me Fear & Greed
- [x] Scanner service (30s polling): discovers tokens, queues for scoring, broadcasts via WebSocket
- [x] Risk scoring engine: all 8 signals implemented with weighted aggregation
- [x] LLM service: Google Gemini provider with fallback rationale
- [x] Persona engine: 3 personas with decide_action() rules
- [x] Trade executor: buy/sell via CLI, position/trade recording
- [x] Approval gate: 4 modes
- [x] Backend routes: tokens, config, activity, positions, actions, avoided, watchlist
- [x] Wallet connection UI (wagmi + viem, BSC chain)
- [x] Frontend: Dashboard (live feed + stats), Settings (persona + budget), OpportunityDetail (8-signal breakdown), Positions, Avoided (stats + cards), Activity feed
- [x] Components: Navbar, TokenCard, RiskBadge, PersonaSelector, BudgetBar
- [x] WebSocket: auto-reconnecting, live push for new tokens and risk scores
- [x] Dark Binance-inspired theme (CSS variables, Tailwind)

**Status:** All pages functional. Scanner discovering and scoring real Four.meme tokens. 8-signal risk engine producing GREEN/AMBER/RED grades with detailed per-signal breakdowns.

### Phase 2 — The Brain (COMPLETE)

**Goal:** End-to-end trade loop (buy + sell) with AI depth, position tracking, and real-time alerting.

#### Core Pipeline
- [x] Complete risk scoring engine: all 8 signals (done in Phase 1)
- [x] LLM integration (Gemini) for rationale generation
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
- [x] End-to-end buy loop: verified with 0.0001 BNB trade on-chain

#### Sell Flow & Position Management
- [x] Complete sell executor: sell quote, slippage protection, position closure, trade recording, PnL fields
- [x] Configurable take-profit/stop-loss thresholds (Settings UI, replaces hardcoded 100%/-50%)
- [x] Auto-sell mode: automatic sell execution at thresholds without approval
- [x] AI-driven position monitoring: Gemini exit analysis every 5 min with drift detection (capped at 3 LLM calls/cycle)
- [x] End-to-end sell loop: position tracker proposes → approve/auto-sell → execute → position closed (verified with 0.0001 BNB, tx `0x3a7f…6e9f`)

#### AI Depth (Competitive Edge)
- [x] Interactive AI chat advisor: `POST /api/chat` endpoint + frontend ChatPanel on Dashboard/OpportunityDetail
- [x] Multi-signal narrative synthesis: enhanced LLM prompt correlating all 8 signals into a pattern-detecting narrative
- [x] Escalation pipeline: quick deterministic scan for GREEN/RED, deep AI analysis reserved for AMBER tokens

#### Real-Time Alerting
- [x] `action_proposed` — trade opportunity pending approval
- [x] `trade_executed` — buy/sell completed with tx details
- [x] `position_update` — PnL change (periodic, from position tracker; toast filtered to milestones ≥50%, ≥100%, ≤-40%)
- [x] `risk_alert` — token grade changed on rescore
- [x] Toast notification system: real-time visual alerts for all WebSocket events (max 5 visible, auto-dismiss 5s)
- [x] `avoided_update` — "dodged a bullet" notification (shipped with Phase 3 avoided tracker)

**End of Phase 2 deliverable:** Full trade loop (buy + sell) works with AI advisor and AI-driven position monitoring. Agent finds token, scores it, synthesizes a narrative, proposes trade, user can ask questions via chat, approves, trade executes, position tracked with AI exit analysis. Sells execute with configurable thresholds and optional auto-sell. Dashboard shows real-time toast notifications for all important events.

### Phase 3 — Polish & Demo Features (MOSTLY COMPLETE)

**Goal:** Demo-ready with killer differentiators and visual polish. Ordered by judging impact.

#### High Priority (Differentiators)
- [x] ERC-8004 agent identity registration: `agent_identity.py` service + Settings UI card + on-chain tx verification (verified: agent wallet registered on BSC mainnet)
- [x] "What I Avoided" background job: checks red-flagged token prices at 1h/6h/24h, confirmed rug detection, savings tally (39+ tokens flagged live)
- [x] Risk visualization: recharts `RadarChart` on OpportunityDetail showing 8-signal breakdown
- [x] Backend Docker self-host (`Dockerfile` + `docker-compose.yml` + `.dockerignore`, SQLite volume persistence verified)
- [ ] Deployment: provision Railway/Render (backend) + Vercel (frontend) for a live URL

#### Medium Priority (Completeness)
- [x] Behavioral nudge: tracks overrides (approve RED / reject GREEN), shows outcome summary on Dashboard
- [x] Watchlist management UI on Settings page (creator + token addresses, add/remove)
- [x] Volume consistency signal: real implementation via on-chain Transfer event analysis (wash-trading detection)

#### Verification
- [x] Playwright UI pass: dashboard, opportunity detail (radar + 8 signals + AMBER deep-analysis narrative), avoided stats, settings (8004 card, persona, approval, exit strategy, budget, watchlist), AI chat panel — all render correctly
- [x] Fixed during verification: event-loop blocking on sync Web3 calls (`3476eb4`); SQLite `database is locked` + ghost-token AMBER mis-grading (`295bd0f`)
- [x] Wallet-gated smoke test: ERC-8004 register tx + buy approve-sign via API → real on-chain trade recorded (position_id 4, 13,069 ORDI tokens, tx `0x8a9e…dbdb`)

#### Demo & Submission
- [x] Visual polish: card fade-in, hover glow, pulsing scanner dot, responsive grid
- [x] README.md with architecture diagram, setup instructions, deployment section, security model
- [ ] Demo seed script for pre-populated avoided rugs (deferred — avoided tracker accumulates naturally over 24h)
- [ ] Demo video recording (3-5 min, see demo script below)
- [ ] DoraHacks BUIDL submission (GitHub repo + demo video link)

---

## 12. Demo Script (3–4 minutes)

This is the narrative arc a judge will see:

**Scene 1 — Setup (30s)**
Open the app. Connect wallet. Register as ERC-8004 agent (show the on-chain tx — proves Four.meme integration depth). Choose "Momentum" persona. Set 0.5 BNB daily cap. Approve-each mode.

**Scene 2 — Scanning (45s)**
Dashboard lights up with live Four.meme launches. Each token card shows name, launch age, bonding curve progress, and a green/amber/red risk badge. Point out a red-scored token: "This creator launched 3 tokens yesterday — all rugged within 2 hours. Agent automatically flags this."

**Scene 3 — Opportunity + AI Advisor (75s)**
Agent highlights a green-scored token. Click into the detail page. Show the risk radar chart and full 8-signal breakdown. Read the multi-signal narrative: "First-time creator with organic social activity. Volume is consistent, not wash-traded. No cross-signal red flags detected." Open the AI advisor chat and ask: "Why does the Momentum persona want to buy this?" — advisor explains the specific signals that triggered the buy recommendation. Click "Approve."

**Scene 4 — Execution (30s)**
Transaction preview shows exact swap details. Sign with wallet. TX confirms on BSC. Position appears in the portfolio view with entry price and live PnL.

**Scene 5 — What I Avoided (45s)**
Switch to the "What I Avoided" tab. Show 4 tokens the agent flagged red earlier in the session. Two have already dropped 90%+. One had liquidity pulled entirely. Running tally: "Avoided 3 confirmed rugs — estimated savings: 0.15 BNB." This is the moment the judge goes "oh, that's useful."

**Scene 6 — Close (15s)**
Back to dashboard. Show the behavioral summary: "1 trade executed. 3 rugs avoided. 0 overrides." End with tagline: "FourScout — your AI sentinel for Four.meme."

---

## 13. What Makes This Hackathon-Worthy

### Judging Criteria Alignment

Projects are evaluated through **expert review (70%)** and **community voting (30%)**.

| Judging Criterion | Weight | How FourScout Delivers |
|-------------------|--------|----------------------|
| **Innovation** (originality + depth of AI) | 30% of expert | Interactive AI advisor (conversational, not just labels). Multi-signal narrative synthesis (pattern detection across 8 signals). Escalation pipeline (deterministic core + deep AI for uncertain cases). ERC-8004 on-chain agent identity. |
| **Technical Implementation** (code quality + demo stability) | 30% of expert | Complete end-to-end pipeline: discover → score → propose → approve → execute → track. 8-signal deterministic risk engine. 4 approval modes. Budget-capped autonomy. Hybrid integration (CLI + Web3.py + REST API). |
| **Practical Value** (user impact + commercial potential) | 20% of expert | "What I Avoided" — concrete savings visualization. Position lifecycle management. Budget enforcement. Persona presets for different risk profiles. Solves real information asymmetry on Four.meme. |
| **Presentation** (pitch clarity + execution capability) | 20% of expert | Risk radar chart visualization. Real-time WebSocket dashboard. Dark Binance-inspired theme. Demo video with scripted narrative arc. |
| **Community Voting** | 30% of total | Deployed on Vercel for public access. Visual polish + animations. Screenshot-worthy "What I Avoided" section. Live trading demo. |

### Core Value Proposition

| Criterion | How FourScout Delivers |
|-----------|----------------------|
| Real problem | Memecoin traders lose money to rugs daily. Information asymmetry on Four.meme is unsolved. |
| Narrow scope | Three capabilities: scan, score, execute. Not trying to be everything. |
| Agentic behavior | Holds wallet, reads market, makes decisions, executes transactions, learns from outcomes. |
| On-chain action | Reads Four.meme contracts, executes swaps on BSC, registers as ERC-8004 agent. |
| Four.meme fit | Built specifically for Four.meme's API, bonding curve, Agentic Mode, and agent identity system. |
| AI depth | Interactive advisor, multi-signal narrative synthesis, escalation pipeline for uncertain tokens. |
| Configurable persona | Three presets with predefined strategies — directly matches AMA guidance. |
| Human oversight | Four approval modes + hard budget caps. User controls the leash. |
| Market awareness | Fear & Greed index, BNB trend, per-token sentiment and on-chain signals. |
| Immediately usable | Open app → connect wallet → pick persona → agent starts working. 2-minute setup. |
| Visual quality | Dark Binance-inspired dashboard, real-time feed, risk radar chart, approval modals, portfolio view. |

---

## 14. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Four.meme API changes or goes down | Cache token data, fallback to on-chain reads only |
| LLM latency slows down scoring | Generate rationale async; show score immediately, rationale loads after |
| BSC testnet vs mainnet differences | Develop on testnet, final demo on mainnet with tiny amounts |
| Too many features for solo build | Phase 3 items are nice-to-have; Phase 1+2 alone is a viable submission |
| Private key security concerns | Strong recommendation for dedicated hot wallet; never store keys server-side |

---

## 15. File Structure

```
meme-guard/
├── backend/
│   ├── main.py                    # FastAPI app + WebSocket + lifespan (init DB, start scanner)
│   ├── config.py                  # Pydantic Settings from .env + Contracts + BudgetDefaults
│   ├── database.py                # aiosqlite: 11 tables, init_db(), get/set_config helpers
│   ├── requirements.txt           # Pinned deps (fastapi, web3, google-genai, httpx>=0.28.1, etc.)
│   ├── services/
│   │   ├── scanner.py             # Token discovery: polls Four.meme API, stores tokens, queues scoring
│   │   ├── risk_engine.py         # All 8 deterministic signals, weighted aggregation → GREEN/AMBER/RED
│   │   ├── persona_engine.py      # 3 persona configs → decide_action() → buy/skip/monitor/exit
│   │   ├── llm_service.py         # Google Gemini provider (google-genai SDK), fallback rationale
│   │   ├── chat_service.py        # Interactive AI advisor: context-aware conversational chat
│   │   ├── tx_builder.py          # prepare_buy/sell via CLI quote → TxPreview
│   │   ├── executor.py            # execute_approved_action() via Four.meme CLI, record trades/positions
│   │   ├── approval_gate.py       # 4 approval modes: approve_each, per_session, budget_threshold, monitor
│   │   ├── position_tracker.py    # PnL tracking, exit recommendations
│   │   ├── avoided_tracker.py     # "What I Avoided" background checker (1h/6h/24h price checks)
│   │   └── agent_identity.py      # ERC-8004 registration via CLI + verification via Web3.py
│   ├── clients/
│   │   ├── fourmeme_cli.py        # Async subprocess wrapper for @four-meme/four-meme-ai CLI
│   │   ├── fourmeme_api.py        # Four.meme REST API (httpx): search, get, rankings, config
│   │   ├── bsc_web3.py            # Web3.py: getTokenInfo (V1+V2 raw decode), holders, creator history, tax
│   │   └── market_api.py          # CoinGecko BNB price + Alternative.me Fear & Greed
│   ├── abis/                      # Lite contract ABIs (only needed functions/events)
│   │   ├── TokenManager2.json     # Events: TokenCreate, TokenPurchase, TokenSale, LiquidityAdded
│   │   ├── TokenManagerHelper3.json # getTokenInfo, tryBuy, trySell
│   │   ├── AgentIdentifier.json   # isAgent, nftCount, nftAt
│   │   ├── TaxToken.json          # feeRate, rateFounder, rateHolder, rateBurn, rateLiquidity
│   │   └── ERC20.json             # Transfer event, balanceOf, totalSupply
│   └── routes/
│       ├── tokens.py              # GET /api/tokens, GET /api/tokens/{address}
│       ├── actions.py             # GET /api/actions/pending, POST approve/reject
│       ├── positions.py           # GET /api/positions
│       ├── avoided.py             # GET /api/avoided, GET /api/avoided/stats
│       ├── config_routes.py       # GET/PUT /api/config, PUT /api/config/bulk
│       ├── watchlist.py           # GET/POST/DELETE /api/watchlist
│       ├── activity.py            # GET /api/activity
│       └── chat.py                # POST /api/chat (interactive AI advisor)
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # BrowserRouter (6 routes) + WagmiProvider + QueryClientProvider
│   │   ├── index.css              # @import "tailwindcss" + Binance dark theme CSS variables
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx      # Live token feed + persona badge + budget bar + stats
│   │   │   ├── OpportunityDetail.jsx  # Full 8-signal risk breakdown + rationale + approve/reject
│   │   │   ├── Positions.jsx      # Active/closed positions table with PnL
│   │   │   ├── Avoided.jsx        # Stats banner + avoided token cards + savings tally
│   │   │   ├── Activity.jsx       # Chronological event feed
│   │   │   └── Settings.jsx       # Persona selector + approval mode + budget caps
│   │   ├── components/
│   │   │   ├── Navbar.jsx         # Navigation + wallet connect button
│   │   │   ├── TokenCard.jsx      # Token info + risk badge + bonding curve progress bar
│   │   │   ├── RiskBadge.jsx      # Green/amber/red pill badge
│   │   │   ├── PersonaSelector.jsx # 3 persona cards with descriptions
│   │   │   └── BudgetBar.jsx      # Daily budget progress indicator
│   │   ├── hooks/
│   │   │   ├── useWallet.js       # wagmi config for BSC (chain ID 56), injected connector
│   │   │   └── useWebSocket.js    # Auto-reconnecting WebSocket, message buffer, getByType()
│   │   └── services/
│   │       └── api.js             # Fetch wrapper for all backend endpoints
│   ├── package.json
│   └── vite.config.js             # React + Tailwind plugins, /api and /ws proxy to backend
├── fourmeme-cli/                  # Local npm install of @four-meme/four-meme-ai (gitignored)
├── FourScout.md                   # This file — full MVP specification
├── CLAUDE.md                      # Project reference for development
├── .env.example
└── .gitignore
```

---

## 16. Environment Variables

```env
# BSC
BSC_RPC_URL=https://bsc-dataseed1.binance.org

# Four.meme CLI (agent hot wallet — never use main holdings)
PRIVATE_KEY=                  # Hex private key for agent wallet

# Four.meme API
FOURMEME_API_BASE=https://four.meme/meme-api/v1

# AI / LLM
GEMINI_API_KEY=               # Google Gemini API key (free tier)

# App
DATABASE_PATH=./data/fourscout.db
SCAN_INTERVAL_SECONDS=30
```

Contract addresses are hardcoded in `backend/config.py` (Contracts class) — not environment variables, since they don't change between environments.

---

## 17. Minimal Viable Demo (If Time Runs Short)

If Phase 3 gets cut, the minimum viable submission is:

- Dashboard with live Four.meme token feed (DONE)
- Risk scoring with green/amber/red badges, all 8 signals (DONE)
- All three personas working with action decisions (DONE)
- Activity feed showing what the agent did (DONE)
- Transaction preview + approval + execution (Phase 2, in progress)
- Position tracking with PnL (Phase 2, in progress)
- **Interactive AI advisor chat** (Phase 2 — highest Innovation differentiator)
- **ERC-8004 agent registration** (Phase 3 — low effort, high Four.meme signal)

That alone is a complete agentic product with AI depth, on-chain action, and deep Four.meme integration. The "What I Avoided" log is the highest-impact Phase 3 item — prioritize it over visual polish. The AI advisor and ERC-8004 are the two features most likely to differentiate from other submissions.

---

## 18. Roadmap: Non-Custodial Session Keys

**Status:** Design only. Not implemented in the MVP. This section describes how FourScout evolves from a single-tenant, self-hosted tool into a hosted product without ever custodying user funds.

### The Problem with the Current Model

The MVP stores one `PRIVATE_KEY` in `backend/.env`. The backend reads it, hands it to the Four.meme CLI subprocess, and the CLI signs every transaction (buy, sell, ERC-8004 register). This is correct for a **self-hosted single-user** deployment — the user owns the key, the server, and the risk.

It is wrong for a hosted SaaS. Two naive alternatives both fail:

- **Custody everyone's keys.** Server generates a keypair per user, encrypts it at rest. One breach drains every user's wallet. Makes the operator a regulated money transmitter in most jurisdictions.
- **Prompt-to-sign every tx in MetaMask.** Breaks the autonomous loop. The position tracker can't auto-sell at 3 AM if it needs a signature prompt.

The resolution is **delegated signing with on-chain-enforced limits** — commonly called session keys. The user signs *once* to grant the server narrow authority. The server signs routine trades with that authority. The smart contract rejects anything outside the grant. The user revokes at any time.

### Target Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Smart account | **ZeroDev Kernel v3** | Most mature session-key module, modular validators, first-class BSC support. |
| Session-key module | **@zerodev/permissions** | Composable policies (call whitelist, spend limit, rate limit, expiry). |
| Bundler | **Pimlico** (BSC mainnet, chain 56) | Reliable, reasonable pricing, works with Kernel out of the box. |
| EntryPoint | **v0.7** (canonical BSC address) | Current ERC-4337 spec. |
| Paymaster | **None** (user pre-funds Kernel in BNB) | Simpler; memecoin agent doesn't need gasless UX. |

### Onboarding Flow (User-Facing, One-Time)

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Connect EOA  │ → │ Compute      │ → │ Fund Kernel  │ → │ Sign session │
│ (MetaMask)   │   │ Kernel addr  │   │ with BNB     │   │ key grant    │
└──────────────┘   │ (counterfact)│   │ (MetaMask)   │   └──────┬───────┘
                   └──────────────┘   └──────────────┘          │
                                                                ▼
                                                         ┌──────────────┐
                                                         │ Backend      │
                                                         │ stores key + │
                                                         │ policy hash  │
                                                         └──────────────┘
```

1. User connects their EOA (already wired today via wagmi).
2. Frontend computes counterfactual Kernel address — no gas cost until first use.
3. User sends BNB from MetaMask/CEX to the Kernel address. This **is** the agent wallet.
4. Frontend generates an ephemeral session-key keypair in the browser.
5. Frontend asks the user to sign a session-key grant in MetaMask with constraints:

   | Policy | Enforces |
   |--------|----------|
   | `toCallPolicy` | Only `TokenManager2`, `TokenManagerHelper3`, `BRC8004 Identity Registry` + specific selectors (`buyTokenAMAP`, `sellToken`, `register`). |
   | `toSpendingLimitPolicy` | Total BNB over session ≤ `max_per_day_bnb` × session days. |
   | `toRateLimitPolicy` | Max N userOps per hour — caps runaway-loop blast radius. |
   | `toTimestampPolicy` | 7-day expiry. User must re-grant to extend. |

6. Frontend posts `{smart_account_address, session_key_private, policy_hash, expires_at}` to the backend. The private key is encrypted at rest (libsodium sealed box or KMS envelope).

### Per-Trade Flow (Fully Autonomous)

No user interaction. Same decision pipeline as today — the only swap is the signing mechanism.

```
scanner → risk engine → persona → approval_gate → pending_action
                                                        │
                                                        ▼
                                              (auto or user approve)
                                                        │
                                                        ▼
                    ┌───────────────────────────────────┴────────────────────────────┐
                    │                                                                │
                    ▼                                                                ▼
          Today (MVP): CLI subprocess                              Future: session-signer sidecar
          ─ fourmeme buy <token> funds <wei>                       ─ Build userOp (sender=Kernel)
          ─ CLI signs with PRIVATE_KEY                             ─ Session key signs
          ─ Broadcast via BSC RPC                                  ─ Submit via Pimlico bundler
                                                                   ─ Kernel validates policies on-chain
                                                                   ─ Execute → BNB paid from Kernel
```

### Python ↔ TypeScript Bridge

ZeroDev's SDK is TypeScript-only. The backend is Python. The cleanest integration is a small Node sidecar alongside `fourmeme-cli/`:

```
session-signer/
├── package.json               # @zerodev/sdk, @zerodev/permissions, viem, express
├── src/
│   ├── index.ts               # POST /userop — build, sign, submit, return txHash
│   ├── policies.ts            # Rebuild policy object from stored policy_hash
│   └── kernel.ts              # Kernel client factory
└── tsconfig.json
```

The Python backend calls `POST http://localhost:3001/userop` via `httpx` with the same shape it already uses for CLI subprocess results. This mirrors the existing CLI-subprocess pattern — just a different port.

### What Stays the Same

Every policy layer above the signing boundary is unchanged:

- Persona rules (Conservative / Momentum / Sniper)
- 4 approval modes (approve each / per session / budget threshold / monitor only)
- Budget caps (max per trade, max per day, max active positions, min liquidity, max slippage, cooldown)
- Position tracker + AI exit analysis + auto-sell flag
- `fourmeme_cli.py` for read-only commands: `quote-buy`, `quote-sell`, `tax-info`, `events`, `token-rankings`, `token-info`

Session keys are a **signing mechanism swap**, not a policy rewrite. If the MVP rejects a trade, so does this. The delta is: even if the server is fully compromised, the smart contract rejects anything the user didn't authorize.

### Revocation

Two paths:

1. **Active revocation.** Settings page → "Revoke session" → user signs `disableValidator` in MetaMask → Kernel refuses future userOps signed by this key.
2. **Passive expiry.** Session key's `toTimestampPolicy` hits its deadline → Kernel starts rejecting. Backend detects via bundler error and prompts user to re-grant.

### Trade-offs, Honest

| Concern | Reality |
|---------|---------|
| Gas cost | userOp ~20–30% more gas than EOA tx. Fine for memecoin timeframes. |
| Latency | Bundler adds ~2–4s vs direct RPC broadcast. Scanner + exit checks already tolerate this. |
| BSC infra maturity | Pimlico and ZeroDev both support BSC mainnet, but AA tooling is younger on BSC than on Ethereum/Base. Validate with testnet first. |
| Kernel deployment cost | First userOp deploys the Kernel (~$1 in BNB). Acceptable one-time onboarding cost. |
| Complexity | Significant new surface (smart-account UX, session grants, revocation, key encryption-at-rest). Post-hackathon scope. |

### What This Unlocks

- **Hosted multi-tenant deployment** without custodial risk or regulatory weight.
- **User-visible auditability.** Every trade is a userOp signed by a session key with a revocable, time-bound, on-chain-enforced policy.
- **Composability with future AA features:** gas sponsorship, fee abstraction (pay in USDT), batched multi-trade ops, social recovery.
- **A credible pitch beyond the hackathon.** "Non-custodial AI trading agent with cryptographically bounded delegation" is a real product shape.

### Open Questions

- Policy upgrade path: if the user raises `max_per_day_bnb` in Settings, does that require a new session-key grant (new signature prompt) or can we layer per-session sub-policies?
- Session-signer sidecar deployment: separate container in `docker-compose.yml`, or merged into the backend container as a supervised process?
- Encryption-at-rest key: environment variable for self-hosted; KMS for eventual hosted deploy.
- Monitoring: userOp failures (bundler reverts, policy rejections) need distinct telemetry from today's CLI subprocess errors.

These are deliberately left unresolved. They become real decisions when implementation starts.

---

*Built for the Four.Meme AI Sprint hackathon. MIT License.*
