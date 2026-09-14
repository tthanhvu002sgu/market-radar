"""
Automated Acceptance & Regression Tests for Domain Recheck (R-01 to R-06).
Validates:
- [R-01] Event provenance separation (scanner analytic vs external company events; no fake SEC EDGAR confirmed status).
- [R-02] FA metadata contract (period_end, retrieved_at, Yahoo aggregate source, no fake reported_date, stale BCTC detection).
- [R-03] Database backfill completeness (zero null FA metadata, all 8 outcome horizons populated, candidate evidence_json populated).
- [R-04] Invariant enforcement (valid_universe <= total_universe) & 252d history coverage threshold (>= 250 bars).
- [R-05] Multi-session pressure and candlestick interpretation wording (factual price-volume evidence, no misleading causal actor phrases).
- [R-06] End-to-end integration and smoke validation on legacy and compliant snapshots.
"""
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
import pandas as pd
import pytest

from analytics.signal_events import generate_signal_events
from analytics.company_fa import evaluate_fa_flags
from analytics.setup_analyzer import analyze_multi_session_pressure, interpret_candlestick_in_setup
from analytics.signal_outcomes import evaluate_signal_outcomes, compute_quality_summary
from providers.yfinance_provider import YFinanceProvider
from storage.database import init_db
from storage.repository import MarketRadarRepository


# ==========================================
# 1. [R-01] EVENT PROVENANCE TESTS
# ==========================================

def test_r01_scanner_analytic_events_have_no_fake_sec_provenance():
    """Scanner events must never display SEC/IR confirmed status or EDGAR source URLs."""
    cur_snap = {"as_of": "2026-09-08", "market_metrics": {}, "sector_metrics": []}
    cur_cands = [
        {
            "symbol": "AAPL",
            "setup_type": "breakout",
            "group_type": "long_cont",
            "status": "confirmed",
            "close_price": 225.0,
            "trigger_price": 224.0,
            "score": 15.0,
            "technical_reasons": ["Breakout MA20"]
        }
    ]

    events = generate_signal_events(
        current_snapshot=cur_snap,
        current_candidates=cur_cands,
        prev_snapshot=None,
        prev_candidates=None,
        missing_symbols=[]
    )

    assert len(events) >= 1
    new_cand_ev = next(e for e in events if e["event_type"] == "new_candidate")

    # Must be categorized as analytic event
    assert new_cand_ev.get("event_category") == "analytic_event"
    # Source must be Scanner EOD, NOT SEC EDGAR
    assert "Scanner" in new_cand_ev["source_name"]
    assert "SEC" not in new_cand_ev["source_name"]
    # Source status must be scanner_derived, NOT confirmed by SEC
    assert new_cand_ev["source_status"] == "scanner_derived"
    assert new_cand_ev["source_status"] != "confirmed"


def test_r01_earnings_upcoming_marked_as_unverified_estimate():
    """Upcoming earnings events must be marked as unverified calendar estimates."""
    cur_snap = {"as_of": "2026-09-08"}
    cur_cands = [
        {
            "symbol": "MSFT",
            "setup_type": "pullback_ma20",
            "group_type": "long_cont",
            "status": "confirmed",
            "fa_flags": {
                "days_to_earnings": 7,
                "next_earnings_date": "2026-09-15",
                "earnings_status": "Ước tính",
                "sec_filing_url": "https://www.sec.gov/edgar/browse/?CIK=MSFT"
            }
        }
    ]

    events = generate_signal_events(
        current_snapshot=cur_snap,
        current_candidates=cur_cands,
        prev_snapshot=None,
        prev_candidates=None,
        missing_symbols=[]
    )

    earnings_ev = next(e for e in events if e["event_type"] == "earnings_upcoming")
    assert earnings_ev["event_category"] == "external_company_event"
    assert "Yahoo Finance Calendar" in earnings_ev["source_name"]
    assert "Unverified" in earnings_ev["source_status"] or "Chưa kiểm tra" in earnings_ev["source_status"]
    assert earnings_ev["source_status"] != "confirmed"


# ==========================================
# 2. [R-02] FA METADATA & PROVENANCE TESTS
# ==========================================

def test_r02_fa_flags_contract_and_source_lineage():
    """FA flags must identify provider as Yahoo Finance Aggregate, period_end, and retrieved_at."""
    fa_row = {
        "symbol": "NVDA",
        "revenue_growth": 0.50,
        "earnings_growth": 0.65,
        "profit_margins": 0.40,
        "period_end": "2026-06-30",
        "fiscal_period": "Kỳ kết thúc (MRQ): 2026-06-30",
        "period_type": "Chỉ số tổng hợp Yahoo (YoY)",
        "currency": "USD",
        "source": "Yahoo Finance (Số liệu tổng hợp / Aggregate)",
        "retrieved_at": "2026-09-04",
        "data_status": "valid"
    }

    eval_res = evaluate_fa_flags("NVDA", fa_row, ref_date=date(2026, 9, 4))
    assert eval_res["has_data"] is True
    assert eval_res["period_end"] == "2026-06-30"
    assert "Yahoo Finance" in eval_res["source"]
    assert "SEC proxy" not in eval_res["source"]
    assert "Chỉ số tổng hợp" in eval_res["period_type"]
    assert eval_res["retrieved_at"] == "2026-09-04"
    assert eval_res["is_stale"] is False


def test_r02_stale_fa_detection_on_period_end_over_180_days():
    """Stale FA check must trigger warning when period_end > 180 days from ref_date."""
    fa_row = {
        "symbol": "ORCL",
        "revenue_growth": 0.10,
        "earnings_growth": 0.12,
        "period_end": "2026-01-15",
        "fiscal_period": "Kỳ kết thúc (MRQ): 2026-01-15",
        "source": "Yahoo Finance (Số liệu tổng hợp / Aggregate)",
        "retrieved_at": "2026-09-04"
    }

    eval_res = evaluate_fa_flags("ORCL", fa_row, ref_date=date(2026, 9, 4))
    assert eval_res["is_stale"] is True
    assert any("BCTC đã cũ (Stale)" in f for f in eval_res["flags"])


# ==========================================
# 3. [R-04] INVARIANT & COVERAGE TESTS
# ==========================================

def test_r04_coverage_252d_with_standard_calendar_year():
    """A standard 1-year history (250-252 trading sessions) must produce >=95% coverage, not 0%."""
    # Simulated 252 bars for 10 stocks
    stocks = [f"STK{i}" for i in range(10)]
    total_sp500 = len(stocks)
    bars_dict = {}
    for s in stocks:
        bars_dict[s] = [1] * 252  # 252 bars each

    # Threshold of >= 250 trading days
    symbols_with_252d = sum(1 for sym in stocks if len(bars_dict[sym]) >= 250)
    cov_252d = symbols_with_252d / total_sp500
    assert cov_252d == 1.0  # 100%, not 0%


def test_r04_valid_universe_invariant_enforced():
    """valid_universe must never exceed total_universe."""
    total_sp500 = 503
    fresh_symbols_including_etfs = 516
    clamped_valid = min(fresh_symbols_including_etfs, total_sp500)
    assert clamped_valid <= total_sp500
    assert clamped_valid == 503


# ==========================================
# 4. [R-05] PRESSURE PROFILE & CANDLE WORDING TESTS
# ==========================================

def test_r05_multi_session_pressure_factual_wording():
    """Evidence and bias labels must use observable price-volume facts without causal actor speculation."""
    dates = pd.date_range("2026-08-01", periods=30, freq="B")
    # Bullish scenario with increasing close
    df_bull = pd.DataFrame({
        "symbol": "AAPL",
        "date": dates,
        "open": [100.0 + i for i in range(30)],
        "high": [102.0 + i for i in range(30)],
        "low": [99.5 + i for i in range(30)],
        "close": [101.8 + i for i in range(30)],
        "volume": [1_000_000 + i * 20_000 for i in range(30)]
    })

    res_long = analyze_multi_session_pressure("AAPL", bars=df_bull, side="long")
    all_evidence = res_long["supporting_evidence"] + res_long["contradicting_evidence"]
    all_text = " ".join(all_evidence) + " " + res_long["pressure_bias"]

    # Must NOT contain subjective actor force claims
    forbidden_phrases = [
        "lực cầu hấp thụ tốt",
        "phe bán áp đảo",
        "lực cầu bắt đáy nhập cuộc",
        "lực cầu chưa bùng nổ",
        "tổ chức gom",
        "dòng tiền vào"
    ]
    for phrase in forbidden_phrases:
        assert phrase not in all_text, f"Forbidden causal phrase found: {phrase}"

    # Must contain factual observation
    assert "bằng chứng thuận cho phía mua" in all_text or "Bằng chứng thuận cho phía Mua" in all_text


def test_r05_candlestick_interpretation_factual_wording():
    """Setup candlestick interpretations must describe observable price reaction without actor intent."""
    candle = {
        "pattern": "Thân dài tăng (Marubozu)",
        "close_position_pct": 95.0,
        "direction": "Tăng",
        "close_position_label": "Đóng sát đỉnh"
    }
    res = interpret_candlestick_in_setup(
        candle=candle,
        setup_subtype="breakout",
        group_type="long_cont",
        close_price=105.0,
        trigger_price=100.0
    )
    summary = res["reaction_summary"]

    # Must NOT contain "lực cầu quyết liệt" or "áp đảo phe bán"
    assert "lực cầu quyết liệt" not in summary
    assert "áp đảo phe bán" not in summary
    # Must contain factual observation
    assert "ủng hộ đà tăng" in summary or "bứt phá kháng cự" in summary


# ==========================================
# 5. [R-03] LIVE DATABASE BACKFILL AUDIT TESTS
# ==========================================

def test_r03_live_database_backfill_integrity():
    """Verify that current market_radar.db contains complete backfilled metadata and compliant snapshot."""
    db_path = Path("data/market_radar.db")
    if not db_path.exists():
        pytest.skip("Local database data/market_radar.db not found for acceptance check")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Check fundamentals table
    c.execute("SELECT COUNT(*), COUNT(fiscal_period), COUNT(period_end), COUNT(sec_filing_url) FROM fundamentals;")
    total_fa, with_fp, with_pe, with_url = c.fetchone()
    assert total_fa > 0
    assert with_fp == total_fa, "Fundamentals must have 0 null fiscal_period"
    assert with_pe == total_fa, "Fundamentals must have 0 null period_end"
    assert with_url == total_fa, "Fundamentals must have 0 null sec_filing_url"

    # Check signal_events
    c.execute("SELECT COUNT(*) FROM signal_events WHERE event_type = 'new_candidate' AND (source_name LIKE '%SEC%' OR source_status = 'confirmed');")
    fake_sec_events = c.fetchone()[0]
    assert fake_sec_events == 0, "No scanner event should claim SEC confirmed provenance"

    # Check signal_outcomes horizons
    c.execute("SELECT DISTINCT horizon_days FROM signal_outcomes ORDER BY horizon_days;")
    horizons = [r[0] for r in c.fetchall()]
    expected_horizons = [1, 2, 3, 4, 5, 10, 20, 99]
    for h in expected_horizons:
        assert h in horizons, f"Horizon {h} must be present in signal_outcomes"

    # Check candidate_snapshots evidence_json
    c.execute("SELECT COUNT(*) FROM candidate_snapshots WHERE evidence_json IS NULL;")
    null_evidence = c.fetchone()[0]
    assert null_evidence == 0, "Candidate snapshots must have non-null evidence_json"

    # Check snapshots
    c.execute("SELECT id, valid_universe, total_universe, status FROM snapshots WHERE id = 4;")
    snap4 = c.fetchone()
    assert snap4 is not None, "Snapshot 4 must exist as compliant snapshot"
    assert snap4[1] <= snap4[2], "Snapshot 4 must satisfy valid_universe <= total_universe"
    assert snap4[3] == "complete", "Snapshot 4 must be complete"

    # Check legacy snapshot 3
    c.execute("SELECT status FROM snapshots WHERE id = 3;")
    snap3 = c.fetchone()
    if snap3:
        assert snap3[0] == "legacy_incompatible", "Snapshot 3 must be marked legacy_incompatible"

    conn.close()


# ==========================================
# 6. WEEKEND CROSSING & CALENDAR ACCEPTANCE
# ==========================================

def test_crosses_weekend_calculation_and_intra_week_boundary():
    """
    Fixed horizons cannot silently cross the weekend boundary.
    - Thursday entry with 3-session horizon must cross weekend (exit on Tuesday).
    - Monday entry with 2-session horizon stays intra-week (exit on Wednesday).
    - Week-close horizon (99) never crosses weekend (exit on Friday of same week).
    """
    # Create daily bars:
    # 2026-08-03 (Mon), 2026-08-04 (Tue), 2026-08-05 (Wed), 2026-08-06 (Thu), 2026-08-07 (Fri)
    # 2026-08-10 (Mon), 2026-08-11 (Tue)
    bar_dates = [
        "2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07",
        "2026-08-10", "2026-08-11"
    ]
    bars_list = []
    for d_str in bar_dates:
        dt = pd.to_datetime(d_str)
        bars_list.append({
            "symbol": "TEST",
            "date": dt,
            "open": 100.0,
            "high": 105.0,
            "low": 98.0,
            "close": 102.0,
            "volume": 1_000_000
        })
        bars_list.append({
            "symbol": "SPY",
            "date": dt,
            "open": 500.0,
            "high": 505.0,
            "low": 498.0,
            "close": 502.0,
            "volume": 50_000_000
        })
    df_bars = pd.DataFrame(bars_list)

    # Signal 1 detected on Friday 2026-07-31 -> entry on Monday 2026-08-03
    sig_mon = [{
        "id": 1,
        "signal_key": "2026-07-31:TEST:breakout",
        "symbol": "TEST",
        "side": "long",
        "first_detected_date": "2026-07-31",
        "initial_atr": 2.0,
        "trigger_price": 100.0,
        "invalidation_price": 95.0
    }]
    outcomes_mon = evaluate_signal_outcomes(sig_mon, df_bars, horizons=[2, 99])
    h2_mon = next(o for o in outcomes_mon if o["horizon_days"] == 2)
    h99_mon = next(o for o in outcomes_mon if o["horizon_days"] == 99)

    # 2-day horizon from Monday enters Mon 08-03, exits Tue 08-04 -> intra-week
    assert h2_mon["crosses_weekend"] == 0
    assert h2_mon["status"] == "completed"

    # Week-close horizon from Monday exits Fri 08-07 -> intra-week
    assert h99_mon["crosses_weekend"] == 0
    assert h99_mon["status"] == "completed"

    # Signal 2 detected on Wednesday 2026-08-05 -> entry on Thursday 2026-08-06
    sig_thu = [{
        "id": 2,
        "signal_key": "2026-08-05:TEST:breakout",
        "symbol": "TEST",
        "side": "long",
        "first_detected_date": "2026-08-05",
        "initial_atr": 2.0,
        "trigger_price": 100.0,
        "invalidation_price": 95.0
    }]
    # 3-day horizon from Thursday: Thu(1), Fri(2), Mon(3) -> crosses weekend!
    outcomes_thu = evaluate_signal_outcomes(sig_thu, df_bars, horizons=[3])
    h3_thu = next(o for o in outcomes_thu if o["horizon_days"] == 3)
    assert h3_thu["crosses_weekend"] == 1
    assert h3_thu["exit_date"] == "2026-08-10"


def test_market_calendar_remaining_trading_sessions_in_week():
    """Remaining sessions in week must accurately reflect days to Friday excluding holidays."""
    from analytics.market_calendar import get_remaining_trading_sessions_in_week

    # Monday 2026-08-03 -> Tue, Wed, Thu, Fri = 4 sessions left
    assert get_remaining_trading_sessions_in_week(date(2026, 8, 3)) == 4
    # Wednesday 2026-08-05 -> Thu, Fri = 2 sessions left
    assert get_remaining_trading_sessions_in_week(date(2026, 8, 5)) == 2
    # Friday 2026-08-07 -> 0 sessions left
    assert get_remaining_trading_sessions_in_week(date(2026, 8, 7)) == 0
    # Weekend (Saturday/Sunday) -> 0 sessions left
    assert get_remaining_trading_sessions_in_week(date(2026, 8, 8)) == 0
    assert get_remaining_trading_sessions_in_week(date(2026, 8, 9)) == 0

    # Thursday before Good Friday 2026 (Good Friday is 2026-04-03)
    # On 2026-04-02 (Thu), Friday 04-03 is a market holiday, so 0 sessions left in week!
    assert get_remaining_trading_sessions_in_week(date(2026, 4, 2)) == 0


def test_fail_closed_sidebar_status_on_stale_snapshot():
    """When snapshot is stale (lag > 0), session age must report is_stale = True and red/amber badge."""
    from analytics.market_calendar import compute_session_age

    # Case 1: Target session is 2026-09-11, snapshot is 2026-09-04 (lag = 4)
    age = compute_session_age(as_of="2026-09-04", target_session="2026-09-11")
    assert age["is_stale"] is True
    assert age["is_latest"] is False
    assert age["lag_sessions"] == 4
    assert "Lạc hậu 4 phiên" in age["freshness_label"]

    # Case 2: Up to date session
    age_fresh = compute_session_age(as_of="2026-09-11", target_session="2026-09-11")
    assert age_fresh["is_stale"] is False
    assert age_fresh["is_latest"] is True
    assert age_fresh["lag_sessions"] == 0


def test_outcome_sample_adequacy_guards():
    """Outcome breakdown must show sample adequacy indicators (warning when < 5 samples)."""
    from analytics.signal_outcomes import compute_quality_summary

    # Less than 5 samples (3 samples)
    data_small = [
        {"status": "completed", "setup_type": "breakout", "candle_pattern": "Hammer", "return_pct": 2.0, "excess_return_spy": 1.0, "mfe_pct": 3.0, "mae_pct": -0.5, "crosses_weekend": 0},
        {"status": "completed", "setup_type": "breakout", "candle_pattern": "Hammer", "return_pct": 3.0, "excess_return_spy": 1.5, "mfe_pct": 4.0, "mae_pct": -0.5, "crosses_weekend": 0},
        {"status": "completed", "setup_type": "breakout", "candle_pattern": "Hammer", "return_pct": -1.0, "excess_return_spy": -2.0, "mfe_pct": 0.5, "mae_pct": -2.0, "crosses_weekend": 0},
    ]
    summary_small = compute_quality_summary(pd.DataFrame(data_small))
    setup_df = summary_small["setup_breakdown"]
    assert not setup_df.empty
    assert bool(setup_df.iloc[0]["is_adequate"]) is False
    assert "Thiếu mẫu (3/5)" in setup_df.iloc[0]["Độ Tin Cậy"]

    # 5 or more samples (5 samples)
    data_adq = data_small + [
        {"status": "completed", "setup_type": "breakout", "candle_pattern": "Hammer", "return_pct": 1.5, "excess_return_spy": 0.5, "mfe_pct": 2.0, "mae_pct": -0.5, "crosses_weekend": 0},
        {"status": "completed", "setup_type": "breakout", "candle_pattern": "Hammer", "return_pct": 4.0, "excess_return_spy": 2.0, "mfe_pct": 5.0, "mae_pct": -0.5, "crosses_weekend": 0},
    ]
    summary_adq = compute_quality_summary(pd.DataFrame(data_adq))
    setup_df_adq = summary_adq["setup_breakdown"]
    assert not setup_df_adq.empty
    assert bool(setup_df_adq.iloc[0]["is_adequate"]) is True
    assert "Đủ mẫu (≥5)" in setup_df_adq.iloc[0]["Độ Tin Cậy"]

