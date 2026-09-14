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
    period_end TEXT,
    fiscal_period TEXT,
    period_type TEXT DEFAULT 'Chỉ số tổng hợp Yahoo (YoY)',
    currency TEXT DEFAULT 'USD',
    reported_date TEXT,
    retrieved_at TEXT,
    source TEXT DEFAULT 'Yahoo Finance (Số liệu tổng hợp / Aggregate)',
    data_status TEXT DEFAULT 'valid',
    sec_filing_url TEXT,
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
    coverage_252d REAL DEFAULT 0.0,
    status TEXT DEFAULT 'complete',
    missing_symbols TEXT,
    market_metrics TEXT,
    sector_metrics TEXT,
    industry_metrics TEXT,
    market_history TEXT,
    sector_rotation TEXT,
    sector_health TEXT,
    methodology_version TEXT DEFAULT 'v2.1'
);

CREATE INDEX IF NOT EXISTS idx_snapshots_as_of ON snapshots(as_of);

CREATE TABLE IF NOT EXISTS candidate_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    company_name TEXT,
    sector TEXT,
    sub_industry TEXT,
    group_type TEXT NOT NULL,
    status TEXT NOT NULL,
    close_price REAL,
    perf_1d REAL,
    perf_5d REAL,
    perf_20d REAL,
    score REAL,
    rank INTEGER,
    is_oneil_leader INTEGER DEFAULT 0,
    industry_comp INTEGER DEFAULT 0,
    technical_reasons TEXT,
    fa_flags TEXT,
    short_caveat TEXT,
    tv_url TEXT,
    setup_type TEXT DEFAULT '',
    trigger_price REAL,
    trigger_condition TEXT,
    invalidation_price REAL,
    invalidation_condition TEXT,
    support_level REAL,
    support_basis TEXT,
    resistance_level REAL,
    resistance_basis TEXT,
    atr14 REAL,
    atr_pct REAL,
    dist_trigger_pct REAL,
    dist_trigger_atr REAL,
    dist_ma20_pct REAL,
    dist_ma20_atr REAL,
    avg_dollar_vol20 REAL,
    rel_volume REAL,
    weekly_context TEXT,
    checklist TEXT,
    evidence_json TEXT,
    signal_key TEXT,
    candle_pattern TEXT DEFAULT 'Không rõ mẫu hình',
    FOREIGN KEY(snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_candidate_snapshot_id ON candidate_snapshots(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_candidate_symbol ON candidate_snapshots(symbol);

CREATE TABLE IF NOT EXISTS signal_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT UNIQUE NOT NULL,
    session_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    company_name TEXT,
    event_type TEXT NOT NULL,
    group_type TEXT,
    setup_type TEXT,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence TEXT,
    severity TEXT DEFAULT 'info',
    is_read INTEGER DEFAULT 0,
    source_url TEXT,
    source_name TEXT,
    published_at TEXT,
    received_at TEXT,
    source_status TEXT DEFAULT 'confirmed',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signal_events_session ON signal_events(session_date);
CREATE INDEX IF NOT EXISTS idx_signal_events_symbol ON signal_events(symbol);
CREATE INDEX IF NOT EXISTS idx_signal_events_type ON signal_events(event_type);
CREATE INDEX IF NOT EXISTS idx_signal_events_read ON signal_events(is_read);

CREATE TABLE IF NOT EXISTS signal_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_key TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    company_name TEXT,
    sector TEXT,
    sub_industry TEXT,
    side TEXT NOT NULL,
    group_type TEXT NOT NULL,
    setup_type TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    first_detected_date TEXT NOT NULL,
    latest_detected_date TEXT NOT NULL,
    streak_count INTEGER DEFAULT 1,
    status TEXT NOT NULL,
    first_snapshot_id INTEGER,
    trigger_price REAL,
    invalidation_price REAL,
    initial_close REAL,
    initial_atr REAL,
    initial_score REAL,
    entry_date TEXT,
    entry_price REAL,
    spy_entry_price REAL,
    baseline_entry_index REAL,
    candle_pattern TEXT DEFAULT 'Không rõ mẫu hình',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signal_records_symbol ON signal_records(symbol);
CREATE INDEX IF NOT EXISTS idx_signal_records_first_date ON signal_records(first_detected_date);
CREATE INDEX IF NOT EXISTS idx_signal_records_status ON signal_records(status);

CREATE TABLE IF NOT EXISTS signal_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER NOT NULL,
    signal_key TEXT NOT NULL,
    symbol TEXT NOT NULL,
    horizon_days INTEGER NOT NULL,
    status TEXT NOT NULL,
    exit_date TEXT,
    exit_price REAL,
    return_pct REAL,
    spy_return_pct REAL,
    excess_return_spy REAL,
    baseline_return_pct REAL,
    excess_return_baseline REAL,
    mfe_pct REAL,
    mae_pct REAL,
    mfe_atr REAL,
    mae_atr REAL,
    hit_trigger INTEGER DEFAULT 0,
    hit_invalidation INTEGER DEFAULT 0,
    entry_day_of_week TEXT,
    horizon_label TEXT,
    crosses_weekend INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL,
    UNIQUE(signal_id, horizon_days),
    FOREIGN KEY(signal_id) REFERENCES signal_records(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_signal_outcomes_signal_id ON signal_outcomes(signal_id);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_horizon ON signal_outcomes(horizon_days);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_status ON signal_outcomes(status);

CREATE TABLE IF NOT EXISTS base_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER,
    symbol TEXT NOT NULL,
    as_of TEXT NOT NULL,
    base_id TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    window_start TEXT,
    window_end TEXT,
    state TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    data_status TEXT DEFAULT 'valid',
    rule_version TEXT NOT NULL,
    upper REAL,
    lower REAL,
    close_price REAL,
    perf_1d REAL,
    width_pct REAL,
    efficiency_ratio REAL,
    center_shift REAL,
    tr_contraction REAL,
    vol_contraction REAL,
    position REAL,
    distance_to_upper_pct REAL,
    signed_volume_balance REAL,
    volume_balance_label TEXT,
    trend_context TEXT,
    rs_vs_spy REAL,
    consecutive_weakening INTEGER DEFAULT 0,
    ma50 REAL,
    ma200 REAL,
    price_vs_ma50_pct REAL,
    price_vs_ma200_pct REAL,
    pressure_bias TEXT,
    lifecycle_phase TEXT DEFAULT 'forming',
    rs_rating INTEGER,
    high_52w REAL,
    from_52w_high_pct REAL,
    now_vs_pivot_pct REAL,
    breakout_date TEXT,
    breakout_price REAL,
    breakout_bar_count INTEGER DEFAULT 0,
    consecutive_below_ma50 INTEGER DEFAULT 0,
    ended_at TEXT,
    end_reason TEXT,
    formula_version TEXT DEFAULT 'v2.0',
    checks TEXT,
    warnings TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_base_snapshots_snapshot ON base_snapshots(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_base_snapshots_symbol_as_of ON base_snapshots(symbol, as_of);
CREATE INDEX IF NOT EXISTS idx_base_snapshots_base_id ON base_snapshots(base_id);
CREATE INDEX IF NOT EXISTS idx_base_snapshots_state ON base_snapshots(state);
CREATE INDEX IF NOT EXISTS idx_base_snapshots_active ON base_snapshots(is_active);
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
    """Initialize the SQLite database with required tables and safe migrations."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.executescript(SCHEMA_SQL)
            cursor = conn.cursor()

            # Safe migrations for snapshots table
            cursor.execute("PRAGMA table_info(snapshots);")
            snap_cols = [row[1] for row in cursor.fetchall()]
            if "industry_metrics" not in snap_cols:
                cursor.execute("ALTER TABLE snapshots ADD COLUMN industry_metrics TEXT;")
            if "coverage_252d" not in snap_cols:
                cursor.execute("ALTER TABLE snapshots ADD COLUMN coverage_252d REAL DEFAULT 0.0;")
            if "status" not in snap_cols:
                cursor.execute("ALTER TABLE snapshots ADD COLUMN status TEXT DEFAULT 'complete';")
            if "market_history" not in snap_cols:
                cursor.execute("ALTER TABLE snapshots ADD COLUMN market_history TEXT;")
            if "sector_rotation" not in snap_cols:
                cursor.execute("ALTER TABLE snapshots ADD COLUMN sector_rotation TEXT;")
            if "sector_health" not in snap_cols:
                cursor.execute("ALTER TABLE snapshots ADD COLUMN sector_health TEXT;")
            if "methodology_version" not in snap_cols:
                cursor.execute("ALTER TABLE snapshots ADD COLUMN methodology_version TEXT DEFAULT 'v2.1';")

            # Safe migrations for candidate_snapshots table [D-04]
            cursor.execute("PRAGMA table_info(candidate_snapshots);")
            cand_cols = [row[1] for row in cursor.fetchall()]
            if "sub_industry" not in cand_cols:
                cursor.execute("ALTER TABLE candidate_snapshots ADD COLUMN sub_industry TEXT;")
            if "score" not in cand_cols:
                cursor.execute("ALTER TABLE candidate_snapshots ADD COLUMN score REAL;")
            if "rank" not in cand_cols:
                cursor.execute("ALTER TABLE candidate_snapshots ADD COLUMN rank INTEGER;")
            if "is_oneil_leader" not in cand_cols:
                cursor.execute("ALTER TABLE candidate_snapshots ADD COLUMN is_oneil_leader INTEGER DEFAULT 0;")
            if "industry_comp" not in cand_cols:
                cursor.execute("ALTER TABLE candidate_snapshots ADD COLUMN industry_comp INTEGER DEFAULT 0;")

            # New columns for setup evidence and metrics
            new_cand_columns = {
                "setup_type": "TEXT DEFAULT ''",
                "trigger_price": "REAL",
                "trigger_condition": "TEXT",
                "invalidation_price": "REAL",
                "invalidation_condition": "TEXT",
                "support_level": "REAL",
                "support_basis": "TEXT",
                "resistance_level": "REAL",
                "resistance_basis": "TEXT",
                "atr14": "REAL",
                "atr_pct": "REAL",
                "dist_trigger_pct": "REAL",
                "dist_trigger_atr": "REAL",
                "dist_ma20_pct": "REAL",
                "dist_ma20_atr": "REAL",
                "avg_dollar_vol20": "REAL",
                "rel_volume": "REAL",
                "weekly_context": "TEXT",
                "checklist": "TEXT",
                "evidence_json": "TEXT",
                "signal_key": "TEXT",
                "candle_pattern": "TEXT DEFAULT 'Không rõ mẫu hình'",
            }
            for col_name, col_type in new_cand_columns.items():
                if col_name not in cand_cols:
                    cursor.execute(f"ALTER TABLE candidate_snapshots ADD COLUMN {col_name} {col_type};")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidate_signal_key ON candidate_snapshots(signal_key);")

            # Safe migrations for signal_records table
            cursor.execute("PRAGMA table_info(signal_records);")
            sig_cols = [row[1] for row in cursor.fetchall()]
            if "candle_pattern" not in sig_cols:
                cursor.execute("ALTER TABLE signal_records ADD COLUMN candle_pattern TEXT DEFAULT 'Không rõ mẫu hình';")

            # Safe migrations for fundamentals table [R-02]
            cursor.execute("PRAGMA table_info(fundamentals);")
            fa_cols = [row[1] for row in cursor.fetchall()]
            new_fa_columns = {
                "period_end": "TEXT",
                "fiscal_period": "TEXT",
                "period_type": "TEXT DEFAULT 'Chỉ số tổng hợp Yahoo (YoY)'",
                "currency": "TEXT DEFAULT 'USD'",
                "reported_date": "TEXT",
                "retrieved_at": "TEXT",
                "source": "TEXT DEFAULT 'Yahoo Finance (Số liệu tổng hợp / Aggregate)'",
                "data_status": "TEXT DEFAULT 'valid'",
                "sec_filing_url": "TEXT"
            }
            for col_name, col_type in new_fa_columns.items():
                if col_name not in fa_cols:
                    cursor.execute(f"ALTER TABLE fundamentals ADD COLUMN {col_name} {col_type};")

            # Safe migrations for signal_events table [D-02]
            cursor.execute("PRAGMA table_info(signal_events);")
            ev_cols = [row[1] for row in cursor.fetchall()]
            new_ev_columns = {
                "source_url": "TEXT",
                "source_name": "TEXT",
                "published_at": "TEXT",
                "received_at": "TEXT",
                "source_status": "TEXT DEFAULT 'confirmed'"
            }
            for col_name, col_type in new_ev_columns.items():
                if col_name not in ev_cols:
                    cursor.execute(f"ALTER TABLE signal_events ADD COLUMN {col_name} {col_type};")

            # Safe migrations for signal_outcomes table [D-04]
            cursor.execute("PRAGMA table_info(signal_outcomes);")
            outcome_cols = [row[1] for row in cursor.fetchall()]
            new_outcome_columns = {
                "entry_day_of_week": "TEXT",
                "horizon_label": "TEXT",
                "crosses_weekend": "INTEGER DEFAULT 0"
            }
            for col_name, col_type in new_outcome_columns.items():
                if col_name not in outcome_cols:
                    cursor.execute(f"ALTER TABLE signal_outcomes ADD COLUMN {col_name} {col_type};")

            # Safe migrations for base_snapshots table
            cursor.execute("PRAGMA table_info(base_snapshots);")
            base_cols = [row[1] for row in cursor.fetchall()]
            new_base_columns = {
                "perf_1d": "REAL",
                "ma50": "REAL",
                "ma200": "REAL",
                "price_vs_ma50_pct": "REAL",
                "price_vs_ma200_pct": "REAL",
                "pressure_bias": "TEXT",
                "lifecycle_phase": "TEXT DEFAULT 'forming'",
                "rs_rating": "INTEGER",
                "high_52w": "REAL",
                "from_52w_high_pct": "REAL",
                "now_vs_pivot_pct": "REAL",
                "breakout_date": "TEXT",
                "breakout_price": "REAL",
                "breakout_bar_count": "INTEGER DEFAULT 0",
                "consecutive_below_ma50": "INTEGER DEFAULT 0",
                "ended_at": "TEXT",
                "end_reason": "TEXT",
                "formula_version": "TEXT DEFAULT 'v2.0'",
            }
            for col_name, col_type in new_base_columns.items():
                if col_name not in base_cols:
                    cursor.execute(f"ALTER TABLE base_snapshots ADD COLUMN {col_name} {col_type};")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_base_snapshots_lifecycle ON base_snapshots(lifecycle_phase);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_base_snapshots_breakout_date ON base_snapshots(breakout_date);")
    finally:
        conn.close()
