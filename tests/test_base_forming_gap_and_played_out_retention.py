"""
Verification tests for:
1. [High] Breakout from Forming state during pipeline gap:
   - Evaluates sequential transitions from forming across unassessed sessions.
   - First session breaks out with confirmed volume, followed by 6 sessions -> advances to Climbing, session 7.
   - Catches intermediate post-breakout failure if price falls below lower bound during gap.
2. [Medium] Played-out base retention across subsequent sessions:
   - When a base ends and is not tracked in the next snapshot, repo.get_latest_base_snapshots(as_of=...)
     still returns the latest state up to that date, keeping it visible in the Played out filter.
"""
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
import pytest

from analytics.base_detector import BaseConfig, BaseResult, detect_base
from storage.database import init_db
from storage.repository import MarketRadarRepository
from tests.test_base_detector import _make_daily_bars, _make_oscillating_closes
from app.components.base_watchlist import get_base_lifecycle


class TestIssue1FormingBreakoutGapReplay:
    """Issue 1: Sequential evaluation of intermediate sessions when base was forming."""

    def test_advances_to_climbing_session_7_when_breakout_happened_6_days_prior(self):
        """
        Scenario:
        - T0: base was in forming state, is_active=True, upper=100.0, lower=90.0.
        - Pipeline stops for 7 sessions (T1 to T7).
        - T1: breaks out above upper (close=105.0) with volume ratio >= 1.4 (confirmed volume).
        - T2 to T7 (6 subsequent sessions): maintains breakout, closes 106..111 with normal volume.
        - Result on T7 must be: Climbing, session 7, breakout_date = T1.
        """
        closes = [95.0] * 60
        df = _make_daily_bars(closes, symbol="NVDA", start_date="2026-05-01")
        day0_date = df["date"].iloc[-1]
        day0_dt = pd.to_datetime(day0_date)

        # Baseline forming base at day 0
        prev_base = {
            "symbol": "NVDA",
            "as_of": day0_date,
            "rule_version": "v1.0",
            "data_status": "valid",
            "base_id": "BASE-NVDA-2026-05-01",
            "detected_at": "2026-05-01",
            "window_start": "2026-05-01",
            "window_end": day0_date,
            "state": "forming",
            "lifecycle_phase": "forming",
            "is_active": True,
            "upper": 100.0,
            "lower": 90.0,
            "close_price": 95.0,
            "width_pct": 11.1,
            "efficiency_ratio": 0.15,
            "center_shift": 0.05,
            "tr_contraction": 0.8,
            "vol_contraction": 0.7,
            "consecutive_weakening": 0,
            "breakout_date": None,
            "breakout_price": None,
            "breakout_bar_count": 0,
            "consecutive_below_ma50": 0,
            "formula_version": "v2.0"
        }

        # Add 7 sessions:
        # Session 1 (i=1): Breakout close=105.0, volume=300_000 (avg is ~100_000 -> 3.0x confirmed)
        # Sessions 2-7 (i=2..7): Closes 106, 107, 108, 109, 110, 111 with normal volume 100_000
        new_bars = []
        for i in range(1, 8):
            d_str = (day0_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            c = 104.0 + float(i)
            v = 300_000.0 if i == 1 else 100_000.0
            new_bars.append({
                "symbol": "NVDA",
                "date": d_str,
                "open": c - 0.5,
                "high": c + 1.0,
                "low": c - 1.0,
                "close": c,
                "volume": v
            })
        df_updated = pd.concat([df, pd.DataFrame(new_bars)], ignore_index=True)
        as_of_final = new_bars[-1]["date"]
        t1_date = new_bars[0]["date"]

        cfg = BaseConfig(min_bars=40, window_bars=20, breakout_vol_ratio=1.4)
        res = detect_base(df_updated, as_of=as_of_final, previous_base=prev_base, config=cfg)

        assert res.state == "climbing", f"Expected state climbing, got {res.state}"
        assert res.lifecycle_phase == "climbing", f"Expected lifecycle climbing, got {res.lifecycle_phase}"
        assert res.breakout_bar_count == 7, f"Expected session 7, got {res.breakout_bar_count}"
        assert res.breakout_date == t1_date, f"Expected breakout date {t1_date}, got {res.breakout_date}"
        assert res.breakout_price == 105.0, f"Expected breakout price 105.0, got {res.breakout_price}"
        assert res.is_active is True

    def test_catches_intermediate_failure_during_gap_after_forming_breakout(self):
        """
        Scenario:
        - T0: forming base.
        - T1: confirmed breakout.
        - T4: price collapses below lower bound (85.0 < 90.0).
        - T7: pipeline runs. Must catch Played Out with ended_at = T4.
        """
        closes = [95.0] * 60
        df = _make_daily_bars(closes, symbol="AMD", start_date="2026-05-01")
        day0_date = df["date"].iloc[-1]
        day0_dt = pd.to_datetime(day0_date)

        prev_base = {
            "symbol": "AMD",
            "as_of": day0_date,
            "rule_version": "v1.0",
            "data_status": "valid",
            "base_id": "BASE-AMD-01",
            "detected_at": "2026-05-01",
            "window_start": "2026-05-01",
            "window_end": day0_date,
            "state": "forming",
            "lifecycle_phase": "forming",
            "is_active": True,
            "upper": 100.0,
            "lower": 90.0,
            "close_price": 95.0,
            "width_pct": 11.1,
            "consecutive_weakening": 0,
            "breakout_date": None,
            "breakout_bar_count": 0,
            "formula_version": "v2.0"
        }

        new_bars = []
        for i in range(1, 8):
            d_str = (day0_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            if i == 1:
                c = 105.0
                v = 300_000.0
            elif i == 4:
                c = 85.0  # Breakdown below 90.0!
                v = 200_000.0
            else:
                c = 106.0
                v = 100_000.0
            new_bars.append({
                "symbol": "AMD",
                "date": d_str,
                "open": c,
                "high": c + 1.0,
                "low": c - 1.0,
                "close": c,
                "volume": v
            })
        df_updated = pd.concat([df, pd.DataFrame(new_bars)], ignore_index=True)
        as_of_final = new_bars[-1]["date"]
        t4_date = new_bars[3]["date"]

        cfg = BaseConfig(min_bars=40, window_bars=20, breakout_vol_ratio=1.4)
        res = detect_base(df_updated, as_of=as_of_final, previous_base=prev_base, config=cfg)

        assert res.state == "played_out", f"Expected played_out, got {res.state}"
        assert res.lifecycle_phase == "played_out"
        assert res.is_active is False
        assert res.ended_at == t4_date, f"Expected ended_at {t4_date}, got {res.ended_at}"

    def test_unconfirmed_breakout_then_confirmed_breakout_at_day_3(self):
        """
        Scenario:
        - T1: close > upper, but volume ratio < 1.4 (unconfirmed breakout).
        - T2: price pulls back inside base (close=98.0).
        - T3: confirmed breakout with volume ratio >= 1.4.
        - T4..T7: 4 subsequent sessions climbing (total session count = 5 -> fresh_breakout, session 5).
        """
        closes = [95.0] * 60
        df = _make_daily_bars(closes, symbol="META", start_date="2026-05-01")
        day0_date = df["date"].iloc[-1]
        day0_dt = pd.to_datetime(day0_date)

        prev_base = {
            "symbol": "META",
            "as_of": day0_date,
            "rule_version": "v1.0",
            "data_status": "valid",
            "base_id": "BASE-META-01",
            "detected_at": "2026-05-01",
            "window_start": "2026-05-01",
            "window_end": day0_date,
            "state": "forming",
            "lifecycle_phase": "forming",
            "is_active": True,
            "upper": 100.0,
            "lower": 90.0,
            "close_price": 95.0,
            "width_pct": 11.1,
            "consecutive_weakening": 0,
            "breakout_date": None,
            "breakout_bar_count": 0,
            "formula_version": "v2.0"
        }

        new_bars = []
        for i in range(1, 8):
            d_str = (day0_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            if i == 1:
                c = 103.0
                v = 80_000.0  # Unconfirmed vol (< 100_000 avg)
            elif i == 2:
                c = 98.0  # Back inside base
                v = 80_000.0
            elif i == 3:
                c = 106.0  # Confirmed breakout!
                v = 350_000.0  # 350k / 200k = 1.75x >= 1.4x!
            else:
                c = 107.0 + float(i)
                v = 100_000.0
            new_bars.append({
                "symbol": "META",
                "date": d_str,
                "open": c,
                "high": c + 1.0,
                "low": c - 1.0,
                "close": c,
                "volume": v
            })
        df_updated = pd.concat([df, pd.DataFrame(new_bars)], ignore_index=True)
        as_of_final = new_bars[-1]["date"]
        t3_date = new_bars[2]["date"]

        cfg = BaseConfig(min_bars=40, window_bars=20, breakout_vol_ratio=1.4)
        res = detect_base(df_updated, as_of=as_of_final, previous_base=prev_base, config=cfg)

        assert res.breakout_date == t3_date
        assert res.breakout_bar_count == 5  # Day 3 (session 1) + Days 4, 5, 6, 7 (4 sessions) = 5 sessions
        assert res.state == "fresh_breakout"
        assert res.lifecycle_phase == "fresh_breakout"
        assert res.is_active is True

    def test_parity_between_session_by_session_and_batch_replay_quality_metrics(self):
        """
        Verify parity between daily updates and gap replay updates:
        - 15/07: Forming base detected
        - 16/07: Still forming, volume begins shifting
        - 17/07: Still forming, vol_contraction shifts to ~1.2 (measured at 17/07)
        - 18/07: Breakout confirmed with volume spike
        - 19/07: Post-breakout session 2

        Compare:
        1. Session-by-session: updating 15/07 -> 16/07 -> 17/07 -> 18/07 -> 19/07
        2. Batch replay: updating directly from 15/07 to 19/07
        Both must have identical quality metrics measured at T-1 of breakout (17/07):
        - vol_contraction
        - tr_contraction
        - efficiency_ratio
        - center_shift
        - window_end == "2026-07-17"
        - breakout_date == "2026-07-18"
        - breakout_bar_count == 2
        """
        closes = _make_oscillating_closes(n_bars=40, center=100.0, amplitude=1.5)
        df = _make_daily_bars(closes, symbol="AMZN", start_date="2026-06-05", volumes=[200_000.0] * 40)
        d0 = df["date"].iloc[-1]

        cfg = BaseConfig(min_bars=40, window_bars=20, breakout_vol_ratio=1.4)
        res_d0 = detect_base(df, as_of=d0, config=cfg)
        assert res_d0.state in ("forming", "tight")
        upper = res_d0.upper

        d0_dt = pd.to_datetime(d0)
        d1 = (d0_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        d2 = (d0_dt + timedelta(days=2)).strftime("%Y-%m-%d")
        d3 = (d0_dt + timedelta(days=3)).strftime("%Y-%m-%d")
        d4 = (d0_dt + timedelta(days=4)).strftime("%Y-%m-%d")

        b1 = pd.DataFrame([{"symbol": "AMZN", "date": d1, "open": 100.0, "high": 101.0, "low": 99.5, "close": 100.5, "volume": 220_000.0}])
        b2 = pd.DataFrame([{"symbol": "AMZN", "date": d2, "open": 100.5, "high": 101.5, "low": 100.0, "close": 101.0, "volume": 240_000.0}])
        b3 = pd.DataFrame([{"symbol": "AMZN", "date": d3, "open": upper + 0.5, "high": upper + 3.0, "low": upper + 0.2, "close": upper + 2.0, "volume": 600_000.0}])
        b4 = pd.DataFrame([{"symbol": "AMZN", "date": d4, "open": upper + 2.0, "high": upper + 3.0, "low": upper + 1.5, "close": upper + 2.5, "volume": 200_000.0}])

        df_full = pd.concat([df, b1, b2, b3, b4], ignore_index=True)
        df_d1 = pd.concat([df, b1], ignore_index=True)
        df_d2 = pd.concat([df, b1, b2], ignore_index=True)
        df_d3 = pd.concat([df, b1, b2, b3], ignore_index=True)

        # 1. Chạy từng phiên (Session-by-session)
        res_d1 = detect_base(df_d1, as_of=d1, previous_base=res_d0.to_dict(), config=cfg)
        res_d2 = detect_base(df_d2, as_of=d2, previous_base=res_d1.to_dict(), config=cfg)
        res_d3 = detect_base(df_d3, as_of=d3, previous_base=res_d2.to_dict(), config=cfg)
        res_d4_step = detect_base(df_full, as_of=d4, previous_base=res_d3.to_dict(), config=cfg)

        # 2. Chạy bù sau gián đoạn (Batch replay directly from d0 to d4)
        res_d4_gap = detect_base(df_full, as_of=d4, previous_base=res_d0.to_dict(), config=cfg)

        # Verify exact parity
        assert res_d4_gap.state == res_d4_step.state == "fresh_breakout"
        assert res_d4_gap.breakout_date == res_d4_step.breakout_date == d3
        assert res_d4_gap.breakout_bar_count == res_d4_step.breakout_bar_count == 2
        assert res_d4_gap.window_end == res_d4_step.window_end == d2
        assert res_d4_gap.vol_contraction == pytest.approx(res_d4_step.vol_contraction, rel=1e-3)
        assert res_d4_gap.tr_contraction == pytest.approx(res_d4_step.tr_contraction, rel=1e-3)
        assert res_d4_gap.efficiency_ratio == pytest.approx(res_d4_step.efficiency_ratio, rel=1e-3)
        assert res_d4_gap.center_shift == pytest.approx(res_d4_step.center_shift, rel=1e-3)
        assert res_d4_gap.signed_volume_balance == pytest.approx(res_d4_step.signed_volume_balance, rel=1e-3)


class TestIssue2PlayedOutBaseRetention:
    """Issue 2: Retain ended bases across subsequent sessions via get_latest_base_snapshots."""

    def test_played_out_base_retained_in_next_sessions(self, tmp_path):
        db_file = tmp_path / "test_played_out_retention.db"
        init_db(db_file)
        repo = MarketRadarRepository(db_file)

        # Session 1: AAPL is climbing, MSFT is forming
        s1_id = repo.save_snapshot(
            as_of="2026-09-01", rule_version="v1.0", total_universe=500, valid_universe=500,
            coverage_pct=1.0, missing_symbols=[], market_metrics={}, sector_metrics=[],
            candidates=[], industry_metrics=[], coverage_252d=1.0, status="complete"
        )
        rec1_aapl = {
            "symbol": "AAPL", "as_of": "2026-09-01", "rule_version": "v1.0", "data_status": "valid",
            "base_id": "BASE-AAPL-01", "detected_at": "2026-08-10", "window_start": "2026-08-10",
            "window_end": "2026-08-30", "state": "climbing", "lifecycle_phase": "climbing",
            "is_active": True, "upper": 150.0, "lower": 140.0, "close_price": 155.0,
            "breakout_date": "2026-08-25", "breakout_price": 152.0, "breakout_bar_count": 6
        }
        rec1_msft = {
            "symbol": "MSFT", "as_of": "2026-09-01", "rule_version": "v1.0", "data_status": "valid",
            "base_id": "BASE-MSFT-01", "detected_at": "2026-08-20", "window_start": "2026-08-20",
            "window_end": "2026-09-01", "state": "forming", "lifecycle_phase": "forming",
            "is_active": True, "upper": 300.0, "lower": 285.0, "close_price": 292.0
        }
        repo.save_base_snapshots([rec1_aapl, rec1_msft], snapshot_id=s1_id)

        # Session 2: AAPL breaks down below lower bound -> played_out! MSFT still forming
        s2_id = repo.save_snapshot(
            as_of="2026-09-02", rule_version="v1.0", total_universe=500, valid_universe=500,
            coverage_pct=1.0, missing_symbols=[], market_metrics={}, sector_metrics=[],
            candidates=[], industry_metrics=[], coverage_252d=1.0, status="complete"
        )
        rec2_aapl = {
            "symbol": "AAPL", "as_of": "2026-09-02", "rule_version": "v1.0", "data_status": "valid",
            "base_id": "BASE-AAPL-01", "detected_at": "2026-08-10", "window_start": "2026-08-10",
            "window_end": "2026-08-30", "state": "played_out", "lifecycle_phase": "played_out",
            "is_active": False, "upper": 150.0, "lower": 140.0, "close_price": 138.0,
            "breakout_date": "2026-08-25", "breakout_price": 152.0, "breakout_bar_count": 7,
            "ended_at": "2026-09-02", "end_reason": "Thủng đáy nền ($140.00) tại giá $138.00."
        }
        rec2_msft = {
            "symbol": "MSFT", "as_of": "2026-09-02", "rule_version": "v1.0", "data_status": "valid",
            "base_id": "BASE-MSFT-01", "detected_at": "2026-08-20", "window_start": "2026-08-20",
            "window_end": "2026-09-02", "state": "forming", "lifecycle_phase": "forming",
            "is_active": True, "upper": 300.0, "lower": 285.0, "close_price": 294.0
        }
        repo.save_base_snapshots([rec2_aapl, rec2_msft], snapshot_id=s2_id)

        # Session 3: Pipeline does not track ended base AAPL. Snapshot 3 ONLY contains MSFT!
        s3_id = repo.save_snapshot(
            as_of="2026-09-03", rule_version="v1.0", total_universe=500, valid_universe=500,
            coverage_pct=1.0, missing_symbols=[], market_metrics={}, sector_metrics=[],
            candidates=[], industry_metrics=[], coverage_252d=1.0, status="complete"
        )
        rec3_msft = {
            "symbol": "MSFT", "as_of": "2026-09-03", "rule_version": "v1.0", "data_status": "valid",
            "base_id": "BASE-MSFT-01", "detected_at": "2026-08-20", "window_start": "2026-08-20",
            "window_end": "2026-09-03", "state": "forming", "lifecycle_phase": "forming",
            "is_active": True, "upper": 300.0, "lower": 285.0, "close_price": 295.0
        }
        repo.save_base_snapshots([rec3_msft], snapshot_id=s3_id)

        # Old way: repo.get_base_snapshots(snapshot_id=s3_id) -> AAPL is missing!
        old_view_records = repo.get_base_snapshots(snapshot_id=s3_id)
        assert len(old_view_records) == 1
        assert old_view_records[0]["symbol"] == "MSFT"

        # New way: repo.get_latest_base_snapshots(as_of="2026-09-03")
        # Retrieves latest status of each base up to 2026-09-03, including ended ones!
        latest_records = repo.get_latest_base_snapshots(as_of="2026-09-03")
        sym_map = {r["symbol"]: r for r in latest_records}

        assert "AAPL" in sym_map, "AAPL played_out base was missing on subsequent session!"
        assert "MSFT" in sym_map

        assert sym_map["AAPL"]["state"] == "played_out"
        assert sym_map["AAPL"]["lifecycle_phase"] == "played_out"
        assert sym_map["AAPL"]["is_active"] is False
        assert sym_map["AAPL"]["ended_at"] == "2026-09-02"

        assert sym_map["MSFT"]["state"] == "forming"
        assert sym_map["MSFT"]["is_active"] is True

        # Verify UI filter categorization:
        played_out_setups = [b for b in latest_records if get_base_lifecycle(b) == "played_out"]
        forming_setups = [b for b in latest_records if get_base_lifecycle(b) == "forming"]

        assert len(played_out_setups) == 1
        assert played_out_setups[0]["symbol"] == "AAPL"
        assert len(forming_setups) == 1
        assert forming_setups[0]["symbol"] == "MSFT"

    def test_no_future_lookahead_in_get_latest_base_snapshots(self, tmp_path):
        """Viewing Session 1 does NOT show future played_out state that happened in Session 2."""
        db_file = tmp_path / "test_no_lookahead.db"
        init_db(db_file)
        repo = MarketRadarRepository(db_file)

        # Day 1: AAPL is climbing
        rec1 = {
            "symbol": "AAPL", "as_of": "2026-09-01", "rule_version": "v1.0", "data_status": "valid",
            "base_id": "BASE-AAPL-01", "detected_at": "2026-08-10", "window_start": "2026-08-10",
            "window_end": "2026-08-30", "state": "climbing", "lifecycle_phase": "climbing",
            "is_active": True, "upper": 150.0, "lower": 140.0, "close_price": 155.0
        }
        # Day 2: AAPL is played_out
        rec2 = {
            "symbol": "AAPL", "as_of": "2026-09-02", "rule_version": "v1.0", "data_status": "valid",
            "base_id": "BASE-AAPL-01", "detected_at": "2026-08-10", "window_start": "2026-08-10",
            "window_end": "2026-08-30", "state": "played_out", "lifecycle_phase": "played_out",
            "is_active": False, "upper": 150.0, "lower": 140.0, "close_price": 138.0,
            "ended_at": "2026-09-02"
        }
        repo.save_base_snapshots([rec1, rec2])

        # Query as of Day 1: must be climbing, not played_out!
        records_day1 = repo.get_latest_base_snapshots(as_of="2026-09-01")
        assert len(records_day1) == 1
        assert records_day1[0]["state"] == "climbing"
        assert records_day1[0]["is_active"] is True
