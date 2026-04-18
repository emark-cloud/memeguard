"""SQLite database initialization and async query helpers."""

import time

import aiosqlite
import os
from config import settings

# get_all_config() is called from the scanner, position tracker, approval gate,
# persona engine, and chat — roughly N+ times per scan cycle. Config only
# changes on explicit Settings saves, so TTL-cache the read and invalidate on
# writes. Not worth a whole connection pool, but this alone removes 10+
# redundant SQLite opens per cycle.
_CONFIG_TTL_S = 30.0
_config_cache: tuple[float, dict] | None = None

SCHEMA = """
-- Token discoveries
CREATE TABLE IF NOT EXISTS tokens (
    address TEXT PRIMARY KEY,
    name TEXT,
    symbol TEXT,
    creator_address TEXT,
    launch_time TEXT,
    risk_score TEXT,
    risk_detail TEXT,
    risk_rationale TEXT,
    bonding_curve_progress REAL,
    graduated INTEGER DEFAULT 0,
    is_tax_token INTEGER DEFAULT 0,
    last_checked TEXT,
    created_at TEXT
);

-- Scan events
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    scan_type TEXT,
    risk_score TEXT,
    persona_action TEXT,
    rationale TEXT,
    created_at TEXT
);

-- Active and closed positions
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    entry_price REAL,
    entry_amount_bnb REAL,
    token_quantity REAL,
    current_price REAL,
    status TEXT DEFAULT 'active',
    exit_price REAL,
    exit_amount_bnb REAL,
    pnl_bnb REAL,
    entry_risk_score TEXT,
    opened_at TEXT,
    closed_at TEXT
);

-- Trade execution log
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER,
    token_address TEXT,
    side TEXT,
    amount_bnb REAL,
    token_quantity REAL,
    price REAL,
    tx_hash TEXT,
    slippage REAL,
    gas_used REAL,
    approval_mode TEXT,
    was_override INTEGER DEFAULT 0,
    executed_at TEXT
);

-- What I Avoided log
CREATE TABLE IF NOT EXISTS avoided (
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
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Watchlist
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type TEXT,
    value TEXT,
    label TEXT,
    created_at TEXT
);

-- Activity feed
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT,
    token_address TEXT,
    detail TEXT,
    created_at TEXT
);

-- Token snapshots for velocity tracking
CREATE TABLE IF NOT EXISTS token_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    funds REAL,
    offers REAL,
    price REAL,
    holder_count INTEGER,
    captured_at TEXT
);

-- Override tracking for behavioral nudge
CREATE TABLE IF NOT EXISTS overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    agent_recommendation TEXT,
    user_action TEXT,
    outcome_price_change REAL,
    outcome_was_correct TEXT,
    created_at TEXT
);

-- Pending actions (proposed by agent, awaiting approval)
CREATE TABLE IF NOT EXISTS pending_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    action_type TEXT,
    amount_bnb REAL,
    slippage REAL,
    persona TEXT,
    risk_score TEXT,
    rationale TEXT,
    tx_preview TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    resolved_at TEXT
);

-- Persistent chat history for the AI advisor.
-- token_address NULL  => global (dashboard) chat.
-- token_address != '' => OpportunityDetail chat scoped to that token.
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    role TEXT,
    content TEXT,
    created_at TEXT
);

-- Creator reputation cache. Avoids re-scanning 50k blocks for repeat creators
-- and folds closed-trade / rug outcomes back into the creator score.
CREATE TABLE IF NOT EXISTS creator_reputation (
    creator_address TEXT PRIMARY KEY,
    launch_count INTEGER DEFAULT 0,
    avg_24h_outcome_pct REAL,
    confirmed_rugs INTEGER DEFAULT 0,
    profitable_closes INTEGER DEFAULT 0,
    losing_closes INTEGER DEFAULT 0,
    last_updated TEXT
);

-- Signal accuracy tracker. Joins entry signals (from tokens.risk_detail) to
-- eventual outcomes so the risk engine can surface "historical calibration"
-- summaries in its rationale.
CREATE TABLE IF NOT EXISTS signal_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT,
    entry_risk_grade TEXT,
    entry_risk_percentage REAL,
    creator_score INTEGER,
    concentration_score INTEGER,
    velocity_score INTEGER,
    liquidity_score INTEGER,
    outcome_type TEXT,          -- 'trade_closed' | 'avoided_24h'
    outcome_pnl_pct REAL,
    outcome_price_change_pct REAL,
    outcome_confirmed_rug INTEGER,
    recorded_at TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tokens_creator ON tokens (creator_address);
CREATE INDEX IF NOT EXISTS idx_tokens_risk ON tokens (risk_score);
CREATE INDEX IF NOT EXISTS idx_scans_token ON scans (token_address);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions (status);
CREATE INDEX IF NOT EXISTS idx_positions_token_status ON positions (token_address, status);
CREATE INDEX IF NOT EXISTS idx_avoided_flagged ON avoided (flagged_at);
CREATE INDEX IF NOT EXISTS idx_activity_type ON activity (event_type);
CREATE INDEX IF NOT EXISTS idx_snapshots_token ON token_snapshots (token_address);
CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_actions (status);
CREATE INDEX IF NOT EXISTS idx_pending_token_status ON pending_actions (token_address, status);
CREATE INDEX IF NOT EXISTS idx_trades_executed ON trades (executed_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_token ON chat_messages (token_address, id);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_grade ON signal_outcomes (entry_risk_grade, recorded_at);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_token ON signal_outcomes (token_address);
CREATE INDEX IF NOT EXISTS idx_overrides_token ON overrides (token_address, created_at);
"""


# Columns added after the initial schema. ALTER TABLE ADD COLUMN is the only
# migration SQLite supports cleanly, and it has no "IF NOT EXISTS" form, so we
# check PRAGMA table_info first. Each entry: (table, column, column_definition).
_COLUMN_MIGRATIONS = [
    ("pending_actions", "rejection_reason", "TEXT"),
    ("positions", "last_ai_check_at", "TEXT"),
    ("positions", "last_ai_pnl_pct", "REAL"),
    # Captured at the moment an avoided (RED) token is flagged so the 24h
    # check can detect abandonment by comparing bonding-curve funds delta,
    # not just lastPrice (which sticks to the formula price on dead tokens).
    ("avoided", "funds_at_flag_bnb", "REAL"),
]

# Default configuration values
DEFAULT_CONFIG = {
    "persona": "momentum",
    "approval_mode": "approve_each",
    "min_per_trade_bnb": "0.002",
    "max_per_trade_bnb": "0.05",
    "max_per_day_bnb": "0.3",
    "max_active_positions": "3",
    "max_slippage_pct": "5.0",
    "cooldown_seconds": "60",
    "min_liquidity_usd": "500",
    "take_profit_pct": "100",
    "stop_loss_pct": "-50",
    "auto_sell_enabled": "false",
}


def get_db_path() -> str:
    db_path = settings.database_path
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    return db_path


async def _apply_column_migrations(db):
    """Add new columns to existing tables (SQLite lacks ADD COLUMN IF NOT EXISTS)."""
    for table, column, col_def in _COLUMN_MIGRATIONS:
        cursor = await db.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in await cursor.fetchall()}
        if column not in existing:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")


async def _backfill_signal_outcomes(db):
    """Populate signal_outcomes retroactively from existing closed positions
    and resolved avoided rows. Only runs when the table is empty — safe to
    call on every startup because subsequent runs no-op.

    This gives a fresh deployment immediate "historical calibration" data
    without waiting for 30 days of operation.
    """
    cursor = await db.execute("SELECT COUNT(*) FROM signal_outcomes")
    if (await cursor.fetchone())[0] > 0:
        return

    # Closed positions: join tokens.risk_detail (JSON) to read entry signal scores.
    cursor = await db.execute(
        """SELECT p.token_address, p.entry_risk_score, p.entry_amount_bnb, p.pnl_bnb,
                  p.closed_at, t.risk_detail
           FROM positions p LEFT JOIN tokens t ON p.token_address = t.address
           WHERE p.status = 'closed'"""
    )
    closed = await cursor.fetchall()
    import json as _json
    for row in closed:
        scores = _extract_signal_scores(row["risk_detail"], _json)
        pnl_pct = None
        entry = row["entry_amount_bnb"] or 0
        if entry > 0 and row["pnl_bnb"] is not None:
            pnl_pct = (row["pnl_bnb"] / entry) * 100
        await db.execute(
            """INSERT INTO signal_outcomes (token_address, entry_risk_grade, entry_risk_percentage,
               creator_score, concentration_score, velocity_score, liquidity_score,
               outcome_type, outcome_pnl_pct, recorded_at)
               VALUES (?, ?, NULL, ?, ?, ?, ?, 'trade_closed', ?, ?)""",
            (
                row["token_address"], row["entry_risk_score"],
                scores["creator"], scores["concentration"], scores["velocity"], scores["liquidity"],
                pnl_pct, row["closed_at"],
            ),
        )

    # Resolved avoided rows (24h slot filled): treat as completed outcomes.
    cursor = await db.execute(
        """SELECT a.token_address, a.risk_score, a.price_at_flag, a.price_24h_later,
                  a.confirmed_rug, a.flagged_at, t.risk_detail
           FROM avoided a LEFT JOIN tokens t ON a.token_address = t.address
           WHERE a.price_24h_later IS NOT NULL"""
    )
    avoided_rows = await cursor.fetchall()
    for row in avoided_rows:
        scores = _extract_signal_scores(row["risk_detail"], _json)
        change_pct = None
        start = row["price_at_flag"] or 0
        end = row["price_24h_later"] or 0
        if start > 0:
            change_pct = ((end - start) / start) * 100
        await db.execute(
            """INSERT INTO signal_outcomes (token_address, entry_risk_grade, entry_risk_percentage,
               creator_score, concentration_score, velocity_score, liquidity_score,
               outcome_type, outcome_price_change_pct, outcome_confirmed_rug, recorded_at)
               VALUES (?, ?, NULL, ?, ?, ?, ?, 'avoided_24h', ?, ?, ?)""",
            (
                row["token_address"], row["risk_score"],
                scores["creator"], scores["concentration"], scores["velocity"], scores["liquidity"],
                change_pct, int(row["confirmed_rug"] or 0), row["flagged_at"],
            ),
        )


def _extract_signal_scores(risk_detail_json, json_mod) -> dict:
    """Pull the four tracked signal scores out of a tokens.risk_detail JSON blob."""
    out: dict[str, int | None] = {"creator": None, "concentration": None, "velocity": None, "liquidity": None}
    if not risk_detail_json:
        return out
    try:
        detail = json_mod.loads(risk_detail_json)
        sig_map = {
            "creator": "creator_history",
            "concentration": "holder_concentration",
            "velocity": "bonding_velocity",
            "liquidity": "liquidity",
        }
        for key, signal_name in sig_map.items():
            sig = detail.get(signal_name) if isinstance(detail, dict) else None
            if isinstance(sig, dict) and sig.get("score") is not None:
                try:
                    out[key] = int(sig["score"])
                except (TypeError, ValueError):
                    pass
    except (ValueError, TypeError):
        pass
    return out


async def init_db():
    """Initialize the database with schema and default config."""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        # WAL mode allows concurrent readers + one writer without "database is locked"
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.executescript(SCHEMA)
        await _apply_column_migrations(db)
        # Insert default config values if not present
        for key, value in DEFAULT_CONFIG.items():
            await db.execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                (key, value),
            )
        await _backfill_signal_outcomes(db)
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    """Get a database connection with WAL mode and busy timeout."""
    db = await aiosqlite.connect(get_db_path())
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")
    return db


async def get_config_value(key: str) -> str | None:
    """Get a single config value."""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        cursor = await db.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else None


async def get_all_config() -> dict:
    """Get all config as a dict. Cached for _CONFIG_TTL_S seconds."""
    global _config_cache
    now = time.monotonic()
    if _config_cache and (now - _config_cache[0]) < _CONFIG_TTL_S:
        return dict(_config_cache[1])
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        cursor = await db.execute("SELECT key, value FROM config")
        rows = await cursor.fetchall()
        data = {row["key"]: row["value"] for row in rows}
    _config_cache = (now, data)
    return dict(data)


def invalidate_config_cache():
    """Drop the get_all_config cache. Call after any config write."""
    global _config_cache
    _config_cache = None


async def set_config_value(key: str, value: str):
    """Set a config value."""
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()
    invalidate_config_cache()
