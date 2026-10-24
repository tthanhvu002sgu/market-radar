"""
Order Flow Imbalance (OFI) — Level 1 (best bid/ask).

Methodology: Cont, Kukanov & Stoikov (2014), "The Price Impact of Order Book
Events", Journal of Financial Econometrics. OFI đo áp lực mua-bán ròng sinh ra từ
sự thay đổi khối lượng tại best bid/ask:

    e_n = 1{P_b(n) >= P_b(n-1)} * q_b(n) - 1{P_b(n) <= P_b(n-1)} * q_b(n-1)
          - 1{P_a(n) <= P_a(n-1)} * q_a(n) + 1{P_a(n) >= P_a(n-1)} * q_a(n-1)

Pure functions, không I/O. Input chuẩn: DataFrame quotes với cột
[symbol, timestamp (UTC), bid_price, bid_size, ask_price, ask_size], sorts tăng dần
theo timestamp. Cấu trúc cột phẳng để phase sau mở rộng multi-level (thêm cột level).

Lưu ý dữ liệu: free feed IEX chỉ chiếm ~2-3% khối lượng — OFI từ nguồn này là
xấp xỉ của dòng tiền toàn thị trường, dùng làm bối cảnh phiên chứ không phải
tín hiệu mua/bán cho swing trading (horizon dự báo của OFI ở mức giây-phút).
"""
import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from config.settings import (
    OFI_BUCKET_SECONDS,
    OFI_RULE_VERSION,
    OFI_ZSCORE_MIN_MINUTES,
    OFI_ZSCORE_WINDOW,
)

OFI_NOTE = (
    "OFI Level-1 theo Cont-Kukanov-Stoikov (2014), tổng hợp theo bucket "
    f"{OFI_BUCKET_SECONDS // 60} phút từ quote best bid/ask. Nguồn: feed IEX "
    "(Alpaca free) — chỉ phản ánh ~2-3% khối lượng thị trường nên là xấp xỉ "
    "dòng tiền toàn thị trường. Quote một bên sổ rỗng (giá 0) được giữ như "
    "size 0 để bắt event rút sạch một bên; quote locked (bid = ask) được giữ; "
    "quote cross (bid > ask) và giá âm bị loại. Horizon dự báo ngắn "
    "(giây-phút): dùng làm bối cảnh dòng tiền phiên, không phải tín hiệu mua/bán."
)


def _normalize_quotes(quotes_df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hoá quote và lọc dữ liệu feed lỗi.

    Giữ quote một bên sổ rỗng (giá 0 — size 0, công thức CKS xử lý tự nhiên
    thành event rút sạch một bên) và quote locked (bid == ask). Loại: giá âm,
    cả hai bên rỗng, quote cross (bid > ask — nhiễu feed).
    """
    required = {"timestamp", "bid_price", "bid_size", "ask_price", "ask_size"}
    if quotes_df is None or quotes_df.empty or not required.issubset(quotes_df.columns):
        return pd.DataFrame()

    df = quotes_df.copy()
    if "symbol" not in df.columns:
        df["symbol"] = ""
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    for col in ("bid_price", "bid_size", "ask_price", "ask_size"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["timestamp", "bid_price", "bid_size", "ask_price", "ask_size"])
    invalid = (
        (df["bid_price"] < 0) | (df["ask_price"] < 0)
        | (df["bid_size"] < 0) | (df["ask_size"] < 0)
        | ((df["bid_price"] <= 0) & (df["ask_price"] <= 0))              # cả 2 bên rỗng
        | ((df["bid_price"] > df["ask_price"]) & (df["ask_price"] > 0))  # cross
    )
    df = df[~invalid]
    df = df.sort_values("timestamp").reset_index(drop=True)

    two_sided = (df["bid_price"] > 0) & (df["ask_price"] > 0)
    df["mid_price"] = (df["bid_price"] + df["ask_price"]) / 2.0
    df["spread"] = df["ask_price"] - df["bid_price"]
    df.loc[~two_sided, ["mid_price", "spread"]] = np.nan
    return df


def compute_ofi_events(quotes_df: pd.DataFrame) -> pd.DataFrame:
    """Tính e_n cho từng quote update liên tiếp (công thức CKS ở đầu module).

    Returns DataFrame: timestamp, e, bid_price, ask_price, mid_price, spread.
    Quote đầu tiên không có nền so sánh nên bị loại.
    """
    df = _normalize_quotes(quotes_df)
    if len(df) < 2:
        return pd.DataFrame()

    prev_bp, prev_ap = df["bid_price"].shift(1), df["ask_price"].shift(1)
    prev_bs, prev_as = df["bid_size"].shift(1), df["ask_size"].shift(1)

    bid_term = (
        (df["bid_price"] >= prev_bp) * df["bid_size"]
        - (df["bid_price"] <= prev_bp) * prev_bs
    )
    ask_term = (
        (df["ask_price"] <= prev_ap) * df["ask_size"]
        - (df["ask_price"] >= prev_ap) * prev_as
    )

    events = pd.DataFrame({
        "timestamp": df["timestamp"],
        "e": (bid_term - ask_term).astype(float),
        "bid_price": df["bid_price"],
        "ask_price": df["ask_price"],
        "bid_size": df["bid_size"],
        "ask_size": df["ask_size"],
    })
    events["mid_price"] = (events["bid_price"] + events["ask_price"]) / 2.0
    events["spread"] = events["ask_price"] - events["bid_price"]
    two_sided = (events["bid_price"] > 0) & (events["ask_price"] > 0)
    events.loc[~two_sided, ["mid_price", "spread"]] = np.nan
    return events.iloc[1:].reset_index(drop=True)


def aggregate_ofi_buckets(events_df: pd.DataFrame, bucket_seconds: int = OFI_BUCKET_SECONDS) -> pd.DataFrame:
    """Gộp events thành OFI theo bucket thời gian.

    Returns DataFrame: ts (bucket start), ofi (tổng e), n_updates, spread_avg,
    bid_size_last, ask_size_last, mid_first, mid_last.
    """
    if events_df is None or events_df.empty:
        return pd.DataFrame()

    df = events_df.copy()
    df["ts"] = df["timestamp"].dt.floor(f"{bucket_seconds}s")
    buckets = (
        df.groupby("ts", sort=True)
        .agg(
            ofi=("e", "sum"),
            n_updates=("e", "count"),
            spread_avg=("spread", "mean"),
            bid_size_last=("bid_size", "last"),
            ask_size_last=("ask_size", "last"),
            mid_first=("mid_price", "first"),
            mid_last=("mid_price", "last"),
        )
        .reset_index()
    )
    return buckets


def compute_ofi_metrics(
    bucket_df: pd.DataFrame,
    zscore_window: int = OFI_ZSCORE_WINDOW,
    symbol: Optional[str] = None,
) -> Dict[str, Any]:
    """Tổng hợp metrics OFI từ bucket DataFrame (output của aggregate_ofi_buckets).

    Trả dict: status, integrated_ofi, imbalance_ratio, ofi_zscore, n_minutes,
    first_ts, last_ts, ofi_price_corr, records (per-bucket cho chart),
    methodology_version, note.
    """
    if bucket_df is None or bucket_df.empty:
        return {
            "symbol": symbol,
            "status": "no_data",
            "integrated_ofi": 0.0,
            "imbalance_ratio": 0.0,
            "ofi_zscore": None,
            "n_minutes": 0,
            "first_ts": None,
            "last_ts": None,
            "ofi_price_corr": None,
            "records": [],
            "methodology_version": OFI_RULE_VERSION,
            "note": OFI_NOTE,
        }

    df = bucket_df.sort_values("ts").reset_index(drop=True)
    ofi = df["ofi"].astype(float)
    integrated = float(ofi.sum())
    abs_sum = float(ofi.abs().sum())
    imbalance_ratio = integrated / abs_sum if abs_sum > 0 else 0.0

    # Z-score của block OFI K-phút cuối so với phân phối per-minute cả phiên:
    # z = (sum_last_K - K*mean) / (sqrt(K)*std). Trả None khi chưa đủ phút dữ
    # liệu (đầu phiên k == len(ofi) làm z luôn bằng 0 — vô nghĩa, dễ gây hiểu nhầm).
    ofi_zscore = None
    if len(ofi) >= OFI_ZSCORE_MIN_MINUTES:
        k = min(zscore_window, len(ofi))
        if k >= 2:
            window_sum = float(ofi.iloc[-k:].sum())
            mean_all, std_all = float(ofi.mean()), float(ofi.std(ddof=1))
            if std_all > 0:
                ofi_zscore = (window_sum - k * mean_all) / (math.sqrt(k) * std_all)

    # Chẩn đoán kiểu CKS: tương quan OFI phút với biến động mid-price
    ofi_price_corr = None
    if len(df) >= 3 and "mid_last" in df.columns and "mid_first" in df.columns:
        mid_change = (df["mid_last"] - df["mid_first"]).astype(float)
        if mid_change.std(ddof=1) > 0 and ofi.std(ddof=1) > 0:
            ofi_price_corr = float(ofi.corr(mid_change))

    df_out = df.copy()
    df_out["cum_ofi"] = ofi.cumsum()
    records: List[Dict[str, Any]] = [
        {
            "ts": str(row["ts"]),
            "ofi": float(row["ofi"]),
            "cum_ofi": float(row["cum_ofi"]),
            "n_updates": int(row.get("n_updates", 0)),
        }
        for _, row in df_out.iterrows()
    ]

    return {
        "symbol": symbol,
        "status": "ok",
        "integrated_ofi": integrated,
        "imbalance_ratio": imbalance_ratio,
        "ofi_zscore": ofi_zscore,
        "n_minutes": int(len(df)),
        "first_ts": str(df["ts"].iloc[0]),
        "last_ts": str(df["ts"].iloc[-1]),
        "ofi_price_corr": ofi_price_corr,
        "records": records,
        "methodology_version": OFI_RULE_VERSION,
        "note": OFI_NOTE,
    }


def compute_ofi_from_quotes(
    quotes_df: pd.DataFrame,
    bucket_seconds: int = OFI_BUCKET_SECONDS,
    zscore_window: int = OFI_ZSCORE_WINDOW,
    symbol: Optional[str] = None,
) -> Dict[str, Any]:
    """Pipeline tiện dụng: quotes -> events -> buckets -> metrics."""
    events = compute_ofi_events(quotes_df)
    buckets = aggregate_ofi_buckets(events, bucket_seconds=bucket_seconds)
    return compute_ofi_metrics(buckets, zscore_window=zscore_window, symbol=symbol)
