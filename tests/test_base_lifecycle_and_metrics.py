"""
Test Suite for Base Building Lifecycle and 6 Core Metrics.
Covers:
1. 6 core metrics calculations (signs, percentages, bounds, 52w high >= 252 bars, None handling).
2. Lifecycle state machine: forming -> fresh_breakout (sessions 1-5) -> climbing (session 6+).
3. Termination rules (Played Out): Close < lower bound or 2 consecutive closes below MA50.
4. Pre-breakout failures (broken_down, lost_structure) preserved as failed_before_breakout, not played_out.
5. Idempotence: re-running on same session date preserves counters.
6. Stale / missing data handling does not advance state machine.
7. Historical query point-in-time consistency (no future lookahead).
8. Universal filtering logic and UI helper rendering.
"""
from datetime import date, datetime, timedelta
import pandas as pd
import pytest

from analytics.base_detector import BaseConfig, BaseResult, detect_base, track_post_breakout_base
from app.components.base_watchlist import (
    get_base_lifecycle,
    format_base_summary_line,
    render_base_metrics_grid
)
from storage.database import init_db
from storage.repository import MarketRadarRepository
from tests.test_base_detector import _make_daily_bars, _make_oscillating_closes


class Test6MetricsCalculations:
    """Verify exact formula calculations, signs, and bounds for the 6 core metrics."""

    def test_now_vs_pivot_pct_sign_and_value(self):
        """Now vs pivot (%) = 100 * (Close / Upper - 1). Positive above, negative below."""
        # Oscillating closes with center 100
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes, symbol="NVDA")
        as_of = df["date"].iloc[-1]

        res = detect_base(df, as_of=as_of)
        assert res.state in ("tight", "forming")
        assert res.upper is not None
        assert res.close_price is not None
        assert res.now_vs_pivot_pct is not None

        # Expected formula
        expected_nvp = round(100.0 * (res.close_price / res.upper - 1.0), 2)
        assert res.now_vs_pivot_pct == expected_nvp

        # When close < upper, now_vs_pivot_pct is negative
        if res.close_price < res.upper:
            assert res.now_vs_pivot_pct < 0

    def test_from_52w_high_requires_252_bars(self):
        """From 52-week high is None when bars < 252, and calculated when bars >= 252."""
        # 1. Only 50 bars: should be None
        closes_50 = [100.0] * 50
        df_50 = _make_daily_bars(closes_50, symbol="MSFT")
        res_50 = detect_base(df_50, as_of=df_50["date"].iloc[-1])
        assert res_50.high_52w is None
        assert res_50.from_52w_high_pct is None

        # 2. 260 bars with high 120 and final close 108
        closes_260 = [100.0] * 259 + [108.0]
        df_260 = _make_daily_bars(closes_260, symbol="MSFT", start_date="2025-01-01")
        # Inject high 120 at index 100
        df_260.loc[100, "high"] = 120.0

        as_of_260 = df_260["date"].iloc[-1]
        res_260 = detect_base(df_260, as_of=as_of_260)
        assert res_260.high_52w == 120.0
        # Expected: 100 * (120 - 108) / 120 = 10.0%
        expected_from_high = round(100.0 * (120.0 - 108.0) / 120.0, 2)
        assert res_260.from_52w_high_pct == expected_from_high
        assert res_260.from_52w_high_pct > 0

    def test_signed_volume_balance_bounded(self):
        """Signed volume balance is bounded in [-1.0, 1.0]."""
        closes = _make_oscillating_closes(n_bars=45, center=50.0, amplitude=1.0)
        df = _make_daily_bars(closes, symbol="AAPL")
        res = detect_base(df, as_of=df["date"].iloc[-1])
        assert res.signed_volume_balance is not None
        assert -1.0 <= res.signed_volume_balance <= 1.0

    def test_rs_rating_propagation(self):
        """RS rating (1-99) is received and populated onto BaseResult."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes, symbol="GOOG")
        res = detect_base(df, as_of=df["date"].iloc[-1], rs_rating=92)
        assert res.rs_rating == 92


class TestLifecycleTransitions:
    """Verify transitions: forming -> fresh_breakout (sessions 1-5) -> climbing (session 6+)."""

    def test_fresh_breakout_session_1_to_5(self):
        """Breakout day is session 1 (fresh_breakout). Sessions 2-5 advance count within fresh_breakout."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes, symbol="TSLA")
        as_of_initial = df["date"].iloc[-1]

        # Initial forming base
        base_t0 = detect_base(df, as_of=as_of_initial)
        assert base_t0.is_active is True
        frozen_upper = base_t0.upper
        frozen_lower = base_t0.lower

        # Session 1: Confirmed breakout (Volume 3x)
        d_next1 = pd.to_datetime(as_of_initial) + timedelta(days=1)
        d1_str = d_next1.strftime("%Y-%m-%d")
        bar_bo = pd.DataFrame([{
            "symbol": "TSLA",
            "date": d1_str,
            "open": frozen_upper + 0.5,
            "high": frozen_upper + 2.0,
            "low": frozen_upper + 0.2,
            "close": frozen_upper + 1.5,
            "volume": 600_000.0  # 3x volume
        }])
        df_t1 = pd.concat([df, bar_bo], ignore_index=True)
        res_t1 = detect_base(df_t1, as_of=d1_str, previous_base=base_t0.to_dict())

        assert res_t1.state == "breakout_confirmed"
        assert res_t1.lifecycle_phase == "fresh_breakout"
        assert res_t1.breakout_bar_count == 1
        assert res_t1.breakout_date == d1_str

        # Sessions 2, 3, 4, 5: post-breakout tracker advances count in fresh_breakout
        curr_base = res_t1.to_dict()
        curr_df = df_t1.copy()
        curr_date = d_next1

        for session_num in range(2, 6):
            curr_date += timedelta(days=1)
            d_str = curr_date.strftime("%Y-%m-%d")
            next_bar = pd.DataFrame([{
                "symbol": "TSLA",
                "date": d_str,
                "open": frozen_upper + 1.0,
                "high": frozen_upper + 2.0,
                "low": frozen_upper + 0.5,
                "close": frozen_upper + 1.2,
                "volume": 250_000.0
            }])
            curr_df = pd.concat([curr_df, next_bar], ignore_index=True)
            res = detect_base(curr_df, as_of=d_str, previous_base=curr_base)

            assert res.lifecycle_phase == "fresh_breakout", f"Failed at session {session_num}"
            assert res.state == "fresh_breakout"
            assert res.breakout_bar_count == session_num
            assert res.is_active is True
            curr_base = res.to_dict()

        # Session 6: Strictly transitions to climbing!
        curr_date += timedelta(days=1)
        d6_str = curr_date.strftime("%Y-%m-%d")
        bar6 = pd.DataFrame([{
            "symbol": "TSLA",
            "date": d6_str,
            "open": frozen_upper + 1.2,
            "high": frozen_upper + 2.5,
            "low": frozen_upper + 1.0,
            "close": frozen_upper + 2.0,
            "volume": 250_000.0
        }])
        curr_df = pd.concat([curr_df, bar6], ignore_index=True)
        res6 = detect_base(curr_df, as_of=d6_str, previous_base=curr_base)

        assert res6.breakout_bar_count == 6
        assert res6.lifecycle_phase == "climbing"
        assert res6.state == "climbing"
        assert res6.is_active is True


class TestTerminationConditions:
    """Verify termination (played_out) rules and separation from pre-breakout failure."""

    def test_termination_priority_on_close_below_lower(self):
        """Close < lower bound terminates post-breakout base immediately with priority."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes, symbol="AMD")
        as_of_0 = df["date"].iloc[-1]
        base_0 = detect_base(df, as_of=as_of_0)
        lower_bound = base_0.lower

        # Simulate fresh breakout at bar 2
        prev_base = base_0.to_dict()
        prev_base.update({
            "lifecycle_phase": "fresh_breakout",
            "state": "fresh_breakout",
            "breakout_date": as_of_0,
            "breakout_price": base_0.upper + 1.0,
            "breakout_bar_count": 2,
            "is_active": True
        })

        # Next bar collapses below lower bound
        next_d = (pd.to_datetime(as_of_0) + timedelta(days=1)).strftime("%Y-%m-%d")
        next_bar = pd.DataFrame([{
            "symbol": "AMD",
            "date": next_d,
            "open": lower_bound - 0.5,
            "high": lower_bound,
            "low": lower_bound - 2.0,
            "close": lower_bound - 1.5,
            "volume": 300_000.0
        }])
        df_next = pd.concat([df, next_bar], ignore_index=True)

        res = track_post_breakout_base(prev_base, df_next, as_of=next_d)
        assert res.state == "played_out"
        assert res.lifecycle_phase == "played_out"
        assert res.is_active is False
        assert "Thủng đáy nền" in (res.end_reason or "")
        assert res.ended_at == next_d

    def test_termination_after_2_consecutive_closes_below_ma50(self):
        """2 consecutive closes below MA50 terminates post-breakout setup."""
        # Create 60 bars so MA50 is well-defined (~100)
        closes = [100.0] * 60
        df = _make_daily_bars(closes, symbol="QCOM")
        as_of_0 = df["date"].iloc[-1]

        prev_base = {
            "symbol": "QCOM",
            "as_of": as_of_0,
            "base_id": "BASE-QCOM",
            "detected_at": "2026-06-01",
            "window_start": "2026-06-01",
            "window_end": as_of_0,
            "upper": 105.0,
            "lower": 80.0,
            "lifecycle_phase": "fresh_breakout",
            "state": "fresh_breakout",
            "breakout_date": as_of_0,
            "breakout_price": 106.0,
            "breakout_bar_count": 3,
            "consecutive_below_ma50": 1,  # Already 1 close below MA50
            "is_active": True
        }

        # Next bar closes at 90 (below MA50 ~100, but still above lower 80)
        next_d = (pd.to_datetime(as_of_0) + timedelta(days=1)).strftime("%Y-%m-%d")
        next_bar = pd.DataFrame([{
            "symbol": "QCOM",
            "date": next_d,
            "open": 92.0,
            "high": 93.0,
            "low": 89.0,
            "close": 90.0,
            "volume": 200_000.0
        }])
        df_next = pd.concat([df, next_bar], ignore_index=True)

        res = track_post_breakout_base(prev_base, df_next, as_of=next_d)
        assert res.consecutive_below_ma50 == 2
        assert res.state == "played_out"
        assert res.lifecycle_phase == "played_out"
        assert res.is_active is False
        assert "2 phiên liên tiếp đóng cửa dưới MA50" in (res.end_reason or "")

    def test_failed_before_breakout_not_categorized_as_played_out(self):
        """Bases breaking down before breakout have lifecycle_phase failed_before_breakout, NOT played_out."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes, symbol="INTC")
        as_of_0 = df["date"].iloc[-1]
        base_0 = detect_base(df, as_of=as_of_0)

        # Breakdown before breakout
        next_d = (pd.to_datetime(as_of_0) + timedelta(days=1)).strftime("%Y-%m-%d")
        next_bar = pd.DataFrame([{
            "symbol": "INTC",
            "date": next_d,
            "open": base_0.lower - 0.5,
            "high": base_0.lower - 0.1,
            "low": base_0.lower - 2.0,
            "close": base_0.lower - 1.0,
            "volume": 300_000.0
        }])
        df_next = pd.concat([df, next_bar], ignore_index=True)

        res = detect_base(df_next, as_of=next_d, previous_base=base_0.to_dict())
        assert res.state == "broken_down"
        assert res.lifecycle_phase == "failed_before_breakout"
        assert res.lifecycle_phase != "played_out"
        assert res.is_active is False


class TestIdempotenceAndStaleData:
    """Verify that idempotent runs do not duplicate or advance state."""

    def test_idempotent_run_on_same_session_date(self):
        """Re-running on the exact same as_of date does not increment bar counts."""
        closes = [100.0] * 60
        df = _make_daily_bars(closes, symbol="AMZN")
        as_of = df["date"].iloc[-1]

        prev_base = {
            "symbol": "AMZN",
            "as_of": as_of,
            "base_id": "BASE-AMZN",
            "detected_at": "2026-06-01",
            "upper": 105.0,
            "lower": 95.0,
            "lifecycle_phase": "fresh_breakout",
            "state": "fresh_breakout",
            "breakout_date": as_of,
            "breakout_price": 106.0,
            "breakout_bar_count": 3,
            "consecutive_below_ma50": 0,
            "is_active": True
        }

        # Call with same as_of
        res = track_post_breakout_base(prev_base, df, as_of=as_of)
        assert res.breakout_bar_count == 3  # Did not increment!
        assert res.consecutive_below_ma50 == 0

    def test_stale_data_does_not_advance_state(self):
        """When latest bar date is prior to as_of, returns stale_data without state advance."""
        closes = [100.0] * 50
        df = _make_daily_bars(closes, symbol="NFLX")
        bar_date = df["date"].iloc[-1]

        # Target as_of is 5 days ahead of available bars
        future_as_of = (pd.to_datetime(bar_date) + timedelta(days=5)).strftime("%Y-%m-%d")

        prev_base = {
            "symbol": "NFLX",
            "as_of": bar_date,
            "base_id": "BASE-NFLX",
            "detected_at": "2026-06-01",
            "upper": 105.0,
            "lower": 95.0,
            "lifecycle_phase": "fresh_breakout",
            "state": "fresh_breakout",
            "breakout_bar_count": 2,
            "is_active": True
        }

        res = track_post_breakout_base(prev_base, df, as_of=future_as_of)
        assert res.data_status == "stale_data"
        assert res.breakout_bar_count == 2  # Counter preserved, not advanced


class TestRepositoryAndHistoricalLookahead:
    """Verify SQLite storage and point-in-time querying without future lookahead."""

    def test_save_and_retrieve_base_history_by_symbol(self, tmp_path):
        """Ensure get_base_history_by_symbol filters as_of <= target without future leaks."""
        db_file = tmp_path / "test_lifecycle.db"
        init_db(db_file)
        repo = MarketRadarRepository(db_file)

        # Save setup 1 on session 2026-08-01
        row1 = {
            "symbol": "META",
            "as_of": "2026-08-01",
            "base_id": "BASE-META-1",
            "detected_at": "2026-07-15",
            "window_start": "2026-07-01",
            "window_end": "2026-08-01",
            "state": "forming",
            "lifecycle_phase": "forming",
            "is_active": 1,
            "upper": 300.0,
            "lower": 280.0,
            "close_price": 295.0,
            "width_pct": 7.1,
            "now_vs_pivot_pct": -1.67,
            "rs_rating": 88
        }
        repo.save_base_snapshots([row1], snapshot_id=None)

        # Save setup 2 on session 2026-09-01 (future from 2026-08-01)
        row2 = {
            "symbol": "META",
            "as_of": "2026-09-01",
            "base_id": "BASE-META-2",
            "detected_at": "2026-08-20",
            "window_start": "2026-08-01",
            "window_end": "2026-09-01",
            "state": "fresh_breakout",
            "lifecycle_phase": "fresh_breakout",
            "is_active": 1,
            "upper": 330.0,
            "lower": 310.0,
            "close_price": 335.0,
            "width_pct": 6.5,
            "now_vs_pivot_pct": 1.52,
            "breakout_date": "2026-09-01",
            "breakout_bar_count": 1,
            "rs_rating": 94
        }
        repo.save_base_snapshots([row2], snapshot_id=None)

        # Query as of 2026-08-15: MUST ONLY return BASE-META-1
        hist_aug = repo.get_base_history_by_symbol("META", as_of="2026-08-15")
        assert len(hist_aug) == 1
        assert hist_aug[0]["base_id"] == "BASE-META-1"
        assert hist_aug[0]["as_of"] == "2026-08-01"

        # Query as of 2026-09-10: returns both setups
        hist_sep = repo.get_base_history_by_symbol("META", as_of="2026-09-10")
        assert len(hist_sep) == 2


class TestUniversalFilterAndUIHelpers:
    """Verify UI categorization, summary lines, and 6-metrics grid helper."""

    def test_get_base_lifecycle_mapping(self):
        """Ensure get_base_lifecycle accurately categorizes all base states."""
        assert get_base_lifecycle({"lifecycle_phase": "forming"}) == "forming"
        assert get_base_lifecycle({"lifecycle_phase": "fresh_breakout"}) == "fresh_breakout"
        assert get_base_lifecycle({"lifecycle_phase": "climbing"}) == "climbing"
        assert get_base_lifecycle({"lifecycle_phase": "played_out"}) == "played_out"
        assert get_base_lifecycle({"state": "broken_down"}) == "failed_before_breakout"
        assert get_base_lifecycle({"state": "lost_structure"}) == "failed_before_breakout"
        assert get_base_lifecycle({"state": "tight"}) == "forming"

    def test_format_base_summary_line(self):
        """Format base summary line with depth and pivot."""
        line = format_base_summary_line({"width_pct": 8.4, "upper": 185.5})
        assert "sâu 8.4%" in line
        assert "Pivot $185.50" in line
        assert "20 phiên / khoảng 4 tuần" in line

    def test_render_base_metrics_grid_handles_none_gracefully(self):
        """render_base_metrics_grid renders without error even when fields are None."""
        empty_info = {}
        # Should execute cleanly without raising exception
        render_base_metrics_grid(empty_info)


class TestEdgeCasesAndEnhancements:
    """Verify newly attacked edge cases, queries, and UI helpers."""

    def test_52w_high_exact_251_vs_252_bars(self):
        """Boundary test: bars < 252 produces None, bars == 252 calculates 52w high and distance."""
        # 251 bars: exactly 1 bar short
        closes_251 = [100.0] * 250 + [105.0]
        df_251 = _make_daily_bars(closes_251, symbol="BND1", start_date="2025-01-01")
        res_251 = detect_base(df_251, as_of=df_251["date"].iloc[-1])
        assert res_251.high_52w is None
        assert res_251.from_52w_high_pct is None

        # 252 bars: exactly activates the threshold
        closes_252 = [100.0] * 251 + [105.0]
        df_252 = _make_daily_bars(closes_252, symbol="BND2", start_date="2025-01-01")
        # Set a peak high at bar 100
        df_252.loc[100, "high"] = 125.0
        res_252 = detect_base(df_252, as_of=df_252["date"].iloc[-1])
        assert res_252.high_52w == 125.0
        expected_dist = round(100.0 * (125.0 - 105.0) / 125.0, 2)
        assert res_252.from_52w_high_pct == expected_dist
        assert res_252.from_52w_high_pct == 16.0

    def test_perf_1d_calculation_and_propagation(self, tmp_path):
        """Verify perf_1d is computed from close_T and close_{T-1} and persisted to SQLite."""
        closes = [100.0] * 44 + [102.5]
        df = _make_daily_bars(closes, symbol="P1D")
        as_of = df["date"].iloc[-1]

        res = detect_base(df, as_of=as_of)
        assert res.perf_1d is not None
        # Expected: 100 * (102.5 - 100.0) / 100.0 = +2.50%
        assert res.perf_1d == 2.5

        # Test persistence
        db_file = tmp_path / "test_perf1d.db"
        init_db(db_file)
        repo = MarketRadarRepository(db_file)
        repo.save_base_snapshots([res.to_dict()], snapshot_id=None)

        loaded = repo.get_base_snapshots(as_of=as_of)
        assert len(loaded) == 1
        assert loaded[0]["perf_1d"] == 2.5

    def test_repo_get_active_post_breakout_bases_retrieves_breakout_confirmed(self, tmp_path):
        """Ensure get_active_post_breakout_bases finds session 1 breakout records for subsequent session tracking."""
        db_file = tmp_path / "test_pb_repo.db"
        init_db(db_file)
        repo = MarketRadarRepository(db_file)

        # Record from session 1: breakout_confirmed with is_active=0 (as legacy detector set)
        row = {
            "symbol": "NVDA",
            "as_of": "2026-09-10",
            "base_id": "NVDA:2026-09-01:v1.0",
            "detected_at": "2026-09-01",
            "state": "breakout_confirmed",
            "lifecycle_phase": "fresh_breakout",
            "is_active": 0,
            "breakout_date": "2026-09-10",
            "breakout_bar_count": 1,
            "upper": 120.0,
            "lower": 110.0,
            "close_price": 125.0
        }
        repo.save_base_snapshots([row], snapshot_id=None)

        # Query before 2026-09-11
        active_pbs = repo.get_active_post_breakout_bases(before_date="2026-09-11")
        assert len(active_pbs) == 1
        assert active_pbs[0]["symbol"] == "NVDA"
        assert active_pbs[0]["breakout_bar_count"] == 1
        assert active_pbs[0]["lifecycle_phase"] == "fresh_breakout"

    def test_breakout_below_ma50_tracks_consecutive_and_terminates(self):
        """When breakout bar closes below MA50, consecutive_below_ma50 is initialized and 2nd close terminates setup."""
        # Closes: first 50 bars at 120, next 30 bars oscillating around 100 so MA50 is ~108, upper ~101.5
        closes = [120.0] * 50 + _make_oscillating_closes(n_bars=30, center=100.0, amplitude=1.0)
        df = _make_daily_bars(closes, symbol="BEAR_BO")
        as_of_0 = df["date"].iloc[-1]
        base_0 = detect_base(df, as_of=as_of_0)
        assert base_0.is_active is True
        upper = base_0.upper

        # Breakout at upper + 1.0 (still far below MA50 ~115)
        d_next1 = (pd.to_datetime(as_of_0) + timedelta(days=1)).strftime("%Y-%m-%d")
        bar_bo = pd.DataFrame([{
            "symbol": "BEAR_BO",
            "date": d_next1,
            "open": upper + 0.5,
            "high": upper + 2.0,
            "low": upper + 0.2,
            "close": upper + 1.0,
            "volume": 600_000.0
        }])
        df_t1 = pd.concat([df, bar_bo], ignore_index=True)
        res_t1 = detect_base(df_t1, as_of=d_next1, previous_base=base_0.to_dict())

        assert res_t1.state == "breakout_confirmed"
        # Session 1 closed below MA50: consecutive_below_ma50 starts at 1
        assert res_t1.consecutive_below_ma50 == 1

        # Session 2 also closes below MA50: triggers Played Out!
        d_next2 = (pd.to_datetime(d_next1) + timedelta(days=1)).strftime("%Y-%m-%d")
        bar2 = pd.DataFrame([{
            "symbol": "BEAR_BO",
            "date": d_next2,
            "open": upper + 1.0,
            "high": upper + 1.5,
            "low": upper + 0.5,
            "close": upper + 0.8,
            "volume": 200_000.0
        }])
        df_t2 = pd.concat([df_t1, bar2], ignore_index=True)
        res_t2 = track_post_breakout_base(res_t1.to_dict(), df_t2, as_of=d_next2)

        assert res_t2.consecutive_below_ma50 == 2
        assert res_t2.state == "played_out"
        assert res_t2.lifecycle_phase == "played_out"
        assert res_t2.is_active is False
        assert "2 phiên liên tiếp đóng cửa dưới MA50" in (res_t2.end_reason or "")


class TestBaseCardSynchronizedRendering:
    """Verify synchronized stock card rendering in base_watchlist."""

    def test_render_individual_base_card_resilience(self):
        from app.components.base_watchlist import _render_individual_base_card
        sample_b = {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "sector": "Information Technology",
            "sub_industry": "Technology Hardware",
            "close_price": 220.5,
            "perf_1d": 1.25,
            "upper": 225.0,
            "lower": 210.0,
            "width_pct": 7.1,
            "now_vs_pivot_pct": -2.0,
            "rs_rating": 85,
            "from_52w_high_pct": 3.5,
            "lifecycle_phase": "forming",
            "state": "tight",
            "breakout_bar_count": 0,
            "checks": [{"name": "Biên độ", "threshold": "<= 15%", "value": "7.1%", "pass": True}]
        }

        # 1. repo=None, candidate_map=None
        _render_individual_base_card(sample_b, as_of="2026-09-14", repo=None, key_suffix="test1")

        # 2. With candidate_map and mock repo
        class MockRepo:
            def get_fundamentals(self, symbols):
                return pd.DataFrame()
            def get_base_history_by_symbol(self, sym, as_of=None):
                return []

        cand_map = {
            "AAPL": {
                "symbol": "AAPL",
                "company_name": "Apple Inc.",
                "is_oneil_leader": True,
                "fa_flags": {
                    "has_data": True,
                    "days_to_earnings": 10,
                    "next_earnings_date": "2026-09-24",
                    "flags": ["Cảnh báo: Tỷ lệ nợ cao"],
                    "period_end": "2026-06-30",
                    "metrics": {"profit_margin_str": "24.5%"}
                }
            }
        }
        _render_individual_base_card(sample_b, as_of="2026-09-14", repo=MockRepo(), key_suffix="test2", candidate_map=cand_map)

    def test_render_grouped_base_card_resilience(self):
        from app.components.base_watchlist import _render_grouped_base_card
        setups = [
            {
                "symbol": "MSFT",
                "company_name": "Microsoft Corp.",
                "sector": "Information Technology",
                "sub_industry": "Software",
                "close_price": 430.0,
                "perf_1d": -0.5,
                "upper": 435.0,
                "lower": 415.0,
                "width_pct": 4.8,
                "now_vs_pivot_pct": -1.1,
                "rs_rating": 78,
                "lifecycle_phase": "forming",
                "state": "forming"
            },
            {
                "symbol": "MSFT",
                "company_name": "Microsoft Corp.",
                "sector": "Information Technology",
                "sub_industry": "Software",
                "close_price": 430.0,
                "perf_1d": -0.5,
                "upper": 420.0,
                "lower": 400.0,
                "width_pct": 5.0,
                "now_vs_pivot_pct": 2.3,
                "rs_rating": 78,
                "lifecycle_phase": "played_out",
                "state": "played_out",
                "ended_at": "2026-08-30",
                "end_reason": "Thủng MA50"
            }
        ]
        _render_grouped_base_card("MSFT", setups, as_of="2026-09-14", repo=None, key_suffix="test_grp")

    def test_render_card_fa_column(self):
        from app.components.base_watchlist import _render_card_fa_column
        # Empty flags
        _render_card_fa_column("GOOGL", None, as_of="2026-09-14", repo=None)

        # Full FA flags
        full_fa = {
            "has_data": True,
            "days_to_earnings": 20,
            "next_earnings_date": "2026-10-04",
            "flags": ["Biên ròng ổn định"],
            "period_end": "2026-06-30",
            "metrics": {"profit_margin_str": "28.0%"}
        }
        _render_card_fa_column("GOOGL", full_fa, as_of="2026-09-14", repo=None)

    def test_render_base_watchlist_accepts_candidates_and_handles_empty(self):
        from app.components.base_watchlist import render_base_watchlist
        # Should render empty message gracefully without exception
        render_base_watchlist(
            base_records=[],
            as_of="2026-09-14",
            repo=None,
            snapshot_id=1,
            candidates=[]
        )


