import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from config.settings import (
    MA_PERIODS,
    VOLUME_MA_PERIOD,
    BENCHMARK_TICKER,
    BENCHMARK_EQUAL_WEIGHT,
    MIN_OBS_252D,
    MIN_OBS_126D,
    MIN_OBS_60D,
    MIN_OBS_20D,
    MIN_OBS_5D,
    MIN_OBS_1D,
)
from config.sector_mappings import SECTOR_ETF_MAP

logger = logging.getLogger(__name__)

def compute_stock_indicators(df_bars: pd.DataFrame) -> pd.DataFrame:
    """
    Compute technical indicators for each symbol from its daily bars.
    Requires columns: [symbol, date, open, high, low, close, volume].
    Returns a DataFrame with the latest bar per symbol enriched with indicators.
    Enforces strict observation count thresholds (e.g. 253 closes required for 252-day return).
    """
    if df_bars.empty:
        return pd.DataFrame()

    df_bars = df_bars.sort_values(["symbol", "date"]).copy()
    if not pd.api.types.is_string_dtype(df_bars["date"]):
        df_bars["date_str"] = df_bars["date"].dt.strftime("%Y-%m-%d")
    else:
        df_bars["date_str"] = df_bars["date"].astype(str)

    calendar_sessions = sorted(df_bars["date_str"].unique())
    prev_session_map = {calendar_sessions[i]: calendar_sessions[i-1] for i in range(1, len(calendar_sessions))}

    latest_rows = []
    for symbol, group in df_bars.groupby("symbol"):
        if len(group) < 20:
            continue

        closes = group["close"]
        volumes = group["volume"]
        highs = group["high"]
        lows = group["low"]
        n_bars = len(group)

        group = group.copy()
        group["ma20"] = closes.rolling(window=20).mean()
        group["ma50"] = closes.rolling(window=50).mean()
        group["ma200"] = closes.rolling(window=200).mean() if n_bars >= 200 else np.nan
        group["vol_ma20"] = volumes.rolling(window=VOLUME_MA_PERIOD).mean()

        # True Range and ATR14 (Wilder 14-period True Range rolling mean)
        tr0 = highs - lows
        tr1 = (highs - closes.shift(1)).abs()
        tr2 = (lows - closes.shift(1)).abs()
        tr = pd.concat([tr0, tr1, tr2], axis=1).max(axis=1)
        group["atr14"] = tr.rolling(window=14, min_periods=14).mean()
        group["atr_pct"] = (group["atr14"] / closes) * 100.0

        # Dollar Volume (20-day rolling mean of Close * Volume - estimated turnover)
        group["dollar_volume"] = closes * volumes
        group["avg_dollar_vol20"] = group["dollar_volume"].rolling(window=20, min_periods=20).mean()

        # Relative Volume (vs 20-day SMA Volume - legacy formula)
        group["rel_volume"] = np.where(group["vol_ma20"] > 0, (volumes / group["vol_ma20"]).round(2), 1.0)

        # Baseline RVOL: strictly causal 20 sessions prior, excluding current session [Step 1]
        group["vol_prior20_median"] = volumes.shift(1).rolling(window=20, min_periods=10).median()
        group["vol_prior20_mean"] = volumes.shift(1).rolling(window=20, min_periods=10).mean()
        group["rvol_prior20"] = np.where(group["vol_prior20_median"] > 0, (volumes / group["vol_prior20_median"]).round(2), np.nan)
        group["rvol_prior20_mean"] = np.where(group["vol_prior20_mean"] > 0, (volumes / group["vol_prior20_mean"]).round(2), np.nan)

        # High/Low 20 days:
        # high20 / low20 includes the current session
        group["high20"] = highs.rolling(window=20).max()
        group["low20"] = lows.rolling(window=20).min()
        # Strictly causal previous 20-day high and low (excluding current bar)
        group["prev_high20"] = highs.shift(1).rolling(window=20, min_periods=1).max()
        group["prev_low20"] = lows.shift(1).rolling(window=20, min_periods=1).min()

        # Strictly validated returns: h-period return strictly requires h+1 observations
        # 1D return strictly requires price on immediately preceding calendar session
        grp_prev_date = group["date_str"].shift(1)
        grp_expected_prev = group["date_str"].map(prev_session_map)
        is_consec_1d = (grp_prev_date == grp_expected_prev) & grp_expected_prev.notna()

        raw_perf_1d = closes.pct_change(1, fill_method=None) * 100.0 if n_bars >= MIN_OBS_1D else np.nan
        group["perf_1d"] = raw_perf_1d.where(is_consec_1d, np.nan) if isinstance(raw_perf_1d, pd.Series) else np.nan
        group["perf_5d"] = closes.pct_change(5, fill_method=None) * 100.0 if n_bars >= MIN_OBS_5D else np.nan
        group["perf_20d"] = closes.pct_change(20, fill_method=None) * 100.0 if n_bars >= MIN_OBS_20D else np.nan
        group["perf_60d"] = closes.pct_change(60, fill_method=None) * 100.0 if n_bars >= MIN_OBS_60D else np.nan
        group["perf_126d"] = closes.pct_change(126, fill_method=None) * 100.0 if n_bars >= MIN_OBS_126D else np.nan
        group["perf_252d"] = closes.pct_change(252, fill_method=None) * 100.0 if n_bars >= MIN_OBS_252D else np.nan

        # Previous day indicators for slopes, crossovers & candlestick pattern recognition
        group["prev_close"] = closes.shift(1)
        group["prev_open"] = group["open"].shift(1)
        group["prev_high"] = highs.shift(1)
        group["prev_low"] = lows.shift(1)
        group["prev_ma20"] = group["ma20"].shift(1)
        group["prev_ma50"] = group["ma50"].shift(1)

        # Bar count for provenance
        group["history_bars"] = n_bars

        # Multi-timeframe Weekly Context (resampled to Friday-ending weeks)
        latest_date = pd.to_datetime(group["date"].iloc[-1]).date()
        from analytics.market_calendar import is_end_of_trading_week
        is_week_closed = is_end_of_trading_week(latest_date)

        weekly_ctx = {
            "weekly_trend": "Chưa đủ dữ liệu",
            "weekly_close": None,
            "weekly_ma10": None,
            "weekly_ma30": None,
            "is_week_closed": is_week_closed,
            "as_of_week": latest_date.strftime("%Y-W%W"),
            "provisional_note": "" if is_week_closed else "Tuần chưa đóng (Chỉ số tuần mang tính tạm thời)"
        }

        if n_bars >= 50:
            try:
                g_dt = group.set_index("date")
                weekly_bars = g_dt["close"].resample("W-FRI").last().dropna()
                if len(weekly_bars) >= 10:
                    w_close = float(weekly_bars.iloc[-1])
                    w_ma10 = float(weekly_bars.rolling(10).mean().iloc[-1])
                    w_ma30 = float(weekly_bars.rolling(30).mean().iloc[-1]) if len(weekly_bars) >= 30 else None

                    if w_close > w_ma10 and (w_ma30 is None or w_ma10 >= w_ma30):
                        w_trend = "Xu hướng tăng (Uptrend)"
                    elif w_close < w_ma10 and (w_ma30 is not None and w_ma10 <= w_ma30):
                        w_trend = "Xu hướng giảm (Downtrend)"
                    else:
                        w_trend = "Trung tính / Giằng co (Neutral)"

                    weekly_ctx["weekly_trend"] = w_trend
                    weekly_ctx["weekly_close"] = round(w_close, 2)
                    weekly_ctx["weekly_ma10"] = round(w_ma10, 2) if not pd.isna(w_ma10) else None
                    weekly_ctx["weekly_ma30"] = round(w_ma30, 2) if (w_ma30 is not None and not pd.isna(w_ma30)) else None
            except Exception as e:
                logger.debug(f"Weekly context calculation exception for {symbol}: {e}")

        # Append latest bar
        latest_row = group.iloc[-1].to_dict()
        latest_row["weekly_context"] = weekly_ctx
        latest_rows.append(latest_row)

    if not latest_rows:
        return pd.DataFrame()

    result_df = pd.DataFrame(latest_rows)

    # Compute Stock Relative Strength Rating (1-99 percentile)
    # Exclude benchmark and sector ETFs from ranking universe [D-05]
    etf_symbols = set(SECTOR_ETF_MAP.values()) | {BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT}

    # Weighting components: 60d (40%), 126d (20%), 252d (20%), 20d (20%)
    # Do NOT fallback long horizons to short horizons [D-01]!
    # Instead, re-normalize weights among available valid horizons for stocks with >= 60 bars.
    raw_rs_list = []
    for _, row in result_df.iterrows():
        sym = row["symbol"]
        if sym in etf_symbols:
            raw_rs_list.append(np.nan)
            continue

        p_20 = row.get("perf_20d")
        p_60 = row.get("perf_60d")
        p_126 = row.get("perf_126d")
        p_252 = row.get("perf_252d")

        # Require at least 20d and 60d for meaningful multi-timeframe RS
        if pd.isna(p_20) or pd.isna(p_60):
            raw_rs_list.append(np.nan)
            continue

        components = [(p_60, 0.40), (p_20, 0.20)]
        if not pd.isna(p_126):
            components.append((p_126, 0.20))
        if not pd.isna(p_252):
            components.append((p_252, 0.20))

        total_weight = sum(w for _, w in components)
        val = sum(v * w for v, w in components) / total_weight
        raw_rs_list.append(val)

    result_df["rs_raw"] = raw_rs_list

    # Rank only valid non-ETF stocks
    valid_stocks_mask = ~result_df["symbol"].isin(etf_symbols) & result_df["rs_raw"].notna()
    result_df["rs_rating"] = np.nan

    valid_count = valid_stocks_mask.sum()
    if valid_count > 1:
        ranked = result_df.loc[valid_stocks_mask, "rs_raw"].rank(pct=True, ascending=True)
        result_df.loc[valid_stocks_mask, "rs_rating"] = (ranked * 98 + 1).round().astype(int)
    elif valid_count == 1:
        result_df.loc[valid_stocks_mask, "rs_rating"] = 50

    return result_df

def compute_market_breadth(
    latest_stocks_df: pd.DataFrame,
    df_bars: pd.DataFrame,
    constituents_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Compute market-wide breadth metrics across S&P 500 stocks and benchmark comparison.
    Fact-grounded interpretations without unsupported claims.
    """
    if latest_stocks_df.empty:
        return {
            "expected_count": 0,
            "bars_count": 0,
            "missing_bars_count": 0,
            "total_evaluated": 0,
            "valid_count": 0,
            "eligible_count": 0,
            "missing_count": 0,
            "methodology_version": "v2.1",
            "quality_flags": ["Không có dữ liệu cổ phiếu"],
            "pct_above_ma20": None,
            "pct_above_ma50": None,
            "pct_above_ma200": None,
            "valid_ma20_count": 0,
            "valid_ma50_count": 0,
            "valid_ma200_count": 0,
            "advances": 0,
            "declines": 0,
            "unchanged": 0,
            "net_breadth": None,
            "ad_ratio": None,
            "ad_volume_adv": 0.0,
            "ad_volume_dec": 0.0,
            "ad_volume_pct": None,
            "near_20d_highs": 0,
            "near_20d_lows": 0,
            "new_20d_highs": 0,
            "new_20d_lows": 0,
            "coverage_252d_pct": 0.0,
            "spy_1d": None,
            "spy_5d": None,
            "spy_20d": None,
            "rsp_1d": None,
            "rsp_5d": None,
            "rsp_20d": None,
            "concentration_divergence": "Không đủ dữ liệu",
            "market_summary": "Chưa có đủ dữ liệu để tính toán độ rộng thị trường."
        }

    # Filter out benchmark and sector ETFs from breadth universe calculation
    etf_symbols = set(SECTOR_ETF_MAP.values()) | {BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT}
    stocks_only = latest_stocks_df[~latest_stocks_df["symbol"].isin(etf_symbols)].copy()

    if constituents_df is not None and not constituents_df.empty and "symbol" in constituents_df.columns:
        expected_universe = set(constituents_df["symbol"]) - etf_symbols
    else:
        expected_universe = set(stocks_only["symbol"].unique())

    expected_count = len(expected_universe)
    bars_count = int(stocks_only["symbol"].nunique())
    missing_bars_count = max(0, expected_count - bars_count)

    total = expected_count
    if bars_count == 0 and expected_count == 0:
        return {}

    # Stocks above MAs (denominator: stocks with valid close and MA per domain review line 109)
    valid_ma20_mask = stocks_only["close"].notna() & stocks_only["ma20"].notna()
    n_valid_ma20 = int(valid_ma20_mask.sum())
    pct_ma20 = round(float((stocks_only.loc[valid_ma20_mask, "close"] > stocks_only.loc[valid_ma20_mask, "ma20"]).sum() / n_valid_ma20 * 100.0), 2) if n_valid_ma20 > 0 else None

    valid_ma50_mask = stocks_only["close"].notna() & stocks_only["ma50"].notna()
    n_valid_ma50 = int(valid_ma50_mask.sum())
    pct_ma50 = round(float((stocks_only.loc[valid_ma50_mask, "close"] > stocks_only.loc[valid_ma50_mask, "ma50"]).sum() / n_valid_ma50 * 100.0), 2) if n_valid_ma50 > 0 else None

    valid_ma200_mask = stocks_only["close"].notna() & stocks_only["ma200"].notna()
    n_valid_ma200 = int(valid_ma200_mask.sum())
    pct_ma200 = round(float((stocks_only.loc[valid_ma200_mask, "close"] > stocks_only.loc[valid_ma200_mask, "ma200"]).sum() / n_valid_ma200 * 100.0), 2) if n_valid_ma200 > 0 else None

    # 252d coverage
    valid_252d = stocks_only["perf_252d"].dropna() if "perf_252d" in stocks_only.columns else pd.Series(dtype=float)
    coverage_252d_pct = round(float(len(valid_252d) / total * 100.0), 1) if total > 0 else 0.0

    # Advance / Decline (1-day): separate missing data from unchanged
    has_perf_1d = stocks_only["perf_1d"].notna()
    valid_1d_stocks = stocks_only[has_perf_1d]
    valid_count = int(has_perf_1d.sum())
    missing_count = max(0, expected_count - valid_count)

    advances = int((valid_1d_stocks["perf_1d"] > 0).sum())
    declines = int((valid_1d_stocks["perf_1d"] < 0).sum())
    unchanged = int((valid_1d_stocks["perf_1d"] == 0).sum())
    eligible_count = advances + declines + unchanged
    ad_ratio = round(advances / max(declines, 1), 2) if eligible_count > 0 else None
    net_breadth = round((advances - declines) / eligible_count, 4) if eligible_count > 0 else None

    # Advance / Decline Volume (Volumes of advancing vs declining stocks, NOT order-flow CVD) [Step 2]
    if "volume" in valid_1d_stocks.columns:
        vol_adv = float(valid_1d_stocks.loc[valid_1d_stocks["perf_1d"] > 0, "volume"].sum())
        vol_dec = float(valid_1d_stocks.loc[valid_1d_stocks["perf_1d"] < 0, "volume"].sum())
        tot_ad_vol = vol_adv + vol_dec
        ad_vol_pct = round((vol_adv - vol_dec) / tot_ad_vol * 100.0, 2) if tot_ad_vol > 0 else None
    else:
        vol_adv = 0.0
        vol_dec = 0.0
        ad_vol_pct = None

    # Near 20-day Highs & Lows (close within 0.5% of high20 / low20) [D-08]
    near_highs = int((stocks_only["close"] >= stocks_only["high20"] * 0.995).sum())
    near_lows = int((stocks_only["close"] <= stocks_only["low20"] * 1.005).sum())

    # SPY vs RSP Performance
    spy_row = latest_stocks_df[latest_stocks_df["symbol"] == BENCHMARK_TICKER]
    rsp_row = latest_stocks_df[latest_stocks_df["symbol"] == BENCHMARK_EQUAL_WEIGHT]

    spy_1d = round(float(spy_row["perf_1d"].values[0]), 2) if not spy_row.empty and "perf_1d" in spy_row.columns and pd.notna(spy_row["perf_1d"].values[0]) else None
    spy_5d = round(float(spy_row["perf_5d"].values[0]), 2) if not spy_row.empty and "perf_5d" in spy_row.columns and pd.notna(spy_row["perf_5d"].values[0]) else None
    spy_20d = round(float(spy_row["perf_20d"].values[0]), 2) if not spy_row.empty and "perf_20d" in spy_row.columns and pd.notna(spy_row["perf_20d"].values[0]) else None

    rsp_1d = round(float(rsp_row["perf_1d"].values[0]), 2) if not rsp_row.empty and "perf_1d" in rsp_row.columns and pd.notna(rsp_row["perf_1d"].values[0]) else None
    rsp_5d = round(float(rsp_row["perf_5d"].values[0]), 2) if not rsp_row.empty and "perf_5d" in rsp_row.columns and pd.notna(rsp_row["perf_5d"].values[0]) else None
    rsp_20d = round(float(rsp_row["perf_20d"].values[0]), 2) if not rsp_row.empty and "perf_20d" in rsp_row.columns and pd.notna(rsp_row["perf_20d"].values[0]) else None

    # Concentration Divergence Analysis: SPY vs RSP [D-08]
    has_spy = spy_20d is not None
    has_rsp = rsp_20d is not None

    if has_spy and has_rsp:
        diff_20d = spy_20d - rsp_20d
        if diff_20d > 2.5:
            concentration_status = "Đà tăng tập trung cao ở nhóm vốn hóa lớn (Mega-caps); độ rộng thị trường bị che mờ."
        elif diff_20d < -2.5:
            concentration_status = "Độ rộng lan tỏa sang các thành phần có tỷ trọng nhỏ hơn trong S&P 500 (RSP vượt trội SPY)."
        else:
            concentration_status = "Đà tăng/giảm đồng pha giữa nhóm vốn hóa lớn và các thành phần khác trong S&P 500."
    else:
        concentration_status = "Chưa đủ dữ liệu benchmark (SPY/RSP) để phân tích mức độ tập trung vốn hóa."

    # Quality flags & Metadata
    quality_flags = []
    if missing_count > 0:
        quality_flags.append(f"{missing_count} mã thiếu nến ngày")
    if not (has_spy and has_rsp):
        quality_flags.append("Thiếu benchmark SPY/RSP")
    if coverage_252d_pct < 80.0:
        quality_flags.append("Lịch sử 1Y < 80%")

    # Fact-grounded Advance/Decline sentence [D-08]
    if advances > declines:
        ad_summary = f"Số mã tăng ({advances}) chiếm ưu thế so với số mã giảm ({declines})."
    elif declines > advances:
        ad_summary = f"Số mã giảm ({declines}) chiếm ưu thế so với số mã tăng ({advances})."
    else:
        ad_summary = f"Số mã tăng và giảm cân bằng ({advances}/{declines})."

    # Market Summary Sentence (Fact-grounded, not speculative)
    if pct_ma50 is not None and pct_ma200 is not None:
        if pct_ma50 >= 60.0 and pct_ma200 >= 60.0:
            summary_env = f"Thị trường duy trì xu hướng tăng lành mạnh trên diện rộng: {pct_ma50}% cổ phiếu giữ vững MA50 và {pct_ma200}% trên MA200. {ad_summary}"
        elif pct_ma50 < 40.0 and pct_ma200 < 40.0:
            summary_env = f"Áp lực suy yếu chi phối diện rộng: Chỉ có {pct_ma50}% cổ phiếu trên MA50 và {pct_ma200}% trên MA200. {ad_summary}"
        else:
            summary_env = f"Thị trường phân hóa rõ rệt: {pct_ma50}% cổ phiếu giữ trên MA50 trong khi {pct_ma200}% trên MA200. {ad_summary} {concentration_status}"
    else:
        summary_env = f"Chưa đủ dữ liệu MA để đánh giá xu hướng thị trường trên diện rộng. {ad_summary}"

    return {
        "expected_count": expected_count,
        "bars_count": bars_count,
        "missing_bars_count": missing_bars_count,
        "total_evaluated": total,
        "valid_count": valid_count,
        "eligible_count": eligible_count,
        "missing_count": missing_count,
        "methodology_version": "v2.1",
        "quality_flags": quality_flags,
        "pct_above_ma20": pct_ma20,
        "pct_above_ma50": pct_ma50,
        "pct_above_ma200": pct_ma200,
        "valid_ma20_count": int(n_valid_ma20),
        "valid_ma50_count": int(n_valid_ma50),
        "valid_ma200_count": int(n_valid_ma200),
        "coverage_252d_pct": coverage_252d_pct,
        "advances": advances,
        "declines": declines,
        "unchanged": unchanged,
        "net_breadth": net_breadth,
        "ad_ratio": ad_ratio,
        "ad_volume_adv": vol_adv,
        "ad_volume_dec": vol_dec,
        "ad_volume_pct": ad_vol_pct,
        "near_20d_highs": near_highs,
        "near_20d_lows": near_lows,
        "new_20d_highs": near_highs,  # Backward compatibility
        "new_20d_lows": near_lows,    # Backward compatibility
        "spy_1d": spy_1d,
        "spy_5d": spy_5d,
        "spy_20d": spy_20d,
        "rsp_1d": rsp_1d,
        "rsp_5d": rsp_5d,
        "rsp_20d": rsp_20d,
        "concentration_divergence": concentration_status,
        "market_summary": summary_env,
    }
