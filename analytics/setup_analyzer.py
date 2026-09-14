"""
Setup Analyzer Module.
Extracts structured technical evidence, multi-timeframe context, volatility metrics,
reference levels (trigger, invalidation, support, resistance), and actionable checklists.
Does NOT perform position sizing or order ledger management.
"""
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

CANDLESTICK_THRESHOLDS = {
    "doji_max_body_ratio": 0.10,
    "long_body_min_ratio": 0.70,
    "lower_shadow_min_ratio": 0.55,
    "upper_shadow_min_ratio": 0.55,
    "hammer_max_upper_shadow_ratio": 0.25,
    "shooting_star_max_lower_shadow_ratio": 0.25,
    "close_near_high_min_pct": 70.0,
    "close_near_low_max_pct": 30.0,
    "hammer_min_close_pct": 55.0,
    "shooting_star_max_close_pct": 45.0,
}

def analyze_candlestick(
    open_p: float,
    high_p: float,
    low_p: float,
    close_p: float,
    atr14: Optional[float] = None,
    prev_open: Optional[float] = None,
    prev_high: Optional[float] = None,
    prev_low: Optional[float] = None,
    prev_close: Optional[float] = None,
    bar_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Two-layer daily candlestick analyzer:
    Layer 1: Candlestick geometry & characteristics (direction, body/shadow ratios, close position in range, range vs ATR).
    Layer 2: Candlestick pattern recognition with published thresholds.
    """
    total_range = float(high_p - low_p) if (pd.notna(high_p) and pd.notna(low_p)) else 0.0
    open_p = float(open_p) if pd.notna(open_p) else float(close_p)
    high_p = float(high_p) if pd.notna(high_p) else float(close_p)
    low_p = float(low_p) if pd.notna(low_p) else float(close_p)
    close_p = float(close_p) if pd.notna(close_p) else 0.0

    if total_range <= 1e-6:
        return {
            "date": bar_date or "",
            "direction": "Cân bằng",
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "range": 0.0,
            "body": 0.0,
            "body_ratio": 0.0,
            "upper_shadow": 0.0,
            "upper_shadow_ratio": 0.0,
            "lower_shadow": 0.0,
            "lower_shadow_ratio": 0.0,
            "close_position_pct": 50.0,
            "close_position_label": "Đóng cửa giữa phiên",
            "range_to_atr": None,
            "pattern": "Không rõ mẫu hình",
            "pattern_tags": ["Không rõ mẫu hình"]
        }

    body = abs(close_p - open_p)
    body_ratio = max(0.0, min(1.0, round(body / total_range, 3)))
    upper_shadow = max(0.0, high_p - max(open_p, close_p))
    upper_shadow_ratio = max(0.0, min(1.0, round(upper_shadow / total_range, 3)))
    lower_shadow = max(0.0, min(open_p, close_p) - low_p)
    lower_shadow_ratio = max(0.0, min(1.0, round(lower_shadow / total_range, 3)))
    close_pos = max(0.0, min(100.0, round((close_p - low_p) / total_range * 100.0, 1)))

    range_to_atr = round(total_range / atr14, 2) if (atr14 and atr14 > 0 and not pd.isna(atr14)) else None

    # Direction
    if close_p > open_p:
        direction = "Tăng"
    elif close_p < open_p:
        direction = "Giảm"
    else:
        direction = "Cân bằng"

    # Close position label
    if close_pos >= CANDLESTICK_THRESHOLDS["close_near_high_min_pct"]:
        close_pos_label = "Đóng cửa gần đỉnh phiên"
    elif close_pos <= CANDLESTICK_THRESHOLDS["close_near_low_max_pct"]:
        close_pos_label = "Đóng cửa gần đáy phiên"
    else:
        close_pos_label = "Đóng cửa giữa phiên"

    # Pattern recognition
    pattern_tags = []

    # Inside bar / Outside bar vs previous session
    has_prev = (
        prev_high is not None and prev_low is not None and
        not pd.isna(prev_high) and not pd.isna(prev_low)
    )
    is_inside = False
    is_outside = False
    if has_prev:
        is_inside = (high_p <= prev_high and low_p >= prev_low)
        is_outside = (high_p > prev_high and low_p < prev_low)
        if is_inside:
            pattern_tags.append("Inside bar")
        if is_outside:
            pattern_tags.append("Outside bar")

    # Engulfing vs previous session
    has_prev_body = (
        has_prev and prev_open is not None and prev_close is not None and
        not pd.isna(prev_open) and not pd.isna(prev_close)
    )
    is_bull_engulfing = False
    is_bear_engulfing = False
    if has_prev_body:
        prev_is_bear = prev_close < prev_open
        prev_is_bull = prev_close > prev_open
        is_bull_engulfing = (
            prev_is_bear and (close_p > open_p) and
            (open_p <= prev_close) and (close_p >= prev_open)
        )
        is_bear_engulfing = (
            prev_is_bull and (close_p < open_p) and
            (open_p >= prev_close) and (close_p <= prev_open)
        )
        if is_bull_engulfing:
            pattern_tags.append("Nhấn chìm tăng (Bullish Engulfing)")
        if is_bear_engulfing:
            pattern_tags.append("Nhấn chìm giảm (Bearish Engulfing)")

    # Doji
    is_doji = (body_ratio <= CANDLESTICK_THRESHOLDS["doji_max_body_ratio"])
    if is_doji:
        pattern_tags.append("Doji")

    # Long lower shadow (Hammer / Pinbar)
    is_hammer = (
        lower_shadow_ratio >= CANDLESTICK_THRESHOLDS["lower_shadow_min_ratio"] and
        upper_shadow_ratio <= CANDLESTICK_THRESHOLDS["hammer_max_upper_shadow_ratio"] and
        close_pos >= CANDLESTICK_THRESHOLDS["hammer_min_close_pct"]
    )
    if is_hammer:
        pattern_tags.append("Râu dưới dài (Hammer)")

    # Long upper shadow (Shooting Star / Inverted Hammer)
    is_shooting_star = (
        upper_shadow_ratio >= CANDLESTICK_THRESHOLDS["upper_shadow_min_ratio"] and
        lower_shadow_ratio <= CANDLESTICK_THRESHOLDS["shooting_star_max_lower_shadow_ratio"] and
        close_pos <= CANDLESTICK_THRESHOLDS["shooting_star_max_close_pct"]
    )
    if is_shooting_star:
        pattern_tags.append("Râu trên dài (Shooting Star)")

    # Long body (Marubozu)
    is_long_body = (body_ratio >= CANDLESTICK_THRESHOLDS["long_body_min_ratio"])
    if is_long_body:
        if direction == "Tăng":
            pattern_tags.append("Thân dài tăng (Marubozu)")
        elif direction == "Giảm":
            pattern_tags.append("Thân dài giảm (Marubozu)")

    # Assign primary pattern by priority hierarchy
    if is_bull_engulfing:
        primary_pattern = "Nhấn chìm tăng (Bullish Engulfing)"
    elif is_bear_engulfing:
        primary_pattern = "Nhấn chìm giảm (Bearish Engulfing)"
    elif is_hammer:
        primary_pattern = "Râu dưới dài (Hammer)"
    elif is_shooting_star:
        primary_pattern = "Râu trên dài (Shooting Star)"
    elif is_long_body:
        primary_pattern = "Thân dài tăng (Marubozu)" if direction == "Tăng" else "Thân dài giảm (Marubozu)"
    elif is_inside:
        primary_pattern = "Inside bar"
    elif is_outside:
        primary_pattern = "Outside bar"
    elif is_doji:
        primary_pattern = "Doji"
    else:
        primary_pattern = "Không rõ mẫu hình"
        pattern_tags.append("Không rõ mẫu hình")

    return {
        "date": bar_date or "",
        "direction": direction,
        "open": round(open_p, 2),
        "high": round(high_p, 2),
        "low": round(low_p, 2),
        "close": round(close_p, 2),
        "range": round(total_range, 2),
        "body": round(body, 2),
        "body_ratio": body_ratio,
        "upper_shadow": round(upper_shadow, 2),
        "upper_shadow_ratio": upper_shadow_ratio,
        "lower_shadow": round(lower_shadow, 2),
        "lower_shadow_ratio": lower_shadow_ratio,
        "close_position_pct": close_pos,
        "close_position_label": close_pos_label,
        "range_to_atr": range_to_atr,
        "pattern": primary_pattern,
        "pattern_tags": pattern_tags
    }

def interpret_candlestick_in_setup(
    candle: Dict[str, Any],
    setup_subtype: str,
    group_type: str,
    close_price: float,
    ma20: Optional[float] = None,
    ma50: Optional[float] = None,
    prev_high20: Optional[float] = None,
    prev_low20: Optional[float] = None,
    trigger_price: Optional[float] = None,
    invalidation_price: Optional[float] = None,
    dist_ma20_atr: Optional[float] = None,
    extension_status: str = "Bình thường",
    bar_date: str = ""
) -> Dict[str, str]:
    """
    Context-aware interpretation of the latest closed daily candlestick.
    Separates geometric pattern from setup context.
    Returns 3 clear lines:
    1. candle_summary: Nến gần nhất
    2. context_summary: Bối cảnh
    3. reaction_summary: Trạng thái phản ứng
    4. reaction_status: pass / neutral / fail (used in checklist without score change)
    """
    date_str = candle.get("date") or bar_date or "phiên gần nhất"
    pattern = candle.get("pattern", "Không rõ mẫu hình")
    direction = candle.get("direction", "Cân bằng")
    close_pos_label = candle.get("close_position_label", "")
    close_pos_pct = candle.get("close_position_pct", 50.0)
    range_atr = candle.get("range_to_atr")
    atr_text = f", biên độ {range_atr}x ATR14" if range_atr is not None else ""

    # Line 1: Nến gần nhất
    if pattern != "Không rõ mẫu hình":
        candle_summary = f"{pattern}, {close_pos_label.lower()} ({close_pos_pct:.0f}% biên độ){atr_text} (phiên {date_str})."
    else:
        candle_summary = f"Nến {direction.lower()}, {close_pos_label.lower()} ({close_pos_pct:.0f}% biên độ){atr_text} (phiên {date_str}) — không rõ mẫu hình đặc biệt."

    # Extension check: price extended far beyond MA20 (> 1.5 ATR)
    is_extended = (dist_ma20_atr is not None and dist_ma20_atr > 1.5)

    # Line 2 & 3: Bối cảnh & Trạng thái phản ứng
    if is_extended and "long" in group_type:
        context_summary = f"Giá đã tăng xa MA20 ({dist_ma20_atr:+.1f} ATR) sau nhịp tăng dốc; nằm ngoài vùng tích lũy an toàn."
        reaction_summary = "Dù nến có đà tăng nhưng rủi ro mua đuổi (overextended) cao; không đủ cơ sở khuyến nghị mua mới."
        reaction_status = "fail" if dist_ma20_atr > 2.0 else "neutral"

    elif (dist_ma20_atr is not None and dist_ma20_atr < -1.5) and "short" in group_type:
        context_summary = f"Giá đã giảm quá xa MA20 ({dist_ma20_atr:+.1f} ATR); nằm sâu ngoài biên độ giảm bình thường."
        reaction_summary = "Rủi ro bán đuổi (overextended short) cao, tiềm ẩn nhịp hồi kỹ thuật (short squeeze); không có vị thế bán mới thuận lợi."
        reaction_status = "fail" if dist_ma20_atr < -2.0 else "neutral"

    elif setup_subtype in ("pullback_ma20", "pullback_ma50"):
        ma_name = "MA20" if setup_subtype == "pullback_ma20" else "MA50"
        ma_val = ma20 if setup_subtype == "pullback_ma20" else ma50
        ma_val_str = f" (${ma_val:.2f})" if ma_val else ""
        context_summary = f"Kiểm định hỗ trợ đường trung bình {ma_name}{ma_val_str} trong setup Pullback."

        if pattern in ("Râu dưới dài (Hammer)", "Nhấn chìm tăng (Bullish Engulfing)") or (close_pos_pct >= 60.0 and direction == "Tăng"):
            trig_note = f"; chưa vượt mức kích hoạt (${trigger_price:.2f})" if trigger_price and close_price < trigger_price else ""
            reaction_summary = f"Giá phản ứng rút chân ở nửa trên biên độ ({close_pos_pct:.0f}%) tại hỗ trợ {ma_name}{trig_note}."
            reaction_status = "pass"
        elif pattern in ("Doji", "Inside bar"):
            reaction_summary = f"Biên độ nén hẹp quanh hỗ trợ {ma_name}; thị trường tạm thời cân bằng chờ phiên xác nhận tiếp theo."
            reaction_status = "neutral"
        elif pattern in ("Thân dài giảm (Marubozu)", "Nhấn chìm giảm (Bearish Engulfing)") or (close_pos_pct <= 25.0 and direction == "Giảm"):
            reaction_summary = f"Giá đóng cửa ở vùng thấp ({close_pos_pct:.0f}%) xuyên thủng hỗ trợ {ma_name}; rủi ro vi phạm điều kiện pullback."
            reaction_status = "fail"
        else:
            reaction_summary = f"Đang dao động quanh vùng hỗ trợ {ma_name}; chưa xuất hiện phản ứng đảo chiều rõ nét."
            reaction_status = "neutral"

    elif setup_subtype in ("breakout", "near_breakout"):
        ref_p = prev_high20 or trigger_price
        ref_p_str = f" (${ref_p:.2f})" if ref_p else ""
        is_actual_bo = (setup_subtype == "breakout")
        context_summary = f"{'Phá vỡ' if is_actual_bo else 'Tiệm cận'} kháng cự đỉnh 20 phiên trước{ref_p_str} trong setup Breakout."

        if pattern in ("Thân dài tăng (Marubozu)", "Nhấn chìm tăng (Bullish Engulfing)") or close_pos_pct >= 75.0:
            reaction_summary = f"Giá đóng cửa sát đỉnh phiên ({close_pos_pct:.0f}% biên độ) bứt phá kháng cự; bằng chứng giá-volume ủng hộ đà tăng."
            reaction_status = "pass"
        elif pattern in ("Râu trên dài (Shooting Star)", "Nhấn chìm giảm (Bearish Engulfing)"):
            reaction_summary = "Bị từ chối tại vùng kháng cự (rút đầu để lại râu trên dài); cẩn trọng nguy cơ bứt phá giả (false breakout)."
            reaction_status = "fail"
        elif pattern in ("Doji", "Inside bar"):
            reaction_summary = "Biên độ co hẹp tích lũy nén chặt ngay trước ngưỡng cản; chờ nến bứt phá xác nhận."
            reaction_status = "neutral"
        else:
            reaction_summary = "Đang thử thách vùng kháng cự; giá chưa bứt phá dứt khoát qua ngưỡng cản."
            reaction_status = "neutral"

    elif setup_subtype in ("breakdown", "near_breakdown"):
        ref_low = prev_low20 or trigger_price
        ref_low_str = f" (${ref_low:.2f})" if ref_low else ""
        is_actual_bd = (setup_subtype == "breakdown")
        context_summary = f"{'Thủng' if is_actual_bd else 'Áp sát'} hỗ trợ đáy 20 phiên trước{ref_low_str} trong setup Breakdown."

        if pattern in ("Thân dài giảm (Marubozu)", "Nhấn chìm giảm (Bearish Engulfing)") or close_pos_pct <= 25.0:
            reaction_summary = f"Giá đóng cửa sát đáy phiên ({close_pos_pct:.0f}% biên độ) xuyên thủng đáy; quán tính giảm giá duy trì."
            reaction_status = "pass"
        elif pattern in ("Râu dưới dài (Hammer)", "Nhấn chìm tăng (Bullish Engulfing)"):
            reaction_summary = "Giá phản ứng rút chân ở vùng hỗ trợ đáy; cẩn trọng bẫy giảm giá (bear trap)."
            reaction_status = "fail"
        else:
            reaction_summary = "Dao động ở nửa dưới biên độ quanh vùng đáy; xu hướng giảm chiếm ưu thế."
            reaction_status = "neutral"

    elif setup_subtype == "pullback_ma20_res":
        ma_val_str = f" (${ma20:.2f})" if ma20 else ""
        context_summary = f"Hồi phục kiểm định kháng cự MA20{ma_val_str} trong xu hướng giảm (Short pullback)."

        if pattern in ("Râu trên dài (Shooting Star)", "Nhấn chìm giảm (Bearish Engulfing)") or close_pos_pct <= 35.0:
            reaction_summary = "Bị từ chối tại kháng cự MA20 (đóng cửa ở vùng thấp); duy trì đà rơi ngắn hạn."
            reaction_status = "pass"
        elif pattern in ("Thân dài tăng (Marubozu)", "Nhấn chìm tăng (Bullish Engulfing)"):
            reaction_summary = "Giá hồi phục đóng cửa vượt lên trên MA20; rủi ro setup short bị vô hiệu hóa."
            reaction_status = "fail"
        else:
            reaction_summary = "Chững lại quanh kháng cự MA20; chờ nến giảm xác nhận suy yếu."
            reaction_status = "neutral"

    elif setup_subtype == "reversal_reclaim":
        ma_val_str = f" (${ma20:.2f})" if ma20 else ""
        context_summary = f"Nỗ lực lấy lại đường xu hướng MA20{ma_val_str} từ vùng giá thấp (Long Reversal)."

        if pattern in ("Râu dưới dài (Hammer)", "Nhấn chìm tăng (Bullish Engulfing)", "Thân dài tăng (Marubozu)") or close_pos_pct >= 65.0:
            reaction_summary = "Phản ứng rút chân đóng cửa ở vùng cao; xuất hiện bằng chứng hỗ trợ nhịp hồi phục."
            reaction_status = "pass"
        else:
            reaction_summary = "Biên độ hồi phục còn hẹp; chưa đủ động lượng giá để xác nhận đảo chiều."
            reaction_status = "neutral"

    elif setup_subtype == "reversal_drop":
        context_summary = "Dấu hiệu suy kiệt và đảo chiều giảm từ vùng đỉnh ngắn hạn (Short Reversal)."

        if pattern in ("Râu trên dài (Shooting Star)", "Nhấn chìm giảm (Bearish Engulfing)", "Thân dài giảm (Marubozu)") or close_pos_pct <= 35.0:
            reaction_summary = "Xác nhận tín hiệu từ chối vùng giá cao (đóng sát đáy); bằng chứng thuận cho nhịp điều chỉnh."
            reaction_status = "pass"
        else:
            reaction_summary = "Điều chỉnh giằng co; chưa xuất hiện xung lực bán gãy cấu trúc."
            reaction_status = "neutral"

    else:
        context_summary = f"Theo dõi cấu trúc giá trong nhóm {group_type}."
        reaction_summary = "Chưa ghi nhận phản ứng kỹ thuật bất thường; tiếp tục quan sát."
        reaction_status = "neutral"

    return {
        "candle_summary": candle_summary,
        "context_summary": context_summary,
        "reaction_summary": reaction_summary,
        "reaction_status": reaction_status
    }

def analyze_multi_session_pressure(
    symbol: Any,
    bars: Optional[Any] = None,
    atr14: Optional[float] = None,
    side: str = "long",
    stock_dict: Optional[Dict[str, Any]] = None,
    as_of: Optional[str] = None
) -> Dict[str, Any]:
    """
    Multi-session Buying/Selling Pressure Profile (1, 3, 5 sessions) [D-03].
    Reconstructs factual price-volume evidence across multiple sessions without assuming order book depth
    or falsely claiming institutional accumulation or net inflow.
    """
    if isinstance(symbol, pd.DataFrame):
        df = symbol.copy()
        sym_str = df["symbol"].iloc[0] if ("symbol" in df.columns and not df.empty) else "UNKNOWN"
    else:
        sym_str = str(symbol)
        df = None
        if isinstance(bars, pd.DataFrame) and not bars.empty:
            df = bars.copy()
        elif isinstance(bars, list) and len(bars) > 0:
            df = pd.DataFrame(bars)

    if as_of and df is not None and not df.empty and "date" in df.columns:
        df["_dt_str"] = df["date"].astype(str).str.split().str[0]
        df = df[df["_dt_str"] <= str(as_of)].drop(columns=["_dt_str"]).copy()

    session_rows = []
    if df is not None and not df.empty:
        df = df.sort_values("date").copy()
        if "date" in df.columns:
            df["date_str"] = df["date"].astype(str).str.split().str[0]
        else:
            df["date_str"] = [f"P-{i}" for i in range(len(df))]

        # Compute returns and 20-day median volume prior to evaluation sessions
        df["prev_close"] = df["close"].shift(1)
        df["ret_1d"] = (df["close"] - df["prev_close"]) / df["prev_close"] * 100.0

        # Prior 20 median volume (requires prior bars)
        if "volume" in df.columns:
            df["vol_median20"] = df["volume"].shift(1).rolling(20, min_periods=5).median()
        else:
            df["vol_median20"] = np.nan

        last_5 = df.tail(5)
        for _, row in last_5.iterrows():
            c = float(row.get("close", 0.0))
            o = float(row.get("open", c))
            h = float(row.get("high", c))
            l = float(row.get("low", c))
            v = float(row.get("volume", 0.0))
            tot_range = h - l
            close_pos_pct = round((c - l) / tot_range * 100.0, 1) if tot_range > 1e-6 else None
            med_vol = row.get("vol_median20")
            rvol = round(v / med_vol, 2) if (med_vol and not pd.isna(med_vol) and med_vol > 0) else None
            ret = round(row.get("ret_1d", 0.0), 2) if pd.notna(row.get("ret_1d")) else None
            spread_atr = round(tot_range / atr14, 2) if (atr14 and atr14 > 0 and tot_range > 0) else None

            direction = "Tăng" if c > o else ("Giảm" if c < o else "Cân bằng")

            session_rows.append({
                "date": row.get("date_str", ""),
                "open": round(o, 2),
                "high": round(h, 2),
                "low": round(l, 2),
                "close": round(c, 2),
                "volume": int(v),
                "return_1d": ret,
                "rvol": rvol,
                "close_position_pct": close_pos_pct,
                "spread_to_atr": spread_atr,
                "direction": direction
            })

    # Fallback to stock_dict if bars not available
    if not session_rows and stock_dict:
        perf_1d = stock_dict.get("perf_1d")
        perf_5d = stock_dict.get("perf_5d")
        rel_vol = stock_dict.get("rel_volume")
        c = float(stock_dict.get("close", 0.0))
        h = float(stock_dict.get("high", c))
        l = float(stock_dict.get("low", c))
        tot_range = h - l
        close_pos_pct = round((c - l) / tot_range * 100.0, 1) if tot_range > 1e-6 else None
        session_rows.append({
            "date": str(stock_dict.get("date", "Gần nhất")).split()[0],
            "open": float(stock_dict.get("open", c)),
            "high": h,
            "low": l,
            "close": c,
            "volume": int(stock_dict.get("volume", 0)),
            "return_1d": perf_1d,
            "rvol": rel_vol,
            "close_position_pct": close_pos_pct,
            "spread_to_atr": round(tot_range / atr14, 2) if atr14 and atr14 > 0 else None,
            "direction": "Tăng" if (perf_1d and perf_1d > 0) else ("Giảm" if (perf_1d and perf_1d < 0) else "Cân bằng")
        })

    # Summarize 1, 3, 5 session windows
    supporting: List[str] = []
    contradicting: List[str] = []
    neutral_gaps: List[str] = []

    n_sessions = len(session_rows)
    up_cnt_5d = sum(1 for s in session_rows if s.get("return_1d") is not None and s["return_1d"] > 0)
    down_cnt_5d = sum(1 for s in session_rows if s.get("return_1d") is not None and s["return_1d"] < 0)
    high_vol_up_5d = sum(1 for s in session_rows if (s.get("return_1d") or 0) > 0 and (s.get("rvol") or 1.0) >= 1.0)
    high_vol_down_5d = sum(1 for s in session_rows if (s.get("return_1d") or 0) < 0 and (s.get("rvol") or 1.0) >= 1.0)
    valid_cpos_5d = [s["close_position_pct"] for s in session_rows if s.get("close_position_pct") is not None]
    avg_cpos_5d = round(float(np.mean(valid_cpos_5d)), 1) if valid_cpos_5d else None

    # Latest 1-session metrics
    latest_s = session_rows[-1] if session_rows else {}
    cpos_1d = latest_s.get("close_position_pct")
    rvol_1d = latest_s.get("rvol")
    ret_1d = latest_s.get("return_1d")

    # 3-session window
    last_3 = session_rows[-3:] if len(session_rows) >= 3 else session_rows
    up_cnt_3d = sum(1 for s in last_3 if s.get("return_1d") is not None and s["return_1d"] > 0)
    down_cnt_3d = sum(1 for s in last_3 if s.get("return_1d") is not None and s["return_1d"] < 0)
    valid_cpos_3d = [s["close_position_pct"] for s in last_3 if s.get("close_position_pct") is not None]
    avg_cpos_3d = round(float(np.mean(valid_cpos_3d)), 1) if valid_cpos_3d else None

    # Build evidence based on side
    if "long" in side.lower():
        # Supporting evidence for Long
        if up_cnt_5d >= 3:
            supporting.append(f"Giá tăng {up_cnt_5d}/{n_sessions} phiên gần nhất.")
        if high_vol_up_5d >= 1:
            supporting.append(f"Có {high_vol_up_5d} phiên tăng kèm khối lượng đạt mức tham chiếu (RVOL >= 1.0x).")
        if avg_cpos_5d is not None and avg_cpos_5d >= 55.0:
            supporting.append(f"Vị trí đóng cửa bình quân 5 phiên ({avg_cpos_5d}%) duy trì ở nửa trên biên độ.")
        if cpos_1d is not None and cpos_1d >= 65.0:
            supporting.append(f"Phiên gần nhất đóng cửa ở mức cao ({cpos_1d}% biên độ) — bằng chứng thuận cho phía mua.")

        # Contradicting evidence for Long
        if high_vol_down_5d >= 2:
            contradicting.append(f"Xuất hiện {high_vol_down_5d} phiên giảm kèm khối lượng lớn (RVOL >= 1.0x) — rủi ro điều chỉnh.")
        if cpos_1d is not None and cpos_1d <= 40.0:
            contradicting.append(f"Phiên gần nhất đóng cửa tụt về vùng thấp ({cpos_1d}% biên độ) — áp lực chốt lời ngắn hạn.")
        if rvol_1d is not None and rvol_1d < 0.8 and (ret_1d or 0) > 0:
            contradicting.append(f"Phiên tăng gần nhất có khối lượng sụt giảm (RVOL {rvol_1d}x) — khối lượng chưa đồng thuận với đà tăng.")

        # Bias label
        if len(supporting) > len(contradicting) and (up_cnt_5d >= 3 or up_cnt_3d >= 2):
            pressure_bias = "Bằng chứng thuận cho phía Mua (Giá-Volume 1/3/5 phiên)"
        elif len(contradicting) > len(supporting):
            pressure_bias = "Có bằng chứng trái chiều (Khối lượng cao ở các phiên giảm)"
        else:
            pressure_bias = "Áp lực giằng co / Phân hóa ngắn hạn"

    else:  # Short side
        # Supporting evidence for Short
        if down_cnt_5d >= 3:
            supporting.append(f"Giá giảm {down_cnt_5d}/{n_sessions} phiên gần nhất.")
        if high_vol_down_5d >= 1:
            supporting.append(f"Có {high_vol_down_5d} phiên giảm kèm khối lượng mở rộng (RVOL >= 1.0x).")
        if avg_cpos_5d is not None and avg_cpos_5d <= 45.0:
            supporting.append(f"Vị trí đóng cửa bình quân 5 phiên ({avg_cpos_5d}%) duy trì ở nửa dưới biên độ.")
        if cpos_1d is not None and cpos_1d <= 35.0:
            supporting.append(f"Phiên gần nhất đóng cửa sát đáy ({cpos_1d}% biên độ) — bằng chứng thuận cho phía bán.")

        # Contradicting evidence for Short
        if high_vol_up_5d >= 2:
            contradicting.append(f"Xuất hiện {high_vol_up_5d} phiên tăng kèm khối lượng lớn (RVOL >= 1.0x) — rủi ro nhịp hồi phục.")
        if cpos_1d is not None and cpos_1d >= 60.0:
            contradicting.append(f"Phiên gần nhất rút chân đóng cửa ở vùng cao ({cpos_1d}% biên độ) — rủi ro bear trap.")
        if rvol_1d is not None and rvol_1d < 0.8 and (ret_1d or 0) < 0:
            contradicting.append(f"Phiên giảm gần nhất có khối lượng co hẹp (RVOL {rvol_1d}x) — quán tính bán suy yếu.")

        # Bias label
        if len(supporting) > len(contradicting) and (down_cnt_5d >= 3 or down_cnt_3d >= 2):
            pressure_bias = "Bằng chứng thuận cho phía Bán (Giá-Volume 1/3/5 phiên)"
        elif len(contradicting) > len(supporting):
            pressure_bias = "Có bằng chứng trái chiều (Xuất hiện phiên rút chân đóng cao)"
        else:
            pressure_bias = "Áp lực giằng co / Phân hóa ngắn hạn"

    if n_sessions < 5:
        neutral_gaps.append(f"Dữ liệu lịch sử hiện có {n_sessions}/5 phiên — các nhận định đa phiên mang tính tham khảo.")

    any_flat = any(s.get("close_position_pct") is None for s in session_rows)
    if any_flat:
        neutral_gaps.append("Ghi nhận phiên đứng giá hoặc biên độ dao động bằng 0 (flat bar).")

    return {
        "symbol": sym_str,
        "side": side,
        "n_sessions": n_sessions,
        "sessions": session_rows,
        "summary_1d": {
            "return_1d": ret_1d,
            "rvol": rvol_1d,
            "close_position_pct": cpos_1d
        },
        "summary_3d": {
            "up_sessions": up_cnt_3d,
            "down_sessions": down_cnt_3d,
            "avg_close_position_pct": avg_cpos_3d
        },
        "summary_5d": {
            "up_sessions": up_cnt_5d,
            "down_sessions": down_cnt_5d,
            "high_vol_up_sessions": high_vol_up_5d,
            "high_vol_down_sessions": high_vol_down_5d,
            "avg_close_position_pct": avg_cpos_5d
        },
        "supporting_evidence": supporting if supporting else ["Chưa có tín hiệu ủng hộ áp đảo."],
        "contradicting_evidence": contradicting if contradicting else ["Không có mâu thuẫn kỹ thuật lớn."],
        "neutral_gaps": neutral_gaps if neutral_gaps else ["Đủ 5 phiên giao dịch hợp lệ."],
        "pressure_bias": pressure_bias,
        "methodology_note": "Khối lượng đo lường tổng giao dịch khớp lệnh hai chiều EOD; không phản ánh dòng tiền ròng vào (net inflow) hay tổ chức gom hàng."
    }

def analyze_candidate_setup(
    stock: Dict[str, Any],
    group_type: str,
    setup_subtype: str,
    fa_eval: Optional[Dict[str, Any]] = None,
    spy_perf_20d: Optional[float] = None
) -> Dict[str, Any]:
    """
    Generate structured setup details for a screened candidate.
    Returns:
        {
            "setup_type": str,
            "trigger_price": float or None,
            "trigger_condition": str,
            "trigger_method": str,
            "invalidation_price": float or None,
            "invalidation_condition": str,
            "invalidation_method": str,
            "support_level": float or None,
            "support_basis": str,
            "resistance_level": float or None,
            "resistance_basis": str,
            "atr14": float or None,
            "atr_pct": float or None,
            "dist_trigger_pct": float or None,
            "dist_trigger_atr": float or None,
            "dist_ma20_pct": float or None,
            "dist_ma20_atr": float or None,
            "dist_ma50_pct": float or None,
            "dist_ma50_atr": float or None,
            "extension_status": str,
            "avg_dollar_vol20": float or None,
            "rel_volume": float or None,
            "weekly_context": dict,
            "checklist": list of dicts,
            "evidence_json": dict
        }
    """
    close = float(stock.get("close", 0.0))
    vol = float(stock.get("volume", 0.0))
    vol_ma20 = float(stock.get("vol_ma20", 0.0))
    ma20 = float(stock.get("ma20", 0.0)) if pd.notna(stock.get("ma20")) else None
    ma50 = float(stock.get("ma50", 0.0)) if pd.notna(stock.get("ma50")) else None
    ma200 = float(stock.get("ma200", 0.0)) if pd.notna(stock.get("ma200")) else None
    high20 = float(stock.get("high20", close))
    low20 = float(stock.get("low20", close))
    prev_high20 = float(stock.get("prev_high20", high20))
    prev_low20 = float(stock.get("prev_low20", low20))
    atr14 = float(stock.get("atr14", 0.0)) if pd.notna(stock.get("atr14")) else None
    atr_pct = float(stock.get("atr_pct", 0.0)) if pd.notna(stock.get("atr_pct")) else None
    avg_dollar_vol20 = float(stock.get("avg_dollar_vol20", 0.0)) if pd.notna(stock.get("avg_dollar_vol20")) else None
    rel_vol = float(stock.get("rel_volume", 1.0)) if pd.notna(stock.get("rel_volume")) else (round(vol / vol_ma20, 2) if vol_ma20 > 0 else 1.0)
    perf_1d = float(stock.get("perf_1d", 0.0)) if pd.notna(stock.get("perf_1d")) else None
    perf_5d = float(stock.get("perf_5d", 0.0)) if pd.notna(stock.get("perf_5d")) else None
    perf_20d = float(stock.get("perf_20d", 0.0)) if pd.notna(stock.get("perf_20d")) else None
    weekly_ctx = stock.get("weekly_context", {})

    # Candlestick extraction
    open_p = float(stock.get("open", close))
    high_p = float(stock.get("high", close))
    low_p = float(stock.get("low", close))
    prev_open = float(stock.get("prev_open")) if pd.notna(stock.get("prev_open")) else None
    prev_high = float(stock.get("prev_high")) if pd.notna(stock.get("prev_high")) else None
    prev_low = float(stock.get("prev_low")) if pd.notna(stock.get("prev_low")) else None
    prev_close = float(stock.get("prev_close")) if pd.notna(stock.get("prev_close")) else None
    bar_date = str(stock.get("date", "")).split()[0] if stock.get("date") else ""

    # Defaults
    trigger_price = None
    trigger_condition = "N/A"
    trigger_method = "N/A"
    invalidation_price = None
    invalidation_condition = "N/A"
    invalidation_method = "N/A"
    support_level = None
    support_basis = "N/A"
    resistance_level = None
    resistance_basis = "N/A"

    # Distances
    dist_ma20_pct = round((close - ma20) / ma20 * 100.0, 2) if ma20 else None
    dist_ma20_atr = round((close - ma20) / atr14, 2) if (atr14 and atr14 > 0 and ma20) else None
    dist_ma50_pct = round((close - ma50) / ma50 * 100.0, 2) if ma50 else None
    dist_ma50_atr = round((close - ma50) / atr14, 2) if (atr14 and atr14 > 0 and ma50) else None

    # Logic per group & subtype
    if group_type == "long_cont":
        resistance_level = round(prev_high20, 2)
        resistance_basis = "Đỉnh 20 phiên trước đó (20-day high)"
        support_level = round(ma20 if ma20 else (ma50 or close), 2)
        support_basis = "Hỗ trợ đường trung bình MA20" if ma20 else "Hỗ trợ MA50"

        if setup_subtype == "breakout":
            trigger_price = round(prev_high20, 2)
            trigger_condition = f"Giá vượt đỉnh 20 phiên (${prev_high20:.2f}) kèm volume xác nhận >= 1.3x SMA20"
            trigger_method = "Breakout mức kháng cự đỉnh 20 phiên gần nhất"
            # Invalidation: gãy lại dưới MA20 hoặc gãy dưới trigger quá 1 ATR
            invalidation_price = round(max(ma20 or 0.0, prev_high20 - (atr14 or prev_high20 * 0.03)), 2)
            invalidation_condition = f"Đóng cửa thủng lại dưới ${invalidation_price:.2f} (phá vỡ giả / mất hỗ trợ MA20)"
            invalidation_method = "Mức vi phạm mẫu hình breakout (False breakout threshold)"
        elif setup_subtype == "near_breakout":
            trigger_price = round(prev_high20, 2)
            trigger_condition = f"Chờ đóng cửa vượt đỉnh 20 phiên (${prev_high20:.2f}) kèm volume bùng nổ"
            trigger_method = "Mức kích hoạt phá vỡ đỉnh 20 phiên gần nhất"
            invalidation_price = round(ma20 if ma20 else close * 0.95, 2)
            invalidation_condition = f"Đóng cửa thủng dưới MA20 (${invalidation_price:.2f}) mất hỗ trợ ngắn hạn"
            invalidation_method = "Hỗ trợ động MA20"
        elif setup_subtype == "pullback_ma20":
            trigger_price = round(ma20, 2) if ma20 else round(close, 2)
            trigger_condition = f"Bật tăng từ vùng hỗ trợ MA20 (${trigger_price:.2f}) với nến xanh"
            trigger_method = "Kiểm định thành công hỗ trợ động MA20"
            invalidation_price = round(ma50 if (ma50 and ma50 < (ma20 or close)) else (close - (atr14 or close * 0.03)), 2)
            invalidation_condition = f"Đóng cửa thủng dứt khoát MA50 (${invalidation_price:.2f})"
            invalidation_method = "Ngưỡng gãy xu hướng trung hạn MA50"
        else:  # pullback_ma50
            trigger_price = round(ma50, 2) if ma50 else round(close, 2)
            trigger_condition = f"Giữ vững và bật tăng từ hỗ trợ trung hạn MA50 (${trigger_price:.2f})"
            trigger_method = "Kiểm định hỗ trợ xu hướng chủ đạo MA50"
            invalidation_price = round(ma200 if (ma200 and ma200 < (ma50 or close)) else ((ma50 or close) - (atr14 or close * 0.04)), 2)
            invalidation_condition = f"Thủng dưới hỗ trợ dài hạn (${invalidation_price:.2f})"
            invalidation_method = "Ngưỡng vi phạm xu hướng lớn"

    elif group_type == "short_cont":
        support_level = round(prev_low20, 2)
        support_basis = "Đáy 20 phiên trước đó (20-day low)"
        resistance_level = round(ma20 if ma20 else (ma50 or close), 2)
        resistance_basis = "Kháng cự đường MA20" if ma20 else "Kháng cự MA50"

        if setup_subtype == "breakdown":
            trigger_price = round(prev_low20, 2)
            trigger_condition = f"Đóng cửa thủng đáy 20 phiên (${prev_low20:.2f}) kèm áp lực bán gia tăng"
            trigger_method = "Breakdown mức hỗ trợ đáy 20 phiên"
            invalidation_price = round(min(ma20 or (prev_low20 * 1.05), prev_low20 + (atr14 or prev_low20 * 0.03)), 2)
            invalidation_condition = f"Hồi phục vượt lại trên ${invalidation_price:.2f} (Bear trap / phá vỡ giả)"
            invalidation_method = "Ngưỡng phủ nhận breakdown"
        elif setup_subtype == "near_breakdown":
            trigger_price = round(prev_low20, 2)
            trigger_condition = f"Chờ xác nhận thủng đáy 20 phiên (${prev_low20:.2f})"
            trigger_method = "Kích hoạt breakdown đáy tích lũy dưới"
            invalidation_price = round(ma20 if ma20 else close * 1.05, 2)
            invalidation_condition = f"Vượt trở lại lên trên MA20 (${invalidation_price:.2f})"
            invalidation_method = "Kháng cự MA20 bị vượt"
        else:  # pullback_ma20 resistance
            trigger_price = round(ma20, 2) if ma20 else round(close, 2)
            trigger_condition = f"Bị từ chối tại kháng cự MA20 (${trigger_price:.2f}) và quay đầu giảm"
            trigger_method = "Chạm kháng cự trong xu hướng giảm"
            invalidation_price = round(ma50 if (ma50 and ma50 > (ma20 or close)) else (close + (atr14 or close * 0.03)), 2)
            invalidation_condition = f"Đóng cửa bứt phá qua MA50 (${invalidation_price:.2f})"
            invalidation_method = "Đảo chiều vượt kháng cự trung hạn"

    elif group_type == "long_rev":
        support_level = round(prev_low20, 2)
        support_basis = "Đáy kiểm định 20 phiên trước (${prev_low20:.2f})"
        resistance_level = round(ma50 if (ma50 and ma50 > close) else (prev_high20), 2)
        resistance_basis = "Kháng cự MA50 phía trên" if (ma50 and ma50 > close) else "Kháng cự đỉnh cũ"

        trigger_price = round(ma20 if ma20 else prev_low20 * 1.03, 2)
        trigger_condition = f"Lấy lại và đóng cửa vững chắc trên MA20 (${trigger_price:.2f}) kèm volume mở rộng"
        trigger_method = "Reclaim MA20 sau nhịp giảm sâu"
        invalidation_price = round(prev_low20, 2)
        invalidation_condition = f"Đóng cửa phá thủng đáy cũ 20 phiên (${prev_low20:.2f})"
        invalidation_method = "Đáy hỗ trợ gần nhất bị phá vỡ"

    elif group_type == "short_rev":
        resistance_level = round(prev_high20, 2)
        resistance_basis = "Đỉnh 20 phiên gần nhất"
        support_level = round(ma50 if (ma50 and ma50 < close) else prev_low20, 2)
        support_basis = "Hỗ trợ MA50 phía dưới" if (ma50 and ma50 < close) else "Hỗ trợ đáy cũ"

        trigger_price = round(ma20 if ma20 else prev_high20 * 0.97, 2)
        trigger_condition = f"Gãy xuống dưới MA20 (${trigger_price:.2f}) với volume bán gia tăng"
        trigger_method = "Gãy hỗ trợ MA20 sau nhịp tăng suy yếu"
        invalidation_price = round(prev_high20, 2)
        invalidation_condition = f"Vượt trở lại đỉnh 20 phiên (${prev_high20:.2f})"
        invalidation_method = "Phủ nhận tín hiệu đảo chiều đỉnh"

    else:  # watchlist / neutral
        trigger_price = round(prev_high20, 2)
        trigger_condition = "Theo dõi bứt phá đỉnh tích lũy hoặc xác nhận lại xu hướng"
        trigger_method = "Quan sát tín hiệu chưa rõ ràng"
        invalidation_price = round(prev_low20, 2)
        invalidation_condition = f"Thủng đáy 20 phiên (${prev_low20:.2f})"
        invalidation_method = "Mất vùng hỗ trợ"

    # Distances to trigger
    dist_trigger_pct = None
    dist_trigger_atr = None
    if trigger_price and trigger_price > 0:
        dist_trigger_pct = round((close - trigger_price) / trigger_price * 100.0, 2)
        if atr14 and atr14 > 0:
            dist_trigger_atr = round((close - trigger_price) / atr14, 2)

    # Extension Status
    extension_status = "Bình thường"
    if dist_trigger_atr is not None:
        if "long" in group_type:
            if dist_trigger_atr > 1.5:
                extension_status = "Quá xa điểm mua (Extended > 1.5 ATR - Rủi ro chase)"
            elif dist_trigger_atr >= 0.0:
                extension_status = "Vùng mua hợp lý (Actionable 0 - 1.5 ATR)"
            else:
                extension_status = "Đang tích lũy dưới điểm kích hoạt (Chưa kích hoạt)"
        elif "short" in group_type:
            if dist_trigger_atr < -1.5:
                extension_status = "Quá xa điểm short (Extended < -1.5 ATR)"
            elif dist_trigger_atr <= 0.0:
                extension_status = "Vùng short hợp lý (Actionable 0 - 1.5 ATR)"
            else:
                extension_status = "Đang hồi phục trên điểm kích hoạt"

    # Checklist Construction
    checklist = []

    # 1. Trend Filter
    if ma50 is not None:
        if "long" in group_type:
            is_above = close > ma50
            checklist.append({
                "criterion": "Cấu trúc Xu hướng (MA50)",
                "status": "pass" if is_above else "fail",
                "detail": f"Giá (${close:.2f}) {'nằm trên' if is_above else 'nằm dưới'} MA50 (${ma50:.2f})",
                "evidence_val": round(close - ma50, 2)
            })
        else:
            is_below = close < ma50
            checklist.append({
                "criterion": "Cấu trúc Xu hướng (MA50)",
                "status": "pass" if is_below else "fail",
                "detail": f"Giá (${close:.2f}) {'nằm dưới' if is_below else 'nằm trên'} MA50 (${ma50:.2f})",
                "evidence_val": round(close - ma50, 2)
            })
    else:
        checklist.append({
            "criterion": "Cấu trúc Xu hướng (MA50)",
            "status": "missing_data",
            "detail": "Thiếu dữ liệu nến để tính MA50",
            "evidence_val": None
        })

    # 2. Long-term MA200 Filter
    if ma200 is not None:
        if "long" in group_type:
            is_ok = close > ma200
            checklist.append({
                "criterion": "Hỗ trợ Dài hạn (MA200)",
                "status": "pass" if is_ok else "fail",
                "detail": f"Giá (${close:.2f}) {'trên' if is_ok else 'dưới'} MA200 (${ma200:.2f})",
                "evidence_val": round(close - ma200, 2)
            })
        else:
            is_ok = close < ma200
            checklist.append({
                "criterion": "Kháng cự Dài hạn (MA200)",
                "status": "pass" if is_ok else "fail",
                "detail": f"Giá (${close:.2f}) {'dưới' if is_ok else 'trên'} MA200 (${ma200:.2f})",
                "evidence_val": round(close - ma200, 2)
            })
    else:
        checklist.append({
            "criterion": "Kiểm định Dài hạn (MA200)",
            "status": "missing_data",
            "detail": "Chưa đủ 200 phiên lịch sử để tính MA200 (Hiển thị N/A)",
            "evidence_val": None
        })

    # 3. Liquidity and Dollar Volume
    liq_pass = (avg_dollar_vol20 is not None and avg_dollar_vol20 >= 10_000_000) or (vol_ma20 >= 500_000)
    checklist.append({
        "criterion": "Thanh khoản & Giá trị giao dịch",
        "status": "pass" if liq_pass else "fail",
        "detail": f"SMA20 vol: {vol_ma20:,.0f} cp, Giá trị GD TB: ${((avg_dollar_vol20 or 0)/1e6):.1f}M/phiên",
        "evidence_val": avg_dollar_vol20
    })

    # 4. Relative Strength vs SPY
    if spy_perf_20d is not None and perf_20d is not None:
        rs_diff = round(perf_20d - spy_perf_20d, 2)
        if "long" in group_type:
            rs_pass = rs_diff > 0
            checklist.append({
                "criterion": "Sức mạnh Tương đối (RS vs SPY)",
                "status": "pass" if rs_pass else "fail",
                "detail": f"RS 20 phiên: {rs_diff:+0.2f}% pts so với SPY",
                "evidence_val": rs_diff
            })
        else:
            rs_pass = rs_diff < 0
            checklist.append({
                "criterion": "Sức mạnh Tương đối (RS vs SPY)",
                "status": "pass" if rs_pass else "fail",
                "detail": f"RS 20 phiên: {rs_diff:+0.2f}% pts so với SPY",
                "evidence_val": rs_diff
            })
    else:
        checklist.append({
            "criterion": "Sức mạnh Tương đối (RS vs SPY)",
            "status": "missing_data",
            "detail": "Thiếu dữ liệu benchmark SPY để tính RS 20 phiên",
            "evidence_val": None
        })

    # 5. Earnings Risk
    if fa_eval and fa_eval.get("days_to_earnings") is not None:
        days_e = fa_eval["days_to_earnings"]
        if days_e < 0:
            e_status = "pass"
            e_detail = "Kỳ BCTC gần nhất đã qua"
        elif days_e <= 14:
            e_status = "fail"
            e_detail = f"BCTC trong {days_e} ngày tới ({fa_eval.get('earnings_status')}) — Rủi ro gap!"
        else:
            e_status = "pass"
            e_detail = f"BCTC cách {days_e} ngày ({fa_eval.get('earnings_status')})"
        checklist.append({
            "criterion": "Rủi ro Sự kiện BCTC (Earnings)",
            "status": e_status,
            "detail": e_detail,
            "evidence_val": days_e
        })
    else:
        checklist.append({
            "criterion": "Rủi ro Sự kiện BCTC (Earnings)",
            "status": "missing_data",
            "detail": "Lịch BCTC chưa xác minh",
            "evidence_val": None
        })

    # 6. Candlestick Analysis & Price Reaction (Nhận diện nến gần nhất đã đóng)
    candle_res = analyze_candlestick(
        open_p=open_p,
        high_p=high_p,
        low_p=low_p,
        close_p=close,
        atr14=atr14,
        prev_open=prev_open,
        prev_high=prev_high,
        prev_low=prev_low,
        prev_close=prev_close,
        bar_date=bar_date
    )
    candle_interp = interpret_candlestick_in_setup(
        candle=candle_res,
        setup_subtype=setup_subtype,
        group_type=group_type,
        close_price=close,
        ma20=ma20,
        ma50=ma50,
        prev_high20=prev_high20,
        prev_low20=prev_low20,
        trigger_price=trigger_price,
        invalidation_price=invalidation_price,
        dist_ma20_atr=dist_ma20_atr,
        extension_status=extension_status,
        bar_date=bar_date
    )

    checklist.append({
        "criterion": "Nến gần nhất & Phản ứng giá",
        "status": candle_interp["reaction_status"],
        "detail": f"{candle_res['pattern']} — {candle_interp['reaction_summary']}",
        "evidence_val": candle_res["pattern"]
    })

    candlestick_analysis = {
        "features": candle_res,
        "interpretation": candle_interp,
        "thresholds": CANDLESTICK_THRESHOLDS
    }

    # Multi-session buying/selling pressure analysis [D-03]
    side_str = "short" if "short" in group_type else "long"
    pressure_profile = analyze_multi_session_pressure(
        symbol=stock.get("symbol", ""),
        bars=None,
        atr14=atr14,
        side=side_str,
        stock_dict=stock
    )

    # Pack comprehensive evidence JSON
    evidence_json = {
        "setup_type": setup_subtype,
        "group_type": group_type,
        "levels": {
            "trigger": {"price": trigger_price, "condition": trigger_condition, "method": trigger_method},
            "invalidation": {"price": invalidation_price, "condition": invalidation_condition, "method": invalidation_method},
            "support": {"price": support_level, "basis": support_basis},
            "resistance": {"price": resistance_level, "basis": resistance_basis},
        },
        "volatility": {
            "atr14": round(atr14, 2) if atr14 else None,
            "atr_pct": round(atr_pct, 2) if atr_pct else None,
            "dist_trigger_pct": dist_trigger_pct,
            "dist_trigger_atr": dist_trigger_atr,
            "dist_ma20_pct": dist_ma20_pct,
            "dist_ma20_atr": dist_ma20_atr,
            "extension_status": extension_status
        },
        "liquidity": {
            "avg_volume_20": round(vol_ma20, 0),
            "avg_dollar_vol20": round(avg_dollar_vol20, 0) if avg_dollar_vol20 else None,
            "rel_volume": rel_vol
        },
        "weekly_context": weekly_ctx,
        "candlestick": candlestick_analysis,
        "multi_session_pressure": pressure_profile,
        "checklist": checklist
    }

    return {
        "setup_type": setup_subtype,
        "candle_pattern": candle_res["pattern"],
        "candlestick_analysis": candlestick_analysis,
        "multi_session_pressure": pressure_profile,
        "trigger_price": trigger_price,
        "trigger_condition": trigger_condition,
        "invalidation_price": invalidation_price,
        "invalidation_condition": invalidation_condition,
        "support_level": support_level,
        "support_basis": support_basis,
        "resistance_level": resistance_level,
        "resistance_basis": resistance_basis,
        "atr14": round(atr14, 2) if atr14 else None,
        "atr_pct": round(atr_pct, 2) if atr_pct else None,
        "dist_trigger_pct": dist_trigger_pct,
        "dist_trigger_atr": dist_trigger_atr,
        "dist_ma20_pct": dist_ma20_pct,
        "dist_ma20_atr": dist_ma20_atr,
        "dist_ma50_pct": dist_ma50_pct,
        "dist_ma50_atr": dist_ma50_atr,
        "avg_dollar_vol20": round(avg_dollar_vol20, 2) if avg_dollar_vol20 else None,
        "rel_volume": rel_vol,
        "weekly_context": weekly_ctx,
        "checklist": checklist,
        "evidence_json": evidence_json
    }
