import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from storage.database import get_connection, init_db

class MarketRadarRepository:
    def __init__(self, db_path=None):
        self.db_path = db_path
        init_db(self.db_path)

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
        if not records:
            return 0
        query = """
        INSERT INTO fundamentals (
            symbol, sector, industry, revenue_growth, earnings_growth,
            profit_margins, operating_margins, operating_cashflow, total_debt,
            next_earnings_date, is_financial, period_end, fiscal_period, period_type,
            currency, reported_date, retrieved_at, source, data_status, sec_filing_url, updated_at
        ) VALUES (
            :symbol, :sector, :industry, :revenue_growth, :earnings_growth,
            :profit_margins, :operating_margins, :operating_cashflow, :total_debt,
            :next_earnings_date, :is_financial, :period_end, :fiscal_period, :period_type,
            :currency, :reported_date, :retrieved_at, :source, :data_status, :sec_filing_url, :updated_at
        )
        ON CONFLICT(symbol) DO UPDATE SET
            sector = CASE WHEN excluded.sector != '' THEN excluded.sector ELSE fundamentals.sector END,
            industry = CASE WHEN excluded.industry != '' THEN excluded.industry ELSE fundamentals.industry END,
            revenue_growth = COALESCE(excluded.revenue_growth, fundamentals.revenue_growth),
            earnings_growth = COALESCE(excluded.earnings_growth, fundamentals.earnings_growth),
            profit_margins = COALESCE(excluded.profit_margins, fundamentals.profit_margins),
            operating_margins = COALESCE(excluded.operating_margins, fundamentals.operating_margins),
            operating_cashflow = COALESCE(excluded.operating_cashflow, fundamentals.operating_cashflow),
            total_debt = COALESCE(excluded.total_debt, fundamentals.total_debt),
            next_earnings_date = CASE WHEN excluded.next_earnings_date IS NOT NULL AND excluded.next_earnings_date != '' AND excluded.next_earnings_date != 'Chưa xác minh' THEN excluded.next_earnings_date ELSE fundamentals.next_earnings_date END,
            is_financial = CASE WHEN excluded.is_financial = 1 THEN 1 ELSE fundamentals.is_financial END,
            period_end = COALESCE(excluded.period_end, fundamentals.period_end),
            fiscal_period = COALESCE(excluded.fiscal_period, fundamentals.fiscal_period),
            period_type = COALESCE(excluded.period_type, fundamentals.period_type),
            currency = COALESCE(excluded.currency, fundamentals.currency),
            reported_date = COALESCE(excluded.reported_date, fundamentals.reported_date),
            retrieved_at = COALESCE(excluded.retrieved_at, fundamentals.retrieved_at),
            source = COALESCE(excluded.source, fundamentals.source),
            data_status = COALESCE(excluded.data_status, fundamentals.data_status),
            sec_filing_url = COALESCE(excluded.sec_filing_url, fundamentals.sec_filing_url),
            updated_at = excluded.updated_at
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
                "next_earnings_date": r.get("next_earnings_date") or "Chưa xác minh",
                "is_financial": 1 if r.get("is_financial") else 0,
                "period_end": r.get("period_end"),
                "fiscal_period": r.get("fiscal_period"),
                "period_type": r.get("period_type") or "Chỉ số tổng hợp Yahoo (YoY)",
                "currency": r.get("currency") or "USD",
                "reported_date": r.get("reported_date"),
                "retrieved_at": r.get("retrieved_at") or now_str[:10],
                "source": r.get("source") or "Yahoo Finance (Số liệu tổng hợp / Aggregate)",
                "data_status": r.get("data_status") or "valid",
                "sec_filing_url": r.get("sec_filing_url") or f"https://www.sec.gov/edgar/browse/?CIK={r['symbol']}",
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
        candidates: List[Dict[str, Any]],
        industry_metrics: Optional[List[Dict[str, Any]]] = None,
        coverage_252d: float = 0.0,
        status: str = "complete",
        market_history: Optional[Dict[str, Any]] = None,
        sector_rotation: Optional[Dict[str, Any]] = None,
        sector_health: Optional[List[Dict[str, Any]]] = None,
        methodology_version: str = "v2.1"
    ) -> int:
        now_str = datetime.now().isoformat()
        conn = self._conn()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO snapshots (
                        as_of, created_at, rule_version, total_universe, valid_universe,
                        coverage_pct, coverage_252d, status, missing_symbols, market_metrics,
                        sector_metrics, industry_metrics, market_history, sector_rotation,
                        sector_health, methodology_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    as_of,
                    now_str,
                    rule_version,
                    total_universe,
                    valid_universe,
                    coverage_pct,
                    coverage_252d,
                    status,
                    json.dumps(missing_symbols),
                    json.dumps(market_metrics, ensure_ascii=False),
                    json.dumps(sector_metrics, ensure_ascii=False),
                    json.dumps(industry_metrics or [], ensure_ascii=False),
                    json.dumps(market_history or {}, ensure_ascii=False) if market_history is not None else None,
                    json.dumps(sector_rotation or {}, ensure_ascii=False) if sector_rotation is not None else None,
                    json.dumps(sector_health or [], ensure_ascii=False) if sector_health is not None else None,
                    methodology_version
                ))
                snapshot_id = cur.lastrowid

                # Assign ranks within each group_type sorted by score descending [D-04]
                # Partition by group_type
                grouped_cands: Dict[str, List[Dict[str, Any]]] = {}
                for c in candidates:
                    g = c.get("group_type", "watchlist")
                    grouped_cands.setdefault(g, []).append(c)

                cand_records = []
                for g_type, g_list in grouped_cands.items():
                    # Sort by score descending
                    sorted_g = sorted(g_list, key=lambda x: x.get("score", 0.0), reverse=True)
                    for r_idx, c in enumerate(sorted_g, 1):
                        score_val = float(c["score"]) if c.get("score") is not None else 0.0
                        cand_records.append((
                            snapshot_id,
                            c["symbol"],
                            c.get("company_name", ""),
                            c.get("sector", ""),
                            c.get("sub_industry", ""),
                            c.get("group_type", g_type),
                            c.get("status", "confirmed"),
                            float(c.get("close_price", 0.0)),
                            float(c.get("perf_1d", 0.0)),
                            float(c.get("perf_5d", 0.0)),
                            float(c.get("perf_20d", 0.0)),
                            score_val,
                            int(c.get("rank") or r_idx),
                            1 if c.get("is_oneil_leader") else 0,
                            int(c.get("industry_comp", 0)),
                            json.dumps(c.get("technical_reasons", []), ensure_ascii=False),
                            json.dumps(c.get("fa_flags", {}), ensure_ascii=False),
                            c.get("short_caveat", ""),
                            c.get("tv_url", f"https://www.tradingview.com/chart/?symbol={c['symbol']}&interval=D"),
                            c.get("setup_type", ""),
                            c.get("trigger_price"),
                            c.get("trigger_condition", ""),
                            c.get("invalidation_price"),
                            c.get("invalidation_condition", ""),
                            c.get("support_level"),
                            c.get("support_basis", ""),
                            c.get("resistance_level"),
                            c.get("resistance_basis", ""),
                            c.get("atr14"),
                            c.get("atr_pct"),
                            c.get("dist_trigger_pct"),
                            c.get("dist_trigger_atr"),
                            c.get("dist_ma20_pct"),
                            c.get("dist_ma20_atr"),
                            c.get("avg_dollar_vol20"),
                            c.get("rel_volume"),
                            json.dumps(c.get("weekly_context", {}), ensure_ascii=False) if c.get("weekly_context") else "{}",
                            json.dumps(c.get("checklist", []), ensure_ascii=False) if c.get("checklist") else "[]",
                            json.dumps(c.get("evidence_json", {}), ensure_ascii=False) if c.get("evidence_json") else "{}",
                            c.get("signal_key", ""),
                            c.get("candle_pattern", "Không rõ mẫu hình")
                        ))

                if cand_records:
                    cur.executemany("""
                        INSERT INTO candidate_snapshots (
                            snapshot_id, symbol, company_name, sector, sub_industry,
                            group_type, status, close_price, perf_1d, perf_5d, perf_20d,
                            score, rank, is_oneil_leader, industry_comp, technical_reasons,
                            fa_flags, short_caveat, tv_url,
                            setup_type, trigger_price, trigger_condition, invalidation_price,
                            invalidation_condition, support_level, support_basis, resistance_level,
                            resistance_basis, atr14, atr_pct, dist_trigger_pct, dist_trigger_atr,
                            dist_ma20_pct, dist_ma20_atr, avg_dollar_vol20, rel_volume,
                            weekly_context, checklist, evidence_json, signal_key, candle_pattern
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, cand_records)

            return snapshot_id
        finally:
            conn.close()

    def update_snapshot_analytics(
        self,
        snapshot_id: int,
        market_history: Optional[Dict[str, Any]] = None,
        sector_rotation: Optional[Dict[str, Any]] = None,
        sector_health: Optional[List[Dict[str, Any]]] = None,
        methodology_version: str = "v2.1"
    ) -> bool:
        """Update newly introduced analytics fields for an existing snapshot."""
        conn = self._conn()
        try:
            with conn:
                conn.execute("""
                    UPDATE snapshots
                    SET market_history = ?,
                        sector_rotation = ?,
                        sector_health = ?,
                        methodology_version = ?
                    WHERE id = ?
                """, (
                    json.dumps(market_history or {}, ensure_ascii=False) if market_history is not None else None,
                    json.dumps(sector_rotation or {}, ensure_ascii=False) if sector_rotation is not None else None,
                    json.dumps(sector_health or [], ensure_ascii=False) if sector_health is not None else None,
                    methodology_version,
                    snapshot_id
                ))
                return True
        except Exception as e:
            logger.error(f"Error updating snapshot {snapshot_id} analytics: {e}")
            return False
        finally:
            conn.close()

    def _deserialize_snapshot(self, row: sqlite3.Row) -> Dict[str, Any]:
        res = dict(row)
        res["missing_symbols"] = json.loads(res["missing_symbols"]) if res.get("missing_symbols") else []
        res["market_metrics"] = json.loads(res["market_metrics"]) if res.get("market_metrics") else {}
        res["sector_metrics"] = json.loads(res["sector_metrics"]) if res.get("sector_metrics") else []
        res["industry_metrics"] = json.loads(res["industry_metrics"]) if res.get("industry_metrics") else []

        # Safe parsing for new analytics fields (returns None if not computed in snapshot)
        try:
            res["market_history"] = json.loads(res["market_history"]) if res.get("market_history") else None
        except Exception:
            res["market_history"] = None

        try:
            res["sector_rotation"] = json.loads(res["sector_rotation"]) if res.get("sector_rotation") else None
        except Exception:
            res["sector_rotation"] = None

        try:
            res["sector_health"] = json.loads(res["sector_health"]) if res.get("sector_health") else None
        except Exception:
            res["sector_health"] = None

        return res

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()
            if not row:
                return None
            return self._deserialize_snapshot(row)
        finally:
            conn.close()

    def get_snapshot_by_id(self, snapshot_id: int) -> Optional[Dict[str, Any]]:
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
            if not row:
                return None
            return self._deserialize_snapshot(row)
        finally:
            conn.close()

    def get_previous_session_snapshot(self, current_as_of: str) -> Optional[Dict[str, Any]]:
        """Get the most recent snapshot from a trading session strictly prior to current_as_of."""
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM snapshots WHERE as_of < ? ORDER BY as_of DESC, id DESC LIMIT 1",
                (current_as_of,)
            ).fetchone()
            if not row:
                return None
            return self._deserialize_snapshot(row)
        finally:
            conn.close()

    def get_snapshots_list(self, limit: int = 30) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT id, as_of, created_at, coverage_pct, coverage_252d, status, valid_universe, total_universe FROM snapshots ORDER BY id DESC LIMIT ?",
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
            # Order by group_type, score descending, rank ascending, symbol ascending [D-04]
            query += " ORDER BY group_type, score DESC, symbol ASC"

            rows = conn.execute(query, params).fetchall()
            candidates = []
            for r in rows:
                c = dict(r)
                tv_url = c.get("tv_url") or f"https://www.tradingview.com/chart/?symbol={c.get('symbol', '')}&interval=D"
                if "interval=" not in tv_url:
                    tv_url = f"{tv_url}{'&' if '?' in tv_url else '?'}interval=D"
                c["tv_url"] = tv_url
                c["technical_reasons"] = json.loads(c["technical_reasons"]) if c.get("technical_reasons") else []
                c["fa_flags"] = json.loads(c["fa_flags"]) if c.get("fa_flags") else {}
                c["is_oneil_leader"] = bool(c.get("is_oneil_leader", 0))
                c["score"] = float(c["score"]) if c.get("score") is not None else 0.0
                c["rank"] = int(c["rank"]) if c.get("rank") is not None else None
                c["industry_comp"] = int(c["industry_comp"]) if c.get("industry_comp") is not None else 0
                c["sub_industry"] = str(c.get("sub_industry") or "")
                
                # Deserialization for structured setup evidence
                c["weekly_context"] = json.loads(c["weekly_context"]) if c.get("weekly_context") else {}
                c["checklist"] = json.loads(c["checklist"]) if c.get("checklist") else []
                c["evidence_json"] = json.loads(c["evidence_json"]) if c.get("evidence_json") else {}
                c["candle_pattern"] = c.get("candle_pattern") or c["evidence_json"].get("candlestick", {}).get("features", {}).get("pattern", "Không rõ mẫu hình")
                c["candlestick_analysis"] = c["evidence_json"].get("candlestick", {})
                candidates.append(c)
            return candidates
        finally:
            conn.close()

    def get_snapshot_diff(self, latest_snapshot_id: int, previous_snapshot_id: int) -> Dict[str, Any]:
        """
        Compare candidates and sectors across snapshots.
        Uses composite key (symbol, setup_type or group_type) to preserve multi-setup info without loss.
        """
        latest_cands = self.get_candidates_by_snapshot(latest_snapshot_id)
        prev_cands = self.get_candidates_by_snapshot(previous_snapshot_id)

        # Key by (symbol, setup_type_or_group)
        def cand_key(cand: Dict[str, Any]) -> str:
            st = cand.get("setup_type") or cand.get("group_type") or "default"
            return f"{cand['symbol']}:{st}"

        latest_map = {cand_key(c): c for c in latest_cands}
        prev_map = {cand_key(c): c for c in prev_cands}

        added = [latest_map[k] for k in latest_map if k not in prev_map]
        removed = [prev_map[k] for k in prev_map if k not in latest_map]
        retained = []
        for k in latest_map:
            if k in prev_map:
                cur = latest_map[k]
                old = prev_map[k]
                retained.append({
                    "symbol": cur["symbol"],
                    "company_name": cur.get("company_name", ""),
                    "old_group": old.get("group_type"),
                    "new_group": cur.get("group_type"),
                    "old_status": old.get("status"),
                    "new_status": cur.get("status"),
                    "group_changed": old.get("group_type") != cur.get("group_type"),
                    "status_changed": old.get("status") != cur.get("status"),
                    "setup_type": cur.get("setup_type", "")
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
                        "change": old_rank - cur_rank
                    })

        return {
            "added": added,
            "removed": removed,
            "retained": retained,
            "sector_moves": sorted(sector_moves, key=lambda x: x["change"], reverse=True)
        }

    # --- Signal Events (Today Dashboard) ---
    def save_signal_events(self, events: List[Dict[str, Any]]) -> int:
        """Save detected signal events idempotently using event_key."""
        if not events:
            return 0
        query = """
        INSERT OR IGNORE INTO signal_events (
            event_key, session_date, symbol, company_name, event_type,
            group_type, setup_type, title, summary, evidence, severity,
            is_read, source_url, source_name, published_at, received_at, source_status, created_at
        ) VALUES (
            :event_key, :session_date, :symbol, :company_name, :event_type,
            :group_type, :setup_type, :title, :summary, :evidence, :severity,
            :is_read, :source_url, :source_name, :published_at, :received_at, :source_status, :created_at
        )
        """
        now_str = datetime.now().isoformat()
        records = []
        for e in events:
            records.append({
                "event_key": e["event_key"],
                "session_date": e["session_date"],
                "symbol": e["symbol"],
                "company_name": e.get("company_name", ""),
                "event_type": e["event_type"],
                "group_type": e.get("group_type", ""),
                "setup_type": e.get("setup_type", ""),
                "title": e["title"],
                "summary": e["summary"],
                "evidence": json.dumps(e.get("evidence", {}), ensure_ascii=False) if isinstance(e.get("evidence"), (dict, list)) else str(e.get("evidence", "")),
                "severity": e.get("severity", "info"),
                "is_read": 1 if e.get("is_read") else 0,
                "source_url": e.get("source_url"),
                "source_name": e.get("source_name") or "System Market Engine",
                "published_at": e.get("published_at") or e["session_date"],
                "received_at": e.get("received_at") or now_str,
                "source_status": e.get("source_status") or "confirmed",
                "created_at": now_str,
            })
        conn = self._conn()
        try:
            with conn:
                cur = conn.cursor()
                cur.executemany(query, records)
                return cur.rowcount
        finally:
            conn.close()

    def get_signal_events(
        self,
        session_date: Optional[str] = None,
        event_type: Optional[str] = None,
        is_read: Optional[int] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            query = "SELECT * FROM signal_events"
            conditions = []
            params: List[Any] = []
            if session_date:
                conditions.append("session_date = ?")
                params.append(session_date)
            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type)
            if is_read is not None:
                conditions.append("is_read = ?")
                params.append(is_read)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            events = []
            for r in rows:
                ev = dict(r)
                try:
                    ev["evidence"] = json.loads(ev["evidence"]) if ev.get("evidence") else {}
                except Exception:
                    pass
                events.append(ev)
            return events
        finally:
            conn.close()

    def mark_event_read(self, event_id: int) -> None:
        conn = self._conn()
        try:
            with conn:
                conn.execute("UPDATE signal_events SET is_read = 1 WHERE id = ?", (event_id,))
        except Exception:
            pass
        finally:
            conn.close()

    def mark_all_events_read(self, session_date: Optional[str] = None) -> None:
        conn = self._conn()
        try:
            with conn:
                if session_date:
                    conn.execute("UPDATE signal_events SET is_read = 1 WHERE session_date = ?", (session_date,))
                else:
                    conn.execute("UPDATE signal_events SET is_read = 1")
        except Exception:
            pass
        finally:
            conn.close()

    def get_unread_event_count(self, session_date: Optional[str] = None) -> int:
        conn = self._conn()
        try:
            if session_date:
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM signal_events WHERE is_read = 0 AND session_date = ?",
                    (session_date,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) as cnt FROM signal_events WHERE is_read = 0").fetchone()
            return int(row["cnt"]) if row else 0
        except Exception:
            return 0
        finally:
            conn.close()

    # --- Signal Records & Outcomes ---
    def upsert_signal_records(self, records: List[Dict[str, Any]]) -> int:
        """
        Record signals detected across snapshots.
        Maintains continuity: if signal for symbol+setup was active on prior day, streak increments.
        """
        if not records:
            return 0
        now_str = datetime.now().isoformat()
        conn = self._conn()
        try:
            with conn:
                cur = conn.cursor()
                for r in records:
                    sig_key = r["signal_key"]
                    existing = cur.execute("SELECT * FROM signal_records WHERE signal_key = ?", (sig_key,)).fetchone()
                    if existing:
                        cur.execute("""
                            UPDATE signal_records SET
                                latest_detected_date = ?,
                                streak_count = ?,
                                status = ?,
                                trigger_price = COALESCE(?, trigger_price),
                                invalidation_price = COALESCE(?, invalidation_price),
                                entry_date = COALESCE(?, entry_date),
                                entry_price = COALESCE(?, entry_price),
                                spy_entry_price = COALESCE(?, spy_entry_price),
                                candle_pattern = COALESCE(?, candle_pattern),
                                updated_at = ?
                            WHERE signal_key = ?
                        """, (
                            r["latest_detected_date"],
                            r.get("streak_count", existing["streak_count"] + 1),
                            r.get("status", existing["status"]),
                            r.get("trigger_price"),
                            r.get("invalidation_price"),
                            r.get("entry_date"),
                            r.get("entry_price"),
                            r.get("spy_entry_price"),
                            r.get("candle_pattern"),
                            now_str,
                            sig_key
                        ))
                    else:
                        cur.execute("""
                            INSERT INTO signal_records (
                                signal_key, symbol, company_name, sector, sub_industry,
                                side, group_type, setup_type, rule_version,
                                first_detected_date, latest_detected_date, streak_count,
                                status, first_snapshot_id, trigger_price, invalidation_price,
                                initial_close, initial_atr, initial_score,
                                entry_date, entry_price, spy_entry_price, baseline_entry_index,
                                candle_pattern, created_at, updated_at
                            ) VALUES (
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                            )
                        """, (
                            sig_key,
                            r["symbol"],
                            r.get("company_name", ""),
                            r.get("sector", ""),
                            r.get("sub_industry", ""),
                            r.get("side", "long"),
                            r.get("group_type", ""),
                            r.get("setup_type", ""),
                            r.get("rule_version", "v2"),
                            r["first_detected_date"],
                            r.get("latest_detected_date", r["first_detected_date"]),
                            r.get("streak_count", 1),
                            r.get("status", "active"),
                            r.get("first_snapshot_id"),
                            r.get("trigger_price"),
                            r.get("invalidation_price"),
                            r.get("initial_close"),
                            r.get("initial_atr"),
                            r.get("initial_score"),
                            r.get("entry_date"),
                            r.get("entry_price"),
                            r.get("spy_entry_price"),
                            r.get("baseline_entry_index"),
                            r.get("candle_pattern", "Không rõ mẫu hình"),
                            now_str,
                            now_str
                        ))
                return len(records)
        finally:
            conn.close()

    def update_signal_entry_info(
        self,
        signal_id: int,
        entry_date: str,
        entry_price: float,
        spy_entry_price: Optional[float] = None
    ) -> bool:
        """Update resolved entry date and execution price for an active/historical signal record."""
        now_str = datetime.now().isoformat()
        conn = self._conn()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE signal_records SET
                        entry_date = COALESCE(?, entry_date),
                        entry_price = COALESCE(?, entry_price),
                        spy_entry_price = COALESCE(?, spy_entry_price),
                        updated_at = ?
                    WHERE id = ?
                """, (entry_date, entry_price, spy_entry_price, now_str, signal_id))
                return cur.rowcount > 0
        finally:
            conn.close()

    def get_signal_records(
        self,
        status: Optional[str] = None,
        rule_version: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            query = "SELECT * FROM signal_records"
            conditions = []
            params: List[Any] = []
            if status:
                conditions.append("status = ?")
                params.append(status)
            if rule_version:
                conditions.append("rule_version = ?")
                params.append(rule_version)
            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY id DESC"

            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def save_signal_outcomes(self, outcomes: List[Dict[str, Any]]) -> int:
        if not outcomes:
            return 0
        now_str = datetime.now().isoformat()
        query = """
        INSERT OR REPLACE INTO signal_outcomes (
            signal_id, signal_key, symbol, horizon_days, status,
            exit_date, exit_price, return_pct, spy_return_pct,
            excess_return_spy, baseline_return_pct, excess_return_baseline,
            mfe_pct, mae_pct, mfe_atr, mae_atr, hit_trigger, hit_invalidation,
            entry_day_of_week, horizon_label, crosses_weekend, updated_at
        ) VALUES (
            :signal_id, :signal_key, :symbol, :horizon_days, :status,
            :exit_date, :exit_price, :return_pct, :spy_return_pct,
            :excess_return_spy, :baseline_return_pct, :excess_return_baseline,
            :mfe_pct, :mae_pct, :mfe_atr, :mae_atr, :hit_trigger, :hit_invalidation,
            :entry_day_of_week, :horizon_label, :crosses_weekend, :updated_at
        )
        """
        clean_records = []
        for o in outcomes:
            clean_records.append({
                "signal_id": o["signal_id"],
                "signal_key": o["signal_key"],
                "symbol": o["symbol"],
                "horizon_days": int(o["horizon_days"]),
                "status": o.get("status", "completed"),
                "exit_date": o.get("exit_date"),
                "exit_price": o.get("exit_price"),
                "return_pct": o.get("return_pct"),
                "spy_return_pct": o.get("spy_return_pct"),
                "excess_return_spy": o.get("excess_return_spy"),
                "baseline_return_pct": o.get("baseline_return_pct"),
                "excess_return_baseline": o.get("excess_return_baseline"),
                "mfe_pct": o.get("mfe_pct"),
                "mae_pct": o.get("mae_pct"),
                "mfe_atr": o.get("mfe_atr"),
                "mae_atr": o.get("mae_atr"),
                "hit_trigger": 1 if o.get("hit_trigger") else 0,
                "hit_invalidation": 1 if o.get("hit_invalidation") else 0,
                "entry_day_of_week": o.get("entry_day_of_week"),
                "horizon_label": o.get("horizon_label"),
                "crosses_weekend": 1 if o.get("crosses_weekend") else 0,
                "updated_at": now_str
            })
        conn = self._conn()
        try:
            with conn:
                conn.executemany(query, clean_records)
                return len(clean_records)
        finally:
            conn.close()

    def get_signal_outcomes(
        self,
        horizon_days: Optional[int] = None,
        rule_version: Optional[str] = None
    ) -> pd.DataFrame:
        conn = self._conn()
        try:
            query = """
            SELECT
                so.*,
                sr.company_name,
                sr.sector,
                sr.sub_industry,
                sr.side,
                sr.group_type,
                sr.setup_type,
                sr.rule_version,
                sr.candle_pattern,
                sr.first_detected_date,
                sr.entry_date,
                sr.entry_price,
                sr.spy_entry_price,
                sr.initial_score,
                sr.initial_atr
            FROM signal_outcomes so
            JOIN signal_records sr ON so.signal_id = sr.id
            """
            conditions = []
            params: List[Any] = []
            if horizon_days is not None:
                conditions.append("so.horizon_days = ?")
                params.append(horizon_days)
            if rule_version:
                conditions.append("sr.rule_version = ?")
                params.append(rule_version)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY sr.first_detected_date DESC, so.horizon_days ASC"

            df = pd.read_sql_query(query, conn, params=params)
            return df
        finally:
            conn.close()

    # --- Base Building Snapshots ("Đang Xây Nền") ---
    def save_base_snapshots(self, records: List[Dict[str, Any]], snapshot_id: Optional[int] = None) -> int:
        """Persist base building records linked to snapshot_id or as_of session."""
        if not records:
            return 0
        now_str = datetime.now().isoformat()
        clean_rows = []
        for r in records:
            checks_val = r.get("checks_json") or (json.dumps(r.get("checks", []), ensure_ascii=False) if isinstance(r.get("checks"), (list, dict)) else str(r.get("checks") or "[]"))
            warnings_val = r.get("warnings_json") or (json.dumps(r.get("warnings", []), ensure_ascii=False) if isinstance(r.get("warnings"), (list, dict)) else str(r.get("warnings") or "[]"))
            notes_val = r.get("notes_json") or (json.dumps(r.get("notes", []), ensure_ascii=False) if isinstance(r.get("notes"), (list, dict)) else str(r.get("notes") or "[]"))

            clean_rows.append({
                "snapshot_id": snapshot_id or r.get("snapshot_id"),
                "symbol": r["symbol"],
                "as_of": str(r.get("as_of", "")),
                "base_id": str(r.get("base_id", "")),
                "detected_at": str(r.get("detected_at", "")),
                "window_start": str(r.get("window_start") or ""),
                "window_end": str(r.get("window_end") or ""),
                "state": str(r.get("state", "none")),
                "lifecycle_phase": str(r.get("lifecycle_phase", "forming")),
                "is_active": 1 if r.get("is_active") else 0,
                "data_status": str(r.get("data_status", "valid")),
                "rule_version": str(r.get("rule_version", "v1.0")),
                "upper": r.get("upper"),
                "lower": r.get("lower"),
                "close_price": r.get("close_price"),
                "perf_1d": r.get("perf_1d"),
                "width_pct": r.get("width_pct"),
                "efficiency_ratio": r.get("efficiency_ratio"),
                "center_shift": r.get("center_shift"),
                "tr_contraction": r.get("tr_contraction"),
                "vol_contraction": r.get("vol_contraction"),
                "position": r.get("position"),
                "distance_to_upper_pct": r.get("distance_to_upper_pct"),
                "now_vs_pivot_pct": r.get("now_vs_pivot_pct"),
                "signed_volume_balance": r.get("signed_volume_balance"),
                "volume_balance_label": str(r.get("volume_balance_label", "Cân bằng")),
                "trend_context": str(r.get("trend_context", "Trung tính")),
                "rs_vs_spy": r.get("rs_vs_spy"),
                "rs_rating": r.get("rs_rating"),
                "high_52w": r.get("high_52w"),
                "from_52w_high_pct": r.get("from_52w_high_pct"),
                "breakout_date": r.get("breakout_date"),
                "breakout_price": r.get("breakout_price"),
                "breakout_bar_count": int(r.get("breakout_bar_count", 0)),
                "consecutive_below_ma50": int(r.get("consecutive_below_ma50", 0)),
                "ended_at": r.get("ended_at"),
                "end_reason": r.get("end_reason"),
                "formula_version": str(r.get("formula_version", "v2.0")),
                "consecutive_weakening": int(r.get("consecutive_weakening", 0)),
                "ma50": r.get("ma50"),
                "ma200": r.get("ma200"),
                "price_vs_ma50_pct": r.get("price_vs_ma50_pct"),
                "price_vs_ma200_pct": r.get("price_vs_ma200_pct"),
                "pressure_bias": str(r.get("pressure_bias", "Chưa tính")),
                "checks": checks_val,
                "warnings": warnings_val,
                "notes": notes_val,
                "created_at": now_str
            })

        query = """
        INSERT INTO base_snapshots (
            snapshot_id, symbol, as_of, base_id, detected_at,
            window_start, window_end, state, lifecycle_phase, is_active, data_status,
            rule_version, upper, lower, close_price, perf_1d, width_pct,
            efficiency_ratio, center_shift, tr_contraction, vol_contraction,
            position, distance_to_upper_pct, now_vs_pivot_pct, signed_volume_balance,
            volume_balance_label, trend_context, rs_vs_spy, rs_rating,
            high_52w, from_52w_high_pct, breakout_date, breakout_price,
            breakout_bar_count, consecutive_below_ma50, ended_at, end_reason, formula_version,
            consecutive_weakening, ma50, ma200, price_vs_ma50_pct, price_vs_ma200_pct, pressure_bias,
            checks, warnings, notes, created_at
        ) VALUES (
            :snapshot_id, :symbol, :as_of, :base_id, :detected_at,
            :window_start, :window_end, :state, :lifecycle_phase, :is_active, :data_status,
            :rule_version, :upper, :lower, :close_price, :perf_1d, :width_pct,
            :efficiency_ratio, :center_shift, :tr_contraction, :vol_contraction,
            :position, :distance_to_upper_pct, :now_vs_pivot_pct, :signed_volume_balance,
            :volume_balance_label, :trend_context, :rs_vs_spy, :rs_rating,
            :high_52w, :from_52w_high_pct, :breakout_date, :breakout_price,
            :breakout_bar_count, :consecutive_below_ma50, :ended_at, :end_reason, :formula_version,
            :consecutive_weakening, :ma50, :ma200, :price_vs_ma50_pct, :price_vs_ma200_pct, :pressure_bias,
            :checks, :warnings, :notes, :created_at
        )
        """
        conn = self._conn()
        try:
            with conn:
                # Ensure idempotent writes without duplicate entries per snapshot
                if snapshot_id is not None:
                    conn.execute("DELETE FROM base_snapshots WHERE snapshot_id = ?", (snapshot_id,))
                elif clean_rows:
                    sample_as_of = clean_rows[0]["as_of"]
                    syms = [r["symbol"] for r in clean_rows]
                    placeholders = ",".join(["?"] * len(syms))
                    conn.execute(f"DELETE FROM base_snapshots WHERE as_of = ? AND symbol IN ({placeholders})", [sample_as_of] + syms)
                conn.executemany(query, clean_rows)
            return len(clean_rows)
        finally:
            conn.close()

    def get_base_snapshots(
        self,
        snapshot_id: Optional[int] = None,
        as_of: Optional[str] = None,
        active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve base building records by snapshot_id or as_of, enriched with sector & company info."""
        conn = self._conn()
        try:
            query = """
            SELECT
                bs.*,
                c.security as company_name,
                c.sector,
                c.sub_industry,
                f.next_earnings_date,
                f.data_status as fa_data_status
            FROM base_snapshots bs
            LEFT JOIN constituents c ON bs.symbol = c.symbol
            LEFT JOIN fundamentals f ON bs.symbol = f.symbol
            """
            conditions = []
            params: List[Any] = []
            if snapshot_id is not None:
                conditions.append("bs.snapshot_id = ?")
                params.append(snapshot_id)
            elif as_of:
                conditions.append("bs.as_of = ?")
                params.append(as_of)

            if active_only:
                conditions.append("bs.is_active = 1")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY bs.is_active DESC, bs.width_pct ASC, bs.symbol ASC"

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["is_active"] = bool(d.get("is_active"))
                for json_col in ["checks", "warnings", "notes"]:
                    if d.get(json_col):
                        try:
                            d[json_col] = json.loads(d[json_col])
                        except Exception:
                            d[json_col] = []
                    else:
                        d[json_col] = []
                results.append(d)
            return results
        finally:
            conn.close()

    def get_latest_base_snapshots(
        self,
        as_of: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the latest snapshot of each distinct base setup up to as_of (inclusive),
        including active, climbing, and ended (played_out, failed) bases.
        Enriched with company name, sector, sub_industry, and fundamentals.
        """
        conn = self._conn()
        try:
            query = """
            WITH ranked AS (
                SELECT
                    bs.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY COALESCE(bs.base_id, bs.symbol)
                        ORDER BY bs.as_of DESC, bs.id DESC
                    ) as rn
                FROM base_snapshots bs
                WHERE (bs.base_id IS NOT NULL OR bs.symbol IS NOT NULL)
                  AND bs.state != 'none'
            """
            params: List[Any] = []
            if as_of:
                query += " AND bs.as_of <= ?"
                params.append(as_of)
            query += """
            )
            SELECT
                r.*,
                c.security as company_name,
                c.sector,
                c.sub_industry,
                f.next_earnings_date,
                f.data_status as fa_data_status
            FROM ranked r
            LEFT JOIN constituents c ON r.symbol = c.symbol
            LEFT JOIN fundamentals f ON r.symbol = f.symbol
            WHERE r.rn = 1
            ORDER BY r.is_active DESC, r.width_pct ASC, r.symbol ASC
            """
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["is_active"] = bool(d.get("is_active"))
                for json_col in ["checks", "warnings", "notes"]:
                    if d.get(json_col):
                        try:
                            d[json_col] = json.loads(d[json_col])
                        except Exception:
                            d[json_col] = []
                    else:
                        d[json_col] = []
                results.append(d)
            return results
        finally:
            conn.close()

    def get_active_bases_by_symbol(
        self,
        as_of: Optional[str] = None,
        before_date: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return mapping of symbol -> latest active base record.
        Use before_date for strictly prior sessions (e.g. pipeline tracking).
        Use as_of for latest active base as of that session (inclusive).
        """
        conn = self._conn()
        try:
            query = """
            WITH ranked AS (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY as_of DESC, id DESC) as rn
                FROM base_snapshots
                WHERE 1=1
            """
            params: List[Any] = []
            if before_date:
                query += " AND as_of < ?"
                params.append(before_date)
            elif as_of:
                query += " AND as_of <= ?"
                params.append(as_of)
            query += """
            )
            SELECT *
            FROM ranked
            WHERE rn = 1 AND is_active = 1
            """
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            res = {}
            for r in rows:
                d = dict(r)
                d["is_active"] = bool(d.get("is_active"))
                for json_col in ["checks", "warnings", "notes"]:
                    if d.get(json_col):
                        try:
                            d[json_col] = json.loads(d[json_col])
                        except Exception:
                            d[json_col] = []
                    else:
                        d[json_col] = []
                res[d["symbol"]] = d
            return res
        finally:
            conn.close()

    def get_last_base_by_symbol(self, symbol: str, before_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return the most recent base record (active or closed) for a symbol strictly prior to before_date."""
        conn = self._conn()
        try:
            query = "SELECT * FROM base_snapshots WHERE symbol = ?"
            params: List[Any] = [symbol]
            if before_date:
                query += " AND as_of < ?"
                params.append(before_date)
            query += " ORDER BY as_of DESC, id DESC LIMIT 1"
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["is_active"] = bool(d.get("is_active"))
            for json_col in ["checks", "warnings", "notes"]:
                if d.get(json_col):
                    try:
                        d[json_col] = json.loads(d[json_col])
                    except Exception:
                        d[json_col] = []
                else:
                    d[json_col] = []
            return d
        finally:
            conn.close()

    def get_active_post_breakout_bases(self, before_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return all active post-breakout bases (fresh_breakout or climbing) strictly prior to before_date.
        Grouped by base_id taking the latest snapshot per base_id chronologically (as_of DESC, id DESC).
        """
        conn = self._conn()
        try:
            query = """
            WITH ranked AS (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY base_id ORDER BY as_of DESC, id DESC) as rn
                FROM base_snapshots
                WHERE base_id IS NOT NULL
            """
            params: List[Any] = []
            if before_date:
                query += " AND as_of < ?"
                params.append(before_date)
            query += """
            )
            SELECT *
            FROM ranked
            WHERE rn = 1
              AND (lifecycle_phase IN ('fresh_breakout', 'climbing') OR state IN ('breakout_confirmed', 'fresh_breakout', 'climbing') OR (breakout_date IS NOT NULL AND is_active = 1))
              AND state NOT IN ('played_out', 'broken_down', 'lost_structure')
              AND lifecycle_phase NOT IN ('played_out', 'failed_before_breakout')
            """
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["is_active"] = bool(d.get("is_active"))
                for json_col in ["checks", "warnings", "notes"]:
                    if d.get(json_col):
                        try:
                            d[json_col] = json.loads(d[json_col])
                        except Exception:
                            d[json_col] = []
                    else:
                        d[json_col] = []
                results.append(d)
            return results
        finally:
            conn.close()

    def get_base_history_by_symbol(self, symbol: str, as_of: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return the history of distinct base setups for a symbol up to as_of (no future lookahead).
        Returns latest record per base_id, ordered by detected_at descending.
        """
        conn = self._conn()
        try:
            query = """
            WITH ranked AS (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY base_id ORDER BY as_of DESC, id DESC) as rn
                FROM base_snapshots
                WHERE symbol = ?
            """
            params: List[Any] = [symbol]
            if as_of:
                query += " AND as_of <= ?"
                params.append(as_of)
            query += """
            )
            SELECT *
            FROM ranked
            WHERE rn = 1
            ORDER BY detected_at DESC, as_of DESC
            """
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["is_active"] = bool(d.get("is_active"))
                for json_col in ["checks", "warnings", "notes"]:
                    if d.get(json_col):
                        try:
                            d[json_col] = json.loads(d[json_col])
                        except Exception:
                            d[json_col] = []
                    else:
                        d[json_col] = []
                results.append(d)
            return results
        finally:
            conn.close()


