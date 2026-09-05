import logging
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from config.settings import MA_PERIODS, VOLUME_MA_PERIOD, BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT

logger = logging.getLogger(__name__)

def compute_stock_indicators(df_bars: pd.DataFrame) -> pd.DataFrame:
    """
    Compute technical indicators for each symbol from its daily bars.
    Requires columns: [symbol, date, open, high, low, close, volume].
    Returns a DataFrame with the latest bar per symbol enriched with indicators.
    """
    if df_bars.empty:
        return pd.DataFrame()

    df_bars = df_bars.sort_values(["symbol", "date"]).copy()
    
    # Group by symbol and calculate moving averages & rolling metrics
    latest_rows = []
    for symbol, group in df_bars.groupby("symbol"):
        if len(group) < 20:
            continue

        closes = group["close"]
        volumes = group["volume"]

        group = group.copy()
        group["ma20"] = closes.rolling(window=20).mean()
        group["ma50"] = closes.rolling(window=50).mean()
        group["ma200"] = closes.rolling(window=200).mean() if len(group) >= 200 else np.nan
        group["vol_ma20"] = volumes.rolling(window=VOLUME_MA_PERIOD).mean()
        
        # High/Low 20 days
        group["high20"] = group["high"].rolling(window=20).max()
        group["low20"] = group["low"].rolling(window=20).min()

        # Returns
        group["perf_1d"] = closes.pct_change(1) * 100.0
        group["perf_5d"] = closes.pct_change(5) * 100.0
        group["perf_20d"] = closes.pct_change(20) * 100.0
        group["perf_60d"] = closes.pct_change(60) * 100.0 if len(group) >= 60 else np.nan

        # Previous day indicators for slopes & crossovers
        group["prev_close"] = closes.shift(1)
        group["prev_ma20"] = group["ma20"].shift(1)
        group["prev_ma50"] = group["ma50"].shift(1)

        # Append latest bar
        latest_row = group.iloc[-1].to_dict()
        latest_rows.append(latest_row)

    if not latest_rows:
        return pd.DataFrame()

    result_df = pd.DataFrame(latest_rows)
    return result_df

def compute_market_breadth(latest_stocks_df: pd.DataFrame, df_bars: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute market-wide breadth metrics across S&P 500 stocks and benchmark comparison.
    """
    if latest_stocks_df.empty:
        return {
            "total_evaluated": 0,
            "pct_above_ma20": 0.0,
            "pct_above_ma50": 0.0,
            "pct_above_ma200": 0.0,
            "advances": 0,
            "declines": 0,
            "unchanged": 0,
            "ad_ratio": 0.0,
            "new_20d_highs": 0,
            "new_20d_lows": 0,
            "spy_1d": 0.0,
            "spy_5d": 0.0,
            "spy_20d": 0.0,
            "rsp_1d": 0.0,
            "rsp_5d": 0.0,
            "rsp_20d": 0.0,
            "concentration_divergence": "Không đủ dữ liệu",
            "market_summary": "Chưa có đủ dữ liệu để tính toán độ rộng thị trường."
        }

    # Filter out benchmark ETFs from universe calculation
    etf_symbols = [BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT, "XLK", "XLF", "XLV", "XLE", "XLI", "XLC", "XLY", "XLP", "XLU", "XLRE", "XLB"]
    stocks_only = latest_stocks_df[~latest_stocks_df["symbol"].isin(etf_symbols)].copy()

    total = len(stocks_only)
    if total == 0:
        return {}

    # Stocks above MAs
    above_ma20 = (stocks_only["close"] > stocks_only["ma20"]).sum()
    pct_ma20 = round(float(above_ma20 / total * 100.0), 2)

    valid_ma50 = stocks_only["ma50"].dropna()
    pct_ma50 = round(float((stocks_only["close"] > stocks_only["ma50"]).sum() / len(valid_ma50) * 100.0), 2) if len(valid_ma50) > 0 else 0.0

    valid_ma200 = stocks_only["ma200"].dropna()
    pct_ma200 = round(float((stocks_only["close"] > stocks_only["ma200"]).sum() / len(valid_ma200) * 100.0), 2) if len(valid_ma200) > 0 else 0.0

    # Advance / Decline (1-day)
    advances = int((stocks_only["perf_1d"] > 0).sum())
    declines = int((stocks_only["perf_1d"] < 0).sum())
    unchanged = total - advances - declines
    ad_ratio = round(advances / max(declines, 1), 2)

    # New 20-day Highs & Lows (close within 0.5% of high20 / low20)
    new_highs = int((stocks_only["close"] >= stocks_only["high20"] * 0.995).sum())
    new_lows = int((stocks_only["close"] <= stocks_only["low20"] * 1.005).sum())

    # SPY vs RSP Performance
    spy_row = latest_stocks_df[latest_stocks_df["symbol"] == BENCHMARK_TICKER]
    rsp_row = latest_stocks_df[latest_stocks_df["symbol"] == BENCHMARK_EQUAL_WEIGHT]

    spy_1d = round(float(spy_row["perf_1d"].values[0]), 2) if not spy_row.empty else 0.0
    spy_5d = round(float(spy_row["perf_5d"].values[0]), 2) if not spy_row.empty and not pd.isna(spy_row["perf_5d"].values[0]) else 0.0
    spy_20d = round(float(spy_row["perf_20d"].values[0]), 2) if not spy_row.empty and not pd.isna(spy_row["perf_20d"].values[0]) else 0.0

    rsp_1d = round(float(rsp_row["perf_1d"].values[0]), 2) if not rsp_row.empty else 0.0
    rsp_5d = round(float(rsp_row["perf_5d"].values[0]), 2) if not rsp_row.empty and not pd.isna(rsp_row["perf_5d"].values[0]) else 0.0
    rsp_20d = round(float(rsp_row["perf_20d"].values[0]), 2) if not rsp_row.empty and not pd.isna(rsp_row["perf_20d"].values[0]) else 0.0

    # Concentration Divergence Analysis: SPY vs RSP
    # If SPY outperforms RSP significantly, rally is concentrated in mega caps (narrow breadth).
    diff_20d = spy_20d - rsp_20d
    if diff_20d > 2.5:
        concentration_status = "Đà tăng tập trung cao ở nhóm vốn hóa lớn (Mega-caps); độ rộng thị trường bị che mờ."
    elif diff_20d < -2.5:
        concentration_status = "Độ rộng lan tỏa mạnh sang nhóm cổ phiếu vừa và nhỏ (Equal-weight dẫn dắt)."
    else:
        concentration_status = "Đà tăng/giảm đồng pha giữa nhóm vốn hóa lớn và toàn thị trường."

    # Market Summary Sentence (Fact-grounded, not speculative)
    if pct_ma50 >= 60.0 and pct_ma200 >= 60.0:
        summary_env = f"Thị trường duy trì xu hướng tăng lành mạnh trên diện rộng: {pct_ma50}% cổ phiếu giữ vững MA50 và {pct_ma200}% trên MA200. Tỷ lệ tăng/giảm đạt {advances}/{declines} mã."
    elif pct_ma50 < 40.0 and pct_ma200 < 40.0:
        summary_env = f"Áp lực suy yếu chi phối diện rộng: Chỉ có {pct_ma50}% cổ phiếu trên MA50 và {pct_ma200}% trên MA200. Số mã giảm ({declines}) áp đảo số mã tăng ({advances})."
    else:
        summary_env = f"Thị trường phân hóa rõ rệt: {pct_ma50}% cổ phiếu giữ trên MA50 trong khi {pct_ma200}% trên MA200. {concentration_status}"

    return {
        "total_evaluated": total,
        "pct_above_ma20": pct_ma20,
        "pct_above_ma50": pct_ma50,
        "pct_above_ma200": pct_ma200,
        "advances": advances,
        "declines": declines,
        "unchanged": unchanged,
        "ad_ratio": ad_ratio,
        "new_20d_highs": new_highs,
        "new_20d_lows": new_lows,
        "spy_1d": spy_1d,
        "spy_5d": spy_5d,
        "spy_20d": spy_20d,
        "rsp_1d": rsp_1d,
        "rsp_5d": rsp_5d,
        "rsp_20d": rsp_20d,
        "concentration_divergence": concentration_status,
        "market_summary": summary_env,
    }
