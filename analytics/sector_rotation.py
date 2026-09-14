"""
analytics/sector_rotation.py

Phân tích luân chuyển sức mạnh tương đối (Relative Strength Rotation) của 11 ngành GICS so với SPY.
Công thức độc lập của Market Radar (không phải bản quyền JdK RRG):
    R_t = P_{ETF, t} / P_{SPY, t}
    X_t = 100 * (R_t / EMA_{20}(R)_t - 1)
    Y_t = X_t - X_{t-5}

Bốn góc phần tư:
    - X >= 0, Y >= 0: Dẫn đầu (Leading)
    - X >= 0, Y < 0:  Suy yếu (Weakening)
    - X < 0,  Y < 0:  Tụt hậu (Lagging)
    - X < 0,  Y >= 0: Đang cải thiện (Improving)
    - |X| < 0.05 và |Y| < 0.05: Trung tính (Neutral)
"""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from config.settings import BENCHMARK_TICKER
from config.sector_mappings import SECTOR_ETF_MAP, SECTOR_NAMES_VI

logger = logging.getLogger(__name__)


def compute_sector_rotation(
    df_bars: pd.DataFrame,
    as_of: Optional[str] = None,
    trail_length: int = 10
) -> Dict[str, Any]:
    """
    Tính toán luân chuyển sức mạnh tương đối cho 11 ngành GICS so với SPY.
    Tạo đuôi lịch sử (trail) gồm `trail_length` phiên gần nhất đến thời điểm `as_of`.
    Loại bỏ mọi rủi ro lookahead (chỉ lấy nến <= as_of).
    """
    if df_bars.empty:
        return {
            "sectors": [],
            "as_of": as_of or "",
            "trail_length": trail_length,
            "methodology": "Luân chuyển sức mạnh tương đối (Market Radar Heuristic)",
            "formula": "R = P_ETF / P_SPY; X = 100 * (R / EMA20(R) - 1); Y = X_t - X_{t-5}",
            "benchmark": BENCHMARK_TICKER
        }

    df = df_bars.copy()
    if not pd.api.types.is_string_dtype(df["date"]):
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    else:
        df["date_str"] = df["date"].astype(str)

    # Strictly filter up to as_of date if specified
    if as_of:
        df = df[df["date_str"] <= as_of].copy()

    # Build continuous chronological trading calendar spine from all available bars <= as_of
    calendar_sessions = sorted(df["date_str"].unique())
    if not calendar_sessions:
        return {
            "sectors": [],
            "as_of": as_of or "",
            "trail_length": trail_length,
            "benchmark": BENCHMARK_TICKER,
            "error": "Không có dữ liệu phiên giao dịch."
        }

    cal_df = pd.DataFrame({"date_str": calendar_sessions})

    # Extract SPY close series and align onto calendar spine
    raw_spy = df[df["symbol"] == BENCHMARK_TICKER][["date_str", "close"]].dropna()
    raw_spy = raw_spy.rename(columns={"close": "spy_close"}).sort_values("date_str")

    if raw_spy.empty or len(raw_spy) < 25:
        logger.warning("Không đủ nến lịch sử cho SPY để tính luân chuyển ngành.")
        return {
            "sectors": [],
            "as_of": as_of or "",
            "trail_length": trail_length,
            "error": "Thiếu dữ liệu benchmark SPY."
        }

    spy_df = pd.merge(cal_df, raw_spy, on="date_str", how="left").sort_values("date_str")

    # Calendar-aligned SPY returns: strictly requires valid price on calendar lag (no fill)
    spy_df["spy_perf_1d"] = (spy_df["spy_close"] / spy_df["spy_close"].shift(1) - 1.0) * 100.0
    spy_df["spy_perf_5d"] = (spy_df["spy_close"] / spy_df["spy_close"].shift(5) - 1.0) * 100.0
    spy_df["spy_perf_20d"] = (spy_df["spy_close"] / spy_df["spy_close"].shift(20) - 1.0) * 100.0

    last_spy_row = spy_df.iloc[-1]
    latest_date = str(last_spy_row["date_str"])
    spy_20d = round(float(last_spy_row["spy_perf_20d"]), 2) if pd.notna(last_spy_row["spy_perf_20d"]) else None

    sectors_data: List[Dict[str, Any]] = []

    for sector_name, etf_ticker in SECTOR_ETF_MAP.items():
        raw_etf = df[df["symbol"] == etf_ticker][["date_str", "close"]].dropna()
        raw_etf = raw_etf.rename(columns={"close": "etf_close"}).sort_values("date_str")

        if raw_etf.empty or len(raw_etf) < 25:
            # Not enough data for this ETF
            sectors_data.append({
                "sector": sector_name,
                "sector_vi": SECTOR_NAMES_VI.get(sector_name, sector_name),
                "etf": etf_ticker,
                "rotation_state": "Chưa xác minh (Thiếu dữ liệu ETF)",
                "rotation_desc": "Không đủ nến lịch sử cho ETF ngành.",
                "current_x": None,
                "current_y": None,
                "etf_1d": None,
                "etf_5d": None,
                "etf_20d": None,
                "spy_20d": spy_20d,
                "regime": "Chưa xác minh",
                "is_stale": True,
                "rank": None,
                "is_ranked": False,
                "trail": []
            })
            continue

        etf_max_date = str(raw_etf["date_str"].iloc[-1])
        if etf_max_date != latest_date:
            # ETF last session is out of sync with target session (stale ETF)
            sectors_data.append({
                "sector": sector_name,
                "sector_vi": SECTOR_NAMES_VI.get(sector_name, sector_name),
                "etf": etf_ticker,
                "rotation_state": "Chưa xác minh (Dữ liệu cũ / Lệch phiên)",
                "rotation_desc": f"Dữ liệu ETF kết thúc ngày {etf_max_date}, lệch so với phiên mục tiêu SPY ({latest_date}).",
                "current_x": None,
                "current_y": None,
                "etf_1d": None,
                "etf_5d": None,
                "etf_20d": None,
                "spy_20d": spy_20d,
                "regime": "Chưa xác minh (Lệch phiên mục tiêu)",
                "is_stale": True,
                "rank": None,
                "is_ranked": False,
                "trail": []
            })
            continue

        # Merge ETF on calendar spine to maintain exact calendar session indexing
        etf_df = pd.merge(cal_df, raw_etf, on="date_str", how="left").sort_values("date_str")

        # Merge SPY and ETF on continuous calendar spine
        merged = pd.merge(spy_df[["date_str", "spy_close"]], etf_df[["date_str", "etf_close"]], on="date_str", how="left").sort_values("date_str")
        valid_bars_count = int(merged["etf_close"].notna().sum())
        if valid_bars_count < 25:
            sectors_data.append({
                "sector": sector_name,
                "sector_vi": SECTOR_NAMES_VI.get(sector_name, sector_name),
                "etf": etf_ticker,
                "rotation_state": "Chưa xác minh (Không đủ phiên giao dịch)",
                "rotation_desc": "Không đủ phiên giao dịch đồng thời với SPY.",
                "current_x": None,
                "current_y": None,
                "etf_1d": None,
                "etf_5d": None,
                "etf_20d": None,
                "spy_20d": spy_20d,
                "regime": "Chưa xác minh",
                "is_stale": True,
                "rank": None,
                "is_ranked": False,
                "trail": []
            })
            continue

        # R_t = P_ETF / P_SPY
        merged["ratio"] = merged["etf_close"] / merged["spy_close"]

        # EMA20 of Ratio
        merged["ema20"] = merged["ratio"].ewm(span=20, adjust=False).mean()

        # X_t = 100 * (R_t / EMA20(R)_t - 1)
        merged["x"] = 100.0 * (merged["ratio"] / merged["ema20"] - 1.0)

        # Y_t = X_t - X_{t-5} (strictly 5 calendar sessions lag on spine)
        merged["y"] = merged["x"] - merged["x"].shift(5)

        # Absolute performance strictly requiring exact calendar session lags on spine
        merged["etf_perf_1d"] = (merged["etf_close"] / merged["etf_close"].shift(1) - 1.0) * 100.0
        merged["etf_perf_5d"] = (merged["etf_close"] / merged["etf_close"].shift(5) - 1.0) * 100.0
        merged["etf_perf_20d"] = (merged["etf_close"] / merged["etf_close"].shift(20) - 1.0) * 100.0

        # Drop sessions where Y is NaN (first 5 sessions after EMA init)
        valid_trail_df = merged.dropna(subset=["x", "y"]).copy()
        if valid_trail_df.empty:
            sectors_data.append({
                "sector": sector_name,
                "sector_vi": SECTOR_NAMES_VI.get(sector_name, sector_name),
                "etf": etf_ticker,
                "rotation_state": "Chưa xác minh (Không đủ phiên hợp lệ)",
                "rotation_desc": "Không đủ phiên sau khi khởi tạo EMA20 và độ lệch 5 phiên.",
                "current_x": None,
                "current_y": None,
                "etf_1d": None,
                "etf_5d": None,
                "etf_20d": None,
                "spy_20d": spy_20d,
                "regime": "Chưa xác minh",
                "is_stale": True,
                "rank": None,
                "is_ranked": False,
                "trail": []
            })
            continue

        latest_point = valid_trail_df.iloc[-1]
        etf_last_valid_date = str(latest_point["date_str"])
        if etf_last_valid_date != latest_date:
            sectors_data.append({
                "sector": sector_name,
                "sector_vi": SECTOR_NAMES_VI.get(sector_name, sector_name),
                "etf": etf_ticker,
                "rotation_state": "Chưa xác minh (Dữ liệu cũ / Lệch phiên)",
                "rotation_desc": f"Phiên hợp lệ cuối của ETF ({etf_last_valid_date}) lệch so với phiên mục tiêu SPY ({latest_date}).",
                "current_x": None,
                "current_y": None,
                "etf_1d": None,
                "etf_5d": None,
                "etf_20d": None,
                "spy_20d": spy_20d,
                "regime": "Chưa xác minh (Lệch phiên mục tiêu)",
                "is_stale": True,
                "rank": None,
                "is_ranked": False,
                "trail": []
            })
            continue

        cur_x = round(float(latest_point["x"]), 2)
        cur_y = round(float(latest_point["y"]), 2)
        etf_1d = round(float(latest_point["etf_perf_1d"]), 2) if pd.notna(latest_point["etf_perf_1d"]) else None
        etf_5d = round(float(latest_point["etf_perf_5d"]), 2) if pd.notna(latest_point["etf_perf_5d"]) else None
        etf_20d = round(float(latest_point["etf_perf_20d"]), 2) if pd.notna(latest_point["etf_perf_20d"]) else None

        # Determine rotation state with neutral boundary
        if abs(cur_x) < 0.05 and abs(cur_y) < 0.05:
            state = "Trung tính (Neutral)"
            state_desc = f"Nằm trên trục phân cách; RS tỷ lệ đạt cân bằng với EMA20 (X={cur_x:+.2f}%, Y={cur_y:+.2f}%)."
        elif cur_x >= 0 and cur_y >= 0:
            state = "Dẫn đầu (Leading)"
            state_desc = f"Mạnh hơn SPY và gia tốc tăng (X={cur_x:+.2f}%, Y={cur_y:+.2f}%)."
        elif cur_x >= 0 and cur_y < 0:
            state = "Suy yếu (Weakening)"
            state_desc = f"Vẫn cao hơn EMA20 nhưng đà tăng đang giảm tốc (X={cur_x:+.2f}%, Y={cur_y:+.2f}%)."
        elif cur_x < 0 and cur_y < 0:
            state = "Tụt hậu (Lagging)"
            state_desc = f"Yếu hơn SPY và tiếp tục mất đà (X={cur_x:+.2f}%, Y={cur_y:+.2f}%)."
        else:
            state = "Đang cải thiện (Improving)"
            state_desc = f"Dưới EMA20 nhưng xung lực đảo chiều phục hồi (X={cur_x:+.2f}%, Y={cur_y:+.2f}%)."

        # Absolute return vs SPY regime context
        if etf_20d is not None and spy_20d is not None:
            if etf_20d > 0 and etf_20d >= spy_20d:
                regime = "Tăng trưởng dẫn dắt (Outperforming & Tăng tuyệt đối)"
            elif etf_20d <= 0 and etf_20d >= spy_20d:
                regime = "Phòng thủ tích cực (Outperforming, giảm ít hơn SPY)"
            elif etf_20d > 0 and etf_20d < spy_20d:
                regime = "Tăng giá nhưng yếu hơn SPY (Tăng tuyệt đối, Lagging SPY)"
            else:
                regime = "Suy yếu tuyệt đối (Underperforming & Giảm tuyệt đối)"
        else:
            regime = "Chưa đủ dữ liệu 1M để phân loại bối cảnh tuyệt đối"

        # Historical trail (past `trail_length` sessions)
        trail_slice = valid_trail_df.tail(trail_length)
        trail_points = []
        for _, tr_row in trail_slice.iterrows():
            trail_points.append({
                "date": str(tr_row["date_str"]),
                "x": round(float(tr_row["x"]), 2) if pd.notna(tr_row["x"]) else 0.0,
                "y": round(float(tr_row["y"]), 2) if pd.notna(tr_row["y"]) else 0.0,
                "ratio": round(float(tr_row["ratio"]), 4) if pd.notna(tr_row["ratio"]) else 0.0,
                "etf_close": round(float(tr_row["etf_close"]), 2) if pd.notna(tr_row["etf_close"]) else 0.0,
                "spy_close": round(float(tr_row["spy_close"]), 2) if pd.notna(tr_row["spy_close"]) else 0.0
            })

        sectors_data.append({
            "sector": sector_name,
            "sector_vi": SECTOR_NAMES_VI.get(sector_name, sector_name),
            "etf": etf_ticker,
            "rotation_state": state,
            "rotation_desc": state_desc,
            "current_x": cur_x,
            "current_y": cur_y,
            "etf_1d": etf_1d,
            "etf_5d": etf_5d,
            "etf_20d": etf_20d,
            "spy_20d": spy_20d,
            "regime": regime,
            "is_stale": False,
            "trail": trail_points
        })

    # Sort sectors: valid sectors by current_x descending first, stale/unverified sectors at the end
    sectors_data.sort(
        key=lambda s: (
            0 if (s.get("is_stale") or s.get("current_x") is None) else 1,
            s.get("current_x") if s.get("current_x") is not None else float("-inf")
        ),
        reverse=True
    )

    # Assign ranks: valid sectors receive 1, 2, ...; stale/unverified receive None (excluded from current ranking)
    rank_idx = 1
    for s in sectors_data:
        if not s.get("is_stale") and s.get("current_x") is not None:
            s["rank"] = rank_idx
            s["is_ranked"] = True
            rank_idx += 1
        else:
            s["rank"] = None
            s["is_ranked"] = False

    return {
        "sectors": sectors_data,
        "as_of": latest_date,
        "trail_length": trail_length,
        "benchmark": BENCHMARK_TICKER,
        "methodology": "Luân chuyển sức mạnh tương đối (Market Radar Heuristic)",
        "formula": "R = P_ETF / P_SPY; X = 100 * (R / EMA20(R) - 1); Y = X_t - X_{t-5}",
        "disclaimer": "Đây là chỉ báo luân chuyển sức mạnh tương đối nội bộ của Market Radar; không phải bản quyền JdK RRG của StockCharts."
    }
