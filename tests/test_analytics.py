import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from analytics.market_breadth import compute_stock_indicators, compute_market_breadth
from analytics.sector_ranker import rank_sectors
from analytics.industry_ranker import rank_industry_groups
from analytics.screening_rules import screen_candidates
from analytics.company_fa import evaluate_fa_flags
from config.settings import BENCHMARK_TICKER

def generate_synthetic_bars(symbol: str, base_price: float, trend: float, days: int = 210) -> pd.DataFrame:
    """Generate synthetic daily OHLCV bars for testing."""
    records = []
    current_date = datetime(2026, 1, 1)
    price = base_price
    for i in range(days):
        date_str = (current_date + timedelta(days=i)).strftime("%Y-%m-%d")
        price = price * (1.0 + trend + np.sin(i / 5.0) * 0.01)
        high = price * 1.01
        low = price * 0.99
        open_p = price * 1.002
        vol = 200_000 + np.random.randint(1000, 50000)
        records.append({
            "symbol": symbol,
            "date": date_str,
            "open": open_p,
            "high": high,
            "low": low,
            "close": price,
            "volume": float(vol)
        })
    return pd.DataFrame(records)

def test_compute_stock_indicators():
    df_bars = generate_synthetic_bars("TEST", 100.0, 0.001, days=220)
    res = compute_stock_indicators(df_bars)
    assert not res.empty
    assert "ma20" in res.columns
    assert "ma50" in res.columns
    assert "ma200" in res.columns
    assert "perf_1d" in res.columns
    assert "perf_20d" in res.columns
    assert res.iloc[0]["symbol"] == "TEST"

def test_compute_market_breadth():
    bars_list = []
    # Create 10 stocks: 7 bullish (+0.002 trend), 3 bearish (-0.002 trend)
    for i in range(7):
        bars_list.append(generate_synthetic_bars(f"BULL_{i}", 50.0 + i*10, 0.002, days=210))
    for i in range(3):
        bars_list.append(generate_synthetic_bars(f"BEAR_{i}", 80.0 + i*10, -0.002, days=210))
    # Add SPY and RSP
    bars_list.append(generate_synthetic_bars("SPY", 500.0, 0.001, days=210))
    bars_list.append(generate_synthetic_bars("RSP", 180.0, 0.0005, days=210))

    all_bars = pd.concat(bars_list, ignore_index=True)
    latest_df = compute_stock_indicators(all_bars)

    breadth = compute_market_breadth(latest_df, all_bars)
    assert breadth["total_evaluated"] == 10
    assert breadth["pct_above_ma50"] >= 50.0
    assert "SPY" not in [f"BULL_{i}" for i in range(7)]
    assert "market_summary" in breadth
    assert "concentration_divergence" in breadth

def test_screening_rules_no_forced_quota():
    # Empty inputs must return empty candidates list without error
    empty_df = pd.DataFrame()
    candidates = screen_candidates(empty_df, [], None)
    assert candidates == []

def test_fa_evaluation_banking_vs_corporate():
    # Corporate with high debt & negative cashflow
    corp_fa = {
        "is_financial": False,
        "revenue_growth": 0.20,
        "earnings_growth": -0.05,
        "profit_margins": 0.10,
        "operating_margins": 0.12,
        "operating_cashflow": -100_000_000,
        "total_debt": 500_000_000,
        "next_earnings_date": "2026-10-15"
    }
    corp_eval = evaluate_fa_flags("CORP", corp_fa)
    assert any("Dòng tiền hoạt động âm" in f for f in corp_eval["flags"])
    assert corp_eval["earnings_status"] == "2026-10-15"

    # Bank with high debt & negative cashflow (standard banking profile)
    bank_fa = {
        "is_financial": True,
        "revenue_growth": 0.10,
        "earnings_growth": 0.15,
        "profit_margins": 0.30,
        "operating_margins": 0.40,
        "operating_cashflow": -500_000_000,
        "total_debt": 10_000_000_000,
        "next_earnings_date": None
    }
    bank_eval = evaluate_fa_flags("JPM", bank_fa)
    # Must NOT flag as debt warning for bank!
    assert not any("Dòng tiền hoạt động âm và có nợ vay" in f for f in bank_eval["flags"])
    assert any("Định chế tài chính/Ngân hàng" in f for f in bank_eval["flags"])
    assert bank_eval["earnings_status"] == "Chưa xác minh"

def test_rank_industry_groups():
    # Synthetic stocks with 3 sub-industries
    stocks_data = [
        {"symbol": "DELL", "perf_1d": 2.5, "perf_5d": 8.0, "perf_20d": 15.0, "perf_60d": 30.0, "perf_126d": 50.0, "perf_252d": 80.0, "close": 120.0, "rs_rating": 95},
        {"symbol": "HPQ", "perf_1d": 1.2, "perf_5d": 5.0, "perf_20d": 10.0, "perf_60d": 20.0, "perf_126d": 35.0, "perf_252d": 50.0, "close": 35.0, "rs_rating": 85},
        {"symbol": "DINO", "perf_1d": -0.5, "perf_5d": 2.0, "perf_20d": 5.0, "perf_60d": 10.0, "perf_126d": 15.0, "perf_252d": 25.0, "close": 55.0, "rs_rating": 70},
        {"symbol": "PBF", "perf_1d": -1.0, "perf_5d": 1.0, "perf_20d": 4.0, "perf_60d": 8.0, "perf_126d": 12.0, "perf_252d": 20.0, "close": 42.0, "rs_rating": 65},
        {"symbol": "MRNA", "perf_1d": -2.5, "perf_5d": -5.0, "perf_20d": -10.0, "perf_60d": -20.0, "perf_126d": -30.0, "perf_252d": -40.0, "close": 70.0, "rs_rating": 20},
    ]
    constituents_data = [
        {"symbol": "DELL", "security": "Dell Technologies", "sector": "Information Technology", "sub_industry": "Computer Hardware"},
        {"symbol": "HPQ", "security": "HP Inc.", "sector": "Information Technology", "sub_industry": "Computer Hardware"},
        {"symbol": "DINO", "security": "HF Sinclair", "sector": "Energy", "sub_industry": "Oil & Gas Refining & Marketing"},
        {"symbol": "PBF", "security": "PBF Energy", "sector": "Energy", "sub_industry": "Oil & Gas Refining & Marketing"},
        {"symbol": "MRNA", "security": "Moderna", "sector": "Health Care", "sub_industry": "Biotechnology"},
    ]
    df_stocks = pd.DataFrame(stocks_data)
    df_constituents = pd.DataFrame(constituents_data)

    results = rank_industry_groups(df_stocks, df_constituents)
    assert len(results) == 3

    # Computer Hardware should be ranked #1
    top_ind = results[0]
    assert top_ind["industry"] == "Computer Hardware"
    assert top_ind["rank"] == 1
    assert top_ind["stk_count"] == 2
    assert top_ind["comp_score"] >= results[1]["comp_score"]
    assert top_ind["is_leading"] is True
    assert 1 <= top_ind["day_rank"] <= 99
    assert 1 <= top_ind["comp_score"] <= 99
    assert 1 <= top_ind["blend_score"] <= 99

    # Check stock pills
    assert len(top_ind["stocks"]) == 2
    assert top_ind["stocks"][0]["symbol"] == "DELL"
    assert "https://www.tradingview.com" in top_ind["stocks"][0]["tv_url"]
    assert "interval=D" in top_ind["stocks"][0]["tv_url"]

def test_screening_rules_with_oneil_leader():
    # Setup stock in leading industry group
    latest_df = pd.DataFrame([{
        "symbol": "LEAD",
        "close": 105.0,
        "volume": 500_000,
        "vol_ma20": 300_000,
        "ma20": 100.0,
        "ma50": 95.0,
        "ma200": 80.0,
        "perf_1d": 2.0,
        "perf_5d": 5.0,
        "perf_20d": 12.0,
        "perf_60d": 25.0,
        "high20": 104.0,
        "low20": 94.0,
        "sub_industry": "Top Tech",
        "sector": "Information Technology"
    }])
    sector_metrics = [{
        "sector": "Information Technology",
        "etf": "XLK",
        "etf_1m": 5.0,
        "status": "Dẫn đầu (Leading)"
    }]
    industry_metrics = [{
        "industry": "Top Tech",
        "comp_score": 95,
        "is_leading": True
    }]
    candidates = screen_candidates(latest_df, sector_metrics, None, industry_metrics)
    assert len(candidates) > 0
    c = candidates[0]
    assert c["is_oneil_leader"] is True
    assert any("O'Neil Leader" in r for r in c["technical_reasons"])


def test_d01_strict_observation_counts_and_missing_1y_rank():
    """[D-01] 252 bars yields NaN for perf_252d; 253 bars yields valid float."""
    bars_252 = generate_synthetic_bars("TEST_252", 100.0, 0.001, days=252)
    res_252 = compute_stock_indicators(bars_252)
    assert np.isnan(res_252.iloc[0]["perf_252d"])

    bars_253 = generate_synthetic_bars("TEST_253", 100.0, 0.001, days=253)
    res_253 = compute_stock_indicators(bars_253)
    assert not np.isnan(res_253.iloc[0]["perf_252d"])

    # Test industry ranking handles missing 1Y cleanly without arbitrary 0.0 or median fallback
    stocks_df = pd.DataFrame([
        {"symbol": "S1", "perf_1d": 1.0, "perf_5d": 2.0, "perf_20d": 5.0, "perf_60d": 10.0, "perf_126d": 15.0, "perf_252d": np.nan, "close": 50.0},
        {"symbol": "S2", "perf_1d": -1.0, "perf_5d": -2.0, "perf_20d": -5.0, "perf_60d": -10.0, "perf_126d": -15.0, "perf_252d": np.nan, "close": 30.0},
    ])
    const_df = pd.DataFrame([
        {"symbol": "S1", "security": "S1 Inc", "sector": "Tech", "sub_industry": "IndA"},
        {"symbol": "S2", "security": "S2 Inc", "sector": "Tech", "sub_industry": "IndB"},
    ])
    ranked = rank_industry_groups(stocks_df, const_df)
    assert len(ranked) == 2
    # Both industries should have rank_1y as None because all perf_252d are NaN
    for group in ranked:
        assert group["rank_1y"] is None
        # But composite score should still be non-null and valid based on available horizons
        assert group["comp_score"] is not None
        assert 1 <= group["comp_score"] <= 99


def test_d02_causal_breakout_vs_setup_and_truthful_trend():
    """[D-02] Causal prior high check and MA50>MA200 trend truthfulness."""
    # Test 1: Setup vs Confirmed breakout
    setup_stock = pd.DataFrame([{
        "symbol": "SETUP",
        "close": 99.5,
        "prev_high20": 100.0,  # Prior high was 100
        "high20": 100.0,
        "low20": 90.0,
        "volume": 600_000,
        "vol_ma20": 200_000,  # 3x volume surge
        "ma20": 95.0,
        "ma50": 90.0,
        "ma200": 85.0,
        "perf_1d": 1.5,
        "perf_5d": 3.0,
        "perf_20d": 8.0,
        "perf_60d": 15.0,
        "sub_industry": "Tech",
        "sector": "Technology"
    }])
    candidates_setup = screen_candidates(setup_stock, [], None)
    setup_c = [c for c in candidates_setup if c["symbol"] == "SETUP"]
    assert len(setup_c) == 1
    # Close 99.5 < prev_high20 100.0 => status MUST be 'setup', NOT 'confirmed'
    assert setup_c[0]["status"] == "setup"
    assert any("đỉnh 20 phiên" in r and "tích lũy" in r for r in setup_c[0]["technical_reasons"])

    confirmed_stock = pd.DataFrame([{
        "symbol": "CONF",
        "close": 101.0,
        "prev_high20": 100.0,  # Broke out above prior high
        "high20": 101.0,
        "low20": 90.0,
        "volume": 600_000,
        "vol_ma20": 200_000,
        "ma20": 95.0,
        "ma50": 90.0,
        "ma200": 85.0,
        "perf_1d": 2.5,
        "perf_5d": 5.0,
        "perf_20d": 10.0,
        "perf_60d": 18.0,
        "sub_industry": "Tech",
        "sector": "Technology"
    }])
    candidates_conf = screen_candidates(confirmed_stock, [], None)
    conf_c = [c for c in candidates_conf if c["symbol"] == "CONF"]
    assert len(conf_c) == 1
    assert conf_c[0]["status"] == "confirmed"
    assert any("Vượt đỉnh 20 phiên" in r or "Breakout" in r for r in conf_c[0]["technical_reasons"])

    # Test 2: Truthful trend reason when MA50 <= MA200
    bearish_cross_stock = pd.DataFrame([{
        "symbol": "BULL_PULLBACK",
        "close": 125.0,
        "prev_high20": 130.0,
        "high20": 130.0,
        "low20": 90.0,
        "volume": 250_000,
        "vol_ma20": 200_000,
        "ma20": 124.0,   # Near MA20 (<3% pullback)
        "ma50": 120.0,   # MA20 >= MA50
        "ma200": 122.0,  # MA50 (120) < MA200 (122), but Close (125) > MA200 and MA50
        "perf_1d": 1.0,
        "perf_5d": 3.0,
        "perf_20d": 6.0,
        "perf_60d": 10.0,
        "sub_industry": "Tech",
        "sector": "Technology"
    }])
    candidates_bull = screen_candidates(bearish_cross_stock, [], None)
    bp_c = [c for c in candidates_bull if c["symbol"] == "BULL_PULLBACK"]
    assert len(bp_c) == 1
    # Must NOT falsely claim MA50 > MA200!
    assert not any("MA50 > MA200" in r for r in bp_c[0]["technical_reasons"])
    assert any("MA50 chưa cắt lên MA200" in r for r in bp_c[0]["technical_reasons"])


def test_d05_stock_leader_requires_both_industry_and_stock_strength():
    """[D-05] Stock in leading industry is NOT an O'Neil leader if the stock itself is lagging."""
    stocks = pd.DataFrame([
        {
            "symbol": "WEAK_IN_TOP_IND",
            "close": 50.0,
            "volume": 300_000,
            "vol_ma20": 300_000,
            "ma20": 52.0,
            "ma50": 55.0,
            "ma200": 60.0,
            "perf_1d": -1.0,
            "perf_5d": -3.0,
            "perf_20d": -8.0,  # Lagging performance
            "rs_rating": 45,    # Weak RS
            "prev_high20": 60.0,
            "prev_low20": 48.0,
            "high20": 60.0,
            "low20": 48.0,
            "sub_industry": "Semiconductors",
            "sector": "Technology"
        },
        {
            "symbol": "STRONG_IN_TOP_IND",
            "close": 150.0,
            "volume": 500_000,
            "vol_ma20": 300_000,
            "ma20": 140.0,
            "ma50": 130.0,
            "ma200": 110.0,
            "perf_1d": 2.5,
            "perf_5d": 6.0,
            "perf_20d": 15.0,  # Strong
            "rs_rating": 88,    # Top quintile RS
            "prev_high20": 148.0,
            "prev_low20": 130.0,
            "high20": 151.0,
            "low20": 130.0,
            "sub_industry": "Semiconductors",
            "sector": "Technology"
        }
    ])
    industry_metrics = [{
        "industry": "Semiconductors",
        "comp_score": 96,
        "is_leading": True
    }]
    candidates = screen_candidates(stocks, [], None, industry_metrics)

    strong = next((c for c in candidates if c["symbol"] == "STRONG_IN_TOP_IND"), None)
    assert strong is not None
    assert strong["is_oneil_leader"] is True

    weak = next((c for c in candidates if c["symbol"] == "WEAK_IN_TOP_IND"), None)
    if weak:
        assert weak["is_oneil_leader"] is False


def test_d06_small_sample_tracking_and_median_perf():
    """[D-06] Small-sample indicator for <= 2 stocks, and median 20d return."""
    stocks_df = pd.DataFrame([
        {"symbol": "SOLO", "perf_1d": 1.0, "perf_5d": 2.0, "perf_20d": 5.0, "perf_60d": 10.0, "perf_126d": 15.0, "perf_252d": 20.0, "close": 50.0, "rs_rating": 80},
        {"symbol": "PAIR1", "perf_1d": 2.0, "perf_5d": 3.0, "perf_20d": 6.0, "perf_60d": 12.0, "perf_126d": 18.0, "perf_252d": 25.0, "close": 60.0, "rs_rating": 85},
        {"symbol": "PAIR2", "perf_1d": 0.0, "perf_5d": 1.0, "perf_20d": 2.0, "perf_60d": 8.0, "perf_126d": 10.0, "perf_252d": 15.0, "close": 40.0, "rs_rating": 70},
        {"symbol": "TRIO1", "perf_1d": 1.0, "perf_5d": 2.0, "perf_20d": 10.0, "perf_60d": 15.0, "perf_126d": 20.0, "perf_252d": 30.0, "close": 70.0, "rs_rating": 90},
        {"symbol": "TRIO2", "perf_1d": 1.5, "perf_5d": 2.5, "perf_20d": 4.0, "perf_60d": 10.0, "perf_126d": 15.0, "perf_252d": 22.0, "close": 80.0, "rs_rating": 75},
        {"symbol": "TRIO3", "perf_1d": 0.5, "perf_5d": 1.5, "perf_20d": 1.0, "perf_60d": 5.0, "perf_126d": 8.0, "perf_252d": 12.0, "close": 90.0, "rs_rating": 60},
    ])
    const_df = pd.DataFrame([
        {"symbol": "SOLO", "security": "Solo Inc", "sector": "Tech", "sub_industry": "SoloGroup"},
        {"symbol": "PAIR1", "security": "Pair 1 Inc", "sector": "Tech", "sub_industry": "PairGroup"},
        {"symbol": "PAIR2", "security": "Pair 2 Inc", "sector": "Tech", "sub_industry": "PairGroup"},
        {"symbol": "TRIO1", "security": "Trio 1 Inc", "sector": "Tech", "sub_industry": "TrioGroup"},
        {"symbol": "TRIO2", "security": "Trio 2 Inc", "sector": "Tech", "sub_industry": "TrioGroup"},
        {"symbol": "TRIO3", "security": "Trio 3 Inc", "sector": "Tech", "sub_industry": "TrioGroup"},
    ])
    ranked = rank_industry_groups(stocks_df, const_df)
    by_ind = {g["industry"]: g for g in ranked}

    # SoloGroup: 1 stock -> is_small_sample True
    assert by_ind["SoloGroup"]["stk_count"] == 1
    assert by_ind["SoloGroup"]["is_small_sample"] is True

    # PairGroup: 2 stocks -> is_small_sample True
    assert by_ind["PairGroup"]["stk_count"] == 2
    assert by_ind["PairGroup"]["is_small_sample"] is True
    # Median of 6.0 and 2.0 is 4.0
    assert abs(by_ind["PairGroup"]["perf_20d_median"] - 4.0) < 1e-4

    # TrioGroup: 3 stocks -> is_small_sample False
    assert by_ind["TrioGroup"]["stk_count"] == 3
    assert by_ind["TrioGroup"]["is_small_sample"] is False
    # Median of 10.0, 4.0, 1.0 is 4.0
    assert abs(by_ind["TrioGroup"]["perf_20d_median"] - 4.0) < 1e-4


def test_d07_earnings_event_risk_warning_attached_to_candidates():
    """[D-07] Candidate with earnings within 14 days gets high warning and alert tag."""
    now_dt = datetime.now()
    soon_earnings_date = (now_dt + timedelta(days=5)).strftime("%Y-%m-%d")

    fa_dict = {
        "RISK_SYM": {
            "is_financial": False,
            "next_earnings_date": soon_earnings_date,
            "revenue_growth": 0.15,
            "earnings_growth": 0.10,
            "profit_margins": 0.12,
            "operating_margins": 0.14,
            "operating_cashflow": 100_000_000,
            "total_debt": 50_000_000
        }
    }
    # Direct FA flag evaluation check
    eval_res = evaluate_fa_flags("RISK_SYM", fa_dict["RISK_SYM"])
    assert eval_res["warning_level"] == "high"
    assert any("RỦI RO BÁO CÁO TÀI CHÍNH" in f for f in eval_res["flags"])
    assert eval_res["days_to_earnings"] <= 14

    # Test attachment in screen_candidates
    stock_df = pd.DataFrame([{
        "symbol": "RISK_SYM",
        "close": 100.0,
        "volume": 400_000,
        "vol_ma20": 200_000,
        "ma20": 95.0,
        "ma50": 90.0,
        "ma200": 80.0,
        "perf_1d": 1.5,
        "perf_5d": 4.0,
        "perf_20d": 9.0,
        "perf_60d": 15.0,
        "prev_high20": 98.0,
        "high20": 100.5,
        "low20": 90.0,
        "sub_industry": "Tech",
        "sector": "Technology"
    }])
    candidates = screen_candidates(stock_df, [], None, None, fa_data_dict=fa_dict)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["fa_flags"]["warning_level"] == "high"
    assert any("Sắp công bố BCTC" in r for r in c["technical_reasons"])


def test_d08_market_breadth_advance_decline_and_labels():
    """[D-08] Verify near-high/low labels, advance/decline counting, and truthful equal-weight interpretation."""
    bars_list = []
    # 6 advancing stocks (+2%), 4 declining stocks (-2%)
    for i in range(6):
        bars_list.append(generate_synthetic_bars(f"ADV_{i}", 100.0 + i*10, 0.003, days=260))
    for i in range(4):
        bars_list.append(generate_synthetic_bars(f"DEC_{i}", 100.0 + i*10, -0.003, days=260))

    # Add SPY and RSP
    bars_list.append(generate_synthetic_bars("SPY", 500.0, 0.001, days=260))
    bars_list.append(generate_synthetic_bars("RSP", 180.0, 0.002, days=260))

    all_bars = pd.concat(bars_list, ignore_index=True)
    latest_df = compute_stock_indicators(all_bars)

    breadth = compute_market_breadth(latest_df, all_bars)

    # 1. Total evaluated must exclude ETFs (SPY, RSP)
    assert breadth["total_evaluated"] == 10

    # 2. Advance / Decline counts must be present and sum to 10
    assert "advances" in breadth
    assert "declines" in breadth
    assert "unchanged" in breadth
    assert breadth["advances"] + breadth["declines"] + breadth["unchanged"] == 10

    # 3. Near-high / Near-low keys must be present and correctly labeled
    assert "near_20d_highs" in breadth
    assert "near_20d_lows" in breadth
    assert "new_20d_highs" in breadth  # Backwards compatibility key

    # 4. Coverage 252d must be 100% since all stocks have 260 days
    assert abs(breadth["coverage_252d_pct"] - 100.0) < 1e-4

    # 5. Breadth summary must mention advance / decline
    summary = breadth["market_summary"]
    assert "tăng" in summary or "giảm" in summary

    # 6. Concentration divergence note must describe RSP (bình quân) vs SPY (vốn hóa lớn) without claiming small-caps
    div_note = breadth["concentration_divergence"]
    assert "small-cap" not in div_note.lower()
    assert "bình quân" in div_note or "trung bình" in div_note or "thành phần khác" in div_note or "RSP" in div_note


def test_d03_session_determination_and_missing_benchmark():
    """[D-03] Verify America/New_York session alignment and missing benchmark safety."""
    from zoneinfo import ZoneInfo
    from jobs.update_pipeline import determine_target_trading_session

    tz = ZoneInfo("America/New_York")

    # 1. Test Wednesday 11:00 AM ET (market open / unclosed)
    wed_open = datetime(2026, 9, 9, 11, 0, tzinfo=tz)
    target_date, is_closed = determine_target_trading_session(wed_open)
    assert is_closed is False
    assert target_date == "2026-09-08"  # Prior closed trading day

    # 2. Test Wednesday 16:30 ET (market closed)
    wed_closed = datetime(2026, 9, 9, 16, 30, tzinfo=tz)
    target_date, is_closed = determine_target_trading_session(wed_closed)
    assert is_closed is True
    assert target_date == "2026-09-09"

    # 3. Test Sunday 14:00 ET (weekend)
    sunday = datetime(2026, 9, 13, 14, 0, tzinfo=tz)
    target_date, is_closed = determine_target_trading_session(sunday)
    assert is_closed is True
    assert target_date == "2026-09-11"  # Friday

    # 4. Test missing benchmark SPY in screen_candidates
    # When SPY is in universe but its 20d return is NaN, RS vs SPY is unavailable
    stock_with_bad_spy = pd.DataFrame([
        {
            "symbol": "SPY",
            "close": 500.0,
            "perf_20d": np.nan,  # Missing / corrupted benchmark return
            "vol_ma20": 50_000_000,
            "ma20": 490.0,
            "ma50": 480.0,
            "ma200": 450.0,
        },
        {
            "symbol": "STOCK_A",
            "close": 110.0,
            "volume": 600_000,
            "vol_ma20": 200_000,
            "ma20": 100.0,
            "ma50": 95.0,
            "ma200": 80.0,
            "perf_1d": 2.0,
            "perf_5d": 5.0,
            "perf_20d": 15.0,
            "perf_60d": 25.0,
            "prev_high20": 105.0,
            "high20": 111.0,
            "low20": 90.0,
            "sub_industry": "Tech",
            "sector": "Information Technology"
        }
    ])
    candidates = screen_candidates(stock_with_bad_spy, [], None)
    # Must NOT confirm trend continuation without valid benchmark outperformance!
    long_cont_cands = [c for c in candidates if c["group_type"] == "long_cont" and c["status"] == "confirmed"]
    assert len(long_cont_cands) == 0

    # 5. Test missing benchmark in compute_market_breadth
    no_benchmark_stocks = pd.DataFrame([
        {"symbol": "STK1", "close": 10.0, "ma20": 9.0, "ma50": 8.0, "ma200": 7.0, "perf_1d": 1.0, "perf_20d": 5.0, "high20": 10.5, "low20": 8.0}
    ])
    no_bench_breadth = compute_market_breadth(no_benchmark_stocks, pd.DataFrame())
    assert "Chưa đủ dữ liệu benchmark" in no_bench_breadth["concentration_divergence"]


def test_d06_sector_quadrants_and_sub_industry_median():
    """[D-06] Verify 4-quadrant state classification and sub-industry median returns."""
    # Sector with positive RS (1M +3%, 3M +5%) but low breadth (20% on MA50)
    stocks_data = [
        {"symbol": "SPY", "perf_5d": 1.0, "perf_20d": 2.0, "perf_60d": 5.0, "close": 500.0, "ma20": 490.0, "ma50": 480.0},
        {"symbol": "XLK", "perf_5d": 2.0, "perf_20d": 5.0, "perf_60d": 10.0, "close": 200.0, "ma20": 195.0, "ma50": 190.0},
        # 1 stock above MA50, 4 stocks below MA50 => breadth = 20%
        {"symbol": "T1", "perf_20d": 15.0, "close": 100.0, "ma20": 90.0, "ma50": 80.0, "sector": "Information Technology", "sub_industry": "Software"},
        {"symbol": "T2", "perf_20d": -2.0, "close": 50.0, "ma20": 55.0, "ma50": 60.0, "sector": "Information Technology", "sub_industry": "Software"},
        {"symbol": "T3", "perf_20d": -5.0, "close": 40.0, "ma20": 45.0, "ma50": 50.0, "sector": "Information Technology", "sub_industry": "Software"},
        {"symbol": "T4", "perf_20d": -8.0, "close": 30.0, "ma20": 35.0, "ma50": 40.0, "sector": "Information Technology", "sub_industry": "Hardware"},
        {"symbol": "T5", "perf_20d": -10.0, "close": 20.0, "ma20": 25.0, "ma50": 30.0, "sector": "Information Technology", "sub_industry": "Hardware"},
    ]
    const_data = [
        {"symbol": "T1", "sector": "Information Technology", "sub_industry": "Software"},
        {"symbol": "T2", "sector": "Information Technology", "sub_industry": "Software"},
        {"symbol": "T3", "sector": "Information Technology", "sub_industry": "Software"},
        {"symbol": "T4", "sector": "Information Technology", "sub_industry": "Hardware"},
        {"symbol": "T5", "sector": "Information Technology", "sub_industry": "Hardware"},
    ]
    df_stocks = pd.DataFrame(stocks_data)
    df_const = pd.DataFrame(const_data)

    sectors = rank_sectors(df_stocks, df_const)
    tech_sector = next((s for s in sectors if s["sector"] == "Information Technology"), None)
    assert tech_sector is not None

    # XLK RS: 1M is +3.0% pts, 3M is +5.0% pts, breadth is 20%
    # MUST be 'Suy yếu (Weakening)' due to breadth narrowing, NEVER 'Tụt hậu (Lagging)'!
    assert tech_sector["status"] == "Suy yếu (Weakening)"
    assert "phân hóa" in tech_sector["status_desc"].lower() or "suy yếu" in tech_sector["status_desc"].lower()
    assert "Tụt hậu" not in tech_sector["status"]

    # Verify sub-industries have median return and small sample tracking
    sub_soft = next((sub for sub in tech_sector["sub_industries"] if sub["sub_industry"] == "Software"), None)
    assert sub_soft is not None
    assert sub_soft["count"] == 3
    assert sub_soft["is_small_sample"] is False
    # Software returns: 15.0, -2.0, -5.0 -> median is -2.0
    assert abs(sub_soft["median_perf_20d"] - (-2.0)) < 1e-4

    sub_hard = next((sub for sub in tech_sector["sub_industries"] if sub["sub_industry"] == "Hardware"), None)
    assert sub_hard is not None
    assert sub_hard["count"] == 2
    assert sub_hard["is_small_sample"] is True


def test_d06_industry_group_breadth_dispersion_and_all_nan_comp_score():
    """[D-06] Verify industry group internal breadth, return dispersion, and clean None for missing comp_score."""
    stocks_data = [
        {"symbol": "A1", "close": 110.0, "ma20": 100.0, "ma50": 90.0, "perf_1d": 1.0, "perf_5d": 2.0, "perf_20d": 20.0, "perf_60d": 30.0},
        {"symbol": "A2", "close": 80.0, "ma20": 85.0, "ma50": 90.0, "perf_1d": -1.0, "perf_5d": -2.0, "perf_20d": -10.0, "perf_60d": -15.0},
        # Group B has no valid timeframe returns at all
        {"symbol": "B1", "close": 50.0, "ma20": 50.0, "ma50": 50.0, "perf_1d": np.nan, "perf_5d": np.nan, "perf_20d": np.nan, "perf_60d": np.nan, "perf_126d": np.nan, "perf_252d": np.nan},
    ]
    const_data = [
        {"symbol": "A1", "security": "A1", "sector": "Tech", "sub_industry": "GroupA"},
        {"symbol": "A2", "security": "A2", "sector": "Tech", "sub_industry": "GroupA"},
        {"symbol": "B1", "security": "B1", "sector": "Tech", "sub_industry": "GroupB"},
    ]
    results = rank_industry_groups(pd.DataFrame(stocks_data), pd.DataFrame(const_data))
    by_ind = {g["industry"]: g for g in results}

    # GroupA: 1 above MA50, 1 below => breadth_ma50_pct = 50.0%
    assert by_ind["GroupA"]["breadth_ma50_pct"] == 50.0
    assert by_ind["GroupA"]["breadth_ma20_pct"] == 50.0
    # Standard deviation of [20.0, -10.0] is 21.21
    assert by_ind["GroupA"]["perf_20d_std"] > 0

    # GroupB: all NaN returns => comp_score MUST be None, not 50!
    assert by_ind["GroupB"]["comp_score"] is None
    assert by_ind["GroupB"]["is_leading"] is False


def test_d02_contradiction_candidate_status_watchlist():
    """[D-02] Verify candidate matching both Long and Short conditions is marked group_type=watchlist, status=watchlist."""
    # Stock with both long pattern (pullback to MA20 in uptrend) and short reversal (lost MA20 from prior session)
    contradiction_stock = pd.DataFrame([{
        "symbol": "CONTR",
        "close": 100.0,
        "prev_close": 102.0,
        "volume": 500_000,
        "vol_ma20": 200_000,
        "ma20": 100.5,   # Near MA20 (<2.5%)
        "prev_ma20": 100.0,
        "ma50": 95.0,    # Close > MA50 and MA20 >= MA50 (Trend Long)
        "ma200": 80.0,
        "perf_1d": -1.5,
        "perf_5d": -2.0,  # Short reversal conditions met
        "perf_20d": 8.0,
        "perf_60d": 15.0,
        "prev_high20": 105.0,
        "high20": 105.0,
        "low20": 90.0,
        "sub_industry": "Software",
        "sector": "Information Technology"
    }])
    candidates = screen_candidates(contradiction_stock, [], None)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["group_type"] == "watchlist"
    assert c["status"] == "watchlist"


def test_sector_ranker_missing_spy_and_missing_etf():
    """Verify rank_sectors safely handles missing SPY and missing ETF without NameError or fake 0.0 returns."""
    # 1. SPY completely missing
    df_no_spy = pd.DataFrame([
        {"symbol": "XLK", "perf_5d": 2.0, "perf_20d": 5.0, "perf_60d": 10.0, "close": 200.0, "ma20": 195.0, "ma50": 190.0},
        {"symbol": "AAPL", "perf_20d": 4.0, "close": 150.0, "ma20": 145.0, "ma50": 140.0, "sector": "Information Technology"}
    ])
    sectors = rank_sectors(df_no_spy, pd.DataFrame())
    assert len(sectors) == 11
    xlk = next(s for s in sectors if s["sector"] == "Information Technology")
    assert xlk["rs_1m"] is None
    assert xlk["rs_3m"] is None
    assert xlk["status"] == "Chưa xác minh (Thiếu SPY)"

    # 2. SPY present, but XLF (Financials ETF) missing from universe
    df_with_spy_no_xlf = pd.DataFrame([
        {"symbol": "SPY", "perf_5d": 1.0, "perf_20d": 3.0, "perf_60d": 6.0, "close": 500.0, "ma20": 490.0, "ma50": 480.0},
        {"symbol": "XLK", "perf_5d": 2.0, "perf_20d": 5.0, "perf_60d": 10.0, "close": 200.0, "ma20": 195.0, "ma50": 190.0},
        {"symbol": "AAPL", "perf_20d": 4.0, "close": 150.0, "ma20": 145.0, "ma50": 140.0, "sector": "Information Technology"}
    ])
    sectors2 = rank_sectors(df_with_spy_no_xlf, pd.DataFrame())
    xlf = next(s for s in sectors2 if s["sector"] == "Financials")
    assert xlf["rs_1m"] is None
    assert xlf["status"] == "Chưa xác minh (Thiếu ETF)"


def test_sector_ranker_stale_etf_marked_unverified_and_not_leading():
    """
    Acceptance Criteria (Issue 2):
    Khi ETF kết thúc sớm hơn phiên mục tiêu SPY (lệch phiên: 11/02 vs 25/02),
    rank_sectors phải gắn nhãn 'Chưa xác minh (Dữ liệu cũ / Lệch phiên)',
    đặt rs_1m = None, rs_3m = None, composite_score = -999.0,
    và KHÔNG ĐƯỢC phân loại thành 'Dẫn đầu (Leading)'!
    """
    spy_df = pd.DataFrame([{"symbol": BENCHMARK_TICKER, "date": "2026-02-25", "close": 500.0, "perf_1d": 1.0, "perf_5d": 2.0, "perf_20d": 3.0, "perf_60d": 5.0}])
    # XLK ends on 2026-02-11 (14 days stale)
    xlk_df = pd.DataFrame([{"symbol": "XLK", "date": "2026-02-11", "close": 200.0, "perf_1d": 1.5, "perf_5d": 3.0, "perf_20d": 8.0, "perf_60d": 12.0}])
    # Member stock
    member_df = pd.DataFrame([{"symbol": "AAPL", "date": "2026-02-25", "close": 150.0, "ma50": 140.0, "ma20": 145.0, "sector": "Information Technology", "perf_20d": 5.0, "perf_1d": 1.0, "volume": 1000.0}])

    stocks_df = pd.concat([spy_df, xlk_df, member_df], ignore_index=True)
    const_df = pd.DataFrame([{"symbol": "AAPL", "sector": "Information Technology", "sub_industry": "Hardware"}])

    sectors = rank_sectors(stocks_df, const_df)
    tech = next(s for s in sectors if s["sector"] == "Information Technology")

    assert tech["is_stale"] is True
    assert "Chưa xác minh" in tech["status"]
    assert "Lệch phiên" in tech["status"] or "Dữ liệu cũ" in tech["status"]
    assert tech["status"] != "Dẫn đầu (Leading)"
    assert tech["rs_1m"] is None
    assert tech["rs_3m"] is None
    assert tech["composite_score"] == -999.0


def test_screen_candidates_require_benchmark_and_missing_benchmark():
    """Verify screen_candidates with require_benchmark=True disables confirmed signals when benchmark is missing."""
    stock_df = pd.DataFrame([{
        "symbol": "BULL",
        "close": 105.0,
        "volume": 500_000,
        "vol_ma20": 200_000,
        "ma20": 100.0,
        "ma50": 90.0,
        "ma200": 80.0,
        "perf_1d": 2.0,
        "perf_5d": 5.0,
        "perf_20d": 12.0,
        "perf_60d": 20.0,
        "prev_high20": 100.0,
        "high20": 105.0,
        "low20": 85.0,
        "sub_industry": "Tech",
        "sector": "Information Technology"
    }])
    # In production pipeline (require_benchmark=True), missing SPY forbids confirmed trend continuation
    candidates = screen_candidates(stock_df, [], None, None, require_benchmark=True)
    assert len(candidates) == 0


def test_compute_stock_indicators_prev_high_20_bars():
    """Verify prev_high20 and prev_low20 are not NaN even on a 20-bar series."""
    bars_20 = generate_synthetic_bars("TEST_20", 100.0, 0.002, days=20)
    res_20 = compute_stock_indicators(bars_20)
    assert not res_20.empty
    row = res_20.iloc[0]
    assert not np.isnan(row["prev_high20"])
    assert not np.isnan(row["prev_low20"])
    assert row["prev_high20"] >= row["prev_low20"]


def test_compute_market_breadth_valid_denominator_with_missing_mas():
    """Verify breadth denominator is strictly the count of stocks with valid MA and close."""
    stocks_df = pd.DataFrame([
        {"symbol": "S1", "close": 100.0, "ma20": 95.0, "ma50": 90.0, "ma200": 80.0, "perf_1d": 1.0, "perf_20d": 5.0, "high20": 102.0, "low20": 90.0},
        {"symbol": "S2", "close": 50.0, "ma20": 55.0, "ma50": np.nan, "ma200": np.nan, "perf_1d": -1.0, "perf_20d": -5.0, "high20": 52.0, "low20": 48.0},
        {"symbol": "S3", "close": 80.0, "ma20": np.nan, "ma50": np.nan, "ma200": np.nan, "perf_1d": 0.5, "perf_20d": 2.0, "high20": 81.0, "low20": 78.0},
    ])
    breadth = compute_market_breadth(stocks_df, pd.DataFrame())
    # S1 above ma20 (100>95), S2 below ma20 (50<55), S3 ma20 is NaN.
    # Valid denominator for MA20 is 2, numerator is 1 => 50.0%
    assert breadth["pct_above_ma20"] == 50.0
    # Valid denominator for MA50 is 1 (S1), numerator is 1 => 100.0%
    assert breadth["pct_above_ma50"] == 100.0


def test_contradiction_candidate_with_imminent_earnings():
    """Verify contradiction candidate marked watchlist still includes imminent earnings alert."""
    contra_stock = pd.DataFrame([{
        "symbol": "CONTR_EARN",
        "close": 100.0,
        "prev_close": 102.0,
        "volume": 500_000,
        "vol_ma20": 200_000,
        "ma20": 100.5,
        "prev_ma20": 100.0,
        "ma50": 95.0,
        "ma200": 80.0,
        "perf_1d": -1.5,
        "perf_5d": -2.0,
        "perf_20d": 8.0,
        "perf_60d": 15.0,
        "prev_high20": 105.0,
        "high20": 105.0,
        "low20": 90.0,
        "sub_industry": "Software",
        "sector": "Information Technology"
    }])
    now_dt = datetime.now()
    fa_data = {
        "CONTR_EARN": {
            "is_financial": False,
            "next_earnings_date": (now_dt + timedelta(days=3)).strftime("%Y-%m-%d"),
        }
    }
    candidates = screen_candidates(contra_stock, [], None, None, fa_data_dict=fa_data)
    assert len(candidates) == 1
    c = candidates[0]
    assert c["group_type"] == "watchlist"
    assert c["status"] == "watchlist"
    assert any("Sắp công bố BCTC" in r for r in c["technical_reasons"])




