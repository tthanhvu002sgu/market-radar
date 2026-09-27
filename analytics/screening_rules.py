import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from config.settings import (
    MIN_AVG_VOLUME,
    MIN_PRICE,
    VOLUME_SURGE_RATIO,
    PULLBACK_TOLERANCE_PCT,
    BENCHMARK_TICKER,
    BENCHMARK_EQUAL_WEIGHT,
    LEADING_GROUP_THRESHOLD,
)
from config.sector_mappings import SECTOR_ETF_MAP
from analytics.company_fa import evaluate_fa_flags
from analytics.setup_analyzer import analyze_candidate_setup
from analytics.candidate_quality import evaluate_quality

logger = logging.getLogger(__name__)

def _format_trend_long_reason(close: float, ma20: float, ma50: float, ma200: Optional[float]) -> str:
    """Format factually accurate description of long trend moving averages [D-02]."""
    parts = [f"Giá (${close:.2f}) > MA50 (${ma50:.2f})"]
    if ma200 is not None and not pd.isna(ma200):
        if ma50 > ma200:
            parts.append(f"MA50 > MA200 (${ma200:.2f})")
        else:
            parts.append(f"Giá > MA200 (${ma200:.2f}), MA50 chưa cắt lên MA200")
    else:
        parts.append("chưa đủ 200 nến để tính MA200")

    if ma20 >= ma50:
        parts.append(f"MA20 (${ma20:.2f}) trên MA50")
    return "Cấu trúc xu hướng tăng: " + ", ".join(parts) + "."

def _format_trend_short_reason(close: float, ma20: float, ma50: float, ma200: Optional[float]) -> str:
    """Format factually accurate description of short trend moving averages [D-02]."""
    parts = [f"Giá (${close:.2f}) < MA50 (${ma50:.2f})"]
    if ma200 is not None and not pd.isna(ma200):
        if ma50 < ma200:
            parts.append(f"MA50 < MA200 (${ma200:.2f})")
        else:
            parts.append(f"Giá < MA200 (${ma200:.2f}), MA50 chưa cắt xuống MA200")
    else:
        parts.append("chưa đủ 200 nến để tính MA200")

    if ma20 <= ma50:
        parts.append(f"MA20 (${ma20:.2f}) dưới MA50")
    return "Cấu trúc xu hướng giảm: " + ", ".join(parts) + "."

def evaluate_market_context_alignment(
    group_type: str,
    setup_type: str,
    market_metrics: Optional[Dict[str, Any]]
) -> Tuple[str, str]:
    """
    Evaluate alignment between individual setup and aggregate market context [D-1].
    Returns (label, reason).
    Labels: 'phù hợp', 'mâu thuẫn', 'chưa đủ dữ liệu', 'phân hóa / trung tính'.
    Used as review support without arbitrarily blocking candidates prior to validation.
    """
    if not market_metrics or not isinstance(market_metrics, dict):
        return "chưa đủ dữ liệu", "Chưa có dữ liệu độ rộng để xác định bối cảnh thị trường."

    pct_ma50 = market_metrics.get("pct_above_ma50")
    if pct_ma50 is None:
        pct_ma50 = market_metrics.get("breadth_ma50_pct")
    pct_ma200 = market_metrics.get("pct_above_ma200")
    if pct_ma200 is None:
        pct_ma200 = market_metrics.get("breadth_ma200_pct")

    if pct_ma50 is None or pd.isna(pct_ma50):
        return "chưa đủ dữ liệu", "Thiếu chỉ số % cổ phiếu trên MA50 để đánh giá bối cảnh thị trường."

    pct_ma50 = float(pct_ma50)
    pct_ma200_val = float(pct_ma200) if (pct_ma200 is not None and not pd.isna(pct_ma200)) else None
    ma200_str = f", {pct_ma200_val:.1f}% > MA200" if pct_ma200_val is not None else ""

    is_broad_bull = (pct_ma50 >= 55.0 and (pct_ma200_val is None or pct_ma200_val >= 50.0))
    is_broad_bear = (pct_ma50 < 45.0 and (pct_ma200_val is None or pct_ma200_val < 50.0))

    if group_type == "long_cont":
        if is_broad_bull:
            return "phù hợp", f"Bối cảnh thị trường tăng đồng thuận ({pct_ma50:.1f}% > MA50{ma200_str}); thuận lợi cho vị thế Long tiếp diễn."
        elif is_broad_bear:
            return "mâu thuẫn", f"Bối cảnh thị trường suy yếu diện rộng ({pct_ma50:.1f}% > MA50{ma200_str}); vị thế Long tiếp diễn đi ngược pha thị trường."
        else:
            return "phân hóa / trung tính", f"Bối cảnh thị trường phân hóa ({pct_ma50:.1f}% > MA50{ma200_str}); cần chọn lọc kỹ cổ phiếu dẫn dắt."

    elif group_type == "short_cont":
        if is_broad_bear:
            return "phù hợp", f"Bối cảnh thị trường suy yếu diện rộng ({pct_ma50:.1f}% > MA50{ma200_str}); thuận lợi cho vị thế Short tiếp diễn."
        elif is_broad_bull:
            return "mâu thuẫn", f"Bối cảnh thị trường tăng mạnh áp đảo ({pct_ma50:.1f}% > MA50{ma200_str}); vị thế Short tiếp diễn gặp rủi ro ngược sóng."
        else:
            return "phân hóa / trung tính", f"Bối cảnh thị trường phân hóa ({pct_ma50:.1f}% > MA50{ma200_str}); mức độ đồng thuận short ở mức trung bình."

    elif group_type == "long_rev":
        if is_broad_bull:
            return "phù hợp", f"Thị trường chung tích cực ({pct_ma50:.1f}% > MA50{ma200_str}); nhịp đảo chiều tăng có xác suất nhận dòng tiền lan tỏa."
        elif is_broad_bear:
            return "mâu thuẫn", f"Thị trường chung chịu áp lực giảm ({pct_ma50:.1f}% > MA50{ma200_str}); bắt đáy đảo chiều long mang rủi ro bẫy tăng giá."
        else:
            return "phân hóa / trung tính", f"Thị trường phân hóa ({pct_ma50:.1f}% > MA50{ma200_str}); đảo chiều tăng cần kiểm tra kỹ lực cầu tại vùng hỗ trợ."

    elif group_type == "short_rev":
        if is_broad_bear:
            return "phù hợp", f"Thị trường chung suy yếu ({pct_ma50:.1f}% > MA50{ma200_str}); hỗ trợ kích hoạt lực bán đảo chiều giảm."
        elif is_broad_bull:
            return "mâu thuẫn", f"Độ rộng thị trường tích cực ({pct_ma50:.1f}% > MA50{ma200_str}); short đảo chiều đỉnh đối mặt rủi ro bị bóp nghẽn ngắn hạn."
        else:
            return "phân hóa / trung tính", f"Thị trường phân hóa ({pct_ma50:.1f}% > MA50{ma200_str}); tín hiệu đảo chiều giảm ở mức trung tính."

    return "phân hóa / trung tính", f"Bối cảnh thị trường ({pct_ma50:.1f}% > MA50{ma200_str}); tín hiệu kỹ thuật nội bộ đang mâu thuẫn."

def screen_candidates(
    latest_stocks_df: pd.DataFrame,
    sector_metrics: List[Dict[str, Any]],
    fundamentals_df: Optional[Any] = None,
    industry_metrics: Optional[List[Dict[str, Any]]] = None,
    fa_data_dict: Optional[Dict[str, Any]] = None,
    ref_date: Optional[date] = None,
    require_benchmark: bool = False,
    market_metrics: Optional[Dict[str, Any]] = None
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
            "perf_1m": s.get("etf_1m"),
            "status": s.get("status")
        }

    # Market benchmark returns [D-03]
    has_spy_ticker = BENCHMARK_TICKER in latest_stocks_df["symbol"].values
    if has_spy_ticker:
        spy_row = latest_stocks_df[latest_stocks_df["symbol"] == BENCHMARK_TICKER]
        spy_val = spy_row["perf_20d"].values[0] if (not spy_row.empty and "perf_20d" in spy_row.columns) else np.nan
        if pd.notna(spy_val):
            spy_1m = float(spy_val)
            spy_is_valid = True
        else:
            # SPY is present in universe but lacks valid 20d return
            spy_1m = None
            spy_is_valid = False
            logger.warning("Benchmark SPY thiếu dữ liệu lợi suất 20 phiên! RS vs SPY không khả dụng.")
    elif require_benchmark or len(latest_stocks_df) > 10:
        # Full universe or required benchmark: missing SPY means RS unavailable [D-03]
        spy_1m = None
        spy_is_valid = False
        logger.warning("Không tìm thấy Benchmark SPY trong vũ trụ! RS vs SPY không khả dụng.")
    else:
        # Isolated test fixture / standalone stock without benchmark
        spy_1m = 0.0
        spy_is_valid = True

    # Fundamentals map
    fa_map = {}
    if fa_data_dict:
        fa_map.update(fa_data_dict)
    if fundamentals_df is not None:
        if isinstance(fundamentals_df, dict):
            fa_map.update(fundamentals_df)
        elif hasattr(fundamentals_df, "iterrows") and not fundamentals_df.empty:
            for _, row in fundamentals_df.iterrows():
                fa_map[row["symbol"]] = row.to_dict()

    # Industry groups map (O'Neil CANSLIM)
    industry_map = {ind["industry"]: ind for ind in (industry_metrics or [])}

    etf_symbols = set(SECTOR_ETF_MAP.values()) | {BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT}

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
        perf_20d = float(stock.get("perf_20d", 0.0)) if pd.notna(stock.get("perf_20d")) else 0.0
        high20 = float(stock.get("high20", close))
        low20 = float(stock.get("low20", close))
        prev_high20 = float(stock.get("prev_high20", high20))
        prev_low20 = float(stock.get("prev_low20", low20))
        prev_close = float(stock.get("prev_close", close))
        prev_ma20 = float(stock.get("prev_ma20", ma20))
        sector = stock.get("sector", "Unknown")
        company_name = stock.get("security", sym)
        rs_rating_val = stock.get("rs_rating")

        # 1. Liquidity & Price sanity filter
        if pd.isna(close) or close < MIN_PRICE or pd.isna(vol_ma) or vol_ma < MIN_AVG_VOLUME or pd.isna(ma50):
            continue

        sec_info = sector_etf_perf.get(sector, {"etf": "SPY", "perf_1m": spy_1m, "status": "Trung tính"})
        sec_perf_1m = sec_info["perf_1m"]
        sec_etf = sec_info["etf"]

        rs_vs_spy = round(perf_20d - spy_1m, 2) if spy_1m is not None else None
        rs_vs_sec = round(perf_20d - sec_perf_1m, 2) if sec_perf_1m is not None else None

        vol_ratio = round(vol / vol_ma, 2) if vol_ma > 0 else 1.0

        matches = []

        # --- A. Long Tiếp Diễn (Trend Continuation) ---
        # Trend: Close > MA50, Close > MA200 (if valid), MA20 >= MA50
        trend_long = close > ma50 and (pd.isna(ma200) or close > ma200) and ma20 >= ma50
        # Strong relative strength requires outperforming benchmark SPY & Sector ETF
        rs_long = (rs_vs_spy is not None and rs_vs_spy > 0 and (rs_vs_sec is None or rs_vs_sec >= 0))
        if trend_long and rs_long:
            # Strictly causal breakout vs near breakout setup [D-02]
            is_breakout = close > prev_high20 and vol_ratio >= VOLUME_SURGE_RATIO
            is_near_breakout = close >= prev_high20 * 0.985 and close <= prev_high20 and vol_ratio >= 1.0

            near_ma20 = abs(close - ma20) / ma20 <= PULLBACK_TOLERANCE_PCT
            near_ma50 = abs(close - ma50) / ma50 <= PULLBACK_TOLERANCE_PCT

            if is_breakout or is_near_breakout or near_ma20 or near_ma50:
                trend_reason = _format_trend_long_reason(close, ma20, ma50, ma200)
                sec_part = f" và +{rs_vs_sec}% pts so với ETF ngành {sec_etf}" if rs_vs_sec is not None else ""
                reasons = [
                    trend_reason,
                    f"Sức mạnh tương đối (RS 1M): +{rs_vs_spy}% pts so với SPY{sec_part}.",
                ]

                if is_breakout:
                    status = "confirmed"
                    score_bonus = 10.0
                    subtype = "breakout"
                    reasons.append(f"Breakout vượt đỉnh 20 phiên trước (${prev_high20:.2f}) kèm volume xác nhận ({vol_ratio}x SMA20 vol).")
                elif is_near_breakout:
                    status = "setup"
                    score_bonus = 6.0
                    subtype = "near_breakout"
                    reasons.append(f"Sát đỉnh 20 phiên trước (${prev_high20:.2f}) — tích lũy kỹ thuật trong biên 1.5% trước đỉnh kèm volume đạt {vol_ratio}x SMA20 vol (chỉ kiểm tra vị trí sát đỉnh, chưa đủ điều kiện nền giá).")
                elif near_ma20:
                    status = "confirmed" if (close > ma20 and perf_1d > 0) else "setup"
                    score_bonus = 5.0
                    subtype = "pullback_ma20"
                    reasons.append(f"Pullback kiểm định hỗ trợ đường MA20 (${ma20:.2f}).")
                else:
                    status = "confirmed" if (close > ma50 and perf_1d > 0) else "setup"
                    score_bonus = 5.0
                    subtype = "pullback_ma50"
                    reasons.append(f"Pullback kiểm định hỗ trợ trung hạn MA50 (${ma50:.2f}).")

                matches.append({
                    "group_type": "long_cont",
                    "subtype": subtype,
                    "status": status,
                    "technical_reasons": reasons,
                    "short_caveat": "",
                    "score": (rs_vs_spy or 0.0) + (rs_vs_sec or 0.0) + score_bonus
                })

        # --- B. Short Tiếp Diễn (Downtrend Continuation) ---
        trend_short = close < ma50 and (pd.isna(ma200) or close < ma200) and ma20 <= ma50
        rs_short = (rs_vs_spy is not None and rs_vs_spy < 0 and (rs_vs_sec is None or rs_vs_sec <= 0))
        if trend_short and rs_short:
            # Strictly causal breakdown vs near breakdown setup [D-02]
            is_breakdown = close < prev_low20 and vol_ratio >= 1.0
            is_near_breakdown = close <= prev_low20 * 1.015 and close >= prev_low20
            near_ma20_res = abs(close - ma20) / ma20 <= PULLBACK_TOLERANCE_PCT

            if is_breakdown or is_near_breakdown or near_ma20_res:
                trend_reason = _format_trend_short_reason(close, ma20, ma50, ma200)
                sec_part = f" và {rs_vs_sec}% pts so với ETF ngành {sec_etf}" if rs_vs_sec is not None else ""
                reasons = [
                    trend_reason,
                    f"Sức mạnh tương đối yếu (RS 1M): {rs_vs_spy}% pts so với SPY{sec_part}.",
                ]

                if is_breakdown:
                    status = "confirmed"
                    score_bonus = 10.0
                    subtype = "breakdown"
                    reasons.append(f"Breakdown thủng hỗ trợ đáy 20 phiên trước (${prev_low20:.2f}) kèm áp lực bán ({vol_ratio}x SMA20 vol).")
                elif is_near_breakdown:
                    status = "setup"
                    score_bonus = 6.0
                    subtype = "near_breakdown"
                    reasons.append(f"Tiệm cận vùng đáy 20 phiên (${prev_low20:.2f}) — có nguy cơ breakdown.")
                else:
                    status = "setup"
                    score_bonus = 5.0
                    subtype = "pullback_ma20_res"
                    reasons.append(f"Hồi phục chạm kháng cự MA20 (${ma20:.2f}) và có tín hiệu suy yếu.")

                matches.append({
                    "group_type": "short_cont",
                    "subtype": subtype,
                    "status": status,
                    "technical_reasons": reasons,
                    "short_caveat": "Chưa xác minh khả năng short / phí vay thực tế tại broker",
                    "score": abs(rs_vs_spy or 0.0) + abs(rs_vs_sec or 0.0) + score_bonus
                })

        # --- C. Long Đảo Chiều (Long Reversal / Mean Reversion) ---
        # Prior downtrend: was below MA20 or MA50
        was_down = prev_close < prev_ma20 or (not pd.isna(ma50) and prev_close < ma50)
        reclaimed_ma20 = close > ma20 and prev_close <= prev_ma20
        rebound_from_low = close > prev_low20 * 1.02 and perf_5d > 0 and (rs_vs_spy is None or rs_vs_spy > -2.0)

        if was_down and (reclaimed_ma20 or rebound_from_low):
            is_confirmed = reclaimed_ma20 and vol_ratio >= VOLUME_SURGE_RATIO
            status = "confirmed" if is_confirmed else "setup"
            subtype = "reversal_reclaim" if reclaimed_ma20 else "reversal_rebound"
            reasons = [
                f"Tín hiệu hồi phục kỹ thuật: Thoát đáy 20 phiên trước (${prev_low20:.2f}) sau nhịp điều chỉnh.",
            ]
            if reclaimed_ma20:
                reasons.append(f"Vượt trở lại lên trên MA20 (${ma20:.2f})" + (f" kèm volume mở rộng ({vol_ratio}x SMA20 vol)." if is_confirmed else "."))
            else:
                reasons.append(f"Nhịp hồi phục ngắn hạn (+{perf_5d:.1f}% trong 5 phiên) từ vùng đáy 20 phiên trước (${prev_low20:.2f}).")

            matches.append({
                "group_type": "long_rev",
                "subtype": subtype,
                "status": status,
                "technical_reasons": reasons,
                "short_caveat": "",
                "score": perf_5d + (10 if is_confirmed else 3)
            })

        # --- D. Short Đảo Chiều (Short Reversal) ---
        was_up = prev_close > prev_ma20 and (pd.isna(ma50) or prev_close > ma50)
        lost_ma20 = close < ma20 and prev_close >= prev_ma20
        pullback_from_high = close < prev_high20 * 0.96 and perf_5d < 0 and (rs_vs_spy is None or rs_vs_spy < 0)

        if was_up and (lost_ma20 or pullback_from_high):
            is_confirmed = lost_ma20 and vol_ratio >= 1.1
            status = "confirmed" if is_confirmed else "setup"
            subtype = "reversal_drop" if lost_ma20 else "reversal_pullback"
            reasons = [
                f"Tín hiệu suy yếu kỹ thuật: Thoái lui sau chuỗi tăng chạm đỉnh 20 phiên trước (${prev_high20:.2f}).",
            ]
            if lost_ma20:
                reasons.append(f"Gãy xuống dưới đường MA20 (${ma20:.2f})" + (f" kèm volume bán gia tăng ({vol_ratio}x SMA20 vol)." if is_confirmed else "."))
            else:
                reasons.append(f"Nhịp suy yếu ngắn hạn ({perf_5d:.1f}% trong 5 phiên) từ vùng đỉnh 20 phiên trước (${prev_high20:.2f}).")

            matches.append({
                "group_type": "short_rev",
                "subtype": subtype,
                "status": status,
                "technical_reasons": reasons,
                "short_caveat": "Chưa xác minh khả năng short / phí vay thực tế tại broker",
                "score": abs(perf_5d) + (10 if is_confirmed else 3)
            })

        # --- Contradiction Filter ---
        has_long = any("long" in m["group_type"] for m in matches)
        has_short = any("short" in m["group_type"] for m in matches)

        # Run complete fundamental evaluation with reference date [D-07]
        fa_raw = fa_map.get(sym, {})
        fa_eval = evaluate_fa_flags(sym, fa_raw, ref_date=ref_date)

        # Industry Leadership & Stock Leadership Check [D-05, D-06]
        sub_ind = str(stock.get("sub_industry", "")).strip()
        ind_info = industry_map.get(sub_ind, {})
        industry_comp = int(ind_info.get("comp_score", 0)) if ind_info.get("comp_score") is not None else 0
        is_group_leading = bool(industry_comp >= LEADING_GROUP_THRESHOLD)
        is_small_sample = bool(ind_info.get("is_small_sample", False))

        # Stock is an actual Leader only if the industry is leading AND the stock itself is strong [D-05]
        stock_is_strong = False
        if pd.notna(rs_rating_val):
            stock_is_strong = (rs_rating_val >= 70)
        else:
            stock_is_strong = (rs_vs_spy is not None and rs_vs_spy > 0 and perf_20d > 0 and close > ma50)

        is_stock_leader = is_group_leading and stock_is_strong

        for m in matches:
            if is_stock_leader and "long" in m["group_type"]:
                bonus = 15.0 if not is_small_sample else 7.5
                sample_note = " (Mẫu nhỏ: ≤2 mã)" if is_small_sample else ""
                m["technical_reasons"].insert(0, f"⭐ O'Neil Leader (Cảm hứng CANSLIM): Thuộc Top 20% nhóm ngành mạnh ({sub_ind} - COMP #{industry_comp}{sample_note}) và RS cổ phiếu vượt trội.")
                m["score"] += bonus
            elif is_group_leading and "long" in m["group_type"]:
                m["technical_reasons"].insert(0, f"Thuộc Top 20% nhóm ngành mạnh ({sub_ind} - COMP #{industry_comp}), nhưng RS cổ phiếu chưa đạt chuẩn Leader.")
                m["score"] += 3.0

            # Attach earnings event alert if imminent [D-07]
            if fa_eval and fa_eval.get("days_to_earnings") is not None and 0 <= fa_eval.get("days_to_earnings") <= 14:
                m["technical_reasons"].append(f"⚠️ Sắp công bố BCTC ({fa_eval.get('earnings_status')}) — rủi ro biến động gap!")

        if has_long and has_short:
            contra_reasons = ["Tín hiệu mâu thuẫn giữa xu hướng lớn và nhịp hồi/chỉnh ngắn hạn (loại khỏi ưu tiên)."]
            if fa_eval and fa_eval.get("days_to_earnings") is not None and 0 <= fa_eval.get("days_to_earnings") <= 14:
                contra_reasons.append(f"⚠️ Sắp công bố BCTC ({fa_eval.get('earnings_status')}) — rủi ro biến động gap!")

            setup_analysis = analyze_candidate_setup(
                stock=stock.to_dict(),
                group_type="watchlist",
                setup_subtype="contradiction",
                fa_eval=fa_eval,
                spy_perf_20d=spy_1m
            )

            align_tag, align_summary = evaluate_market_context_alignment("watchlist", "contradiction", market_metrics)
            candidates_raw.append({
                "symbol": sym,
                "company_name": company_name,
                "sector": sector,
                "sub_industry": sub_ind,
                "is_oneil_leader": False,
                "rs_rating": int(rs_rating_val) if pd.notna(rs_rating_val) else None,
                "rs_vs_spy": rs_vs_spy,
                "industry_comp": industry_comp,
                "group_type": "watchlist",
                "status": "watchlist",
                "setup_type": "contradiction",
                "signal_key": f"{sym}:watchlist:contradiction",
                "close_price": round(close, 2),
                "perf_1d": round(perf_1d, 2),
                "perf_5d": round(perf_5d, 2),
                "perf_20d": round(perf_20d, 2),
                "technical_reasons": contra_reasons,
                "fa_flags": fa_eval,
                "short_caveat": "",
                "score": 0.0,
                "tv_url": f"https://www.tradingview.com/chart/?symbol={sym}&interval=D",
                "trigger_price": setup_analysis.get("trigger_price"),
                "trigger_condition": setup_analysis.get("trigger_condition", ""),
                "invalidation_price": setup_analysis.get("invalidation_price"),
                "invalidation_condition": setup_analysis.get("invalidation_condition", ""),
                "support_level": setup_analysis.get("support_level"),
                "support_basis": setup_analysis.get("support_basis", ""),
                "resistance_level": setup_analysis.get("resistance_level"),
                "resistance_basis": setup_analysis.get("resistance_basis", ""),
                "atr14": setup_analysis.get("atr14"),
                "atr_pct": setup_analysis.get("atr_pct"),
                "dist_trigger_pct": setup_analysis.get("dist_trigger_pct"),
                "dist_trigger_atr": setup_analysis.get("dist_trigger_atr"),
                "dist_ma20_pct": setup_analysis.get("dist_ma20_pct"),
                "dist_ma20_atr": setup_analysis.get("dist_ma20_atr"),
                "avg_dollar_vol20": setup_analysis.get("avg_dollar_vol20"),
                "rel_volume": setup_analysis.get("rel_volume"),
                "weekly_context": setup_analysis.get("weekly_context", {}),
                "candle_pattern": setup_analysis.get("candle_pattern", "Không rõ mẫu hình"),
                "candlestick_analysis": setup_analysis.get("candlestick_analysis", {}),
                "checklist": setup_analysis.get("checklist", []),
                "evidence_json": setup_analysis.get("evidence_json", {}),
                "market_context_alignment": align_tag,
                "market_context_summary": align_summary
            })
        else:
            for m in matches:
                subtype = m.get("subtype", "")
                setup_analysis = analyze_candidate_setup(
                    stock=stock.to_dict(),
                    group_type=m["group_type"],
                    setup_subtype=subtype,
                    fa_eval=fa_eval,
                    spy_perf_20d=spy_1m
                )
                align_tag, align_summary = evaluate_market_context_alignment(m["group_type"], subtype, market_metrics)

                candidates_raw.append({
                    "symbol": sym,
                    "company_name": company_name,
                    "sector": sector,
                    "sub_industry": sub_ind,
                    "is_oneil_leader": is_stock_leader,
                    "rs_rating": int(rs_rating_val) if pd.notna(rs_rating_val) else None,
                    "rs_vs_spy": rs_vs_spy,
                    "industry_comp": industry_comp,
                    "group_type": m["group_type"],
                    "status": m["status"],
                    "setup_type": subtype,
                    "signal_key": f"{sym}:{m['group_type']}:{subtype}",
                    "close_price": round(close, 2),
                    "perf_1d": round(perf_1d, 2),
                    "perf_5d": round(perf_5d, 2),
                    "perf_20d": round(perf_20d, 2),
                    "technical_reasons": m["technical_reasons"],
                    "fa_flags": fa_eval,
                    "short_caveat": m["short_caveat"],
                    "score": round(m["score"], 2),
                    "tv_url": f"https://www.tradingview.com/chart/?symbol={sym}&interval=D",
                    "trigger_price": setup_analysis.get("trigger_price"),
                    "trigger_condition": setup_analysis.get("trigger_condition", ""),
                    "invalidation_price": setup_analysis.get("invalidation_price"),
                    "invalidation_condition": setup_analysis.get("invalidation_condition", ""),
                    "support_level": setup_analysis.get("support_level"),
                    "support_basis": setup_analysis.get("support_basis", ""),
                    "resistance_level": setup_analysis.get("resistance_level"),
                    "resistance_basis": setup_analysis.get("resistance_basis", ""),
                    "atr14": setup_analysis.get("atr14"),
                    "atr_pct": setup_analysis.get("atr_pct"),
                    "dist_trigger_pct": setup_analysis.get("dist_trigger_pct"),
                    "dist_trigger_atr": setup_analysis.get("dist_trigger_atr"),
                    "dist_ma20_pct": setup_analysis.get("dist_ma20_pct"),
                    "dist_ma20_atr": setup_analysis.get("dist_ma20_atr"),
                    "avg_dollar_vol20": setup_analysis.get("avg_dollar_vol20"),
                    "rel_volume": setup_analysis.get("rel_volume"),
                    "weekly_context": setup_analysis.get("weekly_context", {}),
                    "candle_pattern": setup_analysis.get("candle_pattern", "Không rõ mẫu hình"),
                    "candlestick_analysis": setup_analysis.get("candlestick_analysis", {}),
                    "checklist": setup_analysis.get("checklist", []),
                    "evidence_json": setup_analysis.get("evidence_json", {}),
                    "market_context_alignment": align_tag,
                    "market_context_summary": align_summary
                })

    # Sort each group by score descending (no forced quotas)
    final_candidates = sorted(candidates_raw, key=lambda x: x["score"], reverse=True)
    for candidate in final_candidates:
        candidate["evidence_json"]["review_quality"] = evaluate_quality(candidate)
    return final_candidates
