import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from storage.database import get_connection

class MarketRadarRepository:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    # --- Constituents ---
    def save_constituents(self, records: List[Dict[str, Any]]) -> int:
        query = """
        INSERT OR REPLACE INTO constituents (symbol, security, sector, sub_industry, date_added, cik, updated_at)
        VALUES (:symbol, :security, :sector, :sub_industry, :date_added, :cik, :updated_at)
        """
        now_str = datetime.now().isoformat()
        clean_records = []
        for r in records:
            clean_records.append({
                "symbol": r["symbol"],
                "security": r.get("security", ""),
                "sector": r.get("sector", ""),
                "sub_industry": r.get("sub_industry", ""),
                "date_added": str(r.get("date_added", "")),
                "cik": str(r.get("cik", "")),
                "updated_at": now_str
            })
        conn = self._conn()
        try:
            with conn:
                conn.executemany(query, clean_records)
            return len(clean_records)
        finally:
            conn.close()

    def get_constituents(self) -> pd.DataFrame:
        conn = self._conn()
        try:
            df = pd.read_sql_query("SELECT * FROM constituents ORDER BY sector, symbol", conn)
            return df
        finally:
            conn.close()

    # --- Daily Bars ---
    def save_daily_bars(self, records: List[Tuple[str, str, float, float, float, float, float]]) -> int:
        query = """
        INSERT OR REPLACE INTO daily_bars (symbol, date, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        conn = self._conn()
        try:
            with conn:
                conn.executemany(query, records)
            return len(records)
        finally:
            conn.close()

    def get_daily_bars(self, symbols: Optional[List[str]] = None, start_date: Optional[str] = None) -> pd.DataFrame:
        conn = self._conn()
        try:
            query = "SELECT symbol, date, open, high, low, close, volume FROM daily_bars"
            conditions = []
            params: List[Any] = []
            if symbols:
                placeholders = ",".join("?" for _ in symbols)
                conditions.append(f"symbol IN ({placeholders})")
                params.extend(symbols)
            if start_date:
                conditions.append("date >= ?")
                params.append(start_date)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY symbol, date ASC"

            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
            return df
        finally:
            conn.close()

    def get_latest_bar_date(self) -> Optional[str]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT MAX(date) as max_date FROM daily_bars").fetchone()
            return row["max_date"] if row and row["max_date"] else None
        finally:
            conn.close()

    # --- Fundamentals ---
    def save_fundamentals(self, records: List[Dict[str, Any]]) -> int:
        query = """
        INSERT OR REPLACE INTO fundamentals (
            symbol, sector, industry, revenue_growth, earnings_growth,
            profit_margins, operating_margins, operating_cashflow, total_debt,
            next_earnings_date, is_financial, updated_at
        ) VALUES (
            :symbol, :sector, :industry, :revenue_growth, :earnings_growth,
            :profit_margins, :operating_margins, :operating_cashflow, :total_debt,
            :next_earnings_date, :is_financial, :updated_at
        )
        """
        now_str = datetime.now().isoformat()
        clean_records = []
        for r in records:
            clean_records.append({
                "symbol": r["symbol"],
                "sector": r.get("sector", ""),
                "industry": r.get("industry", ""),
                "revenue_growth": r.get("revenue_growth"),
                "earnings_growth": r.get("earnings_growth"),
                "profit_margins": r.get("profit_margins"),
                "operating_margins": r.get("operating_margins"),
                "operating_cashflow": r.get("operating_cashflow"),
                "total_debt": r.get("total_debt"),
                "next_earnings_date": r.get("next_earnings_date", "Chưa xác minh"),
                "is_financial": 1 if r.get("is_financial") else 0,
                "updated_at": now_str,
            })
        conn = self._conn()
        try:
            with conn:
                conn.executemany(query, clean_records)
            return len(clean_records)
        finally:
            conn.close()

    def get_fundamentals(self, symbols: Optional[List[str]] = None) -> pd.DataFrame:
        conn = self._conn()
        try:
            if symbols:
                placeholders = ",".join("?" for _ in symbols)
                query = f"SELECT * FROM fundamentals WHERE symbol IN ({placeholders})"
                return pd.read_sql_query(query, conn, params=symbols)
            else:
                return pd.read_sql_query("SELECT * FROM fundamentals", conn)
        finally:
            conn.close()

    # --- Snapshots & Candidates ---
    def save_snapshot(
        self,
        as_of: str,
        rule_version: str,
        total_universe: int,
        valid_universe: int,
        coverage_pct: float,
        missing_symbols: List[str],
        market_metrics: Dict[str, Any],
        sector_metrics: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]]
    ) -> int:
        now_str = datetime.now().isoformat()
        conn = self._conn()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO snapshots (
                        as_of, created_at, rule_version, total_universe, valid_universe,
                        coverage_pct, missing_symbols, market_metrics, sector_metrics
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    as_of,
                    now_str,
                    rule_version,
                    total_universe,
                    valid_universe,
                    coverage_pct,
                    json.dumps(missing_symbols),
                    json.dumps(market_metrics, ensure_ascii=False),
                    json.dumps(sector_metrics, ensure_ascii=False),
                ))
                snapshot_id = cur.lastrowid

                # Save candidate snapshots
                cand_records = []
                for c in candidates:
                    cand_records.append((
                        snapshot_id,
                        c["symbol"],
                        c.get("company_name", ""),
                        c.get("sector", ""),
                        c.get("group_type", ""),
                        c.get("status", "confirmed"),
                        c.get("close_price", 0.0),
                        c.get("perf_1d", 0.0),
                        c.get("perf_5d", 0.0),
                        c.get("perf_20d", 0.0),
                        json.dumps(c.get("technical_reasons", []), ensure_ascii=False),
                        json.dumps(c.get("fa_flags", {}), ensure_ascii=False),
                        c.get("short_caveat", ""),
                        c.get("tv_url", f"https://www.tradingview.com/chart/?symbol={c['symbol']}")
                    ))

                if cand_records:
                    cur.executemany("""
                        INSERT INTO candidate_snapshots (
                            snapshot_id, symbol, company_name, sector, group_type, status,
                            close_price, perf_1d, perf_5d, perf_20d, technical_reasons,
                            fa_flags, short_caveat, tv_url
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, cand_records)

            return snapshot_id
        finally:
            conn.close()

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()
            if not row:
                return None
            res = dict(row)
            res["missing_symbols"] = json.loads(res["missing_symbols"]) if res["missing_symbols"] else []
            res["market_metrics"] = json.loads(res["market_metrics"]) if res["market_metrics"] else {}
            res["sector_metrics"] = json.loads(res["sector_metrics"]) if res["sector_metrics"] else []
            return res
        finally:
            conn.close()

    def get_snapshot_by_id(self, snapshot_id: int) -> Optional[Dict[str, Any]]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["missing_symbols"] = json.loads(res["missing_symbols"]) if res["missing_symbols"] else []
            res["market_metrics"] = json.loads(res["market_metrics"]) if res["market_metrics"] else {}
            res["sector_metrics"] = json.loads(res["sector_metrics"]) if res["sector_metrics"] else []
            return res
        finally:
            conn.close()

    def get_snapshots_list(self, limit: int = 30) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT id, as_of, created_at, coverage_pct, valid_universe, total_universe FROM snapshots ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_candidates_by_snapshot(self, snapshot_id: int, group_type: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            query = "SELECT * FROM candidate_snapshots WHERE snapshot_id = ?"
            params = [snapshot_id]
            if group_type:
                query += " AND group_type = ?"
                params.append(group_type)
            query += " ORDER BY group_type, symbol"

            rows = conn.execute(query, params).fetchall()
            candidates = []
            for r in rows:
                c = dict(r)
                c["technical_reasons"] = json.loads(c["technical_reasons"]) if c["technical_reasons"] else []
                c["fa_flags"] = json.loads(c["fa_flags"]) if c["fa_flags"] else {}
                candidates.append(c)
            return candidates
        finally:
            conn.close()

    def get_snapshot_diff(self, latest_snapshot_id: int, previous_snapshot_id: int) -> Dict[str, Any]:
        latest_cands = self.get_candidates_by_snapshot(latest_snapshot_id)
        prev_cands = self.get_candidates_by_snapshot(previous_snapshot_id)

        latest_map = {c["symbol"]: c for c in latest_cands}
        prev_map = {c["symbol"]: c for c in prev_cands}

        added = [latest_map[s] for s in latest_map if s not in prev_map]
        removed = [prev_map[s] for s in prev_map if s not in latest_map]
        retained = []
        for s in latest_map:
            if s in prev_map:
                retained.append({
                    "symbol": s,
                    "company_name": latest_map[s]["company_name"],
                    "old_group": prev_map[s]["group_type"],
                    "new_group": latest_map[s]["group_type"],
                    "group_changed": prev_map[s]["group_type"] != latest_map[s]["group_type"]
                })

        # Sector rank differences
        latest_snap = self.get_snapshot_by_id(latest_snapshot_id)
        prev_snap = self.get_snapshot_by_id(previous_snapshot_id)
        sector_moves = []
        if latest_snap and prev_snap:
            latest_sectors = {s["sector"]: s for s in latest_snap.get("sector_metrics", [])}
            prev_sectors = {s["sector"]: s for s in prev_snap.get("sector_metrics", [])}
            for sec, cur in latest_sectors.items():
                old = prev_sectors.get(sec)
                if old:
                    cur_rank = cur.get("rank", 0)
                    old_rank = old.get("rank", 0)
                    sector_moves.append({
                        "sector": sec,
                        "old_rank": old_rank,
                        "new_rank": cur_rank,
                        "change": old_rank - cur_rank  # positive means improved rank (e.g. 5 -> 2 = +3)
                    })

        return {
            "added": added,
            "removed": removed,
            "retained": retained,
            "sector_moves": sorted(sector_moves, key=lambda x: x["change"], reverse=True)
        }
