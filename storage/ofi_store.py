"""
OFI history store — SQLite file riêng (mặc định data/ofi_history.db).

Tách khỏi DB chính (market_radar.db) vì DB chính chỉ có một writer duy nhất là
workflow pipeline 4 lần/ngày upload asset market_radar.db.gz bằng --clobber;
job OFI chạy intraday nếu ghi chung sẽ hai workflow ghi đè asset của nhau.
Asset ofi_history.db.gz được upload lên cùng Release data-latest, độc lập.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from config.settings import OFI_DB_PATH

OFI_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ofi_minute_bars (
    symbol TEXT NOT NULL,
    ts TEXT NOT NULL,
    session_date TEXT NOT NULL,
    ofi REAL NOT NULL,
    n_updates INTEGER NOT NULL DEFAULT 0,
    spread_avg REAL,
    bid_size_last REAL,
    ask_size_last REAL,
    mid_first REAL,
    mid_last REAL,
    source TEXT NOT NULL DEFAULT 'iex',
    PRIMARY KEY (symbol, ts)
);
CREATE INDEX IF NOT EXISTS idx_ofi_minute_session ON ofi_minute_bars(session_date);
CREATE INDEX IF NOT EXISTS idx_ofi_minute_symbol_session ON ofi_minute_bars(symbol, session_date);

CREATE TABLE IF NOT EXISTS ofi_sync_cursor (
    symbol TEXT PRIMARY KEY,
    last_quote_ts TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class OfiHistoryRepository:
    def __init__(self, db_path: Optional[Any] = None):
        self.db_path = str(Path(db_path or OFI_DB_PATH))
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        target = Path(self.db_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(target, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self) -> None:
        conn = self._conn()
        try:
            with conn:
                conn.executescript(OFI_SCHEMA_SQL)
        finally:
            conn.close()

    # --- Minute bars ---
    def save_ofi_minutes(self, records: List[Dict[str, Any]]) -> int:
        """Lưu bucket OFI theo phút. Idempotent: PK (symbol, ts) + INSERT OR REPLACE."""
        if not records:
            return 0
        query = """
        INSERT OR REPLACE INTO ofi_minute_bars (
            symbol, ts, session_date, ofi, n_updates, spread_avg,
            bid_size_last, ask_size_last, mid_first, mid_last, source
        ) VALUES (
            :symbol, :ts, :session_date, :ofi, :n_updates, :spread_avg,
            :bid_size_last, :ask_size_last, :mid_first, :mid_last, :source
        )
        """
        conn = self._conn()
        try:
            with conn:
                conn.executemany(query, records)
            return len(records)
        finally:
            conn.close()

    def get_ofi_history(
        self,
        symbols: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Đọc lịch sử OFI phút, kèm cum_ofi tính dần theo (symbol, ts)."""
        conn = self._conn()
        try:
            query = "SELECT * FROM ofi_minute_bars"
            conditions, params = [], []
            if symbols:
                placeholders = ",".join("?" for _ in symbols)
                conditions.append(f"symbol IN ({placeholders})")
                params.extend(symbols)
            if start_date:
                conditions.append("session_date >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("session_date <= ?")
                params.append(end_date)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY symbol, ts ASC"

            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                # cum_ofi reset theo phiên — lũy kế xuyên phiên là vô nghĩa
                # (gap qua đêm không phải dòng tiền trong phiên).
                df["cum_ofi"] = df.groupby(["symbol", "session_date"])["ofi"].cumsum()
            return df
        finally:
            conn.close()

    def get_session_dates(self) -> List[str]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT DISTINCT session_date FROM ofi_minute_bars ORDER BY session_date DESC"
            ).fetchall()
            return [r["session_date"] for r in rows]
        finally:
            conn.close()

    def get_session_summaries(self, session_date: Optional[str] = None) -> pd.DataFrame:
        """Tổng kết mỗi (symbol, session_date): integrated OFI, imbalance, biến động mid."""
        conn = self._conn()
        try:
            query = """
            SELECT symbol, session_date,
                   SUM(ofi) AS integrated_ofi,
                   SUM(ABS(ofi)) AS abs_ofi_sum,
                   COUNT(*) AS n_minutes,
                   MIN(ts) AS first_ts,
                   MAX(ts) AS last_ts
            FROM ofi_minute_bars
            """
            params: List[Any] = []
            if session_date:
                query += " WHERE session_date = ?"
                params.append(session_date)
            query += " GROUP BY symbol, session_date ORDER BY session_date DESC, integrated_ofi DESC"

            df = pd.read_sql_query(query, conn, params=params)
            if df.empty:
                return df
            df["integrated_ofi"] = df["integrated_ofi"].astype(float)
            df["imbalance_ratio"] = df["integrated_ofi"] / df["abs_ofi_sum"].replace(0, pd.NA)
            return df.drop(columns=["abs_ofi_sum"])
        finally:
            conn.close()

    # --- Sync cursor ---
    def get_cursor(self, symbol: str) -> Optional[str]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT last_quote_ts FROM ofi_sync_cursor WHERE symbol = ?", (symbol,)
            ).fetchone()
            return row["last_quote_ts"] if row else None
        finally:
            conn.close()

    def save_cursor(self, symbol: str, last_quote_ts: str) -> None:
        conn = self._conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO ofi_sync_cursor (symbol, last_quote_ts, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (symbol, last_quote_ts, datetime.now().isoformat()),
                )
        finally:
            conn.close()
