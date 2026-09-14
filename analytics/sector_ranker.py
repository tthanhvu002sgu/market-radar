import logging
from typing import Any, Dict, List
import numpy as np
import pandas as pd

from config.sector_mappings import SECTOR_ETF_MAP, SECTOR_NAMES_VI, BENCHMARK_TICKER

logger = logging.getLogger(__name__)

def rank_sectors(latest_stocks_df: pd.DataFrame, constituents_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Rank the 11 GICS sectors based on ETF relative strength vs SPY, and sector internal breadth.
    Heuristic độc lập của Market Radar (không phải bản sao RRG của StockCharts) [D-05, D-06].
    """
    if latest_stocks_df.empty:
        return []

    # Get SPY returns
    spy_row = latest_stocks_df[latest_stocks_df["symbol"] == BENCHMARK_TICKER]
    if not spy_row.empty:
        spy_1d_val = spy_row["perf_1d"].values[0] if "perf_1d" in spy_row.columns else np.nan
        spy_1w_val = spy_row["perf_5d"].values[0] if "perf_5d" in spy_row.columns else np.nan
        spy_1m_val = spy_row["perf_20d"].values[0] if "perf_20d" in spy_row.columns else np.nan
        spy_3m_val = spy_row["perf_60d"].values[0] if "perf_60d" in spy_row.columns else np.nan

        spy_1d = float(spy_1d_val) if pd.notna(spy_1d_val) else None
        spy_1w = float(spy_1w_val) if pd.notna(spy_1w_val) else None
        spy_1m = float(spy_1m_val) if pd.notna(spy_1m_val) else None
        spy_3m = float(spy_3m_val) if pd.notna(spy_3m_val) else None
        spy_is_valid = (spy_1m is not None)
        spy_date = str(spy_row["date_str"].values[0]) if "date_str" in spy_row.columns else (
            str(spy_row["date"].values[0])[:10] if "date" in spy_row.columns and pd.notna(spy_row["date"].values[0]) else None
        )
    else:
        logger.warning("Benchmark SPY không khả dụng hoặc bị thiếu trong nến ngày! RS ngành sẽ được gắn cờ thiếu.")
        spy_1d = None
        spy_1w = None
        spy_1m = None
        spy_3m = None
        spy_is_valid = False
        spy_date = None

    # Merge constituent sector info if not already in latest_stocks_df
    stocks_with_info = latest_stocks_df.copy()
    if "sector" not in stocks_with_info.columns:
        if not constituents_df.empty and "sector" in constituents_df.columns:
            cols_to_merge = ["symbol", "sector"]
            if "sub_industry" in constituents_df.columns:
                cols_to_merge.append("sub_industry")
            stocks_with_info = pd.merge(
                stocks_with_info,
                constituents_df[cols_to_merge],
                on="symbol",
                how="left"
            )
        else:
            stocks_with_info["sector"] = "Unknown"

    # Exclude benchmark and sector ETFs from member breadth calculation
    etf_symbols = set(SECTOR_ETF_MAP.values()) | {BENCHMARK_TICKER, "RSP"}
    members_df = stocks_with_info[~stocks_with_info["symbol"].isin(etf_symbols)]

    sector_results = []

    for sector_name, etf_ticker in SECTOR_ETF_MAP.items():
        # ETF data
        etf_row = latest_stocks_df[latest_stocks_df["symbol"] == etf_ticker]
        etf_date = None
        if not etf_row.empty:
            if "date_str" in etf_row.columns:
                etf_date = str(etf_row["date_str"].values[0])
            elif "date" in etf_row.columns and pd.notna(etf_row["date"].values[0]):
                etf_date = str(etf_row["date"].values[0])[:10]

        is_etf_stale = bool(spy_date and etf_date and etf_date != spy_date)

        if not etf_row.empty and not is_etf_stale:
            etf_1d_val = etf_row["perf_1d"].values[0] if "perf_1d" in etf_row.columns else np.nan
            etf_1w_val = etf_row["perf_5d"].values[0] if "perf_5d" in etf_row.columns else np.nan
            etf_1m_val = etf_row["perf_20d"].values[0] if "perf_20d" in etf_row.columns else np.nan
            etf_3m_val = etf_row["perf_60d"].values[0] if "perf_60d" in etf_row.columns else np.nan

            etf_1d = float(etf_1d_val) if pd.notna(etf_1d_val) else None
            etf_1w = float(etf_1w_val) if pd.notna(etf_1w_val) else None
            etf_1m = float(etf_1m_val) if pd.notna(etf_1m_val) else None
            etf_3m = float(etf_3m_val) if pd.notna(etf_3m_val) else None
        else:
            etf_1d = None
            etf_1w = None
            etf_1m = None
            etf_3m = None

        # Relative Strength vs SPY (evaluated independently per horizon) [Step 1]
        rs_1d = round(etf_1d - spy_1d, 2) if (etf_1d is not None and spy_1d is not None) else None
        rs_1w = round(etf_1w - spy_1w, 2) if (etf_1w is not None and spy_1w is not None) else None
        rs_1m = round(etf_1m - spy_1m, 2) if (etf_1m is not None and spy_1m is not None) else None
        rs_3m = round(etf_3m - spy_3m, 2) if (etf_3m is not None and spy_3m is not None) else None

        # Sector members breadth: denominator strictly counts valid observations [Step 1]
        sector_members = members_df[members_df["sector"] == sector_name]
        member_count = len(sector_members)
        if member_count > 0:
            valid_ma50 = sector_members["close"].notna() & sector_members["ma50"].notna()
            n_valid_ma50 = int(valid_ma50.sum())
            above_ma50 = int((sector_members.loc[valid_ma50, "close"] > sector_members.loc[valid_ma50, "ma50"]).sum())
            breadth_ma50_pct = round(float(above_ma50 / n_valid_ma50 * 100.0), 1) if n_valid_ma50 > 0 else None

            valid_ma20 = sector_members["close"].notna() & sector_members["ma20"].notna()
            n_valid_ma20 = int(valid_ma20.sum())
            above_ma20 = int((sector_members.loc[valid_ma20, "close"] > sector_members.loc[valid_ma20, "ma20"]).sum())
            breadth_ma20_pct = round(float(above_ma20 / n_valid_ma20 * 100.0), 1) if n_valid_ma20 > 0 else None

            # Internal returns (median of member stocks) [Step 2]
            valid_ret_1m = sector_members["perf_20d"].dropna() if "perf_20d" in sector_members.columns else pd.Series(dtype=float)
            median_return_1m = round(float(valid_ret_1m.median()), 2) if not valid_ret_1m.empty else None

            valid_ret_1d = sector_members["perf_1d"].dropna() if "perf_1d" in sector_members.columns else pd.Series(dtype=float)
            median_return_1d = round(float(valid_ret_1d.median()), 2) if not valid_ret_1d.empty else None

            # Estimated turnover (Close * Volume) & top 5 concentration [Step 2]
            if "close" in sector_members.columns and "volume" in sector_members.columns:
                m_turnover = (sector_members["close"] * sector_members["volume"]).dropna()
                turnover_est = float(m_turnover.sum())
                top5_val = float(m_turnover.nlargest(5).sum()) if len(m_turnover) > 0 else 0.0
                top5_concentration_pct = round(top5_val / turnover_est * 100.0, 1) if turnover_est > 0 else 0.0
            else:
                turnover_est = 0.0
                top5_concentration_pct = 0.0
        else:
            n_valid_ma50 = 0
            n_valid_ma20 = 0
            breadth_ma50_pct = None
            breadth_ma20_pct = None
            median_return_1m = None
            median_return_1d = None
            turnover_est = 0.0
            top5_concentration_pct = 0.0

        # Composite score for ranking: weighted RS + Breadth [D-06]
        b_score_term = (breadth_ma50_pct - 50.0) * 0.3 if breadth_ma50_pct is not None else 0.0
        if is_etf_stale:
            composite_score = -999.0
        elif rs_1m is not None and rs_3m is not None:
            composite_score = round(rs_1m * 0.4 + rs_3m * 0.3 + b_score_term, 2)
        elif breadth_ma50_pct is not None:
            composite_score = round((breadth_ma50_pct - 50.0) * 0.5, 2)
        else:
            composite_score = -999.0

        # Determine 4-quadrant state [D-06: factually grounded, no false lagging when RS is positive]
        b_50_val = breadth_ma50_pct if breadth_ma50_pct is not None else 0.0
        b_50_str = f"{breadth_ma50_pct}%" if breadth_ma50_pct is not None else "N/A"

        if is_etf_stale:
            status = "Chưa xác minh (Dữ liệu cũ / Lệch phiên)"
            status_desc = f"Dữ liệu ETF kết thúc ngày {etf_date}, lệch so với phiên mục tiêu SPY ({spy_date}). Độ rộng nội bộ: {b_50_str} mã trên MA50."
        elif not spy_is_valid or rs_1m is None or rs_3m is None:
            status = "Chưa xác minh (Thiếu SPY)" if not spy_is_valid else "Chưa xác minh (Thiếu ETF)"
            status_desc = f"Thiếu dữ liệu benchmark hoặc ETF để tính RS tương đối. Độ rộng nội bộ: {b_50_str} mã trên MA50."
        elif rs_1m >= 0 and rs_3m >= 0 and b_50_val >= 50.0 and breadth_ma50_pct is not None:
            status = "Dẫn đầu (Leading)"
            status_desc = f"Sức mạnh tương đối vượt trội so với SPY cả 1M (+{rs_1m:+.2f}% pts) và 3M (+{rs_3m:+.2f}% pts). Độ rộng vững chắc với {b_50_str} mã trên MA50."
        elif (rs_1m >= 0 and rs_3m >= 0 and (b_50_val < 50.0 or breadth_ma50_pct is None)) or (rs_1m < 0 and rs_3m >= 0):
            status = "Suy yếu (Weakening)"
            if rs_1m >= 0 and rs_3m >= 0:
                status_desc = f"RS vẫn tích cực (1M: +{rs_1m:+.2f}% pts, 3M: +{rs_3m:+.2f}% pts) nhưng độ rộng nội bộ suy yếu (chỉ {b_50_str} mã trên MA50 — phân hóa)."
            else:
                status_desc = f"Đang mất đà ngắn hạn (RS 1M: {rs_1m:+.2f}% pts), độ rộng đạt {b_50_str} trên MA50 dù nền 3M vẫn vượt SPY (+{rs_3m:+.2f}% pts)."
        elif rs_1m >= 0 and rs_3m < 0:
            status = "Đang cải thiện (Improving)"
            status_desc = f"Sức mạnh ngắn hạn tăng tốc (RS 1M: +{rs_1m:+.2f}% pts), tỷ lệ trên MA50 đạt {b_50_str}, đang nỗ lực thoát đáy 3M (RS 3M: {rs_3m:+.2f}% pts)."
        else:
            status = "Tụt hậu (Lagging)"
            status_desc = f"Yếu thế toàn diện so với thị trường (RS 1M: {rs_1m:+.2f}% pts, RS 3M: {rs_3m:+.2f}% pts), chỉ {b_50_str} mã giữ được MA50."

        # Sub-industry summary within sector [D-06]
        sub_industries = []
        if member_count > 0 and "sub_industry" in sector_members.columns:
            for sub_name, sub_group in sector_members.groupby("sub_industry"):
                sub_name_str = str(sub_name).strip()
                if not sub_name_str or sub_name_str.lower() in ("unknown", "nan", "none"):
                    continue
                sub_count = len(sub_group)
                v_20 = sub_group["perf_20d"].dropna() if "perf_20d" in sub_group.columns else pd.Series(dtype=float)
                sub_avg_1m = round(float(v_20.mean()), 2) if not v_20.empty else 0.0
                sub_med_1m = round(float(v_20.median()), 2) if not v_20.empty else 0.0
                is_small = bool(sub_count <= 2)
                best_stock = sub_group.sort_values("perf_20d", ascending=False).iloc[0] if not sub_group.empty and "perf_20d" in sub_group.columns else None
                sub_industries.append({
                    "sub_industry": sub_name_str,
                    "count": sub_count,
                    "is_small_sample": is_small,
                    "avg_perf_20d": sub_avg_1m,
                    "median_perf_20d": sub_med_1m,
                    "top_stock": best_stock["symbol"] if best_stock is not None else "",
                    "top_stock_perf": round(float(best_stock["perf_20d"]), 2) if best_stock is not None and not pd.isna(best_stock.get("perf_20d")) else 0.0
                })

        sub_industries.sort(key=lambda x: x["avg_perf_20d"], reverse=True)

        sector_results.append({
            "sector": sector_name,
            "sector_vi": SECTOR_NAMES_VI.get(sector_name, sector_name),
            "etf": etf_ticker,
            "etf_1d": round(etf_1d, 2) if etf_1d is not None else None,
            "etf_1w": round(etf_1w, 2) if etf_1w is not None else None,
            "etf_1m": round(etf_1m, 2) if etf_1m is not None else None,
            "etf_3m": round(etf_3m, 2) if etf_3m is not None else None,
            "rs_1d": rs_1d,
            "rs_1w": rs_1w,
            "rs_1m": rs_1m,
            "rs_3m": rs_3m,
            "member_count": member_count,
            "valid_ma50_count": n_valid_ma50,
            "valid_ma20_count": n_valid_ma20,
            "breadth_ma50_pct": breadth_ma50_pct,
            "breadth_ma20_pct": breadth_ma20_pct,
            "median_return_1m": median_return_1m,
            "median_return_1d": median_return_1d,
            "turnover_est": turnover_est,
            "top5_concentration_pct": top5_concentration_pct,
            "methodology_version": "v2.1",
            "composite_score": composite_score,
            "status": status,
            "status_desc": status_desc,
            "is_stale": is_etf_stale,
            "sub_industries": sub_industries
        })

    # Sort sectors: valid sectors by composite score descending first, stale/unverified at the end
    sector_results.sort(
        key=lambda x: (
            0 if (x.get("is_stale") or x["composite_score"] == -999.0) else 1,
            x["composite_score"]
        ),
        reverse=True
    )
    for idx, s in enumerate(sector_results, 1):
        s["rank"] = idx

    return sector_results
