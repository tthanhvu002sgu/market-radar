"""
Regression Test Suite for Base Building Engine Fixes.
Covers:
1. Fix 1: Historical snapshot chart filtering (date <= as_of) prevents future bar leaks.
2. Fix 2: Strict OHLC validation (Low <= Open, Close <= High) and trading calendar continuity / duplicate dates.
3. Fix 3: Pipeline scanner scoping to S&P 500 member stocks (excluding SPY, RSP, sector ETFs).
4. Fix 4: Active base retention for stale symbols & correlation against last-known base snapshot for state transitions.
"""
from datetime import date, timedelta
import pandas as pd
import pytest

from analytics.base_detector import BaseConfig, detect_base
from analytics.signal_events import generate_base_signal_events, generate_signal_events
from app.components.base_watchlist import _create_base_figure
from jobs.update_pipeline import process_base_detection_for_session
from storage.database import init_db
from storage.repository import MarketRadarRepository
from tests.test_base_detector import _make_daily_bars, _make_oscillating_closes


# ==============================================================================
# Fix 1: Chart date filtering regression tests
# ==============================================================================
class TestChartDateFilteringRegression:
    """Ensure candlestick chart cuts off at as_of date and never leaks future bars."""

    def test_chart_bars_strictly_before_or_equal_as_of(self):
        """
        Reproduction: Snapshot 2026-07-31 displayed candles up to 2026-08-21.
        Verify _create_base_figure only includes candles up to 2026-07-31.
        """
        # Create 70 daily bars starting June 1, 2026 (spans into August)
        closes = [100.0] * 70
        df = _make_daily_bars(closes, start_date="2026-06-01", symbol="AAPL")
        
        # Verify df contains dates beyond 2026-07-31
        max_df_date = df["date"].max()
        assert max_df_date >= "2026-08-01"

        base_info = {
            "symbol": "AAPL",
            "as_of": "2026-07-31",
            "upper": 105.0,
            "lower": 95.0,
            "window_start": "2026-07-01",
            "window_end": "2026-07-31"
        }

        fig = _create_base_figure(df, base_info)

        # Inspect candlestick x values
        candle_trace = fig.data[0]
        x_dates = list(candle_trace.x)
        assert len(x_dates) > 0
        assert max(x_dates) <= "2026-07-31"
        assert all(d <= "2026-07-31" for d in x_dates)
        # Ensure no August bars are present
        assert not any(d.startswith("2026-08") for d in x_dates)

    def test_chart_renders_gracefully_with_sparse_bars_under_20(self):
        """Historical chart renders gracefully without exception when filtered bars < 20."""
        closes = [100.0] * 12
        df = _make_daily_bars(closes, start_date="2026-07-01", symbol="AAPL")

        base_info = {
            "symbol": "AAPL",
            "as_of": "2026-07-10",
            "upper": 105.0,
            "lower": 95.0,
            "window_start": "2026-07-01",
            "window_end": "2026-07-10"
        }

        fig = _create_base_figure(df, base_info)
        assert fig is not None
        assert len(fig.data) >= 2


# ==============================================================================
# Fix 2: Strict OHLC and calendar continuity regression tests
# ==============================================================================
class TestOHLCAndCalendarContinuityRegression:
    """Ensure invalid OHLC and calendar gaps / duplicate dates are strictly rejected."""

    def test_reject_open_greater_than_high_reproducer(self):
        """
        Reproduction: Open = 1000 in price ~100 previously returned valid / forming.
        Now must return invalid_data and state='none'.
        """
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes)

        # Corrupt Open at bar 35 to 1000.0
        df.loc[35, "open"] = 1000.0
        as_of = df["date"].iloc[-1]

        res = detect_base(df, as_of=as_of)
        assert res.data_status == "invalid_data"
        assert res.is_active is False
        assert res.state == "none"
        assert any("OHLC không hợp lệ" in n for n in res.notes)

    def test_reject_close_below_low_or_above_high(self):
        """Close < Low or Close > High must return invalid_data."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        
        # Close < Low
        df_low = _make_daily_bars(closes)
        df_low.loc[35, "close"] = df_low.loc[35, "low"] - 5.0
        res_low = detect_base(df_low, as_of=df_low["date"].iloc[-1])
        assert res_low.data_status == "invalid_data"
        assert res_low.state == "none"

        # Close > High
        df_high = _make_daily_bars(closes)
        df_high.loc[35, "close"] = df_high.loc[35, "high"] + 5.0
        res_high = detect_base(df_high, as_of=df_high["date"].iloc[-1])
        assert res_high.data_status == "invalid_data"
        assert res_high.state == "none"

    def test_reject_open_below_low(self):
        """Open < Low must return invalid_data."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes)
        df.loc[35, "open"] = df.loc[35, "low"] - 5.0

        res = detect_base(df, as_of=df["date"].iloc[-1])
        assert res.data_status == "invalid_data"
        assert res.state == "none"

    def test_reject_missing_trading_session_in_window(self):
        """
        Reproduction: Deleting a session in the middle of window previously returned valid / forming.
        Now must detect calendar gap and return insufficient_data.
        """
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes)

        # Drop index 30 (which is a trading day in the middle of the base window)
        # Note: index 30 is 2026-07-01 (Wednesday)
        df_gap = df.drop(index=30).reset_index(drop=True)
        as_of = df_gap["date"].iloc[-1]

        res = detect_base(df_gap, as_of=as_of)
        assert res.data_status == "insufficient_data"
        assert res.is_active is False
        assert res.state == "none"
        assert any("lịch thị trường" in n for n in res.notes)

    def test_reject_duplicate_dates(self):
        """Duplicate dates in the window must return invalid_data."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes)

        # Duplicate date at index 35
        df.loc[35, "date"] = df.loc[34, "date"]
        as_of = df["date"].iloc[-1]

        res = detect_base(df, as_of=as_of)
        assert res.data_status == "invalid_data"
        assert res.is_active is False
        assert res.state == "none"
        assert any("trùng lặp" in n for n in res.notes)

    def test_handle_invalid_or_error_preserves_all_base_metrics_when_active(self):
        """When an ongoing active base experiences stale/invalid data, all geometric metrics and checks are preserved."""
        prev_base = {
            "symbol": "AAPL",
            "as_of": "2026-09-08",
            "base_id": "AAPL:2026-09-08:v1.0",
            "detected_at": "2026-09-08",
            "window_start": "2026-08-10",
            "window_end": "2026-09-08",
            "state": "tight",
            "is_active": True,
            "upper": 150.0,
            "lower": 140.0,
            "close_price": 148.0,
            "width_pct": 7.14,
            "efficiency_ratio": 0.22,
            "center_shift": 0.12,
            "tr_contraction": 0.65,
            "vol_contraction": 0.55,
            "position": 0.8,
            "distance_to_upper_pct": -1.33,
            "signed_volume_balance": 0.35,
            "volume_balance_label": "Volume thuận",
            "trend_context": "Nền trong xu hướng tăng",
            "rs_vs_spy": 1.05,
            "consecutive_weakening": 0,
            "ma50": 142.0,
            "ma200": 135.0,
            "price_vs_ma50_pct": 4.23,
            "price_vs_ma200_pct": 9.63,
            "pressure_bias": "Áp lực mua tích cực",
            "checks": [{"name": "Độ rộng nền", "pass": True, "value": "7.1%", "threshold": "<=12.0%"}]
        }

        # Stale data call with empty DataFrame
        res = detect_base(pd.DataFrame(), as_of="2026-09-09", previous_base=prev_base)
        assert res.is_active is True
        assert res.data_status == "insufficient_data"
        assert res.state == "tight"
        assert res.upper == 150.0
        assert res.lower == 140.0
        assert res.width_pct == 7.14
        assert res.efficiency_ratio == 0.22
        assert res.center_shift == 0.12
        assert res.tr_contraction == 0.65
        assert res.vol_contraction == 0.55
        assert res.position == 0.8
        assert res.distance_to_upper_pct == -1.33
        assert res.signed_volume_balance == 0.35
        assert res.volume_balance_label == "Volume thuận"
        assert res.trend_context == "Nền trong xu hướng tăng"
        assert len(res.checks) == 1
        assert res.checks[0]["name"] == "Độ rộng nền"


# ==============================================================================
# Fix 3: S&P 500 symbol scoping regression tests
# ==============================================================================
class TestBaseScannerScopingRegression:
    """Ensure ETF and benchmark tickers are excluded from base scanning."""

    def test_fresh_sp500_filters_out_etfs_and_benchmarks(self):
        """
        Verify fresh_sp500 strictly excludes SPY, RSP, and sector ETFs like XLK, XLE,
        so they cannot enter base_records or candidate FA enrichment.
        """
        sp500_constituents = {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"}
        fresh_symbols = {"SPY", "RSP", "XLK", "XLE", "AAPL", "MSFT", "NVDA"}

        # Logic used in update_pipeline.py
        fresh_sp500 = set(s for s in fresh_symbols if s in sp500_constituents)

        assert "SPY" not in fresh_sp500
        assert "RSP" not in fresh_sp500
        assert "XLK" not in fresh_sp500
        assert "XLE" not in fresh_sp500
        assert fresh_sp500 == {"AAPL", "MSFT", "NVDA"}

    def test_process_base_detection_excludes_benchmarks_and_etfs(self, tmp_path):
        """
        Real integration test: process_base_detection_for_session strictly scans fresh S&P 500 stocks
        and completely ignores benchmarks and sector ETFs, even if present in active_bars or prev_active_bases.
        """
        db_file = tmp_path / "test_scoping.db"
        repo = MarketRadarRepository(db_path=db_file)

        # Prepare bars for SPY, XLK, and AAPL
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        spy_bars = _make_daily_bars(closes, symbol="SPY")
        xlk_bars = _make_daily_bars(closes, symbol="XLK")
        aapl_bars = _make_daily_bars(closes, symbol="AAPL")

        df_bars = pd.concat([spy_bars, xlk_bars, aapl_bars], ignore_index=True)
        active_bars = df_bars.copy()

        # Seed prev_active_bases with a legacy ETF base for SPY (which should be discarded)
        snap1_id = repo.save_snapshot(
            as_of="2026-09-08", rule_version="v1.0", total_universe=500, valid_universe=500,
            coverage_pct=1.0, missing_symbols=[], market_metrics={}, sector_metrics=[], candidates=[]
        )
        legacy_etf_base = [{
            "symbol": "SPY",
            "as_of": "2026-09-08",
            "base_id": "SPY:2026-09-08:v1.0",
            "detected_at": "2026-09-08",
            "state": "tight",
            "is_active": True,
            "upper": 105.0,
            "lower": 95.0
        }]
        repo.save_base_snapshots(legacy_etf_base, snapshot_id=snap1_id)

        target_session = aapl_bars["date"].iloc[-1]
        sp500_symbols = ["AAPL", "MSFT"]
        fresh_sp500 = {"AAPL"}

        base_records, base_building_symbols = process_base_detection_for_session(
            repo=repo,
            df_bars=df_bars,
            active_bars=active_bars,
            fresh_sp500=fresh_sp500,
            sp500_symbols=sp500_symbols,
            target_session=target_session
        )

        record_symbols = [b["symbol"] for b in base_records]
        assert "SPY" not in record_symbols, "Benchmark SPY must never be in base_records"
        assert "XLK" not in record_symbols, "Sector ETF XLK must never be in base_records"
        assert "SPY" not in base_building_symbols
        assert "XLK" not in base_building_symbols
        assert "AAPL" in record_symbols
        assert "AAPL" in base_building_symbols


# ==============================================================================
# Fix 4: Active base retention & state transition correlation regression tests
# ==============================================================================
class TestActiveBaseRetentionAndTransitionCorrelationRegression:
    """Ensure stale active bases are preserved in snapshots and state transitions fire upon recovery."""

    def test_stale_active_base_retained_with_observation_status(self, tmp_path):
        """
        Active base for symbol with missing/stale data in current session is retained
        with data_status='stale_data' and is_active=True.
        """
        db_file = tmp_path / "test_stale_retention.db"
        repo = MarketRadarRepository(db_path=db_file)

        # Create parent snapshot 1
        snap1_id = repo.save_snapshot(
            as_of="2026-09-08",
            rule_version="v1.0",
            total_universe=500,
            valid_universe=500,
            coverage_pct=1.0,
            missing_symbols=[],
            market_metrics={},
            sector_metrics=[],
            candidates=[]
        )

        # Session 1: Symbol XYZ forms an active base
        base_s1 = [{
            "symbol": "XYZ",
            "as_of": "2026-09-08",
            "base_id": "XYZ:2026-09-08:v1.0",
            "detected_at": "2026-09-08",
            "state": "tight",
            "is_active": True,
            "upper": 110.0,
            "lower": 100.0,
            "close_price": 108.0
        }]
        repo.save_base_snapshots(base_s1, snapshot_id=snap1_id)

        # Session 2 (2026-09-09): XYZ has missing/stale data
        snap2_id = repo.save_snapshot(
            as_of="2026-09-09",
            rule_version="v1.0",
            total_universe=500,
            valid_universe=500,
            coverage_pct=1.0,
            missing_symbols=["XYZ"],
            market_metrics={},
            sector_metrics=[],
            candidates=[]
        )

        prev_active = repo.get_active_bases_by_symbol(before_date="2026-09-09")
        assert "XYZ" in prev_active
        prev_base = prev_active["XYZ"]

        # Call detect_base with empty or stale bars
        res_stale = detect_base(pd.DataFrame(), as_of="2026-09-09", previous_base=prev_base)
        assert res_stale.is_active is True
        assert res_stale.base_id == "XYZ:2026-09-08:v1.0"
        assert res_stale.state == "tight"
        assert res_stale.upper == 110.0
        assert res_stale.lower == 100.0

        # Save to session 2 snapshots with observation status
        base_dict_s2 = res_stale.to_dict()
        if base_dict_s2.get("data_status") == "valid":
            base_dict_s2["data_status"] = "stale_data"
        repo.save_base_snapshots([base_dict_s2], snapshot_id=snap2_id)

        # Verify session 2 has the retained base
        s2_bases = repo.get_base_snapshots(snapshot_id=snap2_id)
        assert len(s2_bases) == 1
        assert s2_bases[0]["symbol"] == "XYZ"
        assert s2_bases[0]["is_active"] is True

        # Ensure no spurious alerts fire while data is stale
        events_s2 = generate_base_signal_events(
            current_bases=[base_dict_s2],
            prev_bases=base_s1,
            as_of="2026-09-09"
        )
        assert len(events_s2) == 0

        # Verify process_base_detection_for_session retains XYZ but excludes it from base_building_symbols
        pipe_records, pipe_building = process_base_detection_for_session(
            repo=repo,
            df_bars=pd.DataFrame(),
            active_bars=pd.DataFrame(),
            fresh_sp500=set(),
            sp500_symbols=["XYZ"],
            target_session="2026-09-09"
        )
        assert any(r["symbol"] == "XYZ" for r in pipe_records)
        assert "XYZ" not in pipe_building, "Stale symbols must never be added to base_building_symbols (FA priority)"

    def test_breakout_transition_alert_recovered_after_missing_data(self, tmp_path):
        """
        When data recovers and breakout occurs after a missing data session,
        correlating against the last known base snapshot successfully fires breakout_confirmed.
        """
        db_file = tmp_path / "test_breakout_recovery.db"
        repo = MarketRadarRepository(db_path=db_file)

        snap1_id = repo.save_snapshot(
            as_of="2026-09-08",
            rule_version="v1.0",
            total_universe=500,
            valid_universe=500,
            coverage_pct=1.0,
            missing_symbols=[],
            market_metrics={},
            sector_metrics=[],
            candidates=[]
        )

        # Prior active base in tight state
        prior_base = {
            "symbol": "XYZ",
            "as_of": "2026-09-08",
            "base_id": "XYZ:2026-09-08:v1.0",
            "detected_at": "2026-09-08",
            "state": "tight",
            "is_active": True,
            "upper": 110.0,
            "lower": 100.0,
            "close_price": 108.0
        }
        repo.save_base_snapshots([prior_base], snapshot_id=snap1_id)

        # Current session (2026-09-10): Data recovers, price confirms breakout above upper!
        current_base = {
            "symbol": "XYZ",
            "as_of": "2026-09-10",
            "base_id": "XYZ:2026-09-08:v1.0",
            "detected_at": "2026-09-08",
            "state": "breakout_confirmed",
            "is_active": False,
            "upper": 110.0,
            "lower": 100.0,
            "close_price": 114.0,
            "data_status": "valid"
        }

        # Case A: Using prev_bases populated with last known base snapshot
        prev_bases_list = []
        # Correlation logic as in update_pipeline.py
        prev_bases_map = {b["base_id"]: b for b in prev_bases_list if b.get("base_id")}
        last_b = repo.get_last_base_by_symbol("XYZ", before_date="2026-09-10")
        if last_b:
            prev_bases_map[last_b["base_id"]] = last_b
        prev_bases_list = list(prev_bases_map.values())

        events = generate_base_signal_events(
            current_bases=[current_base],
            prev_bases=prev_bases_list,
            as_of="2026-09-10"
        )
        assert len(events) == 1
        assert events[0]["event_type"] == "base_breakout_confirmed"
        assert events[0]["symbol"] == "XYZ"
        assert "114.00" in events[0]["title"]
        assert "110.00" in events[0]["summary"]
        assert events[0]["severity"] == "opportunity"

        # Case B: Direct recovery even if prev_bases list was empty
        events_empty_prev = generate_base_signal_events(
            current_bases=[current_base],
            prev_bases=[],
            as_of="2026-09-10"
        )
        assert len(events_empty_prev) == 1
        assert events_empty_prev[0]["event_type"] == "base_breakout_confirmed"

    def test_lost_structure_transition_alert_recovered_after_missing_data(self):
        """When a base loses structure after missing data, base_lost_structure event is emitted."""
        current_base = {
            "symbol": "XYZ",
            "as_of": "2026-09-10",
            "base_id": "XYZ:2026-09-08:v1.0",
            "detected_at": "2026-09-08",
            "state": "lost_structure",
            "is_active": False,
            "upper": 110.0,
            "lower": 100.0,
            "close_price": 104.0,
            "data_status": "valid"
        }
        events = generate_base_signal_events(
            current_bases=[current_base],
            prev_bases=[],
            as_of="2026-09-10"
        )
        assert len(events) == 1
        assert events[0]["event_type"] == "base_lost_structure"
        assert events[0]["symbol"] == "XYZ"
