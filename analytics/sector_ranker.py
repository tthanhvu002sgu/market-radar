import logging
from typing import Any, Dict, List
import pandas as pd

from config.sector_mappings import SECTOR_ETF_MAP, SECTOR_NAMES_VI, BENCHMARK_TICKER

logger = logging.getLogger(__name__)

def rank_sectors(latest_stocks_df: pd.DataFrame, constituents_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Rank the 11 GICS sectors based on ETF relative strength vs SPY, and sector internal breadth.
    """
    if latest_stocks_df.empty:
        return []

    # Get SPY returns
    spy_row = latest_stocks_df[latest_stocks_df["symbol"] == BENCHMARK_TICKER]
    spy_1w = float(spy_row["perf_5d"].values[0]) if not spy_row.empty and not pd.isna(spy_row["perf_5d"].values[0]) else 0.0
    spy_1m = float(spy_row["perf_20d"].values[0]) if not spy_row.empty and not pd.isna(spy_row["perf_20d"].values[0]) else 0.0
    spy_3m = float(spy_row["perf_60d"].values[0]) if not spy_row.empty and not pd.isna(spy_row["perf_60d"].values[0]) else 0.0

    # Merge constituent sector info if not already in latest_stocks_df
    stocks_with_info = latest_stocks_df.copy()
    if "sector" not in stocks_with_info.columns and not constituents_df.empty:
        stocks_with_info = pd.merge(
            stocks_with_info,
            constituents_df[["symbol", "sector", "sub_industry"]],
            on="symbol",
            how="left"
        )

    # Exclude benchmark and sector ETFs from member breadth calculation
    etf_symbols = set(SECTOR_ETF_MAP.values()) | {BENCHMARK_TICKER, "RSP"}
    members_df = stocks_with_info[~stocks_with_info["symbol"].isin(etf_symbols)]

    sector_results = []

    for sector_name, etf_ticker in SECTOR_ETF_MAP.items():
        # ETF data
        etf_row = latest_stocks_df[latest_stocks_df["symbol"] == etf_ticker]
        etf_1w = float(etf_row["perf_5d"].values[0]) if not etf_row.empty and not pd.isna(etf_row["perf_5d"].values[0]) else 0.0
        etf_1m = float(etf_row["perf_20d"].values[0]) if not etf_row.empty and not pd.isna(etf_row["perf_20d"].values[0]) else 0.0
        etf_3m = float(etf_row["perf_60d"].values[0]) if not etf_row.empty and not pd.isna(etf_row["perf_60d"].values[0]) else 0.0

        # Relative Strength vs SPY
        rs_1w = round(etf_1w - spy_1w, 2)
        rs_1m = round(etf_1m - spy_1m, 2)
        rs_3m = round(etf_3m - spy_3m, 2)

        # Sector members breadth
        sector_members = members_df[members_df["sector"] == sector_name]
        member_count = len(sector_members)
        if member_count > 0:
            above_ma50 = (sector_members["close"] > sector_members["ma50"]).sum()
            breadth_ma50_pct = round(float(above_ma50 / member_count * 100.0), 1)
            above_ma20 = (sector_members["close"] > sector_members["ma20"]).sum()
            breadth_ma20_pct = round(float(above_ma20 / member_count * 100.0), 1)
        else:
            breadth_ma50_pct = 0.0
            breadth_ma20_pct = 0.0

        # Composite score for ranking: weighted RS + Breadth
        # RS 1m (40%) + RS 3m (30%) + Breadth (30%)
        composite_score = round(rs_1m * 0.4 + rs_3m * 0.3 + (breadth_ma50_pct - 50.0) * 0.3, 2)

        # Determine 4-quadrant state
        if rs_1m >= 0 and rs_3m >= 0 and breadth_ma50_pct >= 50.0:
            status = "Dẫn đầu (Leading)"
            status_desc = f"Sức mạnh tương đối vượt trội so với SPY cả 1M (+{rs_1m}%) và 3M (+{rs_3m}%). Độ rộng vững chắc với {breadth_ma50_pct}% mã trên MA50."
        elif rs_1m >= 0 and (rs_3m < 0 or rs_1w > rs_1m):
            status = "Đang cải thiện (Improving)"
            status_desc = f"Sức mạnh ngắn hạn tăng tốc (RS 1W: {rs_1w}%, RS 1M: {rs_1m}%), tỷ lệ trên MA50 phục hồi lên {breadth_ma50_pct}%, dù 3M còn độ trễ."
        elif rs_1m < 0 and rs_3m >= 0:
            status = "Suy yếu (Weakening)"
            status_desc = f"Đang mất đà ngắn hạn (RS 1M: {rs_1m}%), độ rộng tụt xuống {breadth_ma50_pct}% trên MA50 dù nền 3M vẫn cao hơn SPY."
        else:
            status = "Tụt hậu (Lagging)"
            status_desc = f"Yếu thế toàn diện so với thị trường (RS 1M: {rs_1m}%, RS 3M: {rs_3m}%), chỉ {breadth_ma50_pct}% mã giữ được MA50."

        # Sub-industry summary within sector
        sub_industries = []
        if member_count > 0 and "sub_industry" in sector_members.columns:
            for sub_name, sub_group in sector_members.groupby("sub_industry"):
                sub_count = len(sub_group)
                sub_avg_1m = round(float(sub_group["perf_20d"].mean()), 2) if not sub_group["perf_20d"].isna().all() else 0.0
                best_stock = sub_group.sort_values("perf_20d", ascending=False).iloc[0] if not sub_group.empty else None
                sub_industries.append({
                    "sub_industry": sub_name,
                    "count": sub_count,
                    "avg_perf_20d": sub_avg_1m,
                    "top_stock": best_stock["symbol"] if best_stock is not None else "",
                    "top_stock_perf": round(float(best_stock["perf_20d"]), 2) if best_stock is not None and not pd.isna(best_stock["perf_20d"]) else 0.0
                })

        sub_industries.sort(key=lambda x: x["avg_perf_20d"], reverse=True)

        sector_results.append({
            "sector": sector_name,
            "sector_vi": SECTOR_NAMES_VI.get(sector_name, sector_name),
            "etf": etf_ticker,
            "etf_1w": round(etf_1w, 2),
            "etf_1m": round(etf_1m, 2),
            "etf_3m": round(etf_3m, 2),
            "rs_1w": rs_1w,
            "rs_1m": rs_1m,
            "rs_3m": rs_3m,
            "member_count": member_count,
            "breadth_ma50_pct": breadth_ma50_pct,
            "breadth_ma20_pct": breadth_ma20_pct,
            "composite_score": composite_score,
            "status": status,
            "status_desc": status_desc,
            "sub_industries": sub_industries
        })

    # Sort sectors by composite score descending
    sector_results.sort(key=lambda x: x["composite_score"], reverse=True)
    for idx, s in enumerate(sector_results, 1):
        s["rank"] = idx

    return sector_results
