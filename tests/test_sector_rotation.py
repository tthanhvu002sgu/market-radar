import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from analytics.sector_rotation import compute_sector_rotation
from config.settings import BENCHMARK_TICKER


def create_sector_bars(symbol: str, base_price: float, daily_ret: float, n_days: int = 40, start_date: str = "2026-01-01") -> pd.DataFrame:
    base_dt = datetime.strptime(start_date, "%Y-%m-%d")
    records = []
    p = base_price
    for i in range(n_days):
        d_str = (base_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        p = p * (1.0 + daily_ret)
        records.append({
            "symbol": symbol,
            "date": d_str,
            "open": p,
            "high": p * 1.01,
            "low": p * 0.99,
            "close": p,
            "volume": 1_000_000.0
        })
    return pd.DataFrame(records)


def test_sector_rotation_empty():
    res = compute_sector_rotation(pd.DataFrame())
    assert res["sectors"] == []


def test_sector_rotation_missing_benchmark():
    """
    Acceptance Criteria 3:
    Thiếu benchmark không tạo RS bằng 0 hoặc trạng thái rotation giả.
    """
    # Bars contain XLK but not SPY
    xlk_bars = create_sector_bars("XLK", 200.0, 0.005, n_days=30)
    res = compute_sector_rotation(xlk_bars)
    assert res.get("error") == "Thiếu dữ liệu benchmark SPY." or res["sectors"] == []


def test_sector_rotation_defensive_regime_and_negative_return():
    """
    Acceptance Criteria 4:
    Ngành giảm ít hơn SPY có thể mạnh tương đối (RS dương), nhưng vẫn hiện lợi suất âm.
    """
    # SPY declines 1% daily (-0.01)
    spy_bars = create_sector_bars(BENCHMARK_TICKER, 500.0, -0.01, n_days=35)
    # XLU (Utilities) declines 0.2% daily (-0.002) - falling much less than SPY
    xlu_bars = create_sector_bars("XLU", 70.0, -0.002, n_days=35)

    all_bars = pd.concat([spy_bars, xlu_bars], ignore_index=True)
    res = compute_sector_rotation(all_bars)

    xlu = next((s for s in res["sectors"] if s["etf"] == "XLU"), None)
    assert xlu is not None

    # Ratio R_t = XLU / SPY is increasing because XLU falls less than SPY
    # Thus X_t should be positive
    assert xlu["current_x"] is not None
    assert xlu["current_x"] > 0
    # But absolute return of XLU must be negative!
    assert xlu["etf_20d"] < 0
    # Context should describe defensive outperformance
    assert "phòng thủ" in xlu["regime"].lower() or "giảm ít hơn" in xlu["regime"].lower()


def test_sector_rotation_point_in_time_no_future_leakage():
    """
    Acceptance Criteria 5:
    Thêm dữ liệu tương lai không làm thay đổi kết quả đã lưu của snapshot cũ.
    (compute_sector_rotation with as_of strictly filters out future dates).
    """
    spy_bars = create_sector_bars(BENCHMARK_TICKER, 500.0, 0.002, n_days=50, start_date="2026-01-01")
    xlk_bars = create_sector_bars("XLK", 200.0, 0.004, n_days=50, start_date="2026-01-01")
    all_bars = pd.concat([spy_bars, xlk_bars], ignore_index=True)

    # Date at day 30
    as_of_date = (datetime(2026, 1, 1) + timedelta(days=30)).strftime("%Y-%m-%d")

    # Rotation computed point-in-time up to as_of_date
    res_pit = compute_sector_rotation(all_bars, as_of=as_of_date, trail_length=10)
    xlk_pit = next(s for s in res_pit["sectors"] if s["etf"] == "XLK")

    # Date of last point in trail must be as_of_date
    assert xlk_pit["trail"][-1]["date"] == as_of_date
    assert len(xlk_pit["trail"]) == 10

    # If we filter the DataFrame itself to as_of_date, the result must be bit-for-bit identical!
    all_bars_filtered = all_bars[all_bars["date"] <= as_of_date].copy()
    res_frozen = compute_sector_rotation(all_bars_filtered, as_of=as_of_date, trail_length=10)
    xlk_frozen = next(s for s in res_frozen["sectors"] if s["etf"] == "XLK")

    assert xlk_pit["current_x"] == xlk_frozen["current_x"]
    assert xlk_pit["current_y"] == xlk_frozen["current_y"]
    assert xlk_pit["rotation_state"] == xlk_frozen["rotation_state"]


def test_sector_rotation_handles_insufficient_trail_without_dropping_sector():
    """Verify that an ETF with insufficient history is still included in sectors list instead of silently dropped."""
    spy_bars = create_sector_bars(BENCHMARK_TICKER, 500.0, 0.001, n_days=35)
    # XLK has only 3 bars (not enough for 20 EMA)
    xlk_short_bars = create_sector_bars("XLK", 200.0, 0.002, n_days=3)
    # XLE has enough bars
    xle_bars = create_sector_bars("XLE", 90.0, 0.001, n_days=35)

    all_bars = pd.concat([spy_bars, xlk_short_bars, xle_bars], ignore_index=True)
    res = compute_sector_rotation(all_bars)

    # XLK must be in sectors!
    xlk_res = next((s for s in res["sectors"] if s["etf"] == "XLK"), None)
    assert xlk_res is not None
    assert "Chưa xác minh" in xlk_res["rotation_state"]
    assert xlk_res["trail"] == []


def test_sector_rotation_stale_etf_marked_unverified_and_excluded_from_ranking():
    """
    Acceptance Criteria:
    ETF có dữ liệu kết thúc trước phiên mục tiêu (lệch phiên) phải bị gắn stale/chưa xác minh,
    không được xếp hạng cùng các ngành đồng phiên (current_x is None, current_y is None),
    và xếp ở cuối danh sách.
    """
    # SPY has 44 days up to 2026-02-25 (start 2026-01-13)
    start_dt = "2026-01-13"
    spy_bars = create_sector_bars(BENCHMARK_TICKER, 500.0, 0.001, n_days=44, start_date=start_dt)
    target_date = spy_bars["date"].iloc[-1]
    assert target_date == "2026-02-25"

    # XLE is fresh: has 44 days up to 2026-02-25
    xle_bars = create_sector_bars("XLE", 90.0, 0.002, n_days=44, start_date=start_dt)

    # XLK has 30 bars (>= 25) but ends on 2026-02-11 (stale by 14 days)
    xlk_stale_bars = create_sector_bars("XLK", 200.0, 0.003, n_days=30, start_date=start_dt)
    assert xlk_stale_bars["date"].iloc[-1] == "2026-02-11"

    all_bars = pd.concat([spy_bars, xle_bars, xlk_stale_bars], ignore_index=True)
    res = compute_sector_rotation(all_bars)

    assert res["as_of"] == target_date

    # XLK must be flagged as stale / unverified
    xlk_sec = next(s for s in res["sectors"] if s["etf"] == "XLK")
    assert xlk_sec["is_stale"] is True
    assert "Chưa xác minh" in xlk_sec["rotation_state"]
    assert "Lệch phiên" in xlk_sec["rotation_state"] or "Dữ liệu cũ" in xlk_sec["rotation_state"]
    assert xlk_sec["current_x"] is None
    assert xlk_sec["current_y"] is None
    assert xlk_sec["etf_1d"] is None
    assert xlk_sec["etf_20d"] is None
    assert xlk_sec["trail"] == []

    # XLE must be fresh and verified
    xle_sec = next(s for s in res["sectors"] if s["etf"] == "XLE")
    assert xle_sec["is_stale"] is False
    assert xle_sec["current_x"] is not None
    assert xle_sec["current_y"] is not None
    assert len(xle_sec["trail"]) > 0

    # Sector ranking order: XLE (valid) must appear BEFORE XLK (stale)
    xle_idx = next(i for i, s in enumerate(res["sectors"]) if s["etf"] == "XLE")
    xlk_idx = next(i for i, s in enumerate(res["sectors"]) if s["etf"] == "XLK")
    assert xle_idx < xlk_idx

    # Valid ETF is ranked, stale ETF is unranked (rank is None, is_ranked is False)
    assert xle_sec["rank"] == 1
    assert xle_sec["is_ranked"] is True
    assert xlk_sec["rank"] is None
    assert xlk_sec["is_ranked"] is False


def test_sector_rotation_calendar_gap_prevents_multi_day_1d_return():
    """
    Acceptance Criteria (Issue 3 Part B):
    Kiểm tra tương tự cho các kỳ hạn rotation:
    Khi ETF hoặc benchmark thiếu 1 phiên trước liền kề (gap trong trading calendar),
    lợi suất 1D (etf_1d) tại phiên tiếp theo phải trả về None thay vì tính gộp lợi suất đa phiên.
    """
    dates = [f"2026-01-{i:02d}" for i in range(1, 31)]

    # Market anchor has all 30 days
    anchor_bars = pd.DataFrame([
        {"symbol": "ANCHOR", "date": d, "close": 100.0, "open": 100.0, "high": 101.0, "low": 99.0, "volume": 1000.0}
        for d in dates
    ])

    # SPY has all 30 days
    spy_bars = pd.DataFrame([
        {"symbol": BENCHMARK_TICKER, "date": d, "close": 500.0 + i, "open": 500.0, "high": 505.0, "low": 495.0, "volume": 10000.0}
        for i, d in enumerate(dates)
    ])

    # XLK trades day 1..28, MISSES day 29, trades day 30
    xlk_dates = [d for d in dates if d != "2026-01-29"]
    xlk_bars = pd.DataFrame([
        {"symbol": "XLK", "date": d, "close": 200.0 + i, "open": 200.0, "high": 205.0, "low": 195.0, "volume": 1000.0}
        for i, d in enumerate(xlk_dates)
    ])

    all_bars = pd.concat([anchor_bars, spy_bars, xlk_bars], ignore_index=True)
    res = compute_sector_rotation(all_bars)

    xlk_sec = next(s for s in res["sectors"] if s["etf"] == "XLK")
    # On day 30, because day 29 was missed, 1D return MUST be None, not 2-day return!
    assert xlk_sec["etf_1d"] is None



