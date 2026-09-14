import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from config.sector_mappings import BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT, SECTOR_ETF_MAP
from config.settings import (
    COMPOSITE_RS_WEIGHTS,
    BLEND_RS_WEIGHTS,
    LEADING_GROUP_THRESHOLD,
)

logger = logging.getLogger(__name__)

def _to_percentile_series(series: pd.Series) -> pd.Series:
    """Normalize a pandas series to integer percentile rank between 1 and 99, strictly preserving NaNs."""
    if series.empty:
        return series
    valid = series.dropna()
    if valid.empty:
        # All NaN: preserve NaN without assigning arbitrary ranks [D-01]
        return pd.Series([np.nan] * len(series), index=series.index)
    if len(valid) == 1:
        res = pd.Series([np.nan] * len(series), index=series.index)
        res.loc[valid.index] = 50
        return res
    pct = valid.rank(pct=True, ascending=True)
    ranked = (pct * 98 + 1).round().clip(lower=1, upper=99).astype(int)
    res = pd.Series([np.nan] * len(series), index=series.index)
    res.loc[valid.index] = ranked
    return res

def rank_industry_groups(
    latest_stocks_df: pd.DataFrame,
    constituents_df: pd.DataFrame
) -> List[Dict[str, Any]]:
    """
    Rank all GICS Sub-Industries using Market Radar RS (inspired by William O'Neil / CANSLIM):
    - Multi-timeframe performance: DAY (1d), WK (5d), MTH (20d), QTR (60d), 6M (126d), 1Y (252d).
    - Percentile normalization (1 - 99) strictly preserving NaNs when data is insufficient.
    - COMP (Composite RS score) and BLEND score with dynamic re-normalization over valid horizons.
    - Small-sample tracking (stk_count <= 2) and median return alongside mean return.
    - Extract top leading stocks in each industry group with TradingView links.
    """
    if latest_stocks_df.empty:
        return []

    # Merge constituent info if needed
    stocks_df = latest_stocks_df.copy()
    if "sub_industry" not in stocks_df.columns and not constituents_df.empty:
        stocks_df = pd.merge(
            stocks_df,
            constituents_df[["symbol", "security", "sector", "sub_industry"]],
            on="symbol",
            how="left"
        )

    # Exclude benchmark and sector ETFs from industry group calculations [D-05]
    etf_symbols = set(SECTOR_ETF_MAP.values()) | {BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT}
    members_df = stocks_df[~stocks_df["symbol"].isin(etf_symbols)].copy()

    if members_df.empty or "sub_industry" not in members_df.columns:
        return []

    # Group by sub_industry
    group_rows = []
    for sub_name, group in members_df.groupby("sub_industry"):
        sub_name_str = str(sub_name).strip()
        if not sub_name_str or sub_name_str.lower() in ("unknown", "nan", "none"):
            continue

        stk_count = len(group)
        if stk_count == 0:
            continue

        # Get parent sector (majority sector in this sub-industry)
        parent_sector = str(group["sector"].mode().iloc[0]) if "sector" in group.columns and not group["sector"].empty else "Unknown"

        # Equal-weighted mean & median performance across timeframes
        # Do not fill missing with 0.0 [D-01]
        v_1d = group["perf_1d"].dropna() if "perf_1d" in group.columns else pd.Series(dtype=float)
        v_5d = group["perf_5d"].dropna() if "perf_5d" in group.columns else pd.Series(dtype=float)
        v_20d = group["perf_20d"].dropna() if "perf_20d" in group.columns else pd.Series(dtype=float)
        v_60d = group["perf_60d"].dropna() if "perf_60d" in group.columns else pd.Series(dtype=float)
        v_126d = group["perf_126d"].dropna() if "perf_126d" in group.columns else pd.Series(dtype=float)
        v_252d = group["perf_252d"].dropna() if "perf_252d" in group.columns else pd.Series(dtype=float)

        avg_1d = float(v_1d.mean()) if not v_1d.empty else np.nan
        avg_5d = float(v_5d.mean()) if not v_5d.empty else np.nan
        avg_20d = float(v_20d.mean()) if not v_20d.empty else np.nan
        avg_60d = float(v_60d.mean()) if not v_60d.empty else np.nan
        avg_126d = float(v_126d.mean()) if not v_126d.empty else np.nan
        avg_252d = float(v_252d.mean()) if not v_252d.empty else np.nan

        median_20d = float(v_20d.median()) if not v_20d.empty else np.nan
        is_small_sample = bool(stk_count <= 2)

        # Internal Breadth within industry group [D-06]
        valid_ma50 = group["ma50"].dropna() if "ma50" in group.columns else pd.Series(dtype=float)
        breadth_ma50_pct = round(float((group["close"] > group["ma50"]).sum() / len(valid_ma50) * 100.0), 1) if len(valid_ma50) > 0 else None

        valid_ma20 = group["ma20"].dropna() if "ma20" in group.columns else pd.Series(dtype=float)
        breadth_ma20_pct = round(float((group["close"] > group["ma20"]).sum() / len(valid_ma20) * 100.0), 1) if len(valid_ma20) > 0 else None

        # Estimated Turnover (close * volume)
        if "close" in group.columns and "volume" in group.columns:
            m_turnover = (group["close"] * group["volume"]).dropna()
            turnover_est = float(m_turnover.sum())
        else:
            turnover_est = 0.0

        # Dispersion: standard deviation of 20d return [D-06]
        std_20d = round(float(v_20d.std()), 2) if len(v_20d) > 1 else 0.0

        # Sort constituent stocks for leadership:
        # Priority: rs_rating desc -> perf_1d desc
        sorted_members = group.copy()
        if "rs_rating" not in sorted_members.columns:
            sorted_members["rs_rating"] = np.nan
        # Handle NaN in rs_rating by sorting NaN to bottom
        sorted_members["rs_rating_sort"] = sorted_members["rs_rating"].fillna(-1)
        sorted_members = sorted_members.sort_values(
            by=["rs_rating_sort", "perf_1d"],
            ascending=[False, False]
        )

        stock_pills = []
        for _, stock_row in sorted_members.iterrows():
            sym = str(stock_row["symbol"])
            perf_1d_val = float(stock_row["perf_1d"]) if not pd.isna(stock_row.get("perf_1d")) else 0.0
            rs_val = int(stock_row["rs_rating"]) if not pd.isna(stock_row.get("rs_rating")) else None
            close_val = float(stock_row["close"]) if not pd.isna(stock_row.get("close")) else 0.0

            stock_pills.append({
                "symbol": sym,
                "security": str(stock_row.get("security", sym)),
                "perf_1d": round(perf_1d_val, 2),
                "rs_rating": rs_val,
                "close": round(close_val, 2),
                "tv_url": f"https://www.tradingview.com/chart/?symbol={sym}&interval=D"
            })

        group_rows.append({
            "industry": sub_name_str,
            "parent_sector": parent_sector,
            "stk_count": stk_count,
            "is_small_sample": is_small_sample,
            "breadth_ma50_pct": breadth_ma50_pct,
            "breadth_ma20_pct": breadth_ma20_pct,
            "turnover_est": turnover_est,
            "perf_20d_std": std_20d,
            "perf_1d": avg_1d,
            "perf_5d": avg_5d,
            "perf_20d": avg_20d,
            "median_perf_20d": median_20d,
            "perf_20d_median": median_20d,
            "perf_60d": avg_60d,
            "perf_126d": avg_126d,
            "perf_252d": avg_252d,
            "valid_count_252d": len(v_252d),
            "stocks": stock_pills
        })

    if not group_rows:
        return []

    df_groups = pd.DataFrame(group_rows)

    # 1. Calculate Percentile Ranks (1 to 99) for each timeframe, strictly preserving NaNs
    df_groups["day_rank"] = _to_percentile_series(df_groups["perf_1d"])
    df_groups["wk_rank"] = _to_percentile_series(df_groups["perf_5d"])
    df_groups["mth_rank"] = _to_percentile_series(df_groups["perf_20d"])
    df_groups["qtr_rank"] = _to_percentile_series(df_groups["perf_60d"])
    df_groups["rank_6m"] = _to_percentile_series(df_groups["perf_126d"])
    df_groups["rank_1y"] = _to_percentile_series(df_groups["perf_252d"])

    # 2. Compute COMP (Composite RS Score):
    # Dynamically re-normalize weights over available/valid horizons [D-01]
    comp_raw_list = []
    for _, row in df_groups.iterrows():
        horizons = [
            (row["qtr_rank"], COMPOSITE_RS_WEIGHTS["QTR"]),
            (row["rank_6m"], COMPOSITE_RS_WEIGHTS["6M"]),
            (row["rank_1y"], COMPOSITE_RS_WEIGHTS["1Y"]),
            (row["mth_rank"], COMPOSITE_RS_WEIGHTS["MTH"]),
            (row["wk_rank"], COMPOSITE_RS_WEIGHTS["WK"]),
        ]
        valid_h = [(rank, w) for rank, w in horizons if pd.notna(rank)]
        if valid_h:
            tot_w = sum(w for _, w in valid_h)
            score = sum(rank * w for rank, w in valid_h) / tot_w
            comp_raw_list.append(score)
        else:
            comp_raw_list.append(np.nan)

    df_groups["comp_score"] = _to_percentile_series(pd.Series(comp_raw_list, index=df_groups.index))

    # 3. Compute BLEND (Trend-Momentum Blend):
    blend_raw_list = []
    for _, row in df_groups.iterrows():
        b_items = [
            (row["comp_score"], BLEND_RS_WEIGHTS["COMP"]),
            (row["mth_rank"], BLEND_RS_WEIGHTS["MTH"]),
            (row["wk_rank"], BLEND_RS_WEIGHTS["WK"]),
        ]
        valid_b = [(rank, w) for rank, w in b_items if pd.notna(rank)]
        if valid_b:
            tot_w = sum(w for _, w in valid_b)
            score = sum(rank * w for rank, w in valid_b) / tot_w
            blend_raw_list.append(score)
        else:
            blend_raw_list.append(np.nan)

    df_groups["blend_score"] = _to_percentile_series(pd.Series(blend_raw_list, index=df_groups.index))

    # Sort by comp_score descending, then blend_score descending
    df_groups["comp_sort"] = df_groups["comp_score"].fillna(-1)
    df_groups["blend_sort"] = df_groups["blend_score"].fillna(-1)
    df_groups = df_groups.sort_values(by=["comp_sort", "blend_sort"], ascending=[False, False]).reset_index(drop=True)

    # Assign rank (1 to N)
    df_groups["rank"] = df_groups.index + 1
    df_groups["is_leading"] = df_groups["comp_score"].apply(
        lambda x: bool(x >= LEADING_GROUP_THRESHOLD) if pd.notna(x) else False
    )

    # Convert to list of dicts
    results = []
    for _, row in df_groups.iterrows():
        results.append({
            "rank": int(row["rank"]),
            "industry": str(row["industry"]),
            "parent_sector": str(row["parent_sector"]),
            "stk_count": int(row["stk_count"]),
            "is_small_sample": bool(row["is_small_sample"]),
            "day_rank": int(row["day_rank"]) if pd.notna(row["day_rank"]) else None,
            "wk_rank": int(row["wk_rank"]) if pd.notna(row["wk_rank"]) else None,
            "mth_rank": int(row["mth_rank"]) if pd.notna(row["mth_rank"]) else None,
            "qtr_rank": int(row["qtr_rank"]) if pd.notna(row["qtr_rank"]) else None,
            "rank_6m": int(row["rank_6m"]) if pd.notna(row["rank_6m"]) else None,
            "rank_1y": int(row["rank_1y"]) if pd.notna(row["rank_1y"]) else None,
            "comp_score": int(row["comp_score"]) if pd.notna(row["comp_score"]) else None,
            "blend_score": int(row["blend_score"]) if pd.notna(row["blend_score"]) else None,
            "is_leading": bool(row["is_leading"]),
            "breadth_ma50_pct": round(float(row["breadth_ma50_pct"]), 1) if pd.notna(row["breadth_ma50_pct"]) else None,
            "breadth_ma20_pct": round(float(row["breadth_ma20_pct"]), 1) if pd.notna(row["breadth_ma20_pct"]) else None,
            "turnover_est": float(row["turnover_est"]) if "turnover_est" in row and pd.notna(row["turnover_est"]) else 0.0,
            "perf_20d_std": float(row["perf_20d_std"]) if pd.notna(row["perf_20d_std"]) else 0.0,
            "perf_1d": round(float(row["perf_1d"]), 2) if pd.notna(row["perf_1d"]) else None,
            "perf_5d": round(float(row["perf_5d"]), 2) if pd.notna(row["perf_5d"]) else None,
            "perf_20d": round(float(row["perf_20d"]), 2) if pd.notna(row["perf_20d"]) else None,
            "median_perf_20d": round(float(row["median_perf_20d"]), 2) if pd.notna(row["median_perf_20d"]) else None,
            "perf_20d_median": round(float(row["median_perf_20d"]), 2) if pd.notna(row["median_perf_20d"]) else None,
            "perf_60d": round(float(row["perf_60d"]), 2) if pd.notna(row["perf_60d"]) else None,
            "perf_126d": round(float(row["perf_126d"]), 2) if pd.notna(row["perf_126d"]) else None,
            "perf_252d": round(float(row["perf_252d"]), 2) if pd.notna(row["perf_252d"]) else None,
            "valid_count_252d": int(row["valid_count_252d"]),
            "stocks": row["stocks"]
        })

    return results

