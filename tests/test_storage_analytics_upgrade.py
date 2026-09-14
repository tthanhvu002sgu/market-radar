import pytest
import tempfile
from pathlib import Path
import sqlite3

from storage.database import init_db, get_connection
from storage.repository import MarketRadarRepository


@pytest.fixture
def temp_repo():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = Path(f.name)
    init_db(temp_path)
    repo = MarketRadarRepository(temp_path)
    yield repo, temp_path
    if temp_path.exists():
        try:
            temp_path.unlink()
        except OSError:
            pass


def test_save_and_load_snapshot_with_analytics_series(temp_repo):
    repo, db_path = temp_repo

    mock_history = {
        "records": [
            {"date": "2026-09-01", "ad_line": 100, "ad_vol_line": 50000.0, "net_breadth": 0.25, "pct_above_ma50": 60.0},
            {"date": "2026-09-02", "ad_line": 120, "ad_vol_line": 70000.0, "net_breadth": 0.35, "pct_above_ma50": 62.0},
        ],
        "start_date": "2026-09-01",
        "as_of": "2026-09-02",
        "sessions_count": 2,
        "methodology_version": "v2.1"
    }

    mock_rotation = {
        "sectors": [
            {"sector": "Information Technology", "etf": "XLK", "rotation_state": "Dẫn đầu (Leading)", "current_x": 2.5, "current_y": 0.8}
        ],
        "as_of": "2026-09-02",
        "trail_length": 10
    }

    mock_health = [
        {"sector": "Information Technology", "turnover_share_pct": 28.5, "top5_concentration_pct": 55.0, "is_divergent": False}
    ]

    snap_id = repo.save_snapshot(
        as_of="2026-09-02",
        rule_version="v2",
        total_universe=500,
        valid_universe=498,
        coverage_pct=0.996,
        missing_symbols=["BAD1"],
        market_metrics={"pct_above_ma50": 62.0, "methodology_version": "v2.1"},
        sector_metrics=[{"sector": "Information Technology", "rank": 1}],
        candidates=[],
        market_history=mock_history,
        sector_rotation=mock_rotation,
        sector_health=mock_health,
        methodology_version="v2.1"
    )

    assert snap_id > 0

    loaded = repo.get_snapshot_by_id(snap_id)
    assert loaded is not None
    assert loaded["methodology_version"] == "v2.1"
    assert loaded["market_history"] is not None
    assert len(loaded["market_history"]["records"]) == 2
    assert loaded["market_history"]["records"][1]["ad_line"] == 120

    assert loaded["sector_rotation"] is not None
    assert len(loaded["sector_rotation"]["sectors"]) == 1
    assert loaded["sector_rotation"]["sectors"][0]["rotation_state"] == "Dẫn đầu (Leading)"

    assert loaded["sector_health"] is not None
    assert loaded["sector_health"][0]["turnover_share_pct"] == 28.5


def test_backward_compatibility_old_snapshot_lacking_new_columns(temp_repo):
    """
    Acceptance Criteria 8:
    Snapshot cũ thiếu trường mới vẫn mở được, hiển thị None (Chưa tính chỉ số này).
    """
    repo, db_path = temp_repo

    # Simulate an old snapshot created without market_history, sector_rotation, sector_health
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute("""
            INSERT INTO snapshots (
                as_of, created_at, rule_version, total_universe, valid_universe,
                coverage_pct, missing_symbols, market_metrics, sector_metrics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "2026-08-01",
            "2026-08-01T16:30:00",
            "v1.0",
            500,
            495,
            0.99,
            "[]",
            '{"pct_above_ma50": 52.0}',
            "[]"
        ))
        old_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    old_snap = repo.get_snapshot_by_id(old_id)
    assert old_snap is not None
    assert old_snap["as_of"] == "2026-08-01"
    assert old_snap["market_history"] is None
    assert old_snap["sector_rotation"] is None
    assert old_snap["sector_health"] is None


def test_ui_formatting_helpers_none_safety():
    """Verify that UI formatting helpers safely produce 'N/A' without TypeError on None inputs."""
    from app.components.metrics_cards import _fmt_ret, _fmt_diff

    assert _fmt_ret(None) == "N/A"
    assert _fmt_ret(1.234) == "+1.23%"
    assert _fmt_ret(-0.5) == "-0.50%"

    assert _fmt_diff(None, 1.0) == "N/A"
    assert _fmt_diff(1.0, None) == "N/A"
    assert _fmt_diff(None, None) == "N/A"
    assert _fmt_diff(2.5, 1.0) == "+1.50% pts"
    assert _fmt_diff(1.0, 2.5) == "-1.50% pts"


def test_update_snapshot_analytics(temp_repo):
    """Verify that update_snapshot_analytics properly updates existing snapshot rows."""
    repo, db_path = temp_repo

    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute("""
            INSERT INTO snapshots (
                as_of, created_at, rule_version, total_universe, valid_universe,
                coverage_pct, missing_symbols, market_metrics, sector_metrics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "2026-08-01", "2026-08-01T16:30:00", "v1.0",
            500, 495, 0.99, "[]", '{"pct_above_ma50": 52.0}', "[]"
        ))
        old_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    mock_history = {"records": [{"date": "2026-08-01", "ad_line": 50}], "sessions_count": 1}
    mock_rotation = {"sectors": [{"sector": "Technology", "quadrant": "Leading"}], "as_of": "2026-08-01"}
    mock_health = [{"sector": "Technology", "turnover_share_pct": 30.0}]

    ok = repo.update_snapshot_analytics(
        snapshot_id=old_id,
        market_history=mock_history,
        sector_rotation=mock_rotation,
        sector_health=mock_health,
        methodology_version="v2.1"
    )
    assert ok is True

    updated = repo.get_snapshot_by_id(old_id)
    assert updated["market_history"] == mock_history
    assert updated["sector_rotation"] == mock_rotation
    assert updated["sector_health"] == mock_health
    assert updated["methodology_version"] == "v2.1"


