from analytics.order_flow_imbalance import aggregate_ofi_buckets, compute_ofi_events
from analytics.order_flow_imbalance import compute_ofi_from_quotes
from storage.ofi_store import OfiHistoryRepository
from tests.test_order_flow_imbalance import base_quote_stream


def test_ofi_store_roundtrip(tmp_path):
    store = OfiHistoryRepository(db_path=tmp_path / "ofi_test.db")

    metrics = compute_ofi_from_quotes(base_quote_stream(), symbol="TEST")
    events = compute_ofi_events(base_quote_stream())
    buckets = aggregate_ofi_buckets(events, bucket_seconds=60)

    records = []
    for _, row in buckets.iterrows():
        records.append({
            "symbol": "TEST",
            "ts": str(row["ts"]),
            "session_date": "2026-01-05",
            "ofi": float(row["ofi"]),
            "n_updates": int(row["n_updates"]),
            "spread_avg": float(row["spread_avg"]),
            "bid_size_last": float(row["bid_size_last"]),
            "ask_size_last": float(row["ask_size_last"]),
            "mid_first": float(row["mid_first"]),
            "mid_last": float(row["mid_last"]),
            "source": "iex",
        })
    saved = store.save_ofi_minutes(records)
    assert saved == 2

    # Idempotent: lưu lại không nhân đôi
    store.save_ofi_minutes(records)

    history = store.get_ofi_history(symbols=["TEST"])
    assert len(history) == 2
    assert history["ofi"].sum() == metrics["integrated_ofi"]
    assert history["cum_ofi"].iloc[-1] == metrics["integrated_ofi"]
    assert history["session_date"].eq("2026-01-05").all()


def test_ofi_store_cursor(tmp_path):
    store = OfiHistoryRepository(db_path=tmp_path / "ofi_test.db")
    assert store.get_cursor("AAPL") is None
    store.save_cursor("AAPL", "2026-01-05T14:31:30Z")
    assert store.get_cursor("AAPL") == "2026-01-05T14:31:30Z"
    store.save_cursor("AAPL", "2026-01-05T15:00:00Z")  # replace
    assert store.get_cursor("AAPL") == "2026-01-05T15:00:00Z"


def test_ofi_store_session_summaries(tmp_path):
    store = OfiHistoryRepository(db_path=tmp_path / "ofi_test.db")
    base = {
        "symbol": "TEST", "session_date": "2026-01-05",
        "n_updates": 1, "spread_avg": 0.02, "bid_size_last": 100,
        "ask_size_last": 100, "mid_first": 100.0, "mid_last": 100.0, "source": "iex",
    }
    store.save_ofi_minutes([
        {**base, "ts": "2026-01-05T14:30:00Z", "ofi": 200.0},
        {**base, "ts": "2026-01-05T14:31:00Z", "ofi": -50.0},
    ])
    store.save_ofi_minutes([
        {**base, "symbol": "OTHER", "ts": "2026-01-05T14:30:00Z", "ofi": -300.0},
    ])

    summaries = store.get_session_summaries("2026-01-05")
    assert len(summaries) == 2
    test_row = summaries[summaries["symbol"] == "TEST"].iloc[0]
    assert test_row["integrated_ofi"] == 150.0
    assert test_row["imbalance_ratio"] == (150.0 / 250.0)
    assert test_row["n_minutes"] == 2
    assert store.get_session_dates() == ["2026-01-05"]


def test_ofi_store_empty_history(tmp_path):
    store = OfiHistoryRepository(db_path=tmp_path / "ofi_test.db")
    assert store.get_ofi_history().empty
    assert store.get_session_summaries().empty
    assert store.get_session_dates() == []


def test_ofi_store_cumsum_resets_per_session(tmp_path):
    """cum_ofi phải reset theo từng phiên — lũy kế xuyên phiên là vô nghĩa."""
    store = OfiHistoryRepository(db_path=tmp_path / "ofi_test.db")
    base = {
        "symbol": "TEST", "n_updates": 1, "spread_avg": 0.02,
        "bid_size_last": 100, "ask_size_last": 100,
        "mid_first": 100.0, "mid_last": 100.0, "source": "iex",
    }
    store.save_ofi_minutes([
        {**base, "session_date": "2026-01-05", "ts": "2026-01-05T14:30:00Z", "ofi": 100.0},
        {**base, "session_date": "2026-01-05", "ts": "2026-01-05T14:31:00Z", "ofi": 50.0},
        {**base, "session_date": "2026-01-06", "ts": "2026-01-06T14:30:00Z", "ofi": 200.0},
    ])
    history = store.get_ofi_history(symbols=["TEST"])
    by_ts = history.set_index("ts")["cum_ofi"].to_dict()
    assert by_ts["2026-01-05T14:30:00Z"] == 100.0
    assert by_ts["2026-01-05T14:31:00Z"] == 150.0
    assert by_ts["2026-01-06T14:30:00Z"] == 200.0  # reset, không cộng dồn 350
