import os
import pytest
import tempfile
from pathlib import Path

from storage.database import init_db, get_connection
from storage.repository import MarketRadarRepository
from storage.lock import ProcessLock

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = Path(f.name)
    init_db(temp_path)
    yield temp_path
    if temp_path.exists():
        try:
            temp_path.unlink()
        except OSError:
            pass

def test_init_db_and_constituents(temp_db):
    repo = MarketRadarRepository(temp_db)
    records = [
        {"symbol": "AAPL", "security": "Apple Inc.", "sector": "Information Technology", "sub_industry": "Technology Hardware", "date_added": "1982-11-30", "cik": "320193"},
        {"symbol": "JPM", "security": "JPMorgan Chase", "sector": "Financials", "sub_industry": "Diversified Banks", "date_added": "1975-06-30", "cik": "19617"}
    ]
    count = repo.save_constituents(records)
    assert count == 2

    df = repo.get_constituents()
    assert len(df) == 2
    assert "AAPL" in df["symbol"].values
    assert "JPM" in df["symbol"].values

def test_daily_bars_storage(temp_db):
    repo = MarketRadarRepository(temp_db)
    bars = [
        ("AAPL", "2026-09-01", 150.0, 155.0, 149.0, 154.0, 1000000.0),
        ("AAPL", "2026-09-02", 154.0, 156.0, 153.0, 155.5, 1200000.0),
    ]
    saved = repo.save_daily_bars(bars)
    assert saved == 2

    df = repo.get_daily_bars(["AAPL"])
    assert len(df) == 2
    assert repo.get_latest_bar_date() == "2026-09-02"

def test_snapshot_lifecycle_and_diff(temp_db):
    repo = MarketRadarRepository(temp_db)

    # Snapshot 1
    snap1_id = repo.save_snapshot(
        as_of="2026-09-01",
        rule_version="v1.0",
        total_universe=500,
        valid_universe=498,
        coverage_pct=0.996,
        missing_symbols=["BAD1", "BAD2"],
        market_metrics={"pct_above_ma50": 55.0},
        sector_metrics=[{"sector": "Technology", "rank": 1}, {"sector": "Financials", "rank": 2}],
        candidates=[
            {"symbol": "NVDA", "company_name": "NVIDIA", "sector": "Technology", "group_type": "long_cont", "status": "confirmed", "close_price": 120.0, "perf_1d": 2.0, "perf_5d": 5.0, "perf_20d": 15.0, "technical_reasons": ["Breakout"], "fa_flags": {}, "short_caveat": "", "tv_url": "https://tradingview.com"},
            {"symbol": "INTC", "company_name": "Intel", "sector": "Technology", "group_type": "short_cont", "status": "confirmed", "close_price": 20.0, "perf_1d": -1.0, "perf_5d": -3.0, "perf_20d": -10.0, "technical_reasons": ["Breakdown"], "fa_flags": {}, "short_caveat": "Chưa xác minh phí vay", "tv_url": "https://tradingview.com"},
        ]
    )
    assert snap1_id > 0

    # Snapshot 2
    snap2_id = repo.save_snapshot(
        as_of="2026-09-02",
        rule_version="v1.0",
        total_universe=500,
        valid_universe=499,
        coverage_pct=0.998,
        missing_symbols=["BAD1"],
        market_metrics={"pct_above_ma50": 58.0},
        sector_metrics=[{"sector": "Financials", "rank": 1}, {"sector": "Technology", "rank": 2}],
        candidates=[
            {"symbol": "NVDA", "company_name": "NVIDIA", "sector": "Technology", "group_type": "long_cont", "status": "confirmed", "close_price": 125.0, "perf_1d": 4.0, "perf_5d": 8.0, "perf_20d": 20.0, "technical_reasons": ["Continuation"], "fa_flags": {}, "short_caveat": "", "tv_url": "https://tradingview.com"},
            {"symbol": "AAPL", "company_name": "Apple", "sector": "Technology", "group_type": "long_rev", "status": "watchlist", "close_price": 160.0, "perf_1d": 1.5, "perf_5d": 2.0, "perf_20d": 5.0, "technical_reasons": ["Reclaim MA20"], "fa_flags": {}, "short_caveat": "", "tv_url": "https://tradingview.com"},
        ]
    )

    diff = repo.get_snapshot_diff(snap2_id, snap1_id)
    # AAPL was added, INTC was removed, NVDA retained
    added_syms = [a["symbol"] for a in diff["added"]]
    removed_syms = [r["symbol"] for r in diff["removed"]]
    retained_syms = [m["symbol"] for m in diff["retained"]]

    assert "AAPL" in added_syms
    assert "INTC" in removed_syms
    assert "NVDA" in retained_syms

    # Sector moves: Financials improved from rank 2 to 1 (+1 change)
    fin_move = next(m for m in diff["sector_moves"] if m["sector"] == "Financials")
    assert fin_move["old_rank"] == 2
    assert fin_move["new_rank"] == 1
    assert fin_move["change"] == 1

def test_process_lock():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "test.lock"
        lock1 = ProcessLock(lock_file, timeout_seconds=10)
        assert lock1.acquire() is True

        # Second lock attempt must fail
        lock2 = ProcessLock(lock_file, timeout_seconds=10)
        assert lock2.acquire() is False

        lock1.release()
        assert lock2.acquire() is True
        lock2.release()
