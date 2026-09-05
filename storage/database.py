import sqlite3
from pathlib import Path
from typing import Optional
from config.settings import DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS constituents (
    symbol TEXT PRIMARY KEY,
    security TEXT,
    sector TEXT,
    sub_industry TEXT,
    date_added TEXT,
    cik TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS daily_bars (
    symbol TEXT,
    date TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    PRIMARY KEY (symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_bars_symbol_date ON daily_bars(symbol, date);
CREATE INDEX IF NOT EXISTS idx_daily_bars_date ON daily_bars(date);

CREATE TABLE IF NOT EXISTS fundamentals (
    symbol TEXT PRIMARY KEY,
    sector TEXT,
    industry TEXT,
    revenue_growth REAL,
    earnings_growth REAL,
    profit_margins REAL,
    operating_margins REAL,
    operating_cashflow REAL,
    total_debt REAL,
    next_earnings_date TEXT,
    is_financial INTEGER DEFAULT 0,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of TEXT NOT NULL,
    created_at TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    total_universe INTEGER,
    valid_universe INTEGER,
    coverage_pct REAL,
    missing_symbols TEXT,
    market_metrics TEXT,
    sector_metrics TEXT
);

CREATE INDEX IF NOT EXISTS idx_snapshots_as_of ON snapshots(as_of);

CREATE TABLE IF NOT EXISTS candidate_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    company_name TEXT,
    sector TEXT,
    group_type TEXT NOT NULL,
    status TEXT NOT NULL,
    close_price REAL,
    perf_1d REAL,
    perf_5d REAL,
    perf_20d REAL,
    technical_reasons TEXT,
    fa_flags TEXT,
    short_caveat TEXT,
    tv_url TEXT,
    FOREIGN KEY(snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_candidate_snapshot_id ON candidate_snapshots(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_candidate_symbol ON candidate_snapshots(symbol);
"""

def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target_path = Path(db_path or DB_PATH)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize the SQLite database with required tables."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.executescript(SCHEMA_SQL)
    finally:
        conn.close()
