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
        ],
        industry_metrics=[{"industry": "Semiconductors", "comp_score": 98, "is_leading": True}]
    )

    # Verify industry_metrics persistence
    snap2 = repo.get_snapshot_by_id(snap2_id)
    assert snap2 is not None
    assert "industry_metrics" in snap2
    assert len(snap2["industry_metrics"]) == 1
    assert snap2["industry_metrics"][0]["industry"] == "Semiconductors"
    assert snap2["industry_metrics"][0]["comp_score"] == 98

    # Old snapshot without industry metrics loads safely
    snap1 = repo.get_snapshot_by_id(snap1_id)
    assert snap1 is not None
    assert snap1["industry_metrics"] == []

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


def test_d04_candidate_metadata_roundtrip_and_sorting(temp_db):
    """[D-04] Verify candidate score, rank, sub_industry, is_oneil_leader, industry_comp round-trip and score DESC ordering."""
    repo = MarketRadarRepository(temp_db)

    snap_id = repo.save_snapshot(
        as_of="2026-09-08",
        rule_version="v1.2",
        total_universe=503,
        valid_universe=500,
        coverage_pct=0.994,
        coverage_252d=0.965,
        status="complete",
        missing_symbols=[],
        market_metrics={"pct_above_ma50": 55.0},
        sector_metrics=[],
        candidates=[
            {
                "symbol": "LOWER_SCORE",
                "company_name": "Lower Score Corp",
                "sector": "Technology",
                "sub_industry": "Software",
                "group_type": "long_cont",
                "status": "confirmed",
                "close_price": 100.0,
                "perf_1d": 1.0,
                "perf_5d": 3.0,
                "perf_20d": 5.0,
                "score": 75.5,
                "is_oneil_leader": 0,
                "industry_comp": 80,
                "technical_reasons": ["Breakout"],
                "fa_flags": {},
                "short_caveat": "",
                "tv_url": "https://tradingview.com/chart/?symbol=LOWER_SCORE"
            },
            {
                "symbol": "HIGHER_SCORE",
                "company_name": "Higher Score Corp",
                "sector": "Technology",
                "sub_industry": "Semiconductors",
                "group_type": "long_cont",
                "status": "confirmed",
                "close_price": 200.0,
                "perf_1d": 2.5,
                "perf_5d": 7.0,
                "perf_20d": 15.0,
                "score": 96.2,
                "is_oneil_leader": 1,
                "industry_comp": 98,
                "technical_reasons": ["Breakout", "O'Neil Leader"],
                "fa_flags": {},
                "short_caveat": "",
                "tv_url": "https://tradingview.com/chart/?symbol=HIGHER_SCORE"
            }
        ]
    )

    # Check snapshot coverage_252d and status
    snap = repo.get_snapshot_by_id(snap_id)
    assert snap is not None
    assert abs(snap["coverage_252d"] - 0.965) < 1e-4
    assert snap["status"] == "complete"

    snaps_list = repo.get_snapshots_list(limit=5)
    assert len(snaps_list) == 1
    assert snaps_list[0]["coverage_252d"] == 0.965
    assert snaps_list[0]["status"] == "complete"

    # Check candidates retrieval & sorting order
    cands = repo.get_candidates_by_snapshot(snap_id)
    assert len(cands) == 2

    # Higher score should be rank 1 despite being inserted second
    first = cands[0]
    second = cands[1]

    assert first["symbol"] == "HIGHER_SCORE"
    assert first["rank"] == 1
    assert abs(first["score"] - 96.2) < 1e-4
    assert first["sub_industry"] == "Semiconductors"
    assert first["is_oneil_leader"] == 1
    assert first["industry_comp"] == 98

    assert second["symbol"] == "LOWER_SCORE"
    assert second["rank"] == 2
    assert abs(second["score"] - 75.5) < 1e-4
    assert second["sub_industry"] == "Software"
    assert second["is_oneil_leader"] == 0
    assert second["industry_comp"] == 80


def test_d07_safe_upsert_fundamentals_preserves_existing_data(temp_db):
    """[D-07] Verify failed/partial fundamental updates do not wipe out existing good cached data."""
    repo = MarketRadarRepository(temp_db)

    # Initial valid fetch
    initial_records = [{
        "symbol": "NVDA",
        "sector": "Technology",
        "industry": "Semiconductors",
        "revenue_growth": 0.95,
        "earnings_growth": 1.25,
        "profit_margins": 0.55,
        "operating_margins": 0.60,
        "operating_cashflow": 25_000_000_000,
        "total_debt": 10_000_000_000,
        "next_earnings_date": "2026-11-18",
        "is_financial": 0
    }]
    repo.save_fundamentals(initial_records)

    # Subsequent partial / failed update with None values
    failed_update = [{
        "symbol": "NVDA",
        "sector": "",
        "industry": "",
        "revenue_growth": None,
        "earnings_growth": None,
        "profit_margins": None,
        "operating_margins": None,
        "operating_cashflow": None,
        "total_debt": None,
        "next_earnings_date": "Chưa xác minh",
        "is_financial": 0
    }]
    repo.save_fundamentals(failed_update)

    # Verify data was preserved via COALESCE, not wiped out
    df = repo.get_fundamentals(["NVDA"])
    assert len(df) == 1
    row = df.iloc[0]
    assert abs(row["revenue_growth"] - 0.95) < 1e-4
    assert abs(row["earnings_growth"] - 1.25) < 1e-4
    assert row["next_earnings_date"] == "2026-11-18"
    assert row["sector"] == "Technology"

    # Test empty string earnings date does not overwrite
    empty_earnings_update = [{
        "symbol": "NVDA",
        "next_earnings_date": "",
    }]
    repo.save_fundamentals(empty_earnings_update)
    df_empty = repo.get_fundamentals(["NVDA"])
    assert df_empty.iloc[0]["next_earnings_date"] == "2026-11-18"

    # Test bank with is_financial=1 is not overwritten by is_financial=0
    bank_initial = [{
        "symbol": "JPM",
        "sector": "Financials",
        "industry": "Banks - Diversified",
        "is_financial": 1
    }]
    repo.save_fundamentals(bank_initial)
    bank_bad_update = [{
        "symbol": "JPM",
        "sector": "",
        "industry": "",
        "is_financial": 0
    }]
    repo.save_fundamentals(bank_bad_update)
    df_bank = repo.get_fundamentals(["JPM"])
    assert df_bank.iloc[0]["is_financial"] == 1
    assert df_bank.iloc[0]["sector"] == "Financials"


def test_get_unread_event_count(temp_db):
    """Verify get_unread_event_count behaves correctly across lifecycle, sessions, and failures."""
    repo = MarketRadarRepository(temp_db)

    # 1. Initially 0
    assert repo.get_unread_event_count() == 0
    assert repo.get_unread_event_count(session_date="2026-09-08") == 0

    # 2. Add unread events across multiple sessions
    events = [
        {
            "event_key": "2026-09-08:MSFT:breakout",
            "session_date": "2026-09-08",
            "symbol": "MSFT",
            "event_type": "new_candidate",
            "title": "Cơ hội: MSFT",
            "summary": "Breakout",
            "is_read": 0
        },
        {
            "event_key": "2026-09-08:GOOG:breakout",
            "session_date": "2026-09-08",
            "symbol": "GOOG",
            "event_type": "new_candidate",
            "title": "Cơ hội: GOOG",
            "summary": "Breakout",
            "is_read": 0
        },
        {
            "event_key": "2026-09-09:NVDA:breakout",
            "session_date": "2026-09-09",
            "symbol": "NVDA",
            "event_type": "new_candidate",
            "title": "Cơ hội: NVDA",
            "summary": "Breakout",
            "is_read": 0
        }
    ]
    repo.save_signal_events(events)

    # Global unread is 3
    assert repo.get_unread_event_count() == 3
    # Session-specific unread
    assert repo.get_unread_event_count(session_date="2026-09-08") == 2
    assert repo.get_unread_event_count(session_date="2026-09-09") == 1
    assert repo.get_unread_event_count(session_date="2026-09-10") == 0

    # 3. Mark one read in 2026-09-08
    fetched = repo.get_signal_events(session_date="2026-09-08")
    repo.mark_event_read(fetched[0]["id"])
    assert repo.get_unread_event_count(session_date="2026-09-08") == 1
    assert repo.get_unread_event_count() == 2

    # 4. Mark all read for specific session (2026-09-08)
    repo.mark_all_events_read(session_date="2026-09-08")
    assert repo.get_unread_event_count(session_date="2026-09-08") == 0
    # 2026-09-09 remains unread
    assert repo.get_unread_event_count(session_date="2026-09-09") == 1
    assert repo.get_unread_event_count() == 1

    # 5. Mark all read globally
    repo.mark_all_events_read()
    assert repo.get_unread_event_count() == 0

    # 6. Non-existent / corrupted DB safely returns 0 and does not crash
    bad_repo = MarketRadarRepository(temp_db.parent / "non_existent_dir_xyz" / "test.db")
    assert bad_repo.get_unread_event_count() == 0
    assert bad_repo.get_unread_event_count(session_date="2026-09-08") == 0
    # Mark operations should not raise exceptions
    bad_repo.mark_event_read(999)
    bad_repo.mark_all_events_read()


def test_today_dashboard_event_mark_read_and_fallback(temp_db):
    """Verify today_dashboard unread synchronization and fallback mark-all-read behavior."""
    repo = MarketRadarRepository(temp_db)

    # Session 2026-09-04 has 2 events
    events = [
        {
            "event_key": "2026-09-04:AAPL:breakout",
            "session_date": "2026-09-04",
            "symbol": "AAPL",
            "event_type": "new_candidate",
            "title": "Cơ hội: AAPL",
            "summary": "Breakout",
            "is_read": 0
        },
        {
            "event_key": "2026-09-04:MSFT:breakout",
            "session_date": "2026-09-04",
            "symbol": "MSFT",
            "event_type": "new_candidate",
            "title": "Cơ hội: MSFT",
            "summary": "Breakout",
            "is_read": 0
        }
    ]
    repo.save_signal_events(events)

    # When viewing session 2026-09-04
    as_of = "2026-09-04"
    unread_cnt = repo.get_unread_event_count(session_date=as_of)
    assert unread_cnt == 2

    # Simulate viewing a new session 2026-09-05 that has NO events yet
    empty_as_of = "2026-09-05"
    unread_empty = repo.get_unread_event_count(session_date=empty_as_of)
    assert unread_empty == 0

    # Synchronization fallback matching app/main.py:
    if unread_empty == 0 and not repo.get_signal_events(session_date=empty_as_of, limit=1):
        unread_empty = repo.get_unread_event_count()
    assert unread_empty == 2  # Matches displayed events from fallback!

    # Fallback events fetched by today_dashboard
    displayed_events = repo.get_signal_events(session_date=empty_as_of, limit=300)
    if not displayed_events:
        displayed_events = repo.get_signal_events(limit=100)
    assert len(displayed_events) == 2

    # Click "Đánh dấu tất cả đã đọc ✓" under fallback:
    event_sessions = {e["session_date"] for e in displayed_events if e.get("session_date")}
    if empty_as_of and empty_as_of in event_sessions:
        repo.mark_all_events_read(empty_as_of)
    elif event_sessions:
        for s_date in event_sessions:
            repo.mark_all_events_read(s_date)
    else:
        repo.mark_all_events_read()

    # Now all displayed events are read!
    assert repo.get_unread_event_count() == 0
    assert repo.get_unread_event_count(session_date=as_of) == 0





