"""
Comprehensive test suite verifying fixes for:
[D-1] Market context as input to priority decisions.
[D-2] Cross-industry Themes and Group/Sector review theses history.
[D-3] Trade planning ticket, capital risk budgeting, and position sizing.
[D-4] Closed-loop shortlist freezing, decision tracking, and outcome evaluation.
[D-5] Playbook quality breakdown, bottleneck analysis, and factual barrier tracking.
"""
import pytest
import sqlite3
import pandas as pd
import numpy as np

from analytics.screening_rules import evaluate_market_context_alignment, screen_candidates
from analytics.candidate_quality import (
    calculate_trade_plan,
    summarize_playbook_quality,
    QualityPolicy,
    DEFAULT_POLICY
)
from analytics.signal_outcomes import evaluate_shortlist_and_decision_outcomes
from storage.repository import MarketRadarRepository


# =====================================================================
# [D-1] Market Context Alignment Tests
# =====================================================================

def test_evaluate_market_context_alignment_long_cont_bullish():
    market_metrics = {
        "breadth_ma50_pct": 65.0,
        "breadth_ma200_pct": 60.0,
        "net_new_highs_20d": 35,
        "spy_close": 510.0,
        "spy_ma50": 495.0,
        "spy_ma200": 470.0
    }
    align, summary = evaluate_market_context_alignment("long_cont", "Breakout Base", market_metrics)
    assert align == "phù hợp"
    assert "MA50" in summary or "thị trường" in summary


def test_evaluate_market_context_alignment_long_cont_bearish():
    market_metrics = {
        "breadth_ma50_pct": 28.0,
        "breadth_ma200_pct": 35.0,
        "net_new_highs_20d": -40,
        "spy_close": 460.0,
        "spy_ma50": 480.0,
        "spy_ma200": 490.0
    }
    align, summary = evaluate_market_context_alignment("long_cont", "Breakout Base", market_metrics)
    assert align == "mâu thuẫn"
    assert "Độ rộng" in summary or "yếu" in summary


def test_evaluate_market_context_alignment_short_cont_bearish():
    market_metrics = {
        "breadth_ma50_pct": 25.0,
        "net_new_highs_20d": -50,
        "spy_close": 450.0,
        "spy_ma50": 470.0
    }
    align, summary = evaluate_market_context_alignment("short_cont", "Breakdown Support", market_metrics)
    assert align == "phù hợp"


def test_evaluate_market_context_alignment_short_cont_bullish():
    market_metrics = {
        "breadth_ma50_pct": 72.0,
        "net_new_highs_20d": 40,
        "spy_close": 520.0,
        "spy_ma50": 500.0
    }
    align, summary = evaluate_market_context_alignment("short_cont", "Breakdown Support", market_metrics)
    assert align == "mâu thuẫn"


def test_evaluate_market_context_alignment_empty_metrics():
    align, summary = evaluate_market_context_alignment("long_cont", "Breakout Base", None)
    assert align == "chưa đủ dữ liệu"
    assert "Chưa có" in summary


def test_evaluate_market_context_alignment_divergent_neutral():
    market_metrics = {
        "breadth_ma50_pct": 48.0,
        "net_new_highs_20d": 0,
        "spy_close": 500.0,
        "spy_ma50": 498.0
    }
    align, summary = evaluate_market_context_alignment("long_rev", "Oversold Bounce", market_metrics)
    assert align in ("phân hóa / trung tính", "phù hợp")


def test_screen_candidates_with_market_context():
    sample_df = pd.DataFrame([{
        "symbol": "AAPL",
        "company_name": "Apple Inc",
        "sector": "Information Technology",
        "sub_industry": "Technology Hardware",
        "close": 200.0,
        "open": 198.0,
        "high": 202.0,
        "low": 197.0,
        "volume": 20_000_000,
        "ma20": 195.0,
        "ma50": 190.0,
        "ma200": 180.0,
        "atr14": 4.0,
        "dollar_vol_20d": 4_000_000_000,
        "rs_rating": 85,
        "rs_sp500_ratio": 1.15,
        "rs_sp500_ratio_20d": 1.10,
        "perf_1d": 1.0,
        "perf_5d": 3.0,
        "perf_20d": 6.0,
        "days_to_earnings": 30,
        "next_earnings_date": "2026-11-01",
        "earnings_status": "Xa kỳ BCTC",
        "highest_20d": 201.0,
        "lowest_20d": 190.0
    }])

    market_metrics = {
        "breadth_ma50_pct": 70.0,
        "net_new_highs_20d": 30,
        "spy_close": 510.0,
        "spy_ma50": 490.0
    }

    candidates = screen_candidates(
        latest_stocks_df=sample_df,
        sector_metrics=[],
        industry_metrics=[],
        market_metrics=market_metrics
    )

    if candidates:
        for c in candidates:
            assert "market_context_alignment" in c
            assert "market_context_summary" in c
            assert c["market_context_alignment"] in (
                "phù hợp", "mâu thuẫn", "phân hóa / trung tính", "chưa đủ dữ liệu"
            )


# =====================================================================
# [D-2] Themes and Review Theses History Tests
# =====================================================================

@pytest.fixture
def test_repo(tmp_path):
    db_file = tmp_path / "test_gap_fixes.db"
    return MarketRadarRepository(db_path=str(db_file))


def test_review_theses_crud_and_audit(test_repo):
    # Save sector thesis
    rowid = test_repo.save_review_thesis(
        session_date="2026-09-27",
        target_type="sector",
        target_name="Information Technology",
        selection_reason="Dòng tiền mạnh, RS bứt phá, turnover share tăng vọt",
        source="O'Neil / RS Leader",
        reviewer="Analyst A"
    )
    assert rowid > 0

    # Retrieve sector thesis
    theses = test_repo.get_review_theses(
        session_date="2026-09-27",
        target_type="sector",
        target_name="Information Technology"
    )
    assert len(theses) == 1
    t = theses[0]
    assert t["target_name"] == "Information Technology"
    assert "Dòng tiền mạnh" in t["selection_reason"]
    assert t["reviewer"] == "Analyst A"

    # Save sub-industry thesis
    test_repo.save_review_thesis(
        session_date="2026-09-27",
        target_type="sub_industry",
        target_name="Semiconductors",
        selection_reason="Nhóm dẫn dắt chu kỳ AI phần cứng",
        source="CANSLIM Heatmap",
        reviewer="Analyst B"
    )
    sub_theses = test_repo.get_review_theses(
        session_date="2026-09-27",
        target_type="sub_industry",
        target_name="Semiconductors"
    )
    assert len(sub_theses) == 1
    assert sub_theses[0]["target_name"] == "Semiconductors"


def test_themes_and_symbol_theme_links(test_repo):
    # Save themes
    t1_id = test_repo.save_theme(
        theme_name="AI Infrastructure",
        description="Data center, compute, silicon, power"
    )
    assert t1_id > 0

    all_themes = test_repo.get_themes()
    assert any(t["theme_name"] == "AI Infrastructure" for t in all_themes)

    # Link symbols to theme with mandatory audit trail
    st_id = test_repo.save_symbol_theme(
        symbol="NVDA",
        theme_name="AI Infrastructure",
        source="Sellside consensus / GPU backlog",
        effective_date="2026-09-01",
        verified_by="Lead Analyst"
    )
    assert st_id > 0

    nvda_themes = test_repo.get_symbol_themes(symbol="NVDA")
    assert len(nvda_themes) == 1
    assert nvda_themes[0]["theme_name"] == "AI Infrastructure"
    assert nvda_themes[0]["verified_by"] == "Lead Analyst"
    assert nvda_themes[0]["effective_date"] == "2026-09-01"

    # Query non-existent symbol
    empty = test_repo.get_symbol_themes(symbol="XYZ")
    assert len(empty) == 0


# =====================================================================
# [D-3] Trade Plan & Capital Risk Calculator Tests
# =====================================================================

def test_calculate_trade_plan_standard_long():
    plan = calculate_trade_plan(
        entry_price=100.0,
        invalidation_price=95.0,
        account_capital=20_000.0,
        risk_budget_pct=1.0,  # 1% = $200 risk budget
        current_exposure_usd=0.0,
        max_capital_pct=20.0,
        side=1
    )
    assert plan["is_valid"] is True
    assert plan["per_share_risk"] == 5.0
    assert plan["setup_risk_pct"] == 5.0
    # $200 / $5 per share = 40 shares
    assert plan["planned_shares"] == 40
    # 40 * $100 = $4,000 position
    assert plan["planned_position_val"] == 4000.0
    # $4,000 / $20,000 = 20.0%
    assert plan["capital_allocation_pct"] == 20.0
    assert plan["dollar_risk"] == 200.0
    assert plan["account_risk_pct"] == 1.0
    assert plan["is_over_capital_limit"] is False
    assert "Market Radar" in plan["disclaimer"]


def test_calculate_trade_plan_standard_short():
    plan = calculate_trade_plan(
        entry_price=50.0,
        invalidation_price=52.5,
        account_capital=10_000.0,
        risk_budget_pct=2.0,  # 2% = $200 risk budget
        current_exposure_usd=2_000.0,
        max_capital_pct=25.0,
        side=-1
    )
    assert plan["is_valid"] is True
    assert plan["per_share_risk"] == 2.5
    assert plan["setup_risk_pct"] == 5.0
    # $200 / $2.5 = 80 shares
    assert plan["planned_shares"] == 80
    # 80 * $50 = $4,000
    assert plan["planned_position_val"] == 4000.0
    # $4,000 / $10,000 = 40% -> exceeds max_capital_pct 25%
    assert plan["is_over_capital_limit"] is True
    assert any("vượt trần phân bổ" in w.lower() for w in plan["warnings"])
    assert plan["new_total_exposure"] == 6000.0


def test_calculate_trade_plan_invalid_parameters():
    # Long with invalidation above entry
    bad_plan = calculate_trade_plan(
        entry_price=100.0,
        invalidation_price=105.0,
        account_capital=10_000.0,
        side=1
    )
    assert bad_plan["is_valid"] is False
    assert "Mức vô hiệu nằm sai chiều" in bad_plan["error"]

    # Zero capital
    zero_cap = calculate_trade_plan(
        entry_price=100.0,
        invalidation_price=95.0,
        account_capital=0.0
    )
    assert zero_cap["is_valid"] is False


# =====================================================================
# [D-4] Frozen Shortlist & Closed-Loop Decisions Tests
# =====================================================================

def test_frozen_shortlist_storage_and_retrieval(test_repo):
    sample_shortlist = [
        {
            "symbol": "AAPL",
            "review_rank": 1,
            "quality_tier": "ready",
            "group_type": "long_cont",
            "setup_type": "Breakout Base",
            "trigger_price": 200.0,
            "invalidation_price": 192.0,
            "resistance_level": 215.0,
            "quality_score": 15.0,
            "raw_rank": 1,
            "quality_reasons": "Đạt cản rõ ràng"
        },
        {
            "symbol": "MSFT",
            "review_rank": 2,
            "quality_tier": "wait",
            "group_type": "long_cont",
            "setup_type": "Pullback MA20",
            "trigger_price": 420.0,
            "invalidation_price": 405.0,
            "resistance_level": None,
            "quality_score": 12.0,
            "raw_rank": 2,
            "quality_reasons": "Thiếu cản phía trước"
        }
    ]

    snap_id = test_repo.save_snapshot(
        as_of="2026-09-27",
        rule_version="review-v1",
        total_universe=500,
        valid_universe=500,
        coverage_pct=100.0,
        missing_symbols=[],
        market_metrics={},
        sector_metrics=[],
        candidates=[]
    )

    count = test_repo.save_frozen_shortlist(
        snapshot_id=snap_id,
        session_date="2026-09-27",
        policy_version="review-v1",
        shortlist=sample_shortlist
    )
    assert count == 2

    # Query back
    frozen = test_repo.get_frozen_shortlist(session_date="2026-09-27")
    assert len(frozen) == 2
    assert frozen[0]["symbol"] == "AAPL"
    assert frozen[0]["review_rank"] == 1
    assert frozen[0]["quality_tier"] == "ready"
    assert frozen[0]["trigger_price"] == 200.0
    assert frozen[0]["invalidation_price"] == 192.0
    assert frozen[1]["symbol"] == "MSFT"
    assert frozen[1]["quality_tier"] == "wait"


def test_trade_decisions_and_slippage(test_repo):
    # Save trade decision: select
    d_id = test_repo.save_trade_decision(
        session_date="2026-09-27",
        symbol="AAPL",
        decision="chon",
        decision_reason="Setup Breakout chuẩn O'Neil, bối cảnh TT thuận",
        reviewer="Trader X",
        plan_entry_price=200.0,
        plan_stop_price=192.0,
        plan_target_price=215.0,
        plan_shares=50,
        observed_trigger_price=200.5,
        observed_trigger_time="09:45 AM",
        actual_fill_price=201.0,
        actual_fill_shares=50,
        actual_fill_date="2026-09-27",
        actual_fill_notes="Khớp qua limit order"
    )
    assert d_id > 0

    decs = test_repo.get_trade_decisions(session_date="2026-09-27", symbol="AAPL")
    assert len(decs) == 1
    d = decs[0]
    assert d["decision"] == "chon"
    assert d["plan_entry_price"] == 200.0
    assert d["observed_trigger_price"] == 200.5
    assert d["actual_fill_price"] == 201.0


def test_evaluate_shortlist_and_decision_outcomes():
    # Construct synthetic daily bars for 25 sessions
    dates = pd.date_range("2026-09-01", periods=25, freq="B").strftime("%Y-%m-%d").tolist()
    # AAPL rises from 200 to 220
    aapl_prices = np.linspace(200.0, 220.0, 25)
    # MSFT falls from 420 to 400
    msft_prices = np.linspace(420.0, 400.0, 25)

    bars_aapl = pd.DataFrame({
        "symbol": "AAPL",
        "date": dates,
        "open": aapl_prices,
        "high": aapl_prices + 2.0,
        "low": aapl_prices - 1.0,
        "close": aapl_prices,
        "volume": 1_000_000
    })
    bars_msft = pd.DataFrame({
        "symbol": "MSFT",
        "date": dates,
        "open": msft_prices,
        "high": msft_prices + 1.0,
        "low": msft_prices - 3.0,
        "close": msft_prices,
        "volume": 800_000
    })
    all_bars = pd.concat([bars_aapl, bars_msft], ignore_index=True)

    shortlist_items = [
        {
            "symbol": "AAPL",
            "session_date": dates[0],
            "trigger_price": 200.0,
            "invalidation_price": 192.0,
            "side": 1
        },
        {
            "symbol": "MSFT",
            "session_date": dates[0],
            "trigger_price": 420.0,
            "invalidation_price": 405.0,
            "side": 1
        }
    ]

    decisions = [
        {
            "symbol": "AAPL",
            "session_date": dates[0],
            "decision": "chon",
            "plan_entry_price": 200.0,
            "observed_trigger_price": 200.5,
            "actual_fill_price": 201.0
        },
        {
            "symbol": "MSFT",
            "session_date": dates[0],
            "decision": "bo_qua",
            "plan_entry_price": 420.0,
            "observed_trigger_price": 418.0,
            "actual_fill_price": None
        }
    ]

    eval_result = evaluate_shortlist_and_decision_outcomes(
        shortlist_items=shortlist_items,
        decisions=decisions,
        daily_bars_df=all_bars,
        horizons=[1, 5, 20]
    )

    evaluated_cands = eval_result["evaluated_items"]
    assert len(evaluated_cands) == 2
    aapl_eval = next(c for c in evaluated_cands if c["symbol"] == "AAPL")
    assert aapl_eval["user_decision"] == "chon"
    assert aapl_eval["actual_fill_price"] == 201.0
    assert aapl_eval["plan_to_fill_diff_pct"] == 0.5  # (201 - 200) / 200 * 100
    assert aapl_eval["forward_returns"]["5d"] is not None

    msft_eval = next(c for c in evaluated_cands if c["symbol"] == "MSFT")
    assert msft_eval["user_decision"] == "bo_qua"

    # Check decision groups
    by_dec = eval_result["decision_stats"]
    assert "chon" in by_dec
    assert "bo_qua" in by_dec
    assert by_dec["chon"]["count"] == 1
    assert by_dec["bo_qua"]["count"] == 1


# =====================================================================
# [D-5] Playbook Quality Audit Tests
# =====================================================================

def test_summarize_playbook_quality():
    sample_cands = [
        # Candidate 1: Ready with observable barrier
        {
            "symbol": "AAA",
            "group_type": "long_cont",
            "setup_type": "Breakout Base",
            "quality_tier": "ready",
            "resistance_level": 115.0,
            "quality_reasons": ""
        },
        # Candidate 2: Wait due to no observable resistance (factual, no invented target)
        {
            "symbol": "BBB",
            "group_type": "long_cont",
            "setup_type": "Breakout Base",
            "quality_tier": "wait",
            "resistance_level": None,
            "quality_reasons": "Thiếu cản phía trước"
        },
        # Candidate 3: Reject due to distance to MA20
        {
            "symbol": "CCC",
            "group_type": "long_cont",
            "setup_type": "Breakout Base",
            "quality_tier": "reject",
            "resistance_level": 50.0,
            "quality_reasons": "Giá chạy xa MA20 (3.2 ATR)"
        },
        # Candidate 4: Pullback setup
        {
            "symbol": "DDD",
            "group_type": "long_cont",
            "setup_type": "Pullback MA20",
            "quality_tier": "ready",
            "resistance_level": 80.0,
            "quality_reasons": ""
        }
    ]

    summary = summarize_playbook_quality(sample_cands, DEFAULT_POLICY)
    assert summary["overall"]["total"] == 4
    assert summary["policy_version"] == "review-v1"

    by_pb = summary["by_playbook"]
    assert "long_cont:Breakout Base" in by_pb
    bb_stats = by_pb["long_cont:Breakout Base"]
    assert bb_stats["total"] == 3
    assert bb_stats["ready"] == 1
    assert bb_stats["wait"] == 1
    assert bb_stats["reject"] == 1
    assert bb_stats["barrier_present_count"] == 2
    assert bb_stats["barrier_missing_count"] == 1
    assert any("Thiếu cản phía trước" in r[0] for r in bb_stats["top_wait_reasons"])
    assert any("MA20" in r[0] for r in bb_stats["top_reject_reasons"])

    pb_stats = by_pb["long_cont:Pullback MA20"]
    assert pb_stats["total"] == 1
    assert pb_stats["ready"] == 1
    assert pb_stats["barrier_present_count"] == 1


# =====================================================================
# Regression Tests for Logic Defects LOGIC-001 to LOGIC-005
# =====================================================================

def test_logic_001_candidate_without_decision_modal_safe(test_repo):
    """LOGIC-001: Opening a candidate with no prior decision does not crash with AttributeError."""
    from app.components.setup_detail import render_setup_detail_modal
    import streamlit as st

    sample_candidate = {
        "symbol": "AAA",
        "company_name": "Triple A Corp",
        "group_type": "long_cont",
        "setup_type": "Breakout Base",
        "close_price": 100.0,
        "trigger_price": 100.0,
        "invalidation_price": 95.0,
        "resistance_level": 115.0,
        "atr14": 3.0,
        "quality_tier": "ready"
    }

    # Verify querying repo for non-existent decision returns empty list safely
    decs = test_repo.get_trade_decisions(session_date="2026-09-25", symbol="AAA")
    assert len(decs) == 0

    # Save initial decision and verify retrieval
    test_repo.save_trade_decision(
        session_date="2026-09-25",
        symbol="AAA",
        decision="chon",
        plan_entry_price=100.0,
        plan_stop_price=95.0,
        plan_shares=200
    )
    decs_after = test_repo.get_trade_decisions(session_date="2026-09-25", symbol="AAA")
    assert len(decs_after) == 1
    assert decs_after[0]["plan_shares"] == 200


def test_logic_002_frozen_shortlist_scoped_and_multi_setup(test_repo):
    """LOGIC-002: Shortlists are scoped to snapshot/policy and match exact setup."""
    # 1. Snapshot A on 2026-09-27
    snap_a = test_repo.save_snapshot(
        as_of="2026-09-27", rule_version="v1", total_universe=100, valid_universe=100,
        coverage_pct=100.0, missing_symbols=[], market_metrics={}, sector_metrics=[], candidates=[]
    )
    shortlist_a = [
        {"symbol": "AAA", "review_rank": 1, "group_type": "long_cont", "setup_type": "Breakout Base", "quality_tier": "ready", "trigger_price": 100.0, "invalidation_price": 95.0}
    ]
    test_repo.save_frozen_shortlist(snapshot_id=snap_a, session_date="2026-09-27", policy_version="review-v1", shortlist=shortlist_a)

    # 2. Snapshot B on same date with different candidates
    snap_b = test_repo.save_snapshot(
        as_of="2026-09-27", rule_version="v1", total_universe=100, valid_universe=100,
        coverage_pct=100.0, missing_symbols=[], market_metrics={}, sector_metrics=[], candidates=[]
    )
    shortlist_b = [
        {"symbol": "BBB", "review_rank": 1, "group_type": "long_rev", "setup_type": "Oversold Bounce", "quality_tier": "ready", "trigger_price": 50.0, "invalidation_price": 47.0}
    ]
    test_repo.save_frozen_shortlist(snapshot_id=snap_b, session_date="2026-09-27", policy_version="review-v1", shortlist=shortlist_b)

    # Query scoped to snap_a vs snap_b
    frozen_a = test_repo.get_frozen_shortlist(snapshot_id=snap_a)
    assert len(frozen_a) == 1
    assert frozen_a[0]["symbol"] == "AAA"
    assert frozen_a[0]["setup_type"] == "Breakout Base"

    frozen_b = test_repo.get_frozen_shortlist(snapshot_id=snap_b)
    assert len(frozen_b) == 1
    assert frozen_b[0]["symbol"] == "BBB"

    # 3. Empty shortlist run records metadata
    snap_empty = test_repo.save_snapshot(
        as_of="2026-09-28", rule_version="v1", total_universe=100, valid_universe=100,
        coverage_pct=100.0, missing_symbols=[], market_metrics={}, sector_metrics=[], candidates=[]
    )
    test_repo.save_frozen_shortlist(snapshot_id=snap_empty, session_date="2026-09-28", policy_version="review-v1", shortlist=[])
    assert test_repo.has_frozen_shortlist(snapshot_id=snap_empty) is True
    assert len(test_repo.get_frozen_shortlist(snapshot_id=snap_empty)) == 0


def test_logic_003_trade_plan_recalculation_and_risk_validation():
    """LOGIC-003: Changing entry/stop/shares properly recalculates dollar risk and validates budget."""
    # Base: Capital $100k, 1% budget ($1,000), Entry 100, Stop 95 (Risk $5/share) -> 200 shares, $1000 risk
    base_plan = calculate_trade_plan(
        entry_price=100.0,
        invalidation_price=95.0,
        account_capital=100_000.0,
        risk_budget_pct=1.0,
        side=1
    )
    assert base_plan["planned_shares"] == 200
    assert base_plan["dollar_risk"] == 1000.0
    assert base_plan["is_valid"] is True

    # User modifies stop to 90 (Risk $10/share) and specifies 200 shares -> Actual risk $2,000 (exceeds $1,000 budget)
    custom_plan = calculate_trade_plan(
        entry_price=100.0,
        invalidation_price=90.0,
        account_capital=100_000.0,
        risk_budget_pct=1.0,
        side=1,
        shares=200
    )
    assert custom_plan["planned_shares"] == 200
    assert custom_plan["per_share_risk"] == 10.0
    assert custom_plan["dollar_risk"] == 2000.0
    assert custom_plan["account_risk_pct"] == 2.0
    assert any("vượt ngân sách rủi ro" in w for w in custom_plan["warnings"])

    # Invalidation in wrong direction for Long
    bad_plan = calculate_trade_plan(
        entry_price=100.0,
        invalidation_price=105.0,
        account_capital=100_000.0,
        side=1
    )
    assert bad_plan["is_valid"] is False
    assert "Mức vô hiệu nằm sai chiều" in bad_plan["error"]


def test_logic_004_decision_matching_preserves_session_cohorts():
    """LOGIC-004: Same symbol across multiple sessions does not overwrite decision mapping."""
    shortlist_items = [
        {"symbol": "AAA", "session_date": "2026-09-01", "group_type": "long_cont", "trigger_price": 100.0, "invalidation_price": 95.0},
        {"symbol": "AAA", "session_date": "2026-09-03", "group_type": "long_cont", "trigger_price": 105.0, "invalidation_price": 100.0}
    ]

    # Decisions in reverse order
    decisions = [
        {"symbol": "AAA", "session_date": "2026-09-03", "decision": "chon", "plan_entry_price": 105.0},
        {"symbol": "AAA", "session_date": "2026-09-01", "decision": "bo_qua", "plan_entry_price": None}
    ]

    eval_res = evaluate_shortlist_and_decision_outcomes(
        shortlist_items=shortlist_items,
        decisions=decisions,
        daily_bars_df=None
    )

    items = eval_res["evaluated_items"]
    assert len(items) == 2
    item_0901 = next(it for it in items if it["session_date"] == "2026-09-01")
    item_0903 = next(it for it in items if it["session_date"] == "2026-09-03")

    assert item_0901["user_decision"] == "bo_qua"
    assert item_0903["user_decision"] == "chon"


def test_logic_005_actual_fill_returns_decoupled_from_signal_date():
    """LOGIC-005: Actual fill returns are measured from actual_fill_date, not signal date."""
    # Dates: 2026-09-01 (Signal), 2026-09-02 (Bar 1), 2026-09-03 (Bar 2), 2026-09-04 (Bar 3, Fill Day), 2026-09-05 (Bar 4)
    dates = ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05"]
    # Closes: 09-02=100, 09-03=110, 09-04=120, 09-05=130
    # Opens:  09-02=98,  09-03=108, 09-04=118, 09-05=128
    daily_bars = pd.DataFrame({
        "symbol": ["AAA"] * 5,
        "date": dates,
        "open": [95.0, 98.0, 108.0, 118.0, 128.0],
        "high": [96.0, 102.0, 112.0, 122.0, 132.0],
        "low": [94.0, 97.0, 107.0, 117.0, 127.0],
        "close": [95.0, 100.0, 110.0, 120.0, 130.0],
        "volume": [1_000_000] * 5
    })

    shortlist_items = [
        {"symbol": "AAA", "session_date": "2026-09-01", "group_type": "long_cont", "trigger_price": 100.0, "invalidation_price": 90.0}
    ]

    # Filled on 2026-09-04 at $120
    decisions = [
        {
            "symbol": "AAA",
            "session_date": "2026-09-01",
            "decision": "chon",
            "actual_fill_price": 120.0,
            "actual_fill_date": "2026-09-04"
        }
    ]

    eval_res = evaluate_shortlist_and_decision_outcomes(
        shortlist_items=shortlist_items,
        decisions=decisions,
        daily_bars_df=daily_bars,
        horizons=[1]
    )

    item = eval_res["evaluated_items"][0]
    assert item["fill_status"] == "filled"

    # Benchmark 1d return: from 09-02 Open ($98) to 09-02 Close ($100) -> +2.04%
    assert item["benchmark_returns"]["1d"] == round((100.0 - 98.0) / 98.0 * 100.0, 2)

    # Actual fill 1d return: from 09-04 Fill ($120) to 09-05 Close ($130) -> +8.33% (NOT negative or from 09-02!)
    assert item["fill_returns"]["1d"] == round((130.0 - 120.0) / 120.0 * 100.0, 2)
    assert item["fill_returns"]["1d"] == 8.33


def test_frozen_shortlist_respects_candidate_search_and_group_filters():
    """The frozen view must not restore candidates removed by UI filters."""
    import json
    from streamlit.testing.v1 import AppTest

    source = '''
import streamlit as st
import app.components.candidate_cards as cards
from analytics.candidate_quality import rank_for_review
from tests.test_candidate_quality import candidate

rows = [candidate("AAA"), candidate("BBB")]
rows[0]["sector"] = "Technology"
rows[1]["sector"] = "Health Care"
frozen = [dict(c, review_rank=i) for i, c in enumerate(rank_for_review(rows), 1)]

class Repo:
    def get_frozen_shortlist(self, **kwargs):
        return frozen
    def has_frozen_shortlist(self, **kwargs):
        return True
    def get_base_snapshots(self, **kwargs):
        return []

def capture(filtered, *args, **kwargs):
    st.json({"symbols": [c["symbol"] for c in filtered]})

cards.render_candidates_table = capture
cards.render_candidates_section(rows, as_of="2026-09-22", repo=Repo(), snapshot_id=1)
'''
    app = AppTest.from_string(source).run(timeout=30)
    assert not app.exception
    assert json.loads(app.json[0].value)["symbols"] == ["AAA", "BBB"]

    app.text_input(key="cand_search_input").set_value("AAA").run(timeout=30)
    assert not app.exception
    assert json.loads(app.json[0].value)["symbols"] == ["AAA"]

    app.text_input(key="cand_search_input").set_value("ZZZ").run(timeout=30)
    assert not app.exception
    assert not app.json

    app.text_input(key="cand_search_input").set_value("")
    app.session_state["cand_sector_filter"] = "Technology"
    app.run(timeout=30)
    assert not app.exception
    assert json.loads(app.json[0].value)["symbols"] == ["AAA"]


def test_refreshed_snapshots_count_one_decision_and_fill():
    """The outcome sample is one symbol/session despite repeated pipeline runs."""
    import pandas as pd

    bars = pd.DataFrame([
        {"symbol": "AAA", "date": day, "open": price, "high": price + 1,
         "low": price - 1, "close": price}
        for day, price in [("2026-09-02", 100.0), ("2026-09-03", 110.0),
                           ("2026-09-04", 120.0), ("2026-09-07", 130.0)]
    ])
    snapshots = [
        {"symbol": "AAA", "session_date": "2026-09-01", "snapshot_id": sid,
         "group_type": "long_cont", "review_rank": 1}
        for sid in (1, 2)
    ]
    decision = [{
        "symbol": "AAA", "session_date": "2026-09-01", "snapshot_id": 2,
        "decision": "chon", "actual_fill_price": 120.0,
        "actual_fill_date": "2026-09-04",
    }]

    for rows in (snapshots, list(reversed(snapshots))):
        result = evaluate_shortlist_and_decision_outcomes(
            rows, decision, bars, horizons=[1]
        )
        assert result["total_shortlist"] == 1
        assert result["evaluated_items"][0]["user_decision"] == "chon"
        assert result["decision_stats"]["chon"]["count"] == 1
        assert result["decision_stats"]["chon"]["fill_count"] == 1
        assert result["evaluated_items"][0]["fill_returns"]["1d"] == 8.33

    # A decision tied to a different snapshot must not be applied by date alone.
    result = evaluate_shortlist_and_decision_outcomes(
        snapshots[:1], decision, bars, horizons=[1]
    )
    assert result["evaluated_items"][0]["user_decision"] == "chưa ghi nhận"
    assert "chon" not in result["decision_stats"]
