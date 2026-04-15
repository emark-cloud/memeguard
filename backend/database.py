"""SQLite database initialization and async query helpers."""

import aiosqlite
import os
from config import settings

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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tokens_creator ON tokens (creator_address);
CREATE INDEX IF NOT EXISTS idx_tokens_risk ON tokens (risk_score);
CREATE INDEX IF NOT EXISTS idx_scans_token ON scans (token_address);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions (status);
CREATE INDEX IF NOT EXISTS idx_avoided_flagged ON avoided (flagged_at);
CREATE INDEX IF NOT EXISTS idx_activity_type ON activity (event_type);
CREATE INDEX IF NOT EXISTS idx_snapshots_token ON token_snapshots (token_address);
CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_actions (status);
"""

# Default configuration values
DEFAULT_CONFIG = {
    "persona": "momentum",
    "approval_mode": "approve_each",
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


async def init_db():
    """Initialize the database with schema and default config."""
    async with aiosqlite.connect(get_db_path()) as db:
        await db.executescript(SCHEMA)
        # Insert default config values if not present
        for key, value in DEFAULT_CONFIG.items():
            await db.execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                (key, value),
            )
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(get_db_path())
    db.row_factory = aiosqlite.Row
    return db


async def get_config_value(key: str) -> str | None:
    """Get a single config value."""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else None


async def get_all_config() -> dict:
    """Get all config as a dict."""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT key, value FROM config")
        rows = await cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}


async def set_config_value(key: str, value: str):
    """Set a config value."""
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()
