import pandas as pd
import pytest

from analytics.order_flow_imbalance import (
    aggregate_ofi_buckets,
    compute_ofi_events,
    compute_ofi_from_quotes,
    compute_ofi_metrics,
)


def make_quote(ts, bp, bs, ap, as_, symbol="TEST"):
    return {
        "symbol": symbol,
        "timestamp": pd.Timestamp(ts, tz="UTC"),
        "bid_price": bp,
        "bid_size": bs,
        "ask_price": ap,
        "ask_size": as_,
    }


def base_quote_stream():
    """Stream quote nhỏ, e_n tính tay theo công thức CKS:
    r1: bid +100 & ask -100 (cùng giá)        -> e = +200
    r2: bid nhảy lên mức giá mới (size 300)   -> e = +300
    r3: bid side rỗng hoá tại cùng mức giá    -> e = -300
    r4: ask rời lên mức mới, bid cũ đã rỗng   -> e = +400
    """
    return pd.DataFrame([
        make_quote("2026-01-05 14:30:01", 100.00, 500, 100.02, 500),  # base (bị loại)
        make_quote("2026-01-05 14:30:02", 100.00, 600, 100.02, 400),
        make_quote("2026-01-05 14:30:03", 100.01, 300, 100.02, 400),
        make_quote("2026-01-05 14:30:04", 100.01, 0, 100.02, 400),
        make_quote("2026-01-05 14:31:30", 99.99, 200, 100.05, 700),
    ])


def test_ofi_events_cks_formula():
    events = compute_ofi_events(base_quote_stream())
    assert list(events["e"].round(6)) == [200.0, 300.0, -300.0, 400.0]
    assert events.iloc[0]["spread"] == pytest.approx(0.02)


def test_ofi_events_empty_and_single_quote():
    assert compute_ofi_events(pd.DataFrame()).empty
    single = pd.DataFrame([make_quote("2026-01-05 14:30:01", 100.0, 500, 100.02, 500)])
    assert compute_ofi_events(single).empty


def test_ofi_events_filters_crossed_invalid_and_empty_quotes():
    df = pd.DataFrame([
        make_quote("2026-01-05 14:30:01", 100.00, 500, 100.02, 500),  # base
        make_quote("2026-01-05 14:30:02", 100.06, 300, 100.05, 400),  # cross (bp > ap) -> loại
        make_quote("2026-01-05 14:30:03", -1.0, 300, 100.02, 400),    # giá âm -> loại
        make_quote("2026-01-05 14:30:04", 0.0, 0, 0.0, 0),            # cả 2 bên rỗng -> loại
        make_quote("2026-01-05 14:30:05", 100.00, 700, 100.02, 500),
    ])
    events = compute_ofi_events(df)
    # Chỉ còn base + quote cuối -> 1 event: bid +200, ask 0
    assert len(events) == 1
    assert events.iloc[0]["e"] == 200.0


def test_ofi_events_keeps_one_sided_and_locked_quotes():
    """Quote một bên rỗng (giá 0) và quote locked phải được giữ — là event OFI thật."""
    df = pd.DataFrame([
        make_quote("2026-01-05 14:30:01", 100.00, 500, 100.02, 500),  # base
        # Bid bị rút sạch (giá 0, size 0): bid_term = -500, ask_term = 400-500 = -100
        make_quote("2026-01-05 14:30:02", 0.0, 0, 100.02, 400),
        # Bid quay lại thấp hơn: bid_term = +300 (từ size 0)
        make_quote("2026-01-05 14:30:03", 99.99, 300, 100.02, 400),
        # Locked (bid == ask = 100.00): bid +300-0, ask +200-0 -> e = +100
        make_quote("2026-01-05 14:30:04", 100.00, 300, 100.00, 200),
    ])
    events = compute_ofi_events(df)
    assert list(events["e"]) == [-400.0, 300.0, 100.0]
    # Quote một bên rỗng: mid/spread không xác định -> NaN
    assert pd.isna(events.iloc[0]["mid_price"])
    assert pd.isna(events.iloc[0]["spread"])
    # Quote locked: spread = 0
    assert events.iloc[2]["spread"] == pytest.approx(0.0)


def test_aggregate_buckets_sums_by_minute():
    events = compute_ofi_events(base_quote_stream())
    buckets = aggregate_ofi_buckets(events, bucket_seconds=60)
    assert len(buckets) == 2
    row0, row1 = buckets.iloc[0], buckets.iloc[1]
    assert row0["ofi"] == 200.0 and row0["n_updates"] == 3  # 14:30: +200+300-300
    assert row1["ofi"] == 400.0 and row1["n_updates"] == 1  # 14:31
    assert row0["mid_first"] == pytest.approx(100.01)  # mid của event đầu bucket


def test_metrics_basic_values():
    events = compute_ofi_events(base_quote_stream())
    buckets = aggregate_ofi_buckets(events, bucket_seconds=60)
    m = compute_ofi_metrics(buckets, zscore_window=60, symbol="TEST")
    assert m["status"] == "ok"
    assert m["symbol"] == "TEST"
    assert m["integrated_ofi"] == 600.0
    # OFI các phút [200, 400] cùng chiều -> imbalance_ratio = 600/600 = 1.0
    assert m["imbalance_ratio"] == pytest.approx(1.0)
    assert m["n_minutes"] == 2
    # Chỉ 2 phút dữ liệu (< ngưỡng OFI_ZSCORE_MIN_MINUTES) -> z-score None
    # (z tính trên chính cửa sổ sẽ luôn bằng 0 — vô nghĩa ở đầu phiên)
    assert m["ofi_zscore"] is None
    # records có cum_ofi đúng
    assert [r["cum_ofi"] for r in m["records"]] == [200.0, 600.0]
    assert m["methodology_version"] == "ofi-l1-v1"
    assert "IEX" in m["note"]


def test_metrics_zscore_direction_and_degenerate():
    # Chuỗi dài hơn cửa sổ: 80 phút, đuôi dương mạnh -> z > 0; đảo dấu -> z < 0
    tail_up = [0.0] * 70 + [100.0] * 10
    tail_down = [-v for v in tail_up]
    flat = [50.0] * 80

    def buckets_from(values):
        ts = pd.date_range("2026-01-05 14:30", periods=len(values), freq="1min", tz="UTC")
        return pd.DataFrame({"ts": ts, "ofi": values, "n_updates": 1,
                             "spread_avg": 0.02, "bid_size_last": 100, "ask_size_last": 100,
                             "mid_first": 100.0, "mid_last": 100.0})

    m_up = compute_ofi_metrics(buckets_from(tail_up), zscore_window=60)
    m_down = compute_ofi_metrics(buckets_from(tail_down), zscore_window=60)
    m_flat = compute_ofi_metrics(buckets_from(flat), zscore_window=60)
    assert m_up["ofi_zscore"] is not None and m_up["ofi_zscore"] > 0
    assert m_down["ofi_zscore"] is not None and m_down["ofi_zscore"] < 0
    assert abs(m_up["ofi_zscore"] + m_down["ofi_zscore"]) < 1e-9  # đối xứng
    assert m_flat["ofi_zscore"] is None  # std = 0


def test_metrics_empty_input():
    m = compute_ofi_metrics(pd.DataFrame(), symbol="TEST")
    assert m["status"] == "no_data"
    assert m["integrated_ofi"] == 0.0
    assert m["records"] == []

    m2 = compute_ofi_from_quotes(pd.DataFrame(), symbol="TEST")
    assert m2["status"] == "no_data"


def test_pipeline_from_quotes_end_to_end():
    m = compute_ofi_from_quotes(base_quote_stream(), symbol="TEST")
    assert m["status"] == "ok"
    assert m["integrated_ofi"] == 600.0
    assert len(m["records"]) == 2
