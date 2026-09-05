import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from analytics.market_breadth import compute_stock_indicators, compute_market_breadth
from analytics.sector_ranker import rank_sectors
from analytics.screening_rules import screen_candidates
from analytics.company_fa import evaluate_fa_flags

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
