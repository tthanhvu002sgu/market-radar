"""
Comprehensive Unit Tests for Swing Workstation Features:
- Market Calendar: NYSE holidays, early closes, unclosed weeks, session resolution
- Setup Analyzer: Structured evidence, technical levels, volatility, checklists, N/A handling
- Signal Events: Deduplication, transitions, missing-data guardrail, earnings events
- Signal Outcomes: Streak continuity, next-day open entry, horizon returns, short direction, MFE/MAE
- Storage & Migration: Candidate snapshots, signal events, signal records, and outcomes
"""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import pytest

from analytics.market_calendar import (
    get_market_holidays,
    get_early_close_dates,
    is_market_holiday,
    is_early_close,
    is_trading_day,
    is_end_of_trading_week,
    determine_trading_session,
    get_market_close_time,
)
from analytics.setup_analyzer import (
    analyze_candidate_setup,
    analyze_candlestick,
    interpret_candlestick_in_setup,
    CANDLESTICK_THRESHOLDS,
)
from analytics.signal_events import generate_signal_events
from analytics.signal_outcomes import (
    process_signal_streaks,
    evaluate_signal_outcomes,
    compute_quality_summary,
)
from storage.database import init_db
from storage.repository import MarketRadarRepository

# ==========================================
# 1. MARKET CALENDAR TESTS
# ==========================================

def test_market_calendar_holidays_2026():
    holidays = get_market_holidays(2026)
    # Good Friday in 2026 is April 3
    assert date(2026, 4, 3) in holidays
    # Thanksgiving in 2026 is Nov 26
    assert date(2026, 11, 26) in holidays
    # Christmas in 2026 is Dec 25
    assert date(2026, 12, 25) in holidays
    # Independence Day observed is July 3 (since July 4 is Saturday)
    assert date(2026, 7, 3) in holidays

    assert is_market_holiday(date(2026, 4, 3)) is True
    assert is_trading_day(date(2026, 4, 3)) is False

def test_market_calendar_early_closes():
    early_dates = get_early_close_dates(2026)
    # Black Friday in 2026 is Nov 27
    assert date(2026, 11, 27) in early_dates
    assert is_early_close(date(2026, 11, 27)) is True
    assert get_market_close_time(date(2026, 11, 27)) == time(13, 0)

def test_end_of_trading_week():
    # Normal Friday (e.g. 2026-04-10) is end of week
    assert is_end_of_trading_week(date(2026, 4, 10)) is True
    # Wednesday (e.g. 2026-04-08) is not end of week
    assert is_end_of_trading_week(date(2026, 4, 8)) is False
    # Thursday before Good Friday (2026-04-02) is end of week because Friday April 3 is closed!
    assert is_end_of_trading_week(date(2026, 4, 2)) is True

def test_determine_trading_session_with_calendar():
    tz = ZoneInfo("America/New_York")
    # Thanksgiving Day at 18:00 ET -> should resolve to Wednesday Nov 25
    thanksgiving_dt = datetime(2026, 11, 26, 18, 0, tzinfo=tz)
    target, is_closed = determine_trading_session(thanksgiving_dt)
    assert target == "2026-11-25"
    assert is_closed is True

    # Black Friday at 12:00 ET (before 13:00 early close) -> should resolve to Wednesday Nov 25
    black_friday_early = datetime(2026, 11, 27, 12, 0, tzinfo=tz)
    target, is_closed = determine_trading_session(black_friday_early)
    assert target == "2026-11-25"
    assert is_closed is False

    # Black Friday at 14:00 ET (after 13:00 early close) -> should resolve to Friday Nov 27
    black_friday_late = datetime(2026, 11, 27, 14, 0, tzinfo=tz)
    target, is_closed = determine_trading_session(black_friday_late)
    assert target == "2026-11-27"
    assert is_closed is True

# ==========================================
# 2. SETUP ANALYZER TESTS
# ==========================================

def test_setup_analyzer_breakout():
    stock = {
        "symbol": "NVDA",
        "close": 150.0,
        "volume": 50_000_000,
        "vol_ma20": 30_000_000,
        "ma20": 140.0,
        "ma50": 130.0,
        "ma200": 110.0,
        "prev_high20": 148.0,
        "prev_low20": 125.0,
        "atr14": 5.0,
        "atr_pct": 3.33,
        "avg_dollar_vol20": 4_500_000_000.0,
        "perf_1d": 2.5,
        "perf_5d": 6.0,
        "perf_20d": 18.0
    }
    analysis = analyze_candidate_setup(stock, "long_cont", "breakout", spy_perf_20d=5.0)

    assert analysis["trigger_price"] == 148.0
    assert "vượt đỉnh 20 phiên" in analysis["trigger_condition"]
    assert analysis["invalidation_price"] is not None
    assert analysis["invalidation_price"] < 148.0
    assert analysis["support_level"] == 140.0
    assert analysis["resistance_level"] == 148.0
    assert analysis["dist_trigger_pct"] == round((150.0 - 148.0) / 148.0 * 100, 2)
    assert analysis["dist_trigger_atr"] == round((150.0 - 148.0) / 5.0, 2)

    # Checklist checks
    checklist = analysis["checklist"]
    assert len(checklist) >= 4
    criteria_names = [c["criterion"] for c in checklist]
    assert any("Xu hướng (MA50)" in n for n in criteria_names)
    assert any("Thanh khoản" in n for n in criteria_names)
    assert any("Sức mạnh Tương đối" in n for n in criteria_names)

def test_setup_analyzer_missing_data_resilience():
    # Stock with NO MA200 and NO SPY benchmark
    stock = {
        "symbol": "NEW_IPO",
        "close": 45.0,
        "volume": 2_000_000,
        "vol_ma20": 1_500_000,
        "ma20": 42.0,
        "ma50": 40.0,
        "ma200": np.nan,  # Missing MA200
        "prev_high20": 46.0,
        "prev_low20": 38.0,
        "atr14": 2.0,
        "perf_20d": 12.0
    }
    analysis = analyze_candidate_setup(stock, "long_cont", "near_breakout", spy_perf_20d=None)

    # Must NOT raise exception!
    checklist = analysis["checklist"]
    # Check that MA200 and SPY items report missing_data
    ma200_item = next(c for c in checklist if "MA200" in c["criterion"])
    assert ma200_item["status"] == "missing_data"
    assert "N/A" in ma200_item["detail"] or "Chưa đủ" in ma200_item["detail"]

    spy_item = next(c for c in checklist if "SPY" in c["criterion"])
    assert spy_item["status"] == "missing_data"

# ==========================================
# 3. SIGNAL EVENTS & DEDUPLICATION TESTS
# ==========================================

def test_signal_events_generation_and_deduplication():
    cur_snap = {
        "as_of": "2026-09-08",
        "sector_metrics": [{"sector": "Technology", "rank": 1, "etf": "XLK", "etf_1m": 4.5}],
        "market_metrics": {"pct_above_ma50": 65.0}
    }
    prev_snap = {
        "as_of": "2026-09-05",
        "sector_metrics": [{"sector": "Technology", "rank": 3, "etf": "XLK", "etf_1m": 2.0}],
        "market_metrics": {"pct_above_ma50": 58.0}
    }

    # AAPL is a new candidate; MSFT transitioned from setup to confirmed; AMZN disappeared
    cur_cands = [
        {"symbol": "AAPL", "setup_type": "breakout", "group_type": "long_cont", "status": "confirmed", "close_price": 230.0, "score": 25.0},
        {"symbol": "MSFT", "setup_type": "pullback_ma20", "group_type": "long_cont", "status": "confirmed", "close_price": 440.0, "score": 18.0}
    ]
    prev_cands = [
        {"symbol": "MSFT", "setup_type": "pullback_ma20", "group_type": "long_cont", "status": "setup", "close_price": 435.0, "score": 15.0},
        {"symbol": "AMZN", "setup_type": "breakout", "group_type": "long_cont", "status": "confirmed", "close_price": 190.0, "score": 10.0}
    ]

    events = generate_signal_events(
        current_snapshot=cur_snap,
        current_candidates=cur_cands,
        prev_snapshot=prev_snap,
        prev_candidates=prev_cands,
        missing_symbols=[]
    )

    ev_types = [e["event_type"] for e in events]
    assert "new_candidate" in ev_types  # AAPL
    assert "setup_triggered" in ev_types  # MSFT
    assert "setup_invalidated" in ev_types  # AMZN
    assert "sector_rank_shift" in ev_types  # Tech moved #3 -> #1
    assert "market_breadth_shift" in ev_types  # Breadth moved +7%

    # Check that event_key is deterministic
    aapl_ev = next(e for e in events if e["symbol"] == "AAPL")
    assert aapl_ev["event_key"] == "2026-09-08:AAPL:breakout:new_candidate"

def test_missing_data_does_not_flag_setup_failure():
    cur_snap = {"as_of": "2026-09-08"}
    prev_snap = {"as_of": "2026-09-05"}
    cur_cands = []
    # GOOGL was in prev_cands, but is in missing_symbols on current run
    prev_cands = [{"symbol": "GOOGL", "setup_type": "breakout", "group_type": "long_cont", "status": "confirmed"}]

    events = generate_signal_events(
        current_snapshot=cur_snap,
        current_candidates=cur_cands,
        prev_snapshot=prev_snap,
        prev_candidates=prev_cands,
        missing_symbols=["GOOGL"]
    )

    # GOOGL must NOT have a setup_invalidated event!
    googl_invalidated = [e for e in events if e["symbol"] == "GOOGL" and e["event_type"] == "setup_invalidated"]
    assert len(googl_invalidated) == 0

# ==========================================
# 4. SIGNAL OUTCOMES & STREAKS TESTS
# ==========================================

def test_signal_streak_tracking():
    # Day 1
    cands_day1 = [{"symbol": "TSLA", "setup_type": "breakout", "group_type": "long_cont", "close_price": 200.0, "score": 20.0}]
    records1 = process_signal_streaks("2026-09-01", "v2", cands_day1, active_signals=[])
    assert len(records1) == 1
    assert records1[0]["streak_count"] == 1
    assert records1[0]["first_detected_date"] == "2026-09-01"

    # Day 2: TSLA still active -> streak_count becomes 2
    cands_day2 = [{"symbol": "TSLA", "setup_type": "breakout", "group_type": "long_cont", "close_price": 205.0, "score": 22.0}]
    records2 = process_signal_streaks("2026-09-02", "v2", cands_day2, active_signals=records1)
    assert len(records2) == 1
    assert records2[0]["streak_count"] == 2
    assert records2[0]["latest_detected_date"] == "2026-09-02"

def test_forward_outcomes_calculation_long_and_short():
    signals = [
        {
            "id": 1,
            "signal_key": "2026-08-01:LONG_STK:breakout",
            "symbol": "LONG_STK",
            "side": "long",
            "first_detected_date": "2026-08-01",
            "initial_atr": 2.0,
            "trigger_price": 100.0,
            "invalidation_price": 95.0
        },
        {
            "id": 2,
            "signal_key": "2026-08-01:SHORT_STK:breakdown",
            "symbol": "SHORT_STK",
            "side": "short",
            "first_detected_date": "2026-08-01",
            "initial_atr": 3.0,
            "trigger_price": 50.0,
            "invalidation_price": 53.0
        }
    ]

    dates = pd.date_range("2026-08-01", periods=25, freq="B")
    bars_data = []

    # SPY: starts at open=500.0, ends at close=525.0 (+5%)
    for i, d in enumerate(dates):
        bars_data.append({"symbol": "SPY", "date": d, "open": 500.0 + i, "high": 502.0 + i, "low": 499.0 + i, "close": 501.0 + i, "volume": 1000})

    # LONG_STK: Entry open on 2026-08-04 (day 1 after first_date) = 100.0. Exit on day 5 = 110.0 (+10%)
    for i, d in enumerate(dates):
        bars_data.append({"symbol": "LONG_STK", "date": d, "open": 100.0 + i * 2, "high": 102.0 + i * 2, "low": 99.0, "close": 101.0 + i * 2, "volume": 500})

    # SHORT_STK: Entry open = 50.0. Exit on day 5 = 45.0 (+10% in short direction!)
    for i, d in enumerate(dates):
        bars_data.append({"symbol": "SHORT_STK", "date": d, "open": 50.0 - i, "high": 51.0, "low": 49.0 - i, "close": 49.5 - i, "volume": 500})

    df_bars = pd.DataFrame(bars_data)

    outcomes = evaluate_signal_outcomes(signals, df_bars, horizons=[5, 10, 20])

    # Check Long outcome at 5 days
    long_5 = next(o for o in outcomes if o["symbol"] == "LONG_STK" and o["horizon_days"] == 5)
    assert long_5["status"] == "completed"
    assert long_5["return_pct"] > 0
    assert long_5["excess_return_spy"] is not None

    # Check Short outcome at 5 days
    short_5 = next(o for o in outcomes if o["symbol"] == "SHORT_STK" and o["horizon_days"] == 5)
    assert short_5["status"] == "completed"
    # Price dropped, so short return MUST BE POSITIVE
    assert short_5["return_pct"] > 0
    assert short_5["mfe_pct"] > 0

def test_pending_status_for_insufficient_bars():
    signals = [{
        "id": 99,
        "signal_key": "2026-09-07:RECENT:breakout",
        "symbol": "RECENT",
        "side": "long",
        "first_detected_date": "2026-09-07",
        "initial_atr": 1.0
    }]
    # Only 2 bars available after 2026-09-07
    dates = pd.date_range("2026-09-08", periods=2, freq="B")
    bars_data = [{"symbol": "RECENT", "date": d, "open": 50.0, "high": 51.0, "low": 49.0, "close": 50.5, "volume": 100} for d in dates]
    df_bars = pd.DataFrame(bars_data)

    outcomes = evaluate_signal_outcomes(signals, df_bars, horizons=[5, 10, 20])
    for o in outcomes:
        # 5, 10, 20 must ALL report pending because only 2 bars exist!
        assert o["status"] == "pending"
        assert o["return_pct"] is None

# ==========================================
# 5. REPOSITORY INTEGRATION TESTS
# ==========================================

def test_repository_events_and_outcomes_persistence(tmp_path):
    db_file = tmp_path / "test_swing.db"
    init_db(db_file)
    repo = MarketRadarRepository(db_file)

    # Save event
    events = [{
        "event_key": "2026-09-08:AAPL:breakout:new_candidate",
        "session_date": "2026-09-08",
        "symbol": "AAPL",
        "event_type": "new_candidate",
        "title": "Cơ hội mới: AAPL",
        "summary": "Breakout",
        "severity": "opportunity",
        "is_read": 0
    }]
    count1 = repo.save_signal_events(events)
    assert count1 == 1

    # Idempotent re-run must insert 0 duplicates!
    count2 = repo.save_signal_events(events)
    assert count2 == 0

    fetched_events = repo.get_signal_events()
    assert len(fetched_events) == 1
    assert fetched_events[0]["symbol"] == "AAPL"

    # Mark read
    repo.mark_event_read(fetched_events[0]["id"])
    assert repo.get_unread_event_count() == 0

# ==========================================
# 6. CANDLESTICK ANALYSIS & PATTERN TESTS
# ==========================================

def test_candlestick_analyzer_patterns():
    # 1. Doji: body <= 10% of range
    doji_res = analyze_candlestick(open_p=100.0, high_p=105.0, low_p=95.0, close_p=100.2, atr14=5.0)
    assert doji_res["pattern"] == "Doji"
    assert doji_res["body_ratio"] <= CANDLESTICK_THRESHOLDS["doji_max_body_ratio"]
    assert doji_res["range_to_atr"] == 2.0

    # 2. Long Lower Shadow (Hammer): lower shadow >= 55%, close >= 55% of range
    hammer_res = analyze_candlestick(open_p=108.0, high_p=110.0, low_p=100.0, close_p=109.0, atr14=8.0)
    assert hammer_res["pattern"] == "Râu dưới dài (Hammer)"
    assert hammer_res["lower_shadow_ratio"] >= 0.55
    assert hammer_res["close_position_pct"] >= 55.0

    # 3. Long Upper Shadow (Shooting Star): upper shadow >= 55%, close <= 45% of range
    star_res = analyze_candlestick(open_p=102.0, high_p=110.0, low_p=100.0, close_p=101.0, atr14=8.0)
    assert star_res["pattern"] == "Râu trên dài (Shooting Star)"
    assert star_res["upper_shadow_ratio"] >= 0.55
    assert star_res["close_position_pct"] <= 45.0

    # 4. Long Body (Marubozu): body >= 70% of range
    bull_maru = analyze_candlestick(open_p=100.0, high_p=110.0, low_p=99.8, close_p=109.8, atr14=10.0)
    assert bull_maru["pattern"] == "Thân dài tăng (Marubozu)"
    assert bull_maru["body_ratio"] >= 0.70

    bear_maru = analyze_candlestick(open_p=109.8, high_p=110.0, low_p=99.8, close_p=100.0, atr14=10.0)
    assert bear_maru["pattern"] == "Thân dài giảm (Marubozu)"
    assert bear_maru["body_ratio"] >= 0.70

    # 5. Inside Bar: current high <= prev high and current low >= prev low
    inside_res = analyze_candlestick(
        open_p=98.0, high_p=104.0, low_p=96.0, close_p=102.0,
        prev_open=95.0, prev_high=110.0, prev_low=90.0, prev_close=105.0
    )
    assert "Inside bar" in inside_res["pattern_tags"]

    # 6. Outside Bar: current high > prev high and current low < prev low
    outside_res = analyze_candlestick(
        open_p=94.0, high_p=112.0, low_p=88.0, close_p=106.0,
        prev_open=98.0, prev_high=105.0, prev_low=95.0, prev_close=100.0
    )
    assert "Outside bar" in outside_res["pattern_tags"]

    # 7. Bullish Engulfing: prev bear, current bull engulfing prev body
    bull_eng = analyze_candlestick(
        open_p=100.0, high_p=112.0, low_p=98.0, close_p=108.0,
        prev_open=106.0, prev_high=107.0, prev_low=101.0, prev_close=102.0
    )
    assert bull_eng["pattern"] == "Nhấn chìm tăng (Bullish Engulfing)"

    # 8. Standard bar / Không rõ mẫu hình: ordinary bar without extreme geometry
    std_res = analyze_candlestick(open_p=102.0, high_p=105.0, low_p=100.0, close_p=103.5)
    assert std_res["pattern"] == "Không rõ mẫu hình"

def test_interpret_candlestick_in_setup():
    # A. Pullback at MA20 with Hammer -> Pass (positive reaction at support)
    hammer_candle = {
        "date": "2026-09-04",
        "pattern": "Râu dưới dài (Hammer)",
        "direction": "Tăng",
        "close_position_label": "Đóng cửa gần đỉnh phiên",
        "close_position_pct": 85.0,
        "range_to_atr": 1.1
    }
    interp_pb = interpret_candlestick_in_setup(
        candle=hammer_candle,
        setup_subtype="pullback_ma20",
        group_type="long_cont",
        close_price=125.0,
        ma20=124.5,
        trigger_price=130.0
    )
    assert interp_pb["reaction_status"] == "pass"
    assert "MA20" in interp_pb["context_summary"]
    assert "rút chân" in interp_pb["reaction_summary"] or "hấp thụ" in interp_pb["reaction_summary"]

    # B. Extended price > 1.5 ATR above MA20 -> Fail / Caution (overextension)
    interp_ext = interpret_candlestick_in_setup(
        candle=hammer_candle,
        setup_subtype="pullback_ma20",
        group_type="long_cont",
        close_price=150.0,
        ma20=130.0,
        dist_ma20_atr=2.2
    )
    assert interp_ext["reaction_status"] == "fail"
    assert "tăng xa MA20" in interp_ext["context_summary"]
    assert "mua đuổi" in interp_ext["reaction_summary"]

    # C. Breakout with Marubozu -> Pass
    maru_candle = {
        "date": "2026-09-04",
        "pattern": "Thân dài tăng (Marubozu)",
        "direction": "Tăng",
        "close_position_label": "Đóng cửa gần đỉnh phiên",
        "close_position_pct": 95.0,
        "range_to_atr": 1.5
    }
    interp_bo = interpret_candlestick_in_setup(
        candle=maru_candle,
        setup_subtype="breakout",
        group_type="long_cont",
        close_price=160.0,
        prev_high20=158.0,
        trigger_price=158.0
    )
    assert interp_bo["reaction_status"] == "pass"
    assert "bứt phá" in interp_bo["reaction_summary"]

    # D. Breakout with Shooting Star (rejection) -> Fail
    star_candle = {
        "date": "2026-09-04",
        "pattern": "Râu trên dài (Shooting Star)",
        "direction": "Giảm",
        "close_position_label": "Đóng cửa gần đáy phiên",
        "close_position_pct": 20.0,
        "range_to_atr": 1.3
    }
    interp_star = interpret_candlestick_in_setup(
        candle=star_candle,
        setup_subtype="breakout",
        group_type="long_cont",
        close_price=157.0,
        prev_high20=158.0,
        trigger_price=158.0
    )
    assert interp_star["reaction_status"] == "fail"
    assert "từ chối" in interp_star["reaction_summary"]

def test_setup_analyzer_includes_candlestick_in_checklist_and_evidence():
    stock = {
        "symbol": "MSFT",
        "open": 405.0,
        "high": 420.0,
        "low": 404.0,
        "close": 419.0,
        "volume": 25_000_000,
        "vol_ma20": 20_000_000,
        "ma20": 410.0,
        "ma50": 395.0,
        "ma200": 360.0,
        "prev_high20": 418.0,
        "prev_low20": 390.0,
        "prev_open": 408.0,
        "prev_high": 412.0,
        "prev_low": 402.0,
        "prev_close": 406.0,
        "atr14": 6.5,
        "atr_pct": 1.55,
        "perf_1d": 3.2,
        "perf_5d": 5.1,
        "perf_20d": 12.0,
        "date": "2026-09-04"
    }
    analysis = analyze_candidate_setup(
        stock=stock,
        group_type="long_cont",
        setup_subtype="breakout",
        spy_perf_20d=4.0
    )
    assert "candle_pattern" in analysis
    assert "candlestick_analysis" in analysis
    assert "candlestick" in analysis["evidence_json"]

    # Checklist must contain the Candlestick item
    checklist_criteria = [item["criterion"] for item in analysis["checklist"]]
    assert "Nến gần nhất & Phản ứng giá" in checklist_criteria

    # Candlestick features must have correct values
    c_features = analysis["candlestick_analysis"]["features"]
    assert c_features["close"] == 419.0
    assert c_features["date"] == "2026-09-04"

def test_signal_outcomes_candlestick_breakdown():
    # Test compute_quality_summary with setup and candle breakdowns
    data = [
        {"status": "completed", "setup_type": "pullback_ma20", "candle_pattern": "Râu dưới dài (Hammer)", "return_pct": 5.2, "excess_return_spy": 2.1, "mfe_pct": 6.0, "mae_pct": -1.0, "initial_score": 25.0},
        {"status": "completed", "setup_type": "pullback_ma20", "candle_pattern": "Râu dưới dài (Hammer)", "return_pct": 3.8, "excess_return_spy": 1.5, "mfe_pct": 4.5, "mae_pct": -0.8, "initial_score": 22.0},
        {"status": "completed", "setup_type": "pullback_ma20", "candle_pattern": "Không rõ mẫu hình", "return_pct": -1.2, "excess_return_spy": -2.0, "mfe_pct": 1.0, "mae_pct": -3.5, "initial_score": 15.0},
        {"status": "completed", "setup_type": "breakout", "candle_pattern": "Thân dài tăng (Marubozu)", "return_pct": 8.5, "excess_return_spy": 4.0, "mfe_pct": 9.2, "mae_pct": -0.5, "initial_score": 30.0},
        {"status": "pending", "setup_type": "breakout", "candle_pattern": "Thân dài tăng (Marubozu)", "return_pct": None, "excess_return_spy": None, "mfe_pct": None, "mae_pct": None, "initial_score": 28.0},
    ]
    df_outcomes = pd.DataFrame(data)
    summary = compute_quality_summary(df_outcomes)

    assert summary["total_signals"] == 5
    assert summary["completed"] == 4
    assert summary["pending"] == 1

    # Candle breakdown
    candle_df = summary["candle_breakdown"]
    assert not candle_df.empty
    assert "Mẫu Nến" in candle_df.columns
    hammer_row = candle_df[candle_df["Mẫu Nến"] == "Râu dưới dài (Hammer)"]
    assert len(hammer_row) == 1
    assert hammer_row.iloc[0]["Mẫu"] == 2
    assert hammer_row.iloc[0]["Tỷ lệ thắng (%)"] == 100.0

    # Setup + Candle breakdown
    setup_candle_df = summary["setup_candle_breakdown"]
    assert not setup_candle_df.empty
    assert "Setup" in setup_candle_df.columns
    assert "Mẫu Nến" in setup_candle_df.columns

    # Verify filtering: For pullback_ma20, Hammer returns > 0 vs Standard bar returns < 0
    pb_hammer = setup_candle_df[(setup_candle_df["Setup"] == "pullback_ma20") & (setup_candle_df["Mẫu Nến"] == "Râu dưới dài (Hammer)")]
    pb_std = setup_candle_df[(setup_candle_df["Setup"] == "pullback_ma20") & (setup_candle_df["Mẫu Nến"] == "Không rõ mẫu hình")]
    assert pb_hammer.iloc[0]["Lợi suất TB (%)"] > pb_std.iloc[0]["Lợi suất TB (%)"]

def test_candidate_card_rendering_resilience_and_no_name_error():
    from app.components.candidate_cards import render_candidate_card
    # Candidate with empty fa_flags
    cand_empty_fa = {
        "symbol": "TEST_SYM",
        "company_name": "Test Company",
        "close_price": 150.0,
        "perf_1d": 1.5,
        "perf_5d": 3.0,
        "perf_20d": 7.0,
        "status": "setup",
        "fa_flags": {},
        "technical_reasons": ["Test breakout"]
    }
    # Both calls must execute without NameError (repo=None and repo=MockRepo)
    class MockRepo:
        def get_fundamentals(self, symbols):
            return pd.DataFrame()
    
    render_candidate_card(cand_empty_fa, as_of="2026-09-04", repo=None)
    render_candidate_card(cand_empty_fa, as_of="2026-09-04", repo=MockRepo())

def test_point_in_time_fa_evaluation_no_lookahead():
    from analytics.company_fa import evaluate_fa_flags
    fa_row = {
        "symbol": "XYZ",
        "next_earnings_date": "2026-09-15",
        "revenue_growth": 0.25,
        "earnings_growth": 0.30
    }
    # Relative to 2026-09-01 -> exactly 14 days
    res_sep1 = evaluate_fa_flags("XYZ", fa_row, ref_date="2026-09-01")
    assert res_sep1["days_to_earnings"] == 14
    assert res_sep1["warning_level"] == "high"  # imminent <= 14 days

    # Relative to 2026-08-01 -> exactly 45 days
    res_aug1 = evaluate_fa_flags("XYZ", fa_row, ref_date="2026-08-01")
    assert res_aug1["days_to_earnings"] == 45
    assert res_aug1["warning_level"] == "normal"  # > 14 days

def test_signal_streak_preserves_inception_candle_pattern():
    # Day 1: Signal appears with Hammer
    cand_day1 = [{
        "symbol": "NVDA",
        "setup_type": "pullback_ma20",
        "group_type": "long_cont",
        "close_price": 120.0,
        "score": 25.0,
        "candle_pattern": "Râu dưới dài (Hammer)"
    }]
    records1 = process_signal_streaks("2026-09-01", "v2", cand_day1, active_signals=[])
    assert records1[0]["candle_pattern"] == "Râu dưới dài (Hammer)"
    assert records1[0]["streak_count"] == 1

    # Day 2: Signal continues, but day 2 candle is Inside bar
    cand_day2 = [{
        "symbol": "NVDA",
        "setup_type": "pullback_ma20",
        "group_type": "long_cont",
        "close_price": 122.0,
        "score": 26.0,
        "candle_pattern": "Inside bar"
    }]
    records2 = process_signal_streaks("2026-09-02", "v2", cand_day2, active_signals=records1)
    assert len(records2) == 1
    assert records2[0]["streak_count"] == 2
    # Inception pattern MUST remain Hammer, NOT overwritten by Inside bar!
    assert records2[0]["candle_pattern"] == "Râu dưới dài (Hammer)"

def test_candlestick_hammer_rejects_long_upper_shadow():
    # Bar with lower shadow = 55%, but upper shadow = 30% (high-wave bar, NOT a true hammer, body = 15%)
    # Range = 100, Open = 55, High = 100, Low = 0, Close = 70
    # Lower shadow = 55 (55%), Upper shadow = 30 (30%), Body = 15 (15%), Close pos = 70%
    res = analyze_candlestick(open_p=55.0, high_p=100.0, low_p=0.0, close_p=70.0)
    assert res["pattern"] != "Râu dưới dài (Hammer)"
    assert res["pattern"] == "Không rõ mẫu hình"

def test_candlestick_zero_range_flat_halt_bar():
    # Flat bar: Open = High = Low = Close
    res = analyze_candlestick(open_p=50.0, high_p=50.0, low_p=50.0, close_p=50.0)
    assert res["range"] == 0.0
    assert res["body_ratio"] == 0.0
    assert res["pattern"] == "Không rõ mẫu hình"
    assert res["direction"] == "Cân bằng"

def test_multi_session_pressure_profile():
    from analytics.setup_analyzer import analyze_multi_session_pressure
    # 10 bars of synthetic data
    dates = pd.date_range("2026-08-20", periods=10, freq="B")
    # Bullish scenario: prices closing near highs, strong returns, elevated volume
    df_bull = pd.DataFrame({
        "date": dates,
        "symbol": "BULL",
        "open": [100 + i for i in range(10)],
        "high": [102 + i for i in range(10)],
        "low": [99 + i for i in range(10)],
        "close": [101.8 + i for i in range(10)], # closes near high
        "volume": [1_000_000 + i * 100_000 for i in range(10)],
        "vol_ma20": [800_000] * 10
    })
    res_bull = analyze_multi_session_pressure(df_bull, as_of="2026-09-02")
    assert "Phe mua" in res_bull["pressure_bias"] or "Mua" in res_bull["pressure_bias"]
    assert len(res_bull["sessions"]) == 5
    assert len(res_bull["supporting_evidence"]) > 0
    assert "contradicting_evidence" in res_bull
    assert "neutral_gaps" in res_bull
    assert res_bull["methodology_note"] != ""

def test_intra_week_forward_outcomes_and_week_close():
    # Signals:
    # 1) Detected on Thursday 2026-08-27 -> Entry Friday 2026-08-28.
    #    Since Friday is end-of-week, week-close (99) has no remaining intra-week window -> 'no_window_in_week'!
    # 2) Detected on Friday 2026-08-21 -> Entry Monday 2026-08-24.
    #    Week-close window runs Mon 24 to Fri 28 -> 'completed'!
    dates = pd.date_range("2026-08-17", "2026-09-04", freq="B")
    spy_records = []
    sym_records = []
    for d in dates:
        spy_records.append({
            "date": d,
            "symbol": "SPY",
            "open": 500.0,
            "high": 505.0,
            "low": 498.0,
            "close": 502.0,
            "volume": 50_000_000
        })
        sym_records.append({
            "date": d,
            "symbol": "AAPL",
            "open": 150.0,
            "high": 155.0,
            "low": 149.0,
            "close": 153.0,
            "volume": 10_000_000
        })
    df_bars = pd.DataFrame(spy_records + sym_records)

    signals = [
        {
            "id": 1,
            "signal_key": "2026-08-27:AAPL:breakout_20d",
            "symbol": "AAPL",
            "side": "long",
            "first_detected_date": "2026-08-27",
            "setup_type": "breakout_20d",
            "initial_atr": 3.0,
            "candle_pattern": "Thân dài vượt cản"
        },
        {
            "id": 2,
            "signal_key": "2026-08-21:AAPL:breakout_20d",
            "symbol": "AAPL",
            "side": "long",
            "first_detected_date": "2026-08-21",
            "setup_type": "breakout_20d",
            "initial_atr": 3.0,
            "candle_pattern": "Thân dài vượt cản"
        }
    ]

    outcomes = evaluate_signal_outcomes(signals, df_bars, horizons=[1, 2, 3, 4, 99, 5])
    assert len(outcomes) > 0

    # Check signal 1 (entry Friday 2026-08-28):
    s1_wc = [o for o in outcomes if o["signal_id"] == 1 and o["horizon_days"] == 99]
    assert len(s1_wc) == 1
    assert s1_wc[0]["status"] == "no_window_in_week"
    assert s1_wc[0]["entry_day_of_week"] == "Thứ Sáu (T6)"

    # Check signal 2 (entry Monday 2026-08-24):
    s2_wc = [o for o in outcomes if o["signal_id"] == 2 and o["horizon_days"] == 99]
    assert len(s2_wc) == 1
    assert s2_wc[0]["status"] == "completed"
    assert s2_wc[0]["entry_day_of_week"] == "Thứ Hai (T2)"
    assert s2_wc[0]["exit_date"] == "2026-08-28"

    # Check quality summary with breakdowns
    summary = compute_quality_summary(pd.DataFrame(outcomes))
    assert summary["no_window_count"] >= 1
    assert "weekday_breakdown" in summary
    assert "side_breakdown" in summary
    assert not summary["weekday_breakdown"].empty
    assert not summary["side_breakdown"].empty

def test_market_status_and_session_age():
    from analytics.market_calendar import get_market_status_now, compute_session_age
    from zoneinfo import ZoneInfo
    from datetime import datetime

    tz_et = ZoneInfo("America/New_York")
    
    # 1. Saturday noon
    sat_noon = datetime(2026, 9, 12, 12, 0, tzinfo=tz_et)
    status_sat = get_market_status_now(ref_time=sat_noon)
    assert not status_sat["is_open"]
    assert status_sat["status_phase"] == "weekend"
    assert "Cuối tuần" in status_sat["status_badge"]

    # 2. Wednesday 11:00 AM (Regular trading)
    wed_trade = datetime(2026, 9, 9, 11, 0, tzinfo=tz_et)
    status_wed = get_market_status_now(ref_time=wed_trade)
    assert status_wed["is_open"]
    assert status_wed["status_phase"] == "regular"
    assert "Đang giao dịch" in status_wed["status_badge"]

    # 3. Session age: identical to target session
    age_latest = compute_session_age("2026-09-08", ref_time=wed_trade)
    # Target session for Wed 11am (open) is Tuesday 2026-09-08
    assert age_latest["target_session"] == "2026-09-08"
    assert age_latest["lag_sessions"] == 0
    assert age_latest["is_latest"]

    # 4. Session age: lagging 2 sessions
    age_lag = compute_session_age("2026-09-03", ref_time=wed_trade)
    assert age_lag["lag_sessions"] > 0
    assert not age_lag["is_latest"]

def test_signal_outcomes_entry_date_and_price_populated():
    """Verify entry_date, entry_price, and spy_entry_price are returned on outcomes."""
    dates = pd.date_range("2026-08-17", "2026-08-28", freq="B")
    bars = []
    for d in dates:
        bars.append({"date": d, "symbol": "SPY", "open": 500.0, "high": 505.0, "low": 495.0, "close": 502.0, "volume": 1000})
        bars.append({"date": d, "symbol": "XYZ", "open": 100.0, "high": 105.0, "low": 98.0, "close": 103.0, "volume": 1000})
    df_bars = pd.DataFrame(bars)

    signals = [{
        "id": 10,
        "signal_key": "2026-08-17:XYZ:breakout_20d",
        "symbol": "XYZ",
        "side": "long",
        "first_detected_date": "2026-08-17",
        "setup_type": "breakout_20d",
        "initial_atr": 2.0
    }]

    outcomes = evaluate_signal_outcomes(signals, df_bars, horizons=[1, 2, 99])
    assert len(outcomes) == 3
    for o in outcomes:
        assert o["entry_date"] == "2026-08-18"
        assert o["entry_price"] == 100.0
        assert o["spy_entry_price"] == 500.0

def test_update_signal_entry_info_and_persistence(tmp_path):
    """Verify update_signal_entry_info properly persists resolved entry prices to SQLite."""
    from storage.database import init_db
    from storage.repository import MarketRadarRepository

    db_file = str(tmp_path / "test_entry.db")
    init_db(db_file)
    repo = MarketRadarRepository(db_file)

    # Insert a new signal without entry info
    sig = {
        "signal_key": "2026-08-17:TEST:breakout_20d",
        "symbol": "TEST",
        "company_name": "Test Co",
        "sector": "Tech",
        "sub_industry": "Software",
        "side": "long",
        "group_type": "long_breakout",
        "setup_type": "breakout_20d",
        "rule_version": "v2",
        "first_detected_date": "2026-08-17",
        "latest_detected_date": "2026-08-17",
        "streak_count": 1,
        "status": "active",
        "initial_close": 50.0,
        "initial_atr": 1.5,
        "candle_pattern": "Thân dài vượt cản"
    }
    repo.upsert_signal_records([sig])
    records = repo.get_signal_records(symbol="TEST")
    assert len(records) == 1
    sig_id = records[0]["id"]
    assert records[0]["entry_date"] is None
    assert records[0]["entry_price"] is None

    # Update entry info
    ok = repo.update_signal_entry_info(sig_id, "2026-08-18", 51.5, spy_entry_price=500.0)
    assert ok

    updated_records = repo.get_signal_records(symbol="TEST")
    assert updated_records[0]["entry_date"] == "2026-08-18"
    assert updated_records[0]["entry_price"] == 51.5
    assert updated_records[0]["spy_entry_price"] == 500.0

    # Save an outcome and check get_signal_outcomes joins entry info
    outcome = {
        "signal_id": sig_id,
        "signal_key": "2026-08-17:TEST:breakout_20d",
        "symbol": "TEST",
        "horizon_days": 1,
        "status": "completed",
        "exit_date": "2026-08-18",
        "exit_price": 52.0,
        "return_pct": 0.97,
        "spy_return_pct": 0.2,
        "excess_return_spy": 0.77,
        "entry_day_of_week": "Thứ Ba (T3)",
        "horizon_label": "1 phiên"
    }
    repo.save_signal_outcomes([outcome])

    df_outcomes = repo.get_signal_outcomes(horizon_days=1)
    assert not df_outcomes.empty
    row = df_outcomes.iloc[0]
    assert row["entry_date"] == "2026-08-18"
    assert row["entry_price"] == 51.5
    assert row["spy_entry_price"] == 500.0

def test_stale_fa_detection_over_180_days():
    """Verify evaluate_fa_flags identifies reports older than 180 days as stale."""
    from analytics.company_fa import evaluate_fa_flags

    fa_stale = {
        "pe_ratio": 15.0,
        "revenue_growth": 0.25,
        "eps_growth": 0.30,
        "profit_margin": 0.20,
        "reported_date": "2025-12-31", # over 200 days from 2026-09-01
        "fiscal_period": "2025-Q4",
        "period_type": "quarterly",
        "data_status": "verified"
    }
    res = evaluate_fa_flags("OLD", fa_stale, ref_date="2026-09-01")
    assert res["is_stale"] is True
    assert res["warning_level"] == "medium"
    assert any("BCTC đã cũ" in f for f in res["flags"])

    # Fresh FA within 60 days
    fa_fresh = dict(fa_stale)
    fa_fresh["reported_date"] = "2026-07-31"
    res_fresh = evaluate_fa_flags("FRESH", fa_fresh, ref_date="2026-09-01")
    assert res_fresh["is_stale"] is False

def test_yfinance_parse_date_or_ts_variations():
    """Verify _parse_date_or_ts parses integer timestamps, ISO strings, and Pandas Timestamps."""
    from providers.yfinance_provider import _parse_date_or_ts

    # 1. Unix timestamp (1719705600 = 2024-06-30 UTC)
    dt1 = _parse_date_or_ts(1719705600)
    assert dt1 is not None
    assert dt1.year == 2024

    # 2. ISO string
    dt2 = _parse_date_or_ts("2026-06-30")
    assert dt2 is not None
    assert dt2.year == 2026 and dt2.month == 6 and dt2.day == 30

    # 3. Pandas Timestamp
    dt3 = _parse_date_or_ts(pd.Timestamp("2026-08-15"))
    assert dt3 is not None
    assert dt3.year == 2026 and dt3.month == 8 and dt3.day == 15

    # 4. None or invalid
    assert _parse_date_or_ts(None) is None
    assert _parse_date_or_ts("invalid-date-string") is None

def test_short_setup_extended_downward_warning():
    """Verify interpret_candlestick_in_setup warns when short setup is extended far below MA20."""
    candle = {
        "date": "2026-09-04",
        "pattern": "Thân dài giảm (Marubozu)",
        "direction": "Giảm",
        "close_position_label": "Đóng cửa gần đáy phiên",
        "close_position_pct": 10.0,
        "range_to_atr": 1.8
    }
    interp = interpret_candlestick_in_setup(
        candle=candle,
        setup_subtype="breakdown_20d",
        group_type="short_breakdown",
        close_price=80.0,
        ma20=100.0,
        dist_ma20_atr=-2.5
    )
    assert interp["reaction_status"] == "fail"
    assert "bán đuổi" in interp["reaction_summary"] or "giảm quá xa MA20" in interp["context_summary"]




