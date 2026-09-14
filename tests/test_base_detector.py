"""
Comprehensive Test Suite for Base Building Detector ("Đang Xây Nền").
Covers:
1. Geometric base structure & rejection of monotonic trends / V-shapes.
2. Contraction conditions: Tight base vs Forming base.
3. Frozen boundaries & causal breakout testing without lookahead.
4. Future data invariance: Adding future bars does not change past results.
5. Edge cases: Zero volume, flat price, insufficient bars, stale data, invalid OHLC.
6. Accumulation evidence: Signed volume balance & trend context.
7. Lifecycle state transitions & 2-session weakening -> lost_structure.
8. Prohibition of new base until fresh 20-bar window after closed base.
9. Signal events deduplication & event_key determinism.
10. Repository and SQLite persistence of base_snapshots.
11. UI rendering smoke tests.
"""
from datetime import date, datetime, timedelta
import json
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import pytest

from analytics.base_detector import BaseConfig, BaseResult, detect_base
from analytics.signal_events import generate_base_signal_events, generate_signal_events
from storage.database import init_db
from storage.repository import MarketRadarRepository


def _make_daily_bars(
    closes: List[float],
    volumes: Optional[List[float]] = None,
    start_date: str = "2026-06-01",
    symbol: str = "TEST",
    high_spread: float = 0.5,
    low_spread: float = 0.5
) -> pd.DataFrame:
    """Helper to generate a clean, valid DataFrame of OHLCV bars."""
    start_dt = pd.to_datetime(start_date)
    dates = [start_dt + timedelta(days=i) for i in range(len(closes))]
    vols = volumes if volumes is not None else [200_000.0] * len(closes)

    records = []
    for d, c, v in zip(dates, closes, vols):
        o = c - 0.1
        h = max(o, c) + high_spread
        l = min(o, c) - low_spread
        records.append({
            "symbol": symbol,
            "date": d.strftime("%Y-%m-%d"),
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
            "volume": float(v)
        })
    return pd.DataFrame(records)


def _make_oscillating_closes(
    n_bars: int = 45,
    center: float = 100.0,
    amplitude: float = 2.0,
    end_date_str: str = "2026-09-10"
) -> List[float]:
    """Generate oscillating closes (sine wave) for a tight sideways base."""
    t = np.linspace(0, 6 * np.pi, n_bars)
    closes = center + amplitude * np.sin(t)
    return [round(float(c), 2) for c in closes]


class TestBaseDetectorFormulasAndGeometry:
    """Test recognition of tight sideways bases and rejection of trends and V-shapes."""

    def test_detect_sideways_tight_base_fixture(self):
        """Oscillating sideways price within 100-104 with contracting volume passes tight base."""
        # 45 bars total: prior 25 bars + 20-bar base
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        # Volume: first half of base has 300k, second half has 150k (ratio = 0.5 <= 0.8)
        # True Range: will naturally contract if we narrow the last 10 bars
        vols = [300_000.0] * 35 + [150_000.0] * 10
        df = _make_daily_bars(closes, volumes=vols)

        # For the last 10 bars, reduce high/low spread so TR contracts
        for i in range(len(df) - 10, len(df)):
            df.loc[i, "high"] = df.loc[i, "close"] + 0.15
            df.loc[i, "low"] = df.loc[i, "close"] - 0.15

        as_of = df["date"].iloc[-1]
        res = detect_base(df, as_of=as_of)

        assert res.data_status == "valid"
        assert res.is_active is True
        assert res.state == "tight"
        assert res.width_pct <= 12.0
        assert res.efficiency_ratio <= 0.35
        assert res.center_shift <= 0.30
        assert res.tr_contraction <= 0.80
        assert res.vol_contraction <= 0.80
        assert res.base_id == f"TEST:{as_of}:v1.0"
        assert res.detected_at == as_of

    def test_reject_monotonic_upward_trend_even_with_narrow_width(self):
        """Monotonically rising price: width is only 8%, but ER is near 1.0 (fails ER <= 0.35)."""
        # Prior 25 bars flat at 100, then 20 bars rising steadily from 100 to 108
        prior_closes = [100.0] * 25
        base_closes = [100.0 + i * 0.4 for i in range(20)]  # 100.0 to 107.6 (width = 7.6%)
        closes = prior_closes + base_closes
        df = _make_daily_bars(closes)

        as_of = df["date"].iloc[-1]
        res = detect_base(df, as_of=as_of)

        # Efficiency ratio must be 1.0 because every step is strictly up!
        assert res.efficiency_ratio == pytest.approx(1.0, abs=1e-3)
        assert res.state == "none"
        assert res.is_active is False
        # ER check must be False
        er_chk = next(c for c in res.checks if c["name"] == "Hiệu suất dịch chuyển (ER)")
        assert er_chk["pass"] is False

    def test_reject_monotonic_downward_trend(self):
        """Monotonically falling price: width is 9%, but ER is near 1.0 (fails ER <= 0.35)."""
        prior_closes = [110.0] * 25
        base_closes = [110.0 - i * 0.45 for i in range(20)]
        closes = prior_closes + base_closes
        df = _make_daily_bars(closes)

        as_of = df["date"].iloc[-1]
        res = detect_base(df, as_of=as_of)

        assert res.efficiency_ratio == pytest.approx(1.0, abs=1e-3)
        assert res.state == "none"
        assert res.is_active is False

    def test_reject_v_shape_center_shift(self):
        """V-shape: sharp drop to bottom in first half, then rise to top in second half -> fails center_shift."""
        prior_closes = [100.0] * 25
        # First 10 bars drop to 92 (mean ~94), second 10 bars rally to 102 (mean ~100)
        # Center shift = abs(100 - 94) / 10 = 0.60 > 0.30
        first_10 = [98, 96, 94, 93, 92, 92, 93, 94, 95, 96]
        second_10 = [97, 98, 99, 100, 101, 102, 102, 101, 100, 99]
        closes = prior_closes + first_10 + second_10
        df = _make_daily_bars(closes)

        as_of = df["date"].iloc[-1]
        res = detect_base(df, as_of=as_of)

        assert res.center_shift > 0.30
        assert res.state == "none"
        cs_chk = next(c for c in res.checks if c["name"] == "Độ lệch tâm giá (Center Shift)")
        assert cs_chk["pass"] is False

    def test_forming_base_when_volume_not_contracted(self):
        """Sideways base with stable volume (vol_ratio >= 1.0) is classified as forming, NOT tight."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        # Constant volume
        vols = [200_000.0] * 45
        df = _make_daily_bars(closes, volumes=vols)

        as_of = df["date"].iloc[-1]
        res = detect_base(df, as_of=as_of)

        assert res.state == "forming"
        assert res.is_active is True
        assert res.vol_contraction == pytest.approx(1.0, abs=1e-2)


class TestCausalBreakoutAndFrozenBoundaries:
    """Test boundary freezing, causal testing at bar T, and future data invariance."""

    def test_breakout_uses_frozen_boundary_from_prior_session(self):
        """
        At session T, breakout uses frozen_upper from previous_base.
        The breakout bar's high is NOT included in recomputing a new higher boundary.
        """
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes, volumes=[200_000.0] * 45)

        t_minus_1 = df["date"].iloc[-2]
        df_t_minus_1 = df.iloc[:-1].copy()

        # Detect base at T-1
        base_t_minus_1 = detect_base(df_t_minus_1, as_of=t_minus_1)
        assert base_t_minus_1.state in ("forming", "tight")
        frozen_upper = base_t_minus_1.upper
        frozen_lower = base_t_minus_1.lower

        # At session T, price spikes above frozen_upper with 3x volume
        as_of_t = df["date"].iloc[-1]
        df.loc[df["date"] == as_of_t, "close"] = frozen_upper + 3.0
        df.loc[df["date"] == as_of_t, "high"] = frozen_upper + 4.0
        df.loc[df["date"] == as_of_t, "volume"] = 600_000.0  # 3x SMA20 vol

        res_t = detect_base(df, as_of=as_of_t, previous_base=base_t_minus_1.to_dict())

        # Boundaries must remain the frozen ones!
        assert res_t.upper == frozen_upper
        assert res_t.lower == frozen_lower
        assert res_t.state == "breakout_confirmed"
        assert res_t.is_active is False  # closed after confirmed breakout
        assert res_t.position > 1.0  # position unclamped!

    def test_future_data_invariance(self):
        """Adding future bars must NOT alter the detection result at an earlier as_of date."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df_base = _make_daily_bars(closes)
        target_date = df_base["date"].iloc[-1]

        res_before = detect_base(df_base, as_of=target_date)

        # Append 15 future bars of wild crashes and surges
        future_dates = [pd.to_datetime(target_date) + timedelta(days=i) for i in range(1, 16)]
        future_rows = []
        for fd in future_dates:
            future_rows.append({
                "symbol": "TEST",
                "date": fd.strftime("%Y-%m-%d"),
                "open": 150.0,
                "high": 160.0,
                "low": 90.0,
                "close": 120.0,
                "volume": 1_000_000.0
            })
        df_extended = pd.concat([df_base, pd.DataFrame(future_rows)], ignore_index=True)

        res_after = detect_base(df_extended, as_of=target_date)

        assert res_after.state == res_before.state
        assert res_after.upper == res_before.upper
        assert res_after.lower == res_before.lower
        assert res_after.width_pct == res_before.width_pct
        assert res_after.efficiency_ratio == res_before.efficiency_ratio
        assert res_after.position == res_before.position


class TestBaseStateTransitionsAndLifecycle:
    """Test transitions: unconfirmed breakout, wick tests, weakening streak, and closed window."""

    def test_breakout_unconfirmed_then_pullback_back_into_base(self):
        """Close > upper without volume is breakout_unconfirmed; then pulling back notes 'Vượt nền rồi quay lại'."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes)

        # Detect initial base at bar -3
        date_0 = df["date"].iloc[-3]
        base_0 = detect_base(df.iloc[:-2], as_of=date_0)
        frozen_upper = base_0.upper

        # Bar -2: closes above upper but low volume
        date_1 = df["date"].iloc[-2]
        df.loc[df["date"] == date_1, "close"] = frozen_upper + 0.5
        df.loc[df["date"] == date_1, "high"] = frozen_upper + 0.8
        df.loc[df["date"] == date_1, "volume"] = 150_000.0  # < 1.2x

        base_1 = detect_base(df.iloc[:-1], as_of=date_1, previous_base=base_0.to_dict())
        assert base_1.state == "breakout_unconfirmed"
        assert base_1.is_active is True

        # Bar -1: closes back inside base
        date_2 = df["date"].iloc[-1]
        df.loc[df["date"] == date_2, "close"] = frozen_upper - 0.5
        df.loc[df["date"] == date_2, "high"] = frozen_upper - 0.2
        df.loc[df["date"] == date_2, "low"] = frozen_upper - 1.0
        df.loc[df["date"] == date_2, "open"] = frozen_upper - 0.6
        base_2 = detect_base(df, as_of=date_2, previous_base=base_1.to_dict())

        assert base_2.state in ("forming", "tight")
        assert any("Vượt nền rồi quay lại" in n for n in base_2.notes)

    def test_two_consecutive_weakening_sessions_leads_to_lost_structure(self):
        """Failing rolling conditions for 2 consecutive sessions transitions to lost_structure and closes base."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes)

        date_0 = df["date"].iloc[-3]
        base_0 = detect_base(df.iloc[:-2], as_of=date_0)
        assert base_0.is_active is True

        # Day 1 of weakening: stay strictly inside bounds [lower, upper]
        # but set all last 20 closes to rise steadily so ER = 1.0 > 0.35 (fails rolling conditions)
        date_1 = df["date"].iloc[-2]
        step = (base_0.upper - base_0.lower - 0.2) / 20.0
        for idx, k in enumerate(range(len(df) - 21, len(df) - 1)):
            df.loc[k, "close"] = round(base_0.lower + 0.1 + idx * step, 2)
            df.loc[k, "open"] = df.loc[k, "close"]
            df.loc[k, "high"] = df.loc[k, "close"] + 0.05
            df.loc[k, "low"] = df.loc[k, "close"] - 0.05

        base_1 = detect_base(df.iloc[:-1], as_of=date_1, previous_base=base_0.to_dict())
        assert base_1.state == "weakening"
        assert base_1.consecutive_weakening == 1
        assert base_1.is_active is True

        # Day 2 of weakening: still inside bounds and still monotonic -> consecutive_weakening = 2 -> lost_structure
        date_2 = df["date"].iloc[-1]
        df.loc[len(df) - 1, "close"] = df.loc[len(df) - 2, "close"] + 0.01
        df.loc[len(df) - 1, "open"] = df.loc[len(df) - 1, "close"]
        df.loc[len(df) - 1, "high"] = df.loc[len(df) - 1, "close"] + 0.05
        df.loc[len(df) - 1, "low"] = df.loc[len(df) - 1, "close"] - 0.05

        base_2 = detect_base(df, as_of=date_2, previous_base=base_1.to_dict())
        assert base_2.state == "lost_structure"
        assert base_2.is_active is False  # closed

    def test_new_base_cannot_start_before_closed_base_end_date(self):
        """A new base cannot start until its 20-bar window starts after the previous base ended."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes)

        # Previous base was closed yesterday
        yesterday_str = df["date"].iloc[-2]
        today_str = df["date"].iloc[-1]

        closed_base = {
            "symbol": "TEST",
            "base_id": f"TEST:2026-08-01:v1.0",
            "is_active": False,
            "state": "broken_down",
            "window_end": yesterday_str,
            "as_of": yesterday_str
        }

        # The 20-bar window for today starts 19 bars ago, which is well before yesterday_str
        res = detect_base(df, as_of=today_str, previous_base=closed_base)
        assert res.state == "none"
        assert res.is_active is False
        assert any("chưa vượt qua ngày kết thúc" in n for n in res.notes)


class TestAccumulationEvidenceAndEdgeCases:
    """Test OBV volume balance, flat price, zero volume, insufficient data, and stale data."""

    def test_signed_volume_balance_labels(self):
        """Signed volume balance identifies volume accumulation vs distribution."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        # Heavy volume on up days, tiny volume on down days
        vols = []
        for i in range(len(closes)):
            if i > 0 and closes[i] > closes[i - 1]:
                vols.append(500_000.0)
            else:
                vols.append(50_000.0)
        df = _make_daily_bars(closes, volumes=vols)

        res = detect_base(df, as_of=df["date"].iloc[-1])
        assert res.signed_volume_balance > 0.10
        assert res.volume_balance_label == "Volume thuận"

    def test_insufficient_bars_and_stale_data(self):
        """<40 bars returns insufficient_data; stale date returns stale_data."""
        # 30 bars only
        df_short = _make_daily_bars([100.0] * 30)
        res_short = detect_base(df_short, as_of=df_short["date"].iloc[-1])
        assert res_short.data_status == "insufficient_data"

        # Stale bar date vs as_of
        df_45 = _make_daily_bars([100.0] * 45, start_date="2026-01-01")
        res_stale = detect_base(df_45, as_of="2026-09-10")
        assert res_stale.data_status == "stale_data"

    def test_flat_price_and_invalid_ohlc(self):
        """Flat price (path=0) and invalid OHLC (NaN, High < Low) return invalid_data safely."""
        # Flat price
        df_flat = _make_daily_bars([100.0] * 45)
        # Set high and low identical to close for path=0 / upper=lower
        df_flat["high"] = 100.0
        df_flat["low"] = 100.0
        res_flat = detect_base(df_flat, as_of=df_flat["date"].iloc[-1])
        assert res_flat.data_status == "invalid_data"

        # NaN in close
        df_nan = _make_daily_bars([100.0] * 45)
        df_nan.loc[40, "close"] = np.nan
        res_nan = detect_base(df_nan, as_of=df_nan["date"].iloc[-1])
        assert res_nan.data_status == "invalid_data"

        # High < Low
        df_inv = _make_daily_bars([100.0] * 45)
        df_inv.loc[40, "high"] = 90.0
        df_inv.loc[40, "low"] = 105.0
        res_inv = detect_base(df_inv, as_of=df_inv["date"].iloc[-1])
        assert res_inv.data_status == "invalid_data"


class TestSignalEventsDeduplicationAndStorage:
    """Test base signal event deduplication and database persistence."""

    def test_signal_events_only_fire_on_state_change_and_deduplicate(self):
        """Zero duplicate alerts on re-run with exact event_key format."""
        b1 = {
            "symbol": "AAPL",
            "as_of": "2026-09-10",
            "base_id": "AAPL:2026-09-10:v1.0",
            "state": "tight",
            "lower": 150.0,
            "upper": 160.0,
            "close_price": 155.0,
            "width_pct": 6.7
        }

        # Day 1: New tight base event
        events_day1 = generate_base_signal_events([b1], prev_bases=[], as_of="2026-09-10")
        assert len(events_day1) == 1
        assert events_day1[0]["event_key"] == "2026-09-10:AAPL:2026-09-10:v1.0:base_tight"

        # Re-run same day: state hasn't changed against existing state -> 0 events
        events_rerun = generate_base_signal_events([b1], prev_bases=[b1], as_of="2026-09-10")
        assert len(events_rerun) == 0

        # Day 2: Transitions to confirmed breakout
        b2 = dict(b1)
        b2["as_of"] = "2026-09-11"
        b2["state"] = "breakout_confirmed"
        b2["close_price"] = 162.0
        events_day2 = generate_base_signal_events([b2], prev_bases=[b1], as_of="2026-09-11")
        assert len(events_day2) == 1
        assert events_day2[0]["event_type"] == "base_breakout_confirmed"
        assert events_day2[0]["event_key"] == "2026-09-11:AAPL:2026-09-10:v1.0:base_breakout_confirmed"

    def test_repository_save_and_retrieve_base_snapshots(self, tmp_path):
        """Save base snapshots to SQLite and query by snapshot_id and as_of."""
        db_file = tmp_path / "test_base.db"
        repo = MarketRadarRepository(db_path=db_file)

        records = [{
            "symbol": "MSFT",
            "as_of": "2026-09-10",
            "base_id": "MSFT:2026-09-10:v1.0",
            "detected_at": "2026-09-10",
            "window_start": "2026-08-10",
            "window_end": "2026-09-10",
            "state": "tight",
            "is_active": True,
            "data_status": "valid",
            "rule_version": "v1.0",
            "upper": 450.0,
            "lower": 420.0,
            "close_price": 445.0,
            "width_pct": 7.14,
            "efficiency_ratio": 0.22,
            "center_shift": 0.15,
            "tr_contraction": 0.65,
            "vol_contraction": 0.70,
            "position": 0.83,
            "distance_to_upper_pct": 1.12,
            "signed_volume_balance": 0.25,
            "volume_balance_label": "Volume thuận",
            "trend_context": "Nền trong xu hướng tăng",
            "rs_vs_spy": 4.5,
            "consecutive_weakening": 0,
            "checks": [{"name": "Độ rộng nền", "pass": True, "value": "7.1%"}],
            "warnings": ["Kiểm định biên trên"],
            "notes": ["Nền co chặt"]
        }]

        snap_id = repo.save_snapshot(
            as_of="2026-09-10",
            rule_version="v1.0",
            total_universe=500,
            valid_universe=500,
            coverage_pct=1.0,
            missing_symbols=[],
            market_metrics={},
            sector_metrics=[],
            candidates=[]
        )

        cnt = repo.save_base_snapshots(records, snapshot_id=snap_id)
        assert cnt == 1

        # Query by snapshot_id
        fetched = repo.get_base_snapshots(snapshot_id=snap_id)
        assert len(fetched) == 1
        assert fetched[0]["symbol"] == "MSFT"
        assert fetched[0]["state"] == "tight"
        assert fetched[0]["is_active"] is True
        assert fetched[0]["checks"][0]["pass"] is True
        assert "Kiểm định biên trên" in fetched[0]["warnings"]

        # Active bases mapping
        active_map = repo.get_active_bases_by_symbol(as_of="2026-09-10")
        assert "MSFT" in active_map
        assert active_map["MSFT"]["base_id"] == "MSFT:2026-09-10:v1.0"

        # Non-existent or old snapshot query returns empty list gracefully
        old_fetched = repo.get_base_snapshots(snapshot_id=9999)
        assert old_fetched == []

    def test_full_signal_events_with_base_records(self):
        """Test generate_signal_events integrating base events alongside candidate events."""
        current_snap = {"as_of": "2026-09-10"}
        cur_cands = [{
            "symbol": "NVDA",
            "group_type": "long_cont",
            "setup_type": "breakout",
            "status": "confirmed",
            "close_price": 125.0
        }]
        cur_bases = [{
            "symbol": "GOOGL",
            "as_of": "2026-09-10",
            "base_id": "GOOGL:2026-09-10:v1.0",
            "state": "tight",
            "lower": 160.0,
            "upper": 170.0,
            "close_price": 168.0,
            "width_pct": 6.25,
            "tr_contraction": 0.72,
            "vol_contraction": 0.68
        }]

        events = generate_signal_events(
            current_snapshot=current_snap,
            current_candidates=cur_cands,
            current_bases=cur_bases
        )

        cand_ev = [e for e in events if e["symbol"] == "NVDA"]
        base_ev = [e for e in events if e["symbol"] == "GOOGL"]

        assert len(cand_ev) >= 1
        assert len(base_ev) == 1
        assert base_ev[0]["event_type"] == "base_tight"
        assert base_ev[0]["group_type"] == "base"
        assert base_ev[0]["severity"] == "opportunity"

    def test_base_does_not_create_long_signal_outcomes(self, tmp_path):
        """Verify that base building stocks do NOT automatically create Long signal records or outcomes."""
        db_file = tmp_path / "test_outcomes_isolation.db"
        repo = MarketRadarRepository(db_path=db_file)

        # Save snapshot with only candidates
        snap_id = repo.save_snapshot(
            as_of="2026-09-10",
            rule_version="v1.0",
            total_universe=100,
            valid_universe=100,
            coverage_pct=1.0,
            missing_symbols=[],
            market_metrics={},
            sector_metrics=[],
            candidates=[]
        )

        # Save base snapshot for BASE1
        base_rec = [{
            "symbol": "BASE1",
            "as_of": "2026-09-10",
            "base_id": "BASE1:2026-09-10:v1.0",
            "detected_at": "2026-09-10",
            "state": "tight",
            "is_active": True,
            "data_status": "valid",
            "rule_version": "v1.0",
            "upper": 100.0,
            "lower": 92.0,
            "close_price": 98.0
        }]
        repo.save_base_snapshots(base_rec, snapshot_id=snap_id)

        # Query signal_records (used by signal outcomes engine)
        sig_records = repo.get_signal_records(status="active")
        # BASE1 must NOT be in signal_records!
        assert not any(s["symbol"] == "BASE1" for s in sig_records)


class TestBaseWatchlistUI:
    """Test UI figure generation and safety."""

    def test_create_base_figure_generates_valid_plotly_structure(self):
        """_create_base_figure produces valid chart with shaded rect and horizontal lines."""
        from app.components.base_watchlist import _create_base_figure

        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes)

        base_info = {
            "upper": 102.5,
            "lower": 98.0,
            "window_start": df["date"].iloc[-20],
            "window_end": df["date"].iloc[-1]
        }

        fig = _create_base_figure(df, base_info)
        assert fig is not None
        # Must have candlestick trace and volume bar trace
        trace_names = [t.name for t in fig.data if hasattr(t, "name")]
        assert "OHLC" in trace_names
        assert "Volume" in trace_names
        # Layout must have shapes (horizontal lines and vrect)
        assert len(fig.layout.shapes) >= 2


class TestBaseEdgeCasesAndRobustnessFixes:
    """Regression tests for all identified edge cases and contract guarantees."""

    def test_active_base_preserved_when_data_anomalies_occur(self):
        """When an ongoing active base exists, anomalies (empty, missing cols, <40 bars) must preserve active state."""
        active_base = {
            "symbol": "TEST",
            "as_of": "2026-09-09",
            "base_id": "TEST:2026-09-05:v1.0",
            "detected_at": "2026-09-05",
            "window_start": "2026-08-10",
            "window_end": "2026-09-05",
            "state": "tight",
            "is_active": True,
            "upper": 105.0,
            "lower": 98.0,
            "close_price": 101.0,
            "consecutive_weakening": 0,
            "ma50": 95.0,
            "ma200": 90.0,
        }

        # 1. Empty dataframe
        res_empty = detect_base(pd.DataFrame(), as_of="2026-09-10", previous_base=active_base)
        assert res_empty.is_active is True
        assert res_empty.base_id == active_base["base_id"]
        assert res_empty.upper == active_base["upper"]
        assert res_empty.lower == active_base["lower"]
        assert res_empty.data_status == "insufficient_data"
        assert any("không báo thủng" in w for w in res_empty.warnings)

        # 2. Missing columns
        bad_cols_df = pd.DataFrame([{"symbol": "TEST", "date": "2026-09-10", "close": 100.0}])
        res_cols = detect_base(bad_cols_df, as_of="2026-09-10", previous_base=active_base)
        assert res_cols.is_active is True
        assert res_cols.data_status == "invalid_data"
        assert any("không báo thủng" in w for w in res_cols.warnings)

        # 3. Insufficient bars (<40 bars)
        df_short = _make_daily_bars([100.0] * 25, start_date="2026-08-15")
        res_short = detect_base(df_short, as_of=df_short["date"].iloc[-1], previous_base=active_base)
        assert res_short.is_active is True
        assert res_short.data_status == "insufficient_data"
        assert any("không báo thủng" in w for w in res_short.warnings)

    def test_zero_denominator_in_tr_and_vol_returns_invalid_data(self):
        """Per rule: when denominator is 0 (flat price TR=0 or 0 volume), must return invalid_data."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes)

        # Flat price in first 10 bars of base (bars index -20 to -11)
        base_start = len(df) - 20
        for i in range(base_start, base_start + 10):
            df.loc[i, "close"] = 100.0
            df.loc[i, "high"] = 100.0
            df.loc[i, "low"] = 100.0
            df.loc[i, "open"] = 100.0
        df.loc[base_start - 1, ["open", "high", "low", "close"]] = 100.0  # prior bar also flat at 100 so TR = 0

        res_tr = detect_base(df, as_of=df["date"].iloc[-1])
        assert res_tr.data_status == "invalid_data"
        assert any("True Range" in n for n in res_tr.notes)

        # Zero volume in first 10 bars of base
        df_zero_vol = _make_daily_bars(closes)
        for i in range(base_start, base_start + 10):
            df_zero_vol.loc[i, "volume"] = 0.0

        res_vol = detect_base(df_zero_vol, as_of=df_zero_vol["date"].iloc[-1])
        assert res_vol.data_status == "invalid_data"
        assert any("Volume" in n for n in res_vol.notes)

    def test_closed_base_termination_date_enforcement(self):
        """New base cannot overlap with the actual termination session of a closed base."""
        closes = _make_oscillating_closes(n_bars=45, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes, start_date="2026-07-15")

        # Old base had initial window ending 2026-08-01, but actually closed on 2026-08-10
        closed_base = {
            "symbol": "TEST",
            "base_id": "TEST:2026-07-15:v1.0",
            "is_active": False,
            "state": "broken_down",
            "window_end": "2026-08-01",
            "as_of": "2026-08-10"
        }

        # Candidate session whose 20-bar window starts on 2026-08-09 (<= 2026-08-10)
        as_of_test = df["date"].iloc[-1]
        res = detect_base(df, as_of=as_of_test, previous_base=closed_base)
        assert res.state == "none"
        assert res.is_active is False
        assert any("chưa vượt qua ngày kết thúc" in n for n in res.notes)

    def test_repository_idempotent_save_and_strictly_prior_queries(self, tmp_path):
        """Re-running save_base_snapshots does not duplicate rows; get_active_bases uses strictly prior dates."""
        db_file = tmp_path / "test_idempotent.db"
        repo = MarketRadarRepository(db_path=db_file)

        snap_id = repo.save_snapshot(
            as_of="2026-09-10",
            rule_version="v1.0",
            total_universe=100,
            valid_universe=100,
            coverage_pct=1.0,
            missing_symbols=[],
            market_metrics={},
            sector_metrics=[],
            candidates=[]
        )

        records = [{
            "symbol": "NVDA",
            "as_of": "2026-09-10",
            "base_id": "NVDA:2026-09-10:v1.0",
            "detected_at": "2026-09-10",
            "state": "tight",
            "is_active": True,
            "upper": 130.0,
            "lower": 120.0,
            "close_price": 128.0,
            "ma50": 122.0,
            "ma200": 105.0,
            "price_vs_ma50_pct": 4.92,
            "price_vs_ma200_pct": 21.90,
            "pressure_bias": "Bằng chứng thuận cho phía Mua"
        }]

        # Save once
        cnt1 = repo.save_base_snapshots(records, snapshot_id=snap_id)
        assert cnt1 == 1
        assert len(repo.get_base_snapshots(snapshot_id=snap_id)) == 1

        # Re-run same snapshot (pipeline re-run) -> must NOT duplicate rows!
        cnt2 = repo.save_base_snapshots(records, snapshot_id=snap_id)
        assert cnt2 == 1
        assert len(repo.get_base_snapshots(snapshot_id=snap_id)) == 1

        # Verify get_active_bases_by_symbol(before_date="2026-09-10") strictly queries prior sessions
        # Since the record is for 2026-09-10, querying before_date="2026-09-10" must NOT return NVDA
        active_prior = repo.get_active_bases_by_symbol(before_date="2026-09-10")
        assert "NVDA" not in active_prior

        # But querying for next session "2026-09-11" DOES return NVDA
        active_next = repo.get_active_bases_by_symbol(as_of="2026-09-11")
        assert "NVDA" in active_next
        assert active_next["NVDA"]["ma50"] == 122.0
        assert active_next["NVDA"]["pressure_bias"] == "Bằng chứng thuận cho phía Mua"

    def test_new_base_events_only_fire_on_detection_day(self):
        """A base detected in past sessions does not emit spurious 'Nền giá mới' if prev_bases is empty."""
        old_base = {
            "symbol": "AAPL",
            "as_of": "2026-09-11",
            "base_id": "AAPL:2026-09-01:v1.0",
            "detected_at": "2026-09-01",  # 10 days ago!
            "state": "tight",
            "lower": 150.0,
            "upper": 160.0,
            "close_price": 155.0,
            "width_pct": 6.7
        }

        # Cold start on 2026-09-11 where prev_bases is empty: should NOT say 'Nền giá mới'
        events = generate_base_signal_events([old_base], prev_bases=[], as_of="2026-09-11")
        assert len(events) == 0

    def test_ma50_ma200_and_multi_session_pressure_calculated(self):
        """Ensure MA50, MA200 and multi-session pressure profile are computed and returned."""
        closes = _make_oscillating_closes(n_bars=220, center=100.0, amplitude=2.0)
        df = _make_daily_bars(closes)

        as_of = df["date"].iloc[-1]
        res = detect_base(df, as_of=as_of)

        assert res.ma50 is not None
        assert res.ma200 is not None
        assert res.price_vs_ma50_pct is not None
        assert res.price_vs_ma200_pct is not None
        assert res.pressure_bias != ""


