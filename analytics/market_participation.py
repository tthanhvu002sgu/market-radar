"""
analytics/market_participation.py

Bộ phân tích độ rộng thị trường theo thời gian (Market Participation) và
sức khỏe nội bộ 11 ngành GICS cuối ngày:
- Net breadth, A/D Line, AD Volume Line, MA Breadth history (20/50/200).
- Equal-weight return & Median return (loại ETF).
- RVOL ngày (so với trung vị 20 phiên trước, loại phiên hiện tại).
- Sức khỏe ngành: thanh khoản ước lượng, tỷ trọng trong universe, thay đổi tỷ trọng 5 phiên,
  mức tập trung Top 5 mã, phân kỳ đà tăng vốn hóa lớn.
"""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from config.settings import BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT
from config.sector_mappings import SECTOR_ETF_MAP, SECTOR_NAMES_VI

logger = logging.getLogger(__name__)

ETF_SYMBOLS = set(SECTOR_ETF_MAP.values()) | {BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT}


def compute_market_breadth_history(
    df_bars: pd.DataFrame,
    constituents_df: Optional[pd.DataFrame] = None,
    max_sessions: int = 60,
    as_of: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tính toán chuỗi lịch sử độ rộng và thanh khoản thị trường qua từng phiên giao dịch.
    Loại trừ toàn bộ ETF (SPY, RSP, XL*) khỏi tập cổ phiếu tính toán độ rộng.
    Mẫu số MA20/50/200 chỉ tính các mã có dữ liệu hợp lệ tại phiên đó.
    Khóa dữ liệu point-in-time <= as_of để ngăn rò rỉ dữ liệu tương lai.
    """
    if df_bars.empty:
        return {
            "records": [],
            "start_date": "",
            "as_of": as_of or "",
            "sessions_count": 0,
            "methodology_version": "v2.1",
            "ad_volume_note": "AD Volume là khối lượng của các mã tăng/giảm, không phải order flow CVD.",
            "turnover_note": "GTGD ước lượng = Close điều chỉnh * Volume.",
            "constituents_note": "Tính trên tập thành viên S&P 500 hiện tại (không phải point-in-time constituents)."
        }

    df = df_bars.copy()
    if not pd.api.types.is_string_dtype(df["date"]):
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    else:
        df["date_str"] = df["date"].astype(str)

    # Point-in-time boundary: discard bars beyond as_of
    if as_of:
        df = df[df["date_str"] <= as_of].copy()

    # Build chronological market calendar mapping to require exact previous session for 1D returns
    calendar_sessions = sorted(df["date_str"].unique())
    prev_session_map = {calendar_sessions[i]: calendar_sessions[i-1] for i in range(1, len(calendar_sessions))}

    # 1. Extract Benchmark series (SPY and RSP) with calendar alignment
    spy_df = df[df["symbol"] == BENCHMARK_TICKER].sort_values("date_str")
    rsp_df = df[df["symbol"] == BENCHMARK_EQUAL_WEIGHT].sort_values("date_str")

    def _compute_consecutive_1d_rets(series_df: pd.DataFrame) -> Dict[str, float]:
        if series_df.empty:
            return {}
        sdf = series_df.sort_values("date_str").copy()
        sdf["prev_date"] = sdf["date_str"].shift(1)
        sdf["prev_close"] = sdf["close"].shift(1)
        sdf["expected_prev"] = sdf["date_str"].map(prev_session_map)
        is_consec = (sdf["prev_date"] == sdf["expected_prev"]) & sdf["expected_prev"].notna() & (sdf["prev_close"] > 0)
        sdf["ret_1d"] = np.where(is_consec, (sdf["close"] / sdf["prev_close"] - 1.0) * 100.0, np.nan)
        return dict(zip(sdf["date_str"], sdf["ret_1d"].round(2)))

    spy_rets = _compute_consecutive_1d_rets(spy_df)
    rsp_rets = _compute_consecutive_1d_rets(rsp_df)

    # 2. Filter to S&P 500 member stocks only (excluding ETFs)
    stocks_df = df[~df["symbol"].isin(ETF_SYMBOLS)].copy()
    if constituents_df is not None and not constituents_df.empty and "symbol" in constituents_df.columns:
        expected_universe = set(constituents_df["symbol"]) - ETF_SYMBOLS
        stocks_df = stocks_df[stocks_df["symbol"].isin(expected_universe)]
    else:
        expected_universe = set(stocks_df["symbol"].unique())

    expected_count = len(expected_universe)

    if stocks_df.empty or expected_count == 0:
        return {
            "records": [],
            "start_date": "",
            "as_of": as_of or "",
            "sessions_count": 0,
            "methodology_version": "v2.1",
            "constituents_note": "Tính trên tập thành viên S&P 500 hiện tại (không phải point-in-time constituents)."
        }

    # 3. Compute rolling indicators per stock across the entire time series
    stocks_df = stocks_df.sort_values(["symbol", "date_str"])
    stock_groups = []

    for sym, grp in stocks_df.groupby("symbol", sort=False):
        grp = grp.copy()
        c = grp["close"]
        v = grp["volume"] if "volume" in grp.columns else pd.Series(0.0, index=grp.index)

        # Calendar-aware 1D performance: strictly requires price on immediately preceding calendar session
        grp["prev_stock_date"] = grp["date_str"].shift(1)
        grp["prev_stock_close"] = c.shift(1)
        grp["expected_prev_date"] = grp["date_str"].map(prev_session_map)
        is_consec = (grp["prev_stock_date"] == grp["expected_prev_date"]) & grp["expected_prev_date"].notna() & (grp["prev_stock_close"] > 0)
        grp["perf_1d"] = np.where(is_consec, (c / grp["prev_stock_close"] - 1.0) * 100.0, np.nan)

        grp["ma20"] = c.rolling(20).mean()
        grp["ma50"] = c.rolling(50).mean()
        grp["ma200"] = c.rolling(200).mean()
        grp["turnover_est"] = c * v
        stock_groups.append(grp)

    enriched_stocks = pd.concat(stock_groups, ignore_index=True)

    # 4. Aggregate by trading session date
    unique_dates = sorted(enriched_stocks["date_str"].unique())
    daily_aggregates = []

    cum_ad_line = 0
    cum_ad_vol_line = 0.0

    for d in unique_dates:
        day_slice = enriched_stocks[enriched_stocks["date_str"] == d]
        bars_count = int(day_slice["symbol"].nunique())
        if bars_count == 0:
            continue

        missing_bars_count = max(0, expected_count - bars_count)
        total_eval = expected_count

        # 1-day returns (strictly requiring price on immediately preceding calendar session)
        has_perf_1d = day_slice["perf_1d"].notna()
        valid_1d = day_slice[has_perf_1d]
        valid_count = int(has_perf_1d.sum())
        missing_count = max(0, expected_count - valid_count)

        advances = int((valid_1d["perf_1d"] > 0).sum())
        declines = int((valid_1d["perf_1d"] < 0).sum())
        unchanged = int((valid_1d["perf_1d"] == 0).sum())
        eligible_count = advances + declines + unchanged

        net_breadth = round((advances - declines) / eligible_count, 4) if eligible_count > 0 else None

        # AD Volume (volumes of advancing vs declining stocks)
        vol_adv = float(valid_1d.loc[valid_1d["perf_1d"] > 0, "volume"].sum()) if "volume" in valid_1d.columns else 0.0
        vol_dec = float(valid_1d.loc[valid_1d["perf_1d"] < 0, "volume"].sum()) if "volume" in valid_1d.columns else 0.0
        tot_ad_vol = vol_adv + vol_dec
        ad_vol_pct = round((vol_adv - vol_dec) / tot_ad_vol * 100.0, 2) if tot_ad_vol > 0 else None

        # Cumulative lines (idempotent, computed along chronological calendar)
        cum_ad_line += (advances - declines)
        cum_ad_vol_line += (vol_adv - vol_dec)

        # MA breadth (strictly valid denominators)
        has_c = "close" in day_slice.columns
        valid_ma20 = (day_slice["close"].notna() & day_slice["ma20"].notna()) if (has_c and "ma20" in day_slice.columns) else pd.Series(False, index=day_slice.index)
        n_ma20 = int(valid_ma20.sum())
        pct_ma20 = round(float((day_slice.loc[valid_ma20, "close"] > day_slice.loc[valid_ma20, "ma20"]).sum()) / n_ma20 * 100.0, 2) if n_ma20 > 0 else None

        valid_ma50 = (day_slice["close"].notna() & day_slice["ma50"].notna()) if (has_c and "ma50" in day_slice.columns) else pd.Series(False, index=day_slice.index)
        n_ma50 = int(valid_ma50.sum())
        pct_ma50 = round(float((day_slice.loc[valid_ma50, "close"] > day_slice.loc[valid_ma50, "ma50"]).sum()) / n_ma50 * 100.0, 2) if n_ma50 > 0 else None

        valid_ma200 = (day_slice["close"].notna() & day_slice["ma200"].notna()) if (has_c and "ma200" in day_slice.columns) else pd.Series(False, index=day_slice.index)
        n_ma200 = int(valid_ma200.sum())
        pct_ma200 = round(float((day_slice.loc[valid_ma200, "close"] > day_slice.loc[valid_ma200, "ma200"]).sum()) / n_ma200 * 100.0, 2) if n_ma200 > 0 else None

        # Equal-weight & Median returns
        valid_rets = valid_1d["perf_1d"]
        eq_weight_ret = round(float(valid_rets.mean()), 2) if not valid_rets.empty else None
        median_ret = round(float(valid_rets.median()), 2) if not valid_rets.empty else None

        # Turnover and market volume
        day_volume = float(day_slice["volume"].sum()) if "volume" in day_slice.columns else 0.0
        day_turnover = float(day_slice["turnover_est"].sum()) if "turnover_est" in day_slice.columns else 0.0

        daily_aggregates.append({
            "date": d,
            "expected_count": expected_count,
            "bars_count": bars_count,
            "missing_bars_count": missing_bars_count,
            "coverage_pct": round(bars_count / expected_count * 100.0, 1) if expected_count > 0 else 0.0,
            "total_evaluated": total_eval,
            "valid_count": valid_count,
            "coverage_1d_pct": round(valid_count / expected_count * 100.0, 1) if expected_count > 0 else 0.0,
            "eligible_count": eligible_count,
            "missing_count": missing_count,
            "advances": advances,
            "declines": declines,
            "unchanged": unchanged,
            "net_breadth": net_breadth,
            "ad_line": int(cum_ad_line),
            "ad_vol_line": round(cum_ad_vol_line, 0),
            "ad_vol_adv": vol_adv,
            "ad_vol_dec": vol_dec,
            "ad_vol_pct": ad_vol_pct,
            "pct_above_ma20": pct_ma20,
            "pct_above_ma50": pct_ma50,
            "pct_above_ma200": pct_ma200,
            "valid_ma20_count": n_ma20,
            "valid_ma50_count": n_ma50,
            "valid_ma200_count": n_ma200,
            "missing_ma20_count": max(0, expected_count - n_ma20),
            "missing_ma50_count": max(0, expected_count - n_ma50),
            "missing_ma200_count": max(0, expected_count - n_ma200),
            "equal_weight_return": eq_weight_ret,
            "median_return": median_ret,
            "spy_return": spy_rets.get(d),
            "rsp_return": rsp_rets.get(d),
            "total_volume": day_volume,
            "turnover_est": day_turnover,
        })

    df_agg = pd.DataFrame(daily_aggregates)

    # 5. Compute market RVOL daily: volume vs strictly causal prior 20-session median
    if len(df_agg) > 0 and "total_volume" in df_agg.columns:
        prior_vol_median = df_agg["total_volume"].shift(1).rolling(20, min_periods=5).median()
        df_agg["rvol_daily"] = np.where(prior_vol_median > 0, (df_agg["total_volume"] / prior_vol_median).round(2), np.nan)
    else:
        df_agg["rvol_daily"] = np.nan

    all_records = df_agg.to_dict(orient="records")
    recent_records = all_records[-max_sessions:] if len(all_records) > max_sessions else all_records

    # Clean NaNs in recent_records for JSON serialization
    for r in recent_records:
        for k, v in r.items():
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                r[k] = None

    start_date = all_records[0]["date"] if all_records else ""
    as_of = all_records[-1]["date"] if all_records else ""

    return {
        "records": recent_records,
        "start_date": start_date,
        "as_of": as_of,
        "sessions_count": len(recent_records),
        "total_historical_sessions": len(all_records),
        "methodology_version": "v2.1",
        "ad_volume_note": "AD Volume là khối lượng của các mã tăng/giảm, không phải order flow CVD.",
        "turnover_note": "GTGD ước lượng = Close điều chỉnh * Volume.",
        "constituents_note": "Tính trên tập thành viên S&P 500 hiện tại (không phải point-in-time constituents)."
    }


def compute_sector_health(
    latest_stocks_df: pd.DataFrame,
    df_bars: pd.DataFrame,
    constituents_df: pd.DataFrame,
    as_of: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Tính toán chỉ số sức khỏe nội bộ ngành (Sector Health):
    - Độ rộng (Breadth MA20, MA50, MA200 với mẫu số hợp lệ).
    - Lợi suất trung vị (1D, 20D/1M) phân biệt với ETF return.
    - Thanh khoản ước lượng (turnover_est), tỷ trọng trong universe và biến động tỷ trọng 5D.
    - Mức tập trung giao dịch: tỷ trọng top 5 mã trong thanh khoản ngành.
    - Cảnh báo phân kỳ đà tăng vốn hóa lớn (mega-cap divergence).
    """
    if latest_stocks_df.empty:
        return []

    # Merge constituent sector info if needed
    stocks_df = latest_stocks_df.copy()
    if "sector" not in stocks_df.columns:
        if not constituents_df.empty and "sector" in constituents_df.columns:
            stocks_df = pd.merge(
                stocks_df,
                constituents_df[["symbol", "sector", "sub_industry"]],
                on="symbol",
                how="left"
            )
        else:
            stocks_df["sector"] = "Unknown"

    # Filter out ETFs from member stocks
    members_df = stocks_df[~stocks_df["symbol"].isin(ETF_SYMBOLS)].copy()

    # Total market turnover estimate
    if "close" in members_df.columns and "volume" in members_df.columns:
        market_turnover = float((members_df["close"] * members_df["volume"]).sum())
    else:
        market_turnover = 0.0

    # Pre-calculate 5-day historical sector turnover share from df_bars
    # to compute turnover_share_change_5d
    sector_5d_shares: Dict[str, float] = {}
    if not df_bars.empty and "date" in df_bars.columns:
        try:
            b_df = df_bars[~df_bars["symbol"].isin(ETF_SYMBOLS)].copy()
            if not pd.api.types.is_string_dtype(b_df["date"]):
                b_df["date_str"] = b_df["date"].dt.strftime("%Y-%m-%d")
            else:
                b_df["date_str"] = b_df["date"].astype(str)

            # Point-in-time filtering
            if as_of:
                b_df = b_df[b_df["date_str"] <= as_of]

            if "sector" not in b_df.columns and not constituents_df.empty:
                b_df = pd.merge(b_df, constituents_df[["symbol", "sector"]], on="symbol", how="left")

            b_df["turnover"] = b_df["close"] * b_df["volume"]
            # Exclude current session (as_of) and take up to 5 prior sessions
            all_past_dates = sorted([d for d in b_df["date_str"].unique() if (not as_of or d < as_of)])
            recent_dates = all_past_dates[-5:]
            if len(recent_dates) >= 3:
                prior_slice = b_df[b_df["date_str"].isin(recent_dates)]
                tot_by_date = prior_slice.groupby("date_str")["turnover"].sum()
                sec_by_date = prior_slice.groupby(["sector", "date_str"])["turnover"].sum().unstack(level=1)
                # Compute average daily share over prior sessions
                daily_shares = sec_by_date.divide(tot_by_date, axis=1) * 100.0
                sector_5d_shares = daily_shares.mean(axis=1).to_dict()
        except Exception as e:
            logger.debug(f"Không thể tính 5d historical turnover share: {e}")

    sector_health_list = []

    for sector_name, etf_ticker in SECTOR_ETF_MAP.items():
        sec_members = members_df[members_df["sector"] == sector_name].copy()
        member_count = len(sec_members)

        # ETF row
        etf_row = latest_stocks_df[latest_stocks_df["symbol"] == etf_ticker]
        etf_1m = float(etf_row["perf_20d"].values[0]) if not etf_row.empty and "perf_20d" in etf_row.columns and pd.notna(etf_row["perf_20d"].values[0]) else None
        etf_1d = float(etf_row["perf_1d"].values[0]) if not etf_row.empty and "perf_1d" in etf_row.columns and pd.notna(etf_row["perf_1d"].values[0]) else None

        if member_count > 0:
            # Breadth on valid counts (None if 0 valid stocks)
            has_c = "close" in sec_members.columns
            valid_ma20 = (sec_members["close"].notna() & sec_members["ma20"].notna()) if (has_c and "ma20" in sec_members.columns) else pd.Series(False, index=sec_members.index)
            n_ma20 = int(valid_ma20.sum())
            b_ma20 = round(float((sec_members.loc[valid_ma20, "close"] > sec_members.loc[valid_ma20, "ma20"]).sum()) / n_ma20 * 100.0, 1) if n_ma20 > 0 else None

            valid_ma50 = (sec_members["close"].notna() & sec_members["ma50"].notna()) if (has_c and "ma50" in sec_members.columns) else pd.Series(False, index=sec_members.index)
            n_ma50 = int(valid_ma50.sum())
            b_ma50 = round(float((sec_members.loc[valid_ma50, "close"] > sec_members.loc[valid_ma50, "ma50"]).sum()) / n_ma50 * 100.0, 1) if n_ma50 > 0 else None

            valid_ma200 = (sec_members["close"].notna() & sec_members["ma200"].notna()) if (has_c and "ma200" in sec_members.columns) else pd.Series(False, index=sec_members.index)
            n_ma200 = int(valid_ma200.sum())
            b_ma200 = round(float((sec_members.loc[valid_ma200, "close"] > sec_members.loc[valid_ma200, "ma200"]).sum()) / n_ma200 * 100.0, 1) if n_ma200 > 0 else None

            # 1D Advances / Declines
            has_1d = sec_members["perf_1d"].notna() if "perf_1d" in sec_members.columns else pd.Series(False, index=sec_members.index)
            sec_valid_1d = sec_members[has_1d]
            adv = int((sec_valid_1d["perf_1d"] > 0).sum())
            dec = int((sec_valid_1d["perf_1d"] < 0).sum())
            unc = int((sec_valid_1d["perf_1d"] == 0).sum())
            net_b = round((adv - dec) / (adv + dec + unc), 4) if (adv + dec + unc) > 0 else None

            # Median and Mean returns
            p_1d_valid = sec_members["perf_1d"].dropna() if "perf_1d" in sec_members.columns else pd.Series(dtype=float)
            med_1d = round(float(p_1d_valid.median()), 2) if not p_1d_valid.empty else None
            mean_1d = round(float(p_1d_valid.mean()), 2) if not p_1d_valid.empty else None

            p_20d_valid = sec_members["perf_20d"].dropna() if "perf_20d" in sec_members.columns else pd.Series(dtype=float)
            med_20d = round(float(p_20d_valid.median()), 2) if not p_20d_valid.empty else None
            mean_20d = round(float(p_20d_valid.mean()), 2) if not p_20d_valid.empty else None

            # Liquidity / Turnover
            if "close" in sec_members.columns and "volume" in sec_members.columns:
                sec_members["m_dollar_vol"] = sec_members["close"] * sec_members["volume"]
                sec_turnover = float(sec_members["m_dollar_vol"].sum())
            else:
                sec_members["m_dollar_vol"] = 0.0
                sec_turnover = 0.0

            turnover_share_pct = round(sec_turnover / market_turnover * 100.0, 2) if market_turnover > 0 else 0.0
            prior_5d_share = sector_5d_shares.get(sector_name)
            share_change_5d = round(turnover_share_pct - prior_5d_share, 2) if prior_5d_share is not None else 0.0

            # Top 5 Stocks by Dollar Volume
            top5_df = sec_members.sort_values("m_dollar_vol", ascending=False).head(5)
            top5_stocks = []
            for _, r in top5_df.iterrows():
                stk_vol_share = round(float(r["m_dollar_vol"]) / sec_turnover * 100.0, 1) if sec_turnover > 0 else 0.0
                top5_stocks.append({
                    "symbol": r["symbol"],
                    "security": r.get("security", r["symbol"]),
                    "close": round(float(r["close"]), 2) if pd.notna(r.get("close")) else 0.0,
                    "volume": float(r["volume"]) if pd.notna(r.get("volume")) else 0.0,
                    "turnover_est": round(float(r["m_dollar_vol"]), 0),
                    "share_in_sector": stk_vol_share,
                    "perf_1d": round(float(r["perf_1d"]), 2) if pd.notna(r.get("perf_1d")) else None,
                    "perf_20d": round(float(r["perf_20d"]), 2) if pd.notna(r.get("perf_20d")) else None
                })

            top5_sum = sum(s["turnover_est"] for s in top5_stocks)
            top5_concentration_pct = round(top5_sum / sec_turnover * 100.0, 1) if sec_turnover > 0 else 0.0

            # Divergence Detection (Mega-cap mask)
            # When ETF 1M is positive (+), but internal median is negative (-) or breadth MA50 < 40% (only if MA50 is valid)
            is_divergent = bool(
                etf_1m is not None and etf_1m > 0 and (
                    (med_20d is not None and med_20d < 0) or
                    (b_ma50 is not None and b_ma50 < 40.0)
                )
            )
            if is_divergent:
                med_str = f"{med_20d:+.2f}%" if med_20d is not None else "N/A"
                b_str = f"{b_ma50}%" if b_ma50 is not None else "N/A"
                divergence_desc = f"Phân hóa cao: ETF {etf_ticker} tăng (+{etf_1m:.2f}%) nhưng trung vị cổ phiếu âm ({med_str}) hoặc độ rộng MA50 yếu ({b_str})."
            elif top5_concentration_pct > 60.0:
                divergence_desc = f"Mức tập trung giao dịch: Top 5 mã chiếm {top5_concentration_pct}% tổng GTGD ước tính của ngành."
            else:
                divergence_desc = "Mức độ phân bổ giao dịch và độ rộng nội bộ đồng thuận tương đối."

        else:
            n_ma20 = n_ma50 = n_ma200 = 0
            b_ma20 = b_ma50 = b_ma200 = None
            adv = dec = unc = 0
            net_b = None
            med_1d = mean_1d = med_20d = mean_20d = None
            sec_turnover = 0.0
            turnover_share_pct = 0.0
            share_change_5d = 0.0
            top5_concentration_pct = 0.0
            top5_stocks = []
            is_divergent = False
            divergence_desc = "Không có mã thành viên."

        sector_health_list.append({
            "sector": sector_name,
            "sector_vi": SECTOR_NAMES_VI.get(sector_name, sector_name),
            "etf": etf_ticker,
            "etf_1d": etf_1d,
            "etf_1m": etf_1m,
            "member_count": member_count,
            "valid_ma20_count": n_ma20,
            "valid_ma50_count": n_ma50,
            "valid_ma200_count": n_ma200,
            "breadth_ma20_pct": b_ma20,
            "breadth_ma50_pct": b_ma50,
            "breadth_ma200_pct": b_ma200,
            "advances": adv,
            "declines": dec,
            "unchanged": unc,
            "net_breadth": net_b,
            "median_return_1d": med_1d,
            "mean_return_1d": mean_1d,
            "median_return_1m": med_20d,
            "mean_return_1m": mean_20d,
            "turnover_est": sec_turnover,
            "turnover_share_pct": turnover_share_pct,
            "turnover_share_change_5d": share_change_5d,
            "top5_concentration_pct": top5_concentration_pct,
            "top5_stocks": top5_stocks,
            "is_divergent": is_divergent,
            "divergence_desc": divergence_desc,
            "constituents_note": "Tính trên tập thành viên S&P 500 hiện tại (không phải point-in-time constituents)",
            "methodology_version": "v2.1"
        })

    # Sort sectors by turnover share descending
    sector_health_list.sort(key=lambda x: x["turnover_share_pct"], reverse=True)
    return sector_health_list
