import pytest
from storage.repository import MarketRadarRepository

def test_live_database_snapshots():
    repo = MarketRadarRepository()
    snapshots = repo.get_snapshots_list()
    assert len(snapshots) >= 1

    latest = repo.get_latest_snapshot()
    assert latest is not None
    assert latest["valid_universe"] >= 450
    assert latest["coverage_pct"] >= 0.95

    # Check market metrics
    metrics = latest["market_metrics"]
    assert "pct_above_ma50" in metrics
    assert "market_summary" in metrics

    # Check sectors
    sectors = latest["sector_metrics"]
    assert len(sectors) == 11

    # Check candidates
    candidates = repo.get_candidates_by_snapshot(latest["id"])
    assert len(candidates) > 0
    for c in candidates:
        assert "symbol" in c
        assert "group_type" in c
        assert "tv_url" in c
        assert "https://www.tradingview.com" in c["tv_url"]
        assert "interval=D" in c["tv_url"]
