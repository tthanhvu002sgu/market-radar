import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from analytics.market_participation import (
    compute_market_breadth_history,
    compute_sector_health,
    ETF_SYMBOLS
)
from config.settings import BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT


def create_mock_bars(symbol: str, prices: list, volumes: list, start_date: str = "2026-01-01") -> pd.DataFrame:
    records = []
    base_dt = datetime.strptime(start_date, "%Y-%m-%d")
    for i, (p, v) in enumerate(zip(prices, volumes)):
        d_str = (base_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        records.append({
            "symbol": symbol,
            "date": d_str,
            "open": p,
            "high": p * 1.01,
            "low": p * 0.99,
            "close": p,
            "volume": float(v)
        })
    return pd.DataFrame(records)


def test_market_breadth_history_empty():
    res = compute_market_breadth_history(pd.DataFrame())
    assert res["records"] == []
    assert res["sessions_count"] == 0


def test_market_breadth_history_etf_exclusion_and_metrics():
    """Verify that ETFs are strictly excluded from member breadth, and A/D & AD Volume are calculated accurately."""
    bars_list = []
    # 3 stocks over 30 days
    # STK1: price increasing (advances)
    stk1_prices = [100.0 + i for i in range(30)]
    stk1_vols = [1000] * 30
    bars_list.append(create_mock_bars("STK1", stk1_prices, stk1_vols))

    # STK2: price decreasing (declines)
    stk2_prices = [100.0 - i for i in range(30)]
    stk2_vols = [2000] * 30
    bars_list.append(create_mock_bars("STK2", stk2_prices, stk2_vols))

    # STK3: price flat (unchanged)
    stk3_prices = [50.0] * 30
    stk3_vols = [500] * 30
    bars_list.append(create_mock_bars("STK3", stk3_prices, stk3_vols))

    # Benchmark ETF: SPY (should be excluded from stocks breadth, but present in spy_return)
    spy_prices = [500.0 + i * 2 for i in range(30)]
    spy_vols = [50000] * 30
    bars_list.append(create_mock_bars(BENCHMARK_TICKER, spy_prices, spy_vols))

    # Equal weight ETF: RSP
    rsp_prices = [170.0 + i for i in range(30)]
    rsp_vols = [20000] * 30
    bars_list.append(create_mock_bars(BENCHMARK_EQUAL_WEIGHT, rsp_prices, rsp_vols))

    # Sector ETF: XLK
    xlk_prices = [200.0 + i for i in range(30)]
    xlk_vols = [30000] * 30
    bars_list.append(create_mock_bars("XLK", xlk_prices, xlk_vols))

    all_bars = pd.concat(bars_list, ignore_index=True)

    history = compute_market_breadth_history(all_bars, max_sessions=30)
    records = history["records"]
    assert len(records) > 0

    # On day 25 (index 24)
    # Member stocks: STK1 (+), STK2 (-), STK3 (flat) => advances=1, declines=1, unchanged=1
    # ETFs (SPY, RSP, XLK) must NOT be counted in total_evaluated or advances/declines!
    latest_rec = records[-1]
    assert latest_rec["total_evaluated"] == 3  # Only STK1, STK2, STK3
    assert latest_rec["advances"] == 1
    assert latest_rec["declines"] == 1
    assert latest_rec["unchanged"] == 1
    assert latest_rec["eligible_count"] == 3
    # Net breadth = (1 - 1) / 3 = 0.0
    assert abs(latest_rec["net_breadth"] - 0.0) < 1e-4

    # AD Volume: advancing vol = 1000, declining vol = 2000
    # ad_vol_pct = (1000 - 2000) / (1000 + 2000) * 100 = -1000 / 3000 * 100 = -33.33%
    assert abs(latest_rec["ad_vol_pct"] - (-33.33)) < 0.1
    assert latest_rec["ad_vol_adv"] == 1000.0
    assert latest_rec["ad_vol_dec"] == 2000.0

    # Benchmark returns should be recorded
    assert latest_rec["spy_return"] is not None
    assert latest_rec["rsp_return"] is not None


def test_sector_health_mega_cap_divergence():
    """
    Acceptance Criteria 1:
    Ngành tăng do một mã lớn trong khi đa số giảm phải hiện rõ phân kỳ (is_divergent = True,
    median return âm trong khi ETF dương, và top 5 concentration cao).
    """
    # 1 mega-cap stock (NVDA-like) with huge volume (+15% return)
    # 4 small member stocks (-5% return)
    # ETF (XLK) +4%
    stocks_data = [
        {"symbol": "XLK", "perf_1d": 2.0, "perf_20d": 4.0, "close": 200.0, "volume": 10_000_000, "ma20": 195.0, "ma50": 190.0, "sector": "Information Technology"},
        {"symbol": "SPY", "perf_1d": 0.5, "perf_20d": 1.0, "close": 500.0, "volume": 50_000_000, "ma20": 490.0, "ma50": 480.0, "sector": "Benchmark"},
        # Mega-cap
        {"symbol": "MEGA", "security": "Mega Corp", "perf_1d": 5.0, "perf_20d": 15.0, "close": 500.0, "volume": 10_000_000, "ma20": 450.0, "ma50": 400.0, "sector": "Information Technology"},
        # 4 declining stocks
        {"symbol": "S1", "security": "Small 1", "perf_1d": -1.0, "perf_20d": -4.0, "close": 50.0, "volume": 100_000, "ma20": 55.0, "ma50": 60.0, "sector": "Information Technology"},
        {"symbol": "S2", "security": "Small 2", "perf_1d": -2.0, "perf_20d": -6.0, "close": 40.0, "volume": 100_000, "ma20": 45.0, "ma50": 50.0, "sector": "Information Technology"},
        {"symbol": "S3", "security": "Small 3", "perf_1d": -1.5, "perf_20d": -5.0, "close": 30.0, "volume": 100_000, "ma20": 35.0, "ma50": 40.0, "sector": "Information Technology"},
        {"symbol": "S4", "security": "Small 4", "perf_1d": -2.5, "perf_20d": -8.0, "close": 20.0, "volume": 100_000, "ma20": 25.0, "ma50": 30.0, "sector": "Information Technology"},
    ]
    df_stocks = pd.DataFrame(stocks_data)

    const_data = [
        {"symbol": "MEGA", "sector": "Information Technology", "sub_industry": "Semiconductors"},
        {"symbol": "S1", "sector": "Information Technology", "sub_industry": "Software"},
        {"symbol": "S2", "sector": "Information Technology", "sub_industry": "Software"},
        {"symbol": "S3", "sector": "Information Technology", "sub_industry": "Hardware"},
        {"symbol": "S4", "sector": "Information Technology", "sub_industry": "Hardware"},
    ]
    df_const = pd.DataFrame(const_data)

    health = compute_sector_health(df_stocks, pd.DataFrame(), df_const)
    tech = next((h for h in health if h["sector"] == "Information Technology"), None)
    assert tech is not None

    # ETF is +4.0%, but median stock return is -5.0%
    assert tech["etf_1m"] == 4.0
    assert tech["median_return_1m"] == -5.0
    # Breadth on MA50 is 1/5 = 20.0%
    assert tech["breadth_ma50_pct"] == 20.0
    # Must flag divergence!
    assert tech["is_divergent"] is True
    assert "phân hóa" in tech["divergence_desc"].lower()

    # Top stock concentration: MEGA has 500 * 10M = 5B turnover, others have ~10M turnover
    assert tech["top5_concentration_pct"] >= 95.0
    assert tech["top5_stocks"][0]["symbol"] == "MEGA"


def test_sector_breadth_denominator_excludes_missing_ma():
    """
    Acceptance Criteria 2:
    Mã thiếu MA50 không bị tính là dưới MA50. Mẫu số chỉ tính mã đủ điều kiện.
    """
    stocks_data = [
        {"symbol": "XLK", "perf_1d": 1.0, "perf_20d": 2.0, "close": 200.0, "volume": 1000, "sector": "Information Technology"},
        # S1: has MA50 (100 > 90 => above MA50)
        {"symbol": "S1", "perf_1d": 1.0, "perf_20d": 2.0, "close": 100.0, "volume": 1000, "ma50": 90.0, "sector": "Information Technology"},
        # S2: has MA50 (50 < 60 => below MA50)
        {"symbol": "S2", "perf_1d": -1.0, "perf_20d": -2.0, "close": 50.0, "volume": 1000, "ma50": 60.0, "sector": "Information Technology"},
        # S3: lacks MA50 (NaN) - MUST NOT be treated as below MA50!
        {"symbol": "S3", "perf_1d": 0.5, "perf_20d": 1.0, "close": 80.0, "volume": 1000, "ma50": np.nan, "sector": "Information Technology"},
    ]
    df_stocks = pd.DataFrame(stocks_data)
    df_const = pd.DataFrame([{"symbol": f"S{i}", "sector": "Information Technology", "sub_industry": "Ind"} for i in range(1, 4)])

    health = compute_sector_health(df_stocks, pd.DataFrame(), df_const)
    tech = next(h for h in health if h["sector"] == "Information Technology")

    assert tech["member_count"] == 3
    assert tech["valid_ma50_count"] == 2
    # Breadth should be 1 / 2 * 100 = 50.0%, NOT 1 / 3 = 33.3%!
    assert tech["breadth_ma50_pct"] == 50.0


def test_market_breadth_history_point_in_time_as_of():
    """Verify that compute_market_breadth_history with as_of strictly ignores future bars."""
    bars_list = []
    # 40 days of bars
    stk1 = create_mock_bars("STK1", [100.0 + i for i in range(40)], [1000] * 40, start_date="2026-01-01")
    spy = create_mock_bars(BENCHMARK_TICKER, [500.0 + i for i in range(40)], [10000] * 40, start_date="2026-01-01")
    all_bars = pd.concat([stk1, spy], ignore_index=True)

    as_of_date = (datetime(2026, 1, 1) + timedelta(days=25)).strftime("%Y-%m-%d")

    res = compute_market_breadth_history(all_bars, as_of=as_of_date)
    assert res["as_of"] == as_of_date
    assert len(res["records"]) > 0
    # Last record date must not exceed as_of_date
    assert res["records"][-1]["date"] == as_of_date
    for r in res["records"]:
        assert r["date"] <= as_of_date


def test_sector_health_missing_ma50_no_false_divergence_and_note():
    """Missing MA50 data returns None for breadth_ma50_pct and does NOT falsely trigger divergence."""
    stocks_data = [
        {"symbol": "XLK", "perf_1d": 1.0, "perf_20d": 5.0, "close": 200.0, "volume": 1000, "sector": "Information Technology"},
        {"symbol": "S1", "perf_1d": 1.0, "perf_20d": 4.0, "close": 100.0, "volume": 1000, "ma50": np.nan, "sector": "Information Technology"},
        {"symbol": "S2", "perf_1d": 1.2, "perf_20d": 4.5, "close": 110.0, "volume": 1000, "ma50": np.nan, "sector": "Information Technology"},
    ]
    df_stocks = pd.DataFrame(stocks_data)
    df_const = pd.DataFrame([{"symbol": f"S{i}", "sector": "Information Technology", "sub_industry": "Ind"} for i in range(1, 3)])

    health = compute_sector_health(df_stocks, pd.DataFrame(), df_const)
    tech = next(h for h in health if h["sector"] == "Information Technology")

    assert tech["breadth_ma50_pct"] is None
    # With positive returns and no MA50, it must NOT flag false divergence!
    assert tech["is_divergent"] is False
    assert "constituents_note" in tech
    assert "tập thành viên S&P 500 hiện tại" in tech["constituents_note"]


def test_market_breadth_skipped_session_excluded_from_1d():
    """
    Acceptance Criteria (Issue 3):
    Thiếu một phiên bị tính thành lợi suất một ngày:
    Nếu cổ phiếu có giá thứ Hai và thứ Tư nhưng thiếu thứ Ba, lợi suất hai phiên
    phải bị LOẠI KHỎI mẫu số 1D (breadth, advances/declines, equal-weight return, median return).
    """
    # Calendar: 2026-02-02 (Mon), 2026-02-03 (Tue), 2026-02-04 (Wed)
    # SPY has all 3 days
    spy_bars = pd.DataFrame([
        {"symbol": BENCHMARK_TICKER, "date": "2026-02-02", "open": 500.0, "high": 505.0, "low": 495.0, "close": 500.0, "volume": 10000.0},
        {"symbol": BENCHMARK_TICKER, "date": "2026-02-03", "open": 500.0, "high": 505.0, "low": 495.0, "close": 502.0, "volume": 10000.0},
        {"symbol": BENCHMARK_TICKER, "date": "2026-02-04", "open": 502.0, "high": 506.0, "low": 500.0, "close": 504.0, "volume": 10000.0},
    ])

    # STK_A trades every day: 100 -> 105 (+5%) -> 110.25 (+5%)
    stk_a_bars = pd.DataFrame([
        {"symbol": "STK_A", "date": "2026-02-02", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000.0},
        {"symbol": "STK_A", "date": "2026-02-03", "open": 100.0, "high": 106.0, "low": 100.0, "close": 105.0, "volume": 1000.0},
        {"symbol": "STK_A", "date": "2026-02-04", "open": 105.0, "high": 111.0, "low": 105.0, "close": 110.25, "volume": 1000.0},
    ])

    # STK_B trades Mon ($100), MISSES Tue, trades Wed ($120)
    # Return from Mon to Wed is +20%, but it is a 2-day return, NOT a 1D return!
    stk_b_bars = pd.DataFrame([
        {"symbol": "STK_B", "date": "2026-02-02", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000.0},
        {"symbol": "STK_B", "date": "2026-02-04", "open": 105.0, "high": 121.0, "low": 105.0, "close": 120.0, "volume": 1000.0},
    ])

    all_bars = pd.concat([spy_bars, stk_a_bars, stk_b_bars], ignore_index=True)
    history = compute_market_breadth_history(all_bars)
    records = history["records"]

    # Session 2026-02-04 (Wed)
    wed_rec = next(r for r in records if r["date"] == "2026-02-04")

    # STK_B MUST NOT be in valid_1d on Wednesday!
    # Only STK_A is valid for 1D:
    assert wed_rec["valid_count"] == 1
    assert wed_rec["eligible_count"] == 1
    assert wed_rec["advances"] == 1
    assert wed_rec["declines"] == 0
    assert wed_rec["net_breadth"] == 1.0  # (1 - 0) / 1

    # Equal weight return and median return MUST reflect only STK_A (+5.0%), NOT STK_B (+20%)!
    assert wed_rec["equal_weight_return"] == 5.0
    assert wed_rec["median_return"] == 5.0

    # STK_B must be counted in missing_count for 1D
    assert wed_rec["missing_count"] == 1


def test_market_breadth_universe_missing_bars_count():
    """
    Acceptance Criteria (Issue 4):
    Coverage lịch sử bỏ sót mã không có bar:
    Với universe hai mã nhưng chỉ một mã có bar, kết quả phải báo missing_count >= 1
    và tách rõ expected_count = 2, bars_count = 1, missing_bars_count = 1.
    """
    # Universe of 2 stocks defined in constituents_df
    const_df = pd.DataFrame([
        {"symbol": "STK1", "sector": "Technology", "sub_industry": "Software"},
        {"symbol": "STK2", "sector": "Technology", "sub_industry": "Software"},
    ])

    # Day 1: both STK1 and STK2 have bars
    # Day 2: only STK1 has a bar; STK2 is completely missing
    bars_df = pd.DataFrame([
        {"symbol": "STK1", "date": "2026-03-02", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000.0},
        {"symbol": "STK2", "date": "2026-03-02", "open": 50.0, "high": 51.0, "low": 49.0, "close": 50.0, "volume": 1000.0},
        {"symbol": "STK1", "date": "2026-03-03", "open": 100.0, "high": 103.0, "low": 100.0, "close": 102.0, "volume": 1000.0},
        # STK2 has NO bar on 2026-03-03!
    ])

    history = compute_market_breadth_history(bars_df, constituents_df=const_df)
    day2_rec = next(r for r in history["records"] if r["date"] == "2026-03-03")

    # Expected count = 2
    assert day2_rec["expected_count"] == 2
    assert day2_rec["total_evaluated"] == 2

    # Bars count = 1 (only STK1)
    assert day2_rec["bars_count"] == 1
    assert day2_rec["missing_bars_count"] == 1

    # Missing count must be 1, NOT 0!
    assert day2_rec["missing_count"] == 1
    assert day2_rec["coverage_pct"] == 50.0


def test_compute_market_breadth_with_constituents_universe():
    """Verify compute_market_breadth accurately counts expected_count and missing_bars_count when constituents_df is provided."""
    from analytics.market_breadth import compute_market_breadth

    const_df = pd.DataFrame([
        {"symbol": "STK1", "sector": "Technology", "sub_industry": "Software"},
        {"symbol": "STK2", "sector": "Technology", "sub_industry": "Software"},
        {"symbol": "STK3", "sector": "Technology", "sub_industry": "Software"},
    ])

    # Only STK1 has bars in latest_stocks_df
    latest_df = pd.DataFrame([
        {"symbol": "STK1", "close": 100.0, "ma20": 95.0, "ma50": 90.0, "ma200": 80.0, "perf_1d": 1.5, "perf_20d": 5.0, "perf_252d": 20.0, "high20": 105.0, "low20": 95.0, "volume": 1000.0}
    ])

    breadth = compute_market_breadth(latest_df, pd.DataFrame(), constituents_df=const_df)
    assert breadth["expected_count"] == 3
    assert breadth["bars_count"] == 1
    assert breadth["missing_bars_count"] == 2
    assert breadth["valid_count"] == 1
    assert breadth["missing_count"] == 2
    assert breadth["total_evaluated"] == 3



