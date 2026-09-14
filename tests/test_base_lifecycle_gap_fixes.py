"""
Regression and verification test suite for the 5 base lifecycle and data issues:
1. Ended bases (played_out) not resurrected by get_active_post_breakout_bases.
2. Sequential session counting for multiple unassessed bars (advances to climbing, catches intermediate failure).
3. Post-breakout tracker rejects NaN/invalid OHLCV data.
4. Pre-breakout quality metrics frozen at T-1 without corruption from the breakout bar.
5. Missing data immediately after breakout retains base_id, lifecycle, and active state.
"""
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
import pytest

from analytics.base_detector import BaseConfig, BaseResult, detect_base, track_post_breakout_base
from storage.database import init_db
from storage.repository import MarketRadarRepository
from tests.test_base_detector import _make_daily_bars, _make_oscillating_closes


class TestIssue1EndedBaseNotResurrected:
    """Issue 1: get_active_post_breakout_bases must select latest snapshot per base_id before filtering state."""

    def test_ended_base_not_returned_on_subsequent_date(self, tmp_path):
        db_file = tmp_path / "test_lifecycle_resurrect.db"
        init_db(db_file)
        repo = MarketRadarRepository(db_file)

        # Base 1: ended on 2026-09-02 (played_out) after being climbing on 2026-09-01
        rec1_climbing = {
            "symbol": "AAPL",
            "as_of": "2026-09-01",
            "rule_version": "v1.0",
            "data_status": "valid",
            "base_id": "BASE-AAPL-01",
            "detected_at": "2026-08-10",
            "window_start": "2026-08-10",
            "window_end": "2026-08-30",
            "state": "climbing",
            "lifecycle_phase": "climbing",
            "is_active": True,
            "upper": 150.0,
            "lower": 140.0,
            "close_price": 158.0,
            "breakout_date": "2026-08-31",
            "breakout_price": 152.0,
            "breakout_bar_count": 6,
            "formula_version": "v2.0"
        }
        repo.save_base_snapshots([rec1_climbing])

        rec1_played_out = {
            "symbol": "AAPL",
            "as_of": "2026-09-02",
            "rule_version": "v1.0",
            "data_status": "valid",
            "base_id": "BASE-AAPL-01",
            "detected_at": "2026-08-10",
            "window_start": "2026-08-10",
            "window_end": "2026-08-30",
            "state": "played_out",
            "lifecycle_phase": "played_out",
            "is_active": False,
            "upper": 150.0,
            "lower": 140.0,
            "close_price": 138.0,
            "breakout_date": "2026-08-31",
            "breakout_price": 152.0,
            "breakout_bar_count": 7,
            "ended_at": "2026-09-02",
            "end_reason": "Thủng đáy nền ($140.00) tại giá $138.00.",
            "formula_version": "v2.0"
        }
        repo.save_base_snapshots([rec1_played_out])

        # Base 2: MSFT is still climbing on 2026-09-02
        rec2_climbing = {
            "symbol": "MSFT",
            "as_of": "2026-09-02",
            "rule_version": "v1.0",
            "data_status": "valid",
            "base_id": "BASE-MSFT-01",
            "detected_at": "2026-08-10",
            "window_start": "2026-08-10",
            "window_end": "2026-08-30",
            "state": "climbing",
            "lifecycle_phase": "climbing",
            "is_active": True,
            "upper": 300.0,
            "lower": 280.0,
            "close_price": 315.0,
            "breakout_date": "2026-08-31",
            "breakout_price": 305.0,
            "breakout_bar_count": 7,
            "formula_version": "v2.0"
        }
        repo.save_base_snapshots([rec2_climbing])

        # Query on 2026-09-03: AAPL ended on 2026-09-02, so it MUST NOT be returned!
        active_bases = repo.get_active_post_breakout_bases(before_date="2026-09-03")
        active_symbols = [b["symbol"] for b in active_bases]

        assert "AAPL" not in active_symbols, "Ended base AAPL was resurrected by query!"
        assert "MSFT" in active_symbols, "Active base MSFT should be returned"
        assert len(active_bases) == 1

    def test_ended_base_not_resurrected_even_with_out_of_order_insertion_ids(self, tmp_path):
        """Out-of-order insertion / backfill where higher id has older as_of must not resurrect ended base."""
        db_file = tmp_path / "test_lifecycle_ooo.db"
        init_db(db_file)
        repo = MarketRadarRepository(db_file)

        # First insert the newer snapshot: ended on 2026-09-02 (played_out) -> gets lower id (1)
        rec_ended = {
            "symbol": "NVDA",
            "as_of": "2026-09-02",
            "rule_version": "v1.0",
            "data_status": "valid",
            "base_id": "BASE-NVDA-01",
            "detected_at": "2026-08-10",
            "window_start": "2026-08-10",
            "window_end": "2026-08-30",
            "state": "played_out",
            "lifecycle_phase": "played_out",
            "is_active": False,
            "upper": 120.0,
            "lower": 110.0,
            "close_price": 105.0,
            "breakout_date": "2026-08-31",
            "breakout_price": 122.0,
            "breakout_bar_count": 3,
            "ended_at": "2026-09-02",
            "end_reason": "Thủng đáy nền"
        }
        repo.save_base_snapshots([rec_ended])

        # Next backfill an older snapshot: climbing on 2026-08-31 -> gets higher id (2)
        rec_older_climbing = {
            "symbol": "NVDA",
            "as_of": "2026-08-31",
            "rule_version": "v1.0",
            "data_status": "valid",
            "base_id": "BASE-NVDA-01",
            "detected_at": "2026-08-10",
            "window_start": "2026-08-10",
            "window_end": "2026-08-30",
            "state": "climbing",
            "lifecycle_phase": "climbing",
            "is_active": True,
            "upper": 120.0,
            "lower": 110.0,
            "close_price": 125.0,
            "breakout_date": "2026-08-31",
            "breakout_price": 122.0,
            "breakout_bar_count": 1
        }
        repo.save_base_snapshots([rec_older_climbing])

        # Query on 2026-09-03: NVDA ended on 2026-09-02. Chronologically latest record is played_out!
        active_bases = repo.get_active_post_breakout_bases(before_date="2026-09-03")
        active_symbols = [b["symbol"] for b in active_bases]
        assert "NVDA" not in active_symbols, "MAX(id) picked backfilled older record and resurrected NVDA!"


class TestIssue2SequentialBarCounting:
    """Issue 2: Sequential evaluation of unassessed sessions according to trading calendar."""

    def test_advances_to_climbing_when_7_candles_added(self):
        """When 7 candles pass after breakout (total 8 bars), result is session 8 / climbing."""
        closes = [100.0] * 60
        df = _make_daily_bars(closes, symbol="GOOGL", start_date="2026-06-01")
        breakout_date = df["date"].iloc[-1]

        prev_base = {
            "symbol": "GOOGL",
            "as_of": breakout_date,
            "base_id": "BASE-GOOGL",
            "detected_at": "2026-06-01",
            "upper": 105.0,
            "lower": 95.0,
            "state": "breakout_confirmed",
            "lifecycle_phase": "fresh_breakout",
            "breakout_date": breakout_date,
            "breakout_price": 107.0,
            "breakout_bar_count": 1,
            "consecutive_below_ma50": 0,
            "is_active": False
        }

        # Add 7 trading sessions after breakout date
        start_dt = pd.to_datetime(breakout_date)
        new_bars = []
        for i in range(1, 8):
            d_str = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            new_bars.append({
                "symbol": "GOOGL",
                "date": d_str,
                "open": 107.0,
                "high": 109.0,
                "low": 106.0,
                "close": 108.0,
                "volume": 250_000.0
            })
        df_updated = pd.concat([df, pd.DataFrame(new_bars)], ignore_index=True)
        as_of_final = new_bars[-1]["date"]

        # Run tracker once on the final date
        res = track_post_breakout_base(prev_base, df_updated, as_of=as_of_final)

        assert res.breakout_bar_count == 8, f"Expected session 8, got {res.breakout_bar_count}"
        assert res.state == "climbing", f"Expected climbing, got {res.state}"
        assert res.lifecycle_phase == "climbing"
        assert res.is_active is True

    def test_catches_intermediate_failure_even_if_pipeline_skipped_sessions(self):
        """If price collapsed below lower bound on session 4, running on session 8 detects Played Out at session 4."""
        closes = [100.0] * 60
        df = _make_daily_bars(closes, symbol="TSLA", start_date="2026-06-01")
        breakout_date = df["date"].iloc[-1]

        prev_base = {
            "symbol": "TSLA",
            "as_of": breakout_date,
            "base_id": "BASE-TSLA",
            "detected_at": "2026-06-01",
            "upper": 105.0,
            "lower": 95.0,
            "state": "breakout_confirmed",
            "lifecycle_phase": "fresh_breakout",
            "breakout_date": breakout_date,
            "breakout_price": 107.0,
            "breakout_bar_count": 1,
            "consecutive_below_ma50": 0,
            "is_active": False
        }

        # Add 7 sessions: on session 4 (i=4), price drops to 90 (below lower 95.0), then recovers to 110 on session 7
        start_dt = pd.to_datetime(breakout_date)
        new_bars = []
        for i in range(1, 8):
            d_str = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            c = 90.0 if i == 4 else 110.0
            new_bars.append({
                "symbol": "TSLA",
                "date": d_str,
                "open": c,
                "high": c + 1.0,
                "low": c - 1.0,
                "close": c,
                "volume": 250_000.0
            })
        df_updated = pd.concat([df, pd.DataFrame(new_bars)], ignore_index=True)
        as_of_final = new_bars[-1]["date"]
        failed_session_date = new_bars[3]["date"]

        res = track_post_breakout_base(prev_base, df_updated, as_of=as_of_final)

        assert res.state == "played_out", "Intermediate failure was ignored!"
        assert res.lifecycle_phase == "played_out"
        assert res.is_active is False
        assert res.ended_at == failed_session_date
        assert "Thủng đáy nền" in (res.end_reason or "")

    def test_outage_recovery_evaluates_all_unassessed_bars_and_detects_intermediate_failure(self):
        """When tracker previously recorded insufficient_data, subsequent run evaluates all skipped bars."""
        closes = [100.0] * 60
        df = _make_daily_bars(closes, symbol="AMD", start_date="2026-06-01")
        breakout_date = df["date"].iloc[-1]

        # Breakout confirmed on Day 1
        base_bo = {
            "symbol": "AMD",
            "as_of": breakout_date,
            "base_id": "BASE-AMD",
            "detected_at": "2026-06-01",
            "upper": 105.0,
            "lower": 95.0,
            "state": "breakout_confirmed",
            "lifecycle_phase": "fresh_breakout",
            "breakout_date": breakout_date,
            "breakout_price": 107.0,
            "breakout_bar_count": 1,
            "data_status": "valid",
            "is_active": False
        }

        # Day 2: Data outage happens -> tracker returns insufficient_data record
        day2_str = (pd.to_datetime(breakout_date) + timedelta(days=1)).strftime("%Y-%m-%d")
        res_glitch = track_post_breakout_base(base_bo, pd.DataFrame(), as_of=day2_str)
        assert res_glitch.data_status == "insufficient_data"
        assert res_glitch.breakout_bar_count == 1

        # Day 3: Full data restored. On Day 2 (intermediate), price broke down to 88.0!
        day3_str = (pd.to_datetime(breakout_date) + timedelta(days=2)).strftime("%Y-%m-%d")
        new_bars = [
            {"symbol": "AMD", "date": day2_str, "open": 90.0, "high": 91.0, "low": 87.0, "close": 88.0, "volume": 200_000.0},
            {"symbol": "AMD", "date": day3_str, "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 200_000.0}
        ]
        df_restored = pd.concat([df, pd.DataFrame(new_bars)], ignore_index=True)

        res_recovered = track_post_breakout_base(res_glitch.to_dict(), df_restored, as_of=day3_str)
        assert res_recovered.state == "played_out", "Failure on unassessed Day 2 was not detected!"
        assert res_recovered.ended_at == day2_str
        assert res_recovered.is_active is False

    def test_forming_base_intermediate_breakdown_detected(self):
        """A forming base that broke down on an intermediate unassessed session must not be revived."""
        closes = _make_oscillating_closes(n_bars=40, center=100.0, amplitude=1.5)
        df_base = _make_daily_bars(closes, symbol="INTC", start_date="2026-06-01")
        as_of_t0 = df_base["date"].iloc[-1]

        base_t0 = detect_base(df_base, as_of=as_of_t0)
        assert base_t0.is_active is True
        lower = base_t0.lower

        # Skip 3 days: on day 2 price crashes to lower - 10.0, then on day 3 recovers to 100.0
        start_dt = pd.to_datetime(as_of_t0)
        d1 = (start_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        d2 = (start_dt + timedelta(days=2)).strftime("%Y-%m-%d")
        d3 = (start_dt + timedelta(days=3)).strftime("%Y-%m-%d")
        new_bars = [
            {"symbol": "INTC", "date": d1, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 200_000.0},
            {"symbol": "INTC", "date": d2, "open": lower - 8.0, "high": lower - 5.0, "low": lower - 12.0, "close": lower - 10.0, "volume": 500_000.0},
            {"symbol": "INTC", "date": d3, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 200_000.0}
        ]
        df_updated = pd.concat([df_base, pd.DataFrame(new_bars)], ignore_index=True)

        res = detect_base(df_updated, as_of=d3, previous_base=base_t0.to_dict())
        assert res.state == "broken_down", "Intermediate breakdown during forming phase was ignored!"
        assert res.lifecycle_phase == "failed_before_breakout"
        assert res.is_active is False
        assert res.ended_at == d2


class TestIssue3TrackerRejectsNaNPrices:
    """Issue 3: Tracker rejects NaN/invalid prices and returns invalid_data instead of valid Fresh."""

    def test_tracker_rejects_nan_close(self):
        closes = [100.0] * 60
        df = _make_daily_bars(closes, symbol="NVDA", start_date="2026-06-01")
        as_of = df["date"].iloc[-1]

        prev_base = {
            "symbol": "NVDA",
            "as_of": as_of,
            "base_id": "BASE-NVDA",
            "detected_at": "2026-06-01",
            "upper": 105.0,
            "lower": 95.0,
            "state": "breakout_confirmed",
            "lifecycle_phase": "fresh_breakout",
            "breakout_date": as_of,
            "breakout_price": 106.0,
            "breakout_bar_count": 1,
            "is_active": False
        }

        # Next bar has Close = NaN
        next_d = (pd.to_datetime(as_of) + timedelta(days=1)).strftime("%Y-%m-%d")
        next_bar = pd.DataFrame([{
            "symbol": "NVDA",
            "date": next_d,
            "open": 106.0,
            "high": 107.0,
            "low": 105.0,
            "close": np.nan,
            "volume": 200_000.0
        }])
        df_nan = pd.concat([df, next_bar], ignore_index=True)

        res = track_post_breakout_base(prev_base, df_nan, as_of=next_d)

        assert res.data_status == "invalid_data", f"Expected invalid_data but got {res.data_status}"
        assert res.data_status != "valid"
        assert res.base_id == "BASE-NVDA"
        # State should strictly not transition to Fresh
        assert res.state != "fresh_breakout"
        assert res.data_status == "invalid_data"

    def test_detect_base_and_tracker_handle_string_ohlcv_columns_without_crash(self):
        """String / object representations in OHLCV columns must be coerced without TypeError."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=1.5)
        df = _make_daily_bars(closes, symbol="QCOM", start_date="2026-06-01")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(str)

        as_of = df["date"].iloc[-1]
        res_detect = detect_base(df, as_of=as_of)
        assert res_detect.data_status == "valid"

        prev_base = {
            "symbol": "QCOM",
            "as_of": as_of,
            "base_id": "BASE-QCOM",
            "detected_at": "2026-06-01",
            "upper": 105.0,
            "lower": 95.0,
            "state": "breakout_confirmed",
            "lifecycle_phase": "fresh_breakout",
            "breakout_date": as_of,
            "breakout_price": 106.0,
            "breakout_bar_count": 1,
            "is_active": False
        }
        res_track = track_post_breakout_base(prev_base, df, as_of=as_of)
        assert res_track.data_status == "valid"

        # Non-numeric string should safely return invalid_data rather than raising TypeError
        df_invalid = df.copy()
        df_invalid.loc[df_invalid.index[-1], "close"] = "corrupted_text"
        res_invalid = detect_base(df_invalid, as_of=as_of)
        assert res_invalid.data_status == "invalid_data"

        res_track_invalid = track_post_breakout_base(prev_base, df_invalid, as_of=as_of)
        assert res_track_invalid.data_status == "invalid_data"


class TestIssue4PreBreakoutQualityDecoupledFromBreakoutBar:
    """Issue 4: Quality metrics at breakout confirmation are frozen at T-1, not inflated by the breakout candle."""

    def test_vol_contraction_frozen_at_t_minus_1(self):
        # 40 bars oscillating around 100 with perfectly balanced volume (200,000)
        # So vol_contraction at T-1 is exactly 1.0
        closes = _make_oscillating_closes(n_bars=40, center=100.0, amplitude=1.5)
        df_forming = _make_daily_bars(closes, symbol="META", start_date="2026-06-01", volumes=[200_000.0] * 40)
        as_of_t_minus_1 = df_forming["date"].iloc[-1]

        base_t_minus_1 = detect_base(df_forming, as_of=as_of_t_minus_1)
        assert base_t_minus_1.is_active is True
        assert base_t_minus_1.vol_contraction == pytest.approx(1.0, abs=0.05)
        upper = base_t_minus_1.upper

        # Bar 41: Breakout confirmed with 5x volume spike (1,000,000)
        as_of_t = (pd.to_datetime(as_of_t_minus_1) + timedelta(days=1)).strftime("%Y-%m-%d")
        bo_bar = pd.DataFrame([{
            "symbol": "META",
            "date": as_of_t,
            "open": upper + 0.5,
            "high": upper + 3.0,
            "low": upper + 0.2,
            "close": upper + 2.0,
            "volume": 1_000_000.0  # 5x volume spike
        }])
        df_bo = pd.concat([df_forming, bo_bar], ignore_index=True)

        res_bo = detect_base(df_bo, as_of=as_of_t, previous_base=base_t_minus_1.to_dict())

        assert res_bo.state == "breakout_confirmed"
        # Current price data reflects breakout bar
        assert res_bo.close_price == upper + 2.0
        assert res_bo.breakout_price == upper + 2.0
        # But quality metrics must be frozen from T-1 (approx 1.0, NOT 1.2+ inflated by the 1M volume!)
        assert res_bo.vol_contraction == pytest.approx(1.0, abs=0.05)
        assert res_bo.vol_contraction < 1.15, f"vol_contraction was inflated by breakout bar to {res_bo.vol_contraction}"

    def test_fallback_checks_consistent_with_decoupled_quality_metrics(self):
        """When previous_base does not supply checks, fallback must rebuild checks matching decoupled T-1 metrics."""
        closes = _make_oscillating_closes(n_bars=40, center=100.0, amplitude=1.5)
        df_forming = _make_daily_bars(closes, symbol="NFLX", start_date="2026-06-01", volumes=[200_000.0] * 40)
        as_of_t_minus_1 = df_forming["date"].iloc[-1]

        base_t_minus_1 = detect_base(df_forming, as_of=as_of_t_minus_1)
        upper = base_t_minus_1.upper

        # Bar 41: Breakout confirmed with 5x volume spike (1,000,000)
        as_of_t = (pd.to_datetime(as_of_t_minus_1) + timedelta(days=1)).strftime("%Y-%m-%d")
        bo_bar = pd.DataFrame([{
            "symbol": "NFLX",
            "date": as_of_t,
            "open": upper + 0.5,
            "high": upper + 3.0,
            "low": upper + 0.2,
            "close": upper + 2.0,
            "volume": 1_000_000.0
        }])
        df_bo = pd.concat([df_forming, bo_bar], ignore_index=True)

        prev_dict = base_t_minus_1.to_dict()
        prev_dict["checks"] = None
        prev_dict["vol_contraction"] = None

        res_bo = detect_base(df_bo, as_of=as_of_t, previous_base=prev_dict)
        assert res_bo.state == "breakout_confirmed"
        assert res_bo.vol_contraction == pytest.approx(1.0, abs=0.05)

        vol_check = next((c for c in res_bo.checks if "Volume" in c.get("name", "")), None)
        assert vol_check is not None, "Volume check missing from reconstructed checks!"
        vol_val = float(vol_check["value"])
        assert vol_val == pytest.approx(1.0, abs=0.05)
        assert vol_val < 1.15


class TestIssue5PostBreakoutMissingDataRetainsIdentity:
    """Issue 5: Missing data immediately after breakout retains base_id, lifecycle, and labels insufficient_data."""

    def test_missing_data_immediately_after_breakout_preserves_base(self):
        # A base that just confirmed breakout on session T
        breakout_record = {
            "symbol": "AMZN",
            "as_of": "2026-09-01",
            "rule_version": "v1.0",
            "data_status": "valid",
            "base_id": "BASE-AMZN-20260901",
            "detected_at": "2026-08-10",
            "window_start": "2026-08-10",
            "window_end": "2026-08-31",
            "state": "breakout_confirmed",
            "lifecycle_phase": "fresh_breakout",
            "is_active": False,  # Base forming phase finished, is_active was False
            "upper": 180.0,
            "lower": 170.0,
            "close_price": 182.0,
            "breakout_date": "2026-09-01",
            "breakout_price": 182.0,
            "breakout_bar_count": 1,
            "consecutive_below_ma50": 0,
            "formula_version": "v2.0"
        }

        # On session T+1 (2026-09-02), bars DataFrame is empty (missing data)
        empty_bars = pd.DataFrame()
        res = track_post_breakout_base(
            previous_base=breakout_record,
            bars=empty_bars,
            as_of="2026-09-02"
        )

        assert res.data_status == "insufficient_data"
        assert res.base_id == "BASE-AMZN-20260901", "base_id was wiped to None on missing data!"
        assert res.state == "breakout_confirmed", f"state was reset to {res.state} instead of preserved!"
        assert res.lifecycle_phase == "fresh_breakout"
        assert res.is_active is True, "Base should remain active during data glitch"
        assert res.upper == 180.0
        assert res.lower == 170.0
