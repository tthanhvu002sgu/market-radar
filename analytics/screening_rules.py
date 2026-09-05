import logging
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from config.settings import (
    MIN_AVG_VOLUME,
    MIN_PRICE,
    VOLUME_SURGE_RATIO,
    PULLBACK_TOLERANCE_PCT,
    BENCHMARK_TICKER,
)
from config.sector_mappings import SECTOR_ETF_MAP

logger = logging.getLogger(__name__)

def screen_candidates(
    latest_stocks_df: pd.DataFrame,
    sector_metrics: List[Dict[str, Any]],
    fundamentals_df: Optional[pd.DataFrame] = None
) -> List[Dict[str, Any]]:
    """
    Screen S&P 500 universe into 4 candidate groups:
    1. Long Tiếp Diễn (long_cont)
    2. Short Tiếp Diễn (short_cont)
    3. Long Đảo Chiều (long_rev)
    4. Short Đảo Chiều (short_rev)
    Applies contradiction filtering and attaches TA reasons and FA flags.
    Does NOT enforce quotas (supports 0 to N candidates).
    """
    if latest_stocks_df.empty:
        return []

    # Map ETF sector performance
    sector_etf_perf = {}
    for s in sector_metrics:
        sector_etf_perf[s["sector"]] = {
            "etf": s["etf"],
            "perf_1m": s["etf_1m"],
            "status": s["status"]
        }

    # Market benchmark returns
    spy_row = latest_stocks_df[latest_stocks_df["symbol"] == BENCHMARK_TICKER]
    spy_1m = float(spy_row["perf_20d"].values[0]) if not spy_row.empty and not pd.isna(spy_row["perf_20d"].values[0]) else 0.0

    # Fundamentals map
    fa_map = {}
    if fundamentals_df is not None and not fundamentals_df.empty:
        for _, row in fundamentals_df.iterrows():
            fa_map[row["symbol"]] = row.to_dict()

    etf_symbols = set(SECTOR_ETF_MAP.values()) | {BENCHMARK_TICKER, "RSP"}

    candidates_raw: List[Dict[str, Any]] = []

    for _, stock in latest_stocks_df.iterrows():
        sym = stock["symbol"]
        if sym in etf_symbols:
            continue

        close = float(stock.get("close", 0.0))
        vol = float(stock.get("volume", 0.0))
        vol_ma = float(stock.get("vol_ma20", 0.0))
        ma20 = float(stock.get("ma20", 0.0))
        ma50 = float(stock.get("ma50", 0.0))
        ma200 = float(stock.get("ma200", 0.0))
        perf_1d = float(stock.get("perf_1d", 0.0))
        perf_5d = float(stock.get("perf_5d", 0.0))
        perf_20d = float(stock.get("perf_20d", 0.0))
        high20 = float(stock.get("high20", close))
        low20 = float(stock.get("low20", close))
        prev_close = float(stock.get("prev_close", close))
        prev_ma20 = float(stock.get("prev_ma20", ma20))
        sector = stock.get("sector", "Unknown")
        company_name = stock.get("security", sym)

        # 1. Liquidity & Price sanity filter
        if close < MIN_PRICE or vol_ma < MIN_AVG_VOLUME or pd.isna(ma50):
            continue

        sec_info = sector_etf_perf.get(sector, {"etf": "SPY", "perf_1m": spy_1m, "status": "Trung tính"})
        sec_perf_1m = sec_info["perf_1m"]
        sec_etf = sec_info["etf"]

        rs_vs_spy = round(perf_20d - spy_1m, 2)
        rs_vs_sec = round(perf_20d - sec_perf_1m, 2)

        vol_ratio = round(vol / vol_ma, 2) if vol_ma > 0 else 1.0

        matches = []

        # --- A. Long Tiếp Diễn (Trend Continuation) ---
        # Trend: Close > MA50, Close > MA200 (if valid), MA20 >= MA50
        trend_long = close > ma50 and (pd.isna(ma200) or close > ma200) and ma20 >= ma50
        # Strong relative strength
        rs_long = rs_vs_spy > 0 and rs_vs_sec >= 0
        if trend_long and rs_long:
            # Pattern: Pullback to MA20/MA50 or Breakout near 20d High with volume
            near_ma20 = abs(close - ma20) / ma20 <= PULLBACK_TOLERANCE_PCT
            near_ma50 = abs(close - ma50) / ma50 <= PULLBACK_TOLERANCE_PCT
            breakout = close >= high20 * 0.99 and vol_ratio >= VOLUME_SURGE_RATIO

            if near_ma20 or near_ma50 or breakout:
                reasons = [
                    f"Cấu trúc xu hướng tăng: Giá (${close:.2f}) > MA50 (${ma50:.2f}) > MA200 (${ma200:.2f}), MA20 trên MA50.",
                    f"Sức mạnh tương đối (RS 1M): +{rs_vs_spy}% so với SPY và +{rs_vs_sec}% so với ETF ngành {sec_etf}.",
                ]
                if breakout:
                    reasons.append(f"Breakout vùng đỉnh 20 phiên (${high20:.2f}) kèm volume xác nhận ({vol_ratio}x SMA20 vol).")
                elif near_ma20:
                    reasons.append(f"Pullback lành mạnh về hỗ trợ đường MA20 (${ma20:.2f}).")
                else:
                    reasons.append(f"Pullback kiểm định hỗ trợ trung hạn MA50 (${ma50:.2f}).")

                matches.append({
                    "group_type": "long_cont",
                    "status": "confirmed",
                    "technical_reasons": reasons,
                    "short_caveat": "",
                    "score": rs_vs_spy + rs_vs_sec + (10 if breakout else 5)
                })

        # --- B. Short Tiếp Diễn (Downtrend Continuation) ---
        trend_short = close < ma50 and (pd.isna(ma200) or close < ma200) and ma20 <= ma50
        rs_short = rs_vs_spy < 0 and rs_vs_sec <= 0
        if trend_short and rs_short:
            # Pullback up to MA20/MA50 or Breakdown below 20d Low
            near_ma20_res = abs(close - ma20) / ma20 <= PULLBACK_TOLERANCE_PCT
            breakdown = close <= low20 * 1.01 and vol_ratio >= 1.0

            if near_ma20_res or breakdown:
                reasons = [
                    f"Cấu trúc xu hướng giảm: Giá (${close:.2f}) < MA50 (${ma50:.2f}) < MA200 (${ma200:.2f}), MA20 dưới MA50.",
                    f"Sức mạnh tương đối yếu (RS 1M): {rs_vs_spy}% so với SPY và {rs_vs_sec}% so với ETF ngành {sec_etf}.",
                ]
                if breakdown:
                    reasons.append(f"Breakdown thủng hỗ trợ đáy 20 phiên (${low20:.2f}) kèm áp lực bán.")
                else:
                    reasons.append(f"Hồi phục chạm kháng cự MA20 (${ma20:.2f}) và có tín hiệu suy yếu.")

                matches.append({
                    "group_type": "short_cont",
                    "status": "confirmed",
                    "technical_reasons": reasons,
                    "short_caveat": "Chưa xác minh khả năng short / phí vay thực tế tại broker",
                    "score": abs(rs_vs_spy) + abs(rs_vs_sec) + (10 if breakdown else 5)
                })

        # --- C. Long Đảo Chiều (Long Mean Reversion / Reversal) ---
        # Prior downtrend: was below MA20 or MA50
        was_down = prev_close < prev_ma20 or (not pd.isna(ma50) and prev_close < ma50)
        reclaimed_ma20 = close > ma20 and prev_close <= prev_ma20
        higher_low_base = close > low20 * 1.02 and perf_5d > 0 and rs_vs_spy > -2.0

        if was_down and (reclaimed_ma20 or higher_low_base):
            is_confirmed = reclaimed_ma20 and vol_ratio >= VOLUME_SURGE_RATIO
            status = "confirmed" if is_confirmed else "watchlist"
            reasons = [
                f"Tín hiệu đảo chiều đáy: Thoát đáy 20 phiên (${low20:.2f}) sau nhịp điều chỉnh sâu.",
            ]
            if reclaimed_ma20:
                reasons.append(f"Vượt trở lại lên trên MA20 (${ma20:.2f})" + (f" kèm volume mở rộng ({vol_ratio}x SMA20 vol)." if is_confirmed else "."))
            else:
                reasons.append(f"Tạo nền đáy cao hơn hỗ trợ cũ, hiệu suất 5 phiên phục hồi (+{perf_5d:.1f}%).")

            matches.append({
                "group_type": "long_rev",
                "status": status,
                "technical_reasons": reasons,
                "short_caveat": "",
                "score": perf_5d + (10 if is_confirmed else 3)
            })

        # --- D. Short Đảo Chiều (Short Top Reversal) ---
        was_up = prev_close > prev_ma20 and (pd.isna(ma50) or prev_close > ma50)
        lost_ma20 = close < ma20 and prev_close >= prev_ma20
        lower_high_break = close < high20 * 0.96 and perf_5d < 0 and rs_vs_spy < 0

        if was_up and (lost_ma20 or lower_high_break):
            is_confirmed = lost_ma20 and vol_ratio >= 1.1
            status = "confirmed" if is_confirmed else "watchlist"
            reasons = [
                f"Tín hiệu đảo chiều đỉnh: Suy yếu sau chuỗi tăng chạm đỉnh 20 phiên (${high20:.2f}).",
            ]
            if lost_ma20:
                reasons.append(f"Gãy xuống dưới đường MA20 (${ma20:.2f})" + (f" kèm volume bán gia tăng ({vol_ratio}x SMA20 vol)." if is_confirmed else "."))
            else:
                reasons.append(f"Tạo đỉnh thấp hơn và suy giảm đà tăng 5 phiên ({perf_5d:.1f}%).")

            matches.append({
                "group_type": "short_rev",
                "status": status,
                "technical_reasons": reasons,
                "short_caveat": "Chưa xác minh khả năng short / phí vay thực tế tại broker",
                "score": abs(perf_5d) + (10 if is_confirmed else 3)
            })

        # --- Contradiction Filter ---
        # If matches both a Long group and a Short group -> demote to watchlist with contradiction note
        has_long = any("long" in m["group_type"] for m in matches)
        has_short = any("short" in m["group_type"] for m in matches)

        fa_info = fa_map.get(sym, {})

        if has_long and has_short:
            candidates_raw.append({
                "symbol": sym,
                "company_name": company_name,
                "sector": sector,
                "group_type": "watchlist",
                "status": "watchlist",
                "close_price": round(close, 2),
                "perf_1d": round(perf_1d, 2),
                "perf_5d": round(perf_5d, 2),
                "perf_20d": round(perf_20d, 2),
                "technical_reasons": ["Tín hiệu mâu thuẫn giữa xu hướng lớn và nhịp hồi/chỉnh ngắn hạn (loại khỏi ưu tiên)."],
                "fa_flags": fa_info,
                "short_caveat": "",
                "score": 0.0,
                "tv_url": f"https://www.tradingview.com/chart/?symbol={sym}"
            })
        else:
            for m in matches:
                candidates_raw.append({
                    "symbol": sym,
                    "company_name": company_name,
                    "sector": sector,
                    "group_type": m["group_type"],
                    "status": m["status"],
                    "close_price": round(close, 2),
                    "perf_1d": round(perf_1d, 2),
                    "perf_5d": round(perf_5d, 2),
                    "perf_20d": round(perf_20d, 2),
                    "technical_reasons": m["technical_reasons"],
                    "fa_flags": fa_info,
                    "short_caveat": m["short_caveat"],
                    "score": m["score"],
                    "tv_url": f"https://www.tradingview.com/chart/?symbol={sym}"
                })

    # Sort each group by score descending (no forced quotas)
    final_candidates = sorted(candidates_raw, key=lambda x: x["score"], reverse=True)
    return final_candidates
