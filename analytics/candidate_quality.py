"""Versioned review gates. Scores are priorities, never win probabilities.

Uses only supplied snapshot evidence; does not fetch prices or mutate candidates.
"""
from collections import Counter
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class QualityPolicy:
    version: str = "review-v1"
    min_dollar_volume: float = 10_000_000
    max_trigger_atr: float = 1.0
    max_ma20_atr: float = 2.0
    max_risk_atr: float = 2.5
    max_risk_pct: float = 6.0
    min_room_risk: float = 1.5
    earnings_days: int = 7
    min_break_volume: float = 1.2
    min_close_position: float = 60.0
    touch_tolerance_atr: float = 0.25


DEFAULT_POLICY = QualityPolicy()
TIER_LABELS = {"ready": "Đạt bộ lọc", "wait": "Chờ xác nhận", "reject": "Không ưu tiên"}


def number(value):
    try:
        value = float(value)
        return value if isfinite(value) else None
    except (TypeError, ValueError):
        return None


def evaluate_quality(candidate, policy=DEFAULT_POLICY):
    c = candidate
    blocked, waiting = [], []
    group, subtype = c.get("group_type", ""), c.get("setup_type", "")
    side = -1 if group.startswith("short") else 1
    if group not in {"long_cont", "short_cont", "long_rev", "short_rev"}:
        blocked.append("Tín hiệu mâu thuẫn hoặc chưa xác định chiều")
    close, trigger, stop, atr = [number(c.get(k)) for k in
                                ("close_price", "trigger_price", "invalidation_price", "atr14")]
    valid_levels = all(v is not None and v > 0 for v in (close, trigger, stop, atr))
    entry = risk_pct = risk_atr = room_risk = extension = None
    if not valid_levels:
        waiting.append("Thiếu giá/trigger/vô hiệu/ATR hợp lệ")
    else:
        entry = max(close, trigger) if side == 1 else min(close, trigger)
        risk = side * (entry - stop)
        extension = side * (close - trigger) / atr
        if extension > policy.max_trigger_atr:
            blocked.append("Giá đã chạy quá xa trigger")
        if side * (trigger - stop) <= 0 or risk <= 0:
            blocked.append("Mức vô hiệu sai chiều so với điểm vào/trigger")
        else:
            risk_pct, risk_atr = risk / entry * 100, risk / atr
            if risk_pct > policy.max_risk_pct or risk_atr > policy.max_risk_atr:
                blocked.append("Khoảng tới mức vô hiệu quá rộng")
            barrier = number(c.get("resistance_level" if side == 1 else "support_level"))
            room = side * (barrier - entry) if barrier is not None and barrier > 0 else None
            if room is None or room <= 0:
                waiting.append("Chưa có mốc cản phía trước để đánh giá khoảng trống/rủi ro")
            else:
                room_risk = room / risk
                if room_risk < policy.min_room_risk:
                    blocked.append("Khoảng trống đến cản không đủ so với rủi ro")

    ma_extension = number(c.get("dist_ma20_atr"))
    if ma_extension is None:
        waiting.append("Thiếu khoảng cách MA20 theo ATR")
    elif side * ma_extension > policy.max_ma20_atr:
        blocked.append("Giá đã chạy quá xa MA20")
    liquidity = number(c.get("avg_dollar_vol20"))
    if liquidity is None:
        waiting.append("Thiếu giá trị giao dịch trung bình")
    elif liquidity < policy.min_dollar_volume:
        blocked.append("Thanh khoản dưới ngưỡng xét ưu tiên")
    fa = c.get("fa_flags") or {}
    days = number(fa.get("days_to_earnings")) if isinstance(fa, dict) else None
    if days is None or days < 0:
        waiting.append("Chưa xác minh lịch BCTC sắp tới")
    elif days <= policy.earnings_days:
        blocked.append("BCTC quá gần thời điểm xem xét")

    evidence = c.get("evidence_json") or {}
    candle = evidence.get("candlestick", {}) if isinstance(evidence, dict) else {}
    features = candle.get("features", {})
    o, h, l, cc = [number(features.get(k)) for k in ("open", "high", "low", "close")]
    valid_candle = (all(v is not None and v > 0 for v in (o, h, l, cc))
                    and h > l and l <= min(o, cc) <= max(o, cc) <= h
                    and close is not None and abs(cc - close) <= 0.011)
    if not valid_candle:
        waiting.append("Thiếu OHLC hợp lệ để xác nhận phản ứng giá")
    elif valid_levels:
        directional_position = (cc - l) / (h - l) * 100 if side == 1 else (h - cc) / (h - l) * 100
        response = (side * (cc - o) > 0 and side * (cc - trigger) > 0
                    and directional_position >= policy.min_close_position)
        if subtype in {"pullback_ma20", "pullback_ma50", "pullback_ma20_res"}:
            touch = l <= trigger + policy.touch_tolerance_atr * atr if side == 1 else h >= trigger - policy.touch_tolerance_atr * atr
            day_return = number(c.get("perf_1d"))
            response = response and touch and day_return is not None and side * day_return > 0
        elif subtype in {"breakout", "breakdown", "reversal_reclaim", "reversal_drop"}:
            volume = number(c.get("rel_volume"))
            response = response and c.get("status") == "confirmed" and volume is not None and volume >= policy.min_break_volume
        else:
            response = False
        if not response:
            waiting.append("Chưa đủ phản ứng giá/volume xác nhận cho loại setup này")

    tier = "reject" if blocked else "wait" if waiting else "ready"
    return {
        "version": policy.version, "tier": tier, "label": TIER_LABELS[tier],
        "reasons": blocked + waiting or ["Đủ xác nhận, vị trí và khoảng trống/rủi ro theo bộ lọc"],
        "entry_reference": entry, "risk_pct": risk_pct, "risk_atr": risk_atr,
        "room_risk": room_risk, "extension_atr": extension,
    }


def rank_for_review(candidates, policy=DEFAULT_POLICY):
    result = []
    for c in candidates:
        q = evaluate_quality(c, policy)
        result.append({**c, "quality": q, "quality_tier": q["tier"],
                       "quality_version": q["version"], "quality_reasons": "; ".join(q["reasons"]),
                       "entry_reference": q["entry_reference"], "risk_pct": q["risk_pct"],
                       "risk_atr": q["risk_atr"], "room_risk": q["room_risk"]})
    # Raw RS score is only a tie-breaker; no amount of RS can bypass a gate.
    result.sort(key=lambda c: (
        {"ready": 0, "wait": 1, "reject": 2}[c["quality_tier"]],
        -(min(c["room_risk"], 5) if c["room_risk"] is not None else -1),
        c["risk_atr"] if c["risk_atr"] is not None else float("inf"),
        -(number(c.get("score")) or 0), c.get("symbol", ""),
        c.get("group_type", ""), c.get("setup_type", "")))
    for i, c in enumerate(result, 1):
        c["review_rank"] = i
    return result


def select_shortlist(ranked, limit=10, industry_limit=2):
    selected, symbols, counts = [], set(), Counter()
    if limit <= 0:
        return selected
    for c in ranked:
        if c["quality_tier"] != "ready" or c["symbol"] in symbols:
            continue
        industry = c.get("sub_industry") or c.get("sector") or "Chưa rõ ngành"
        if industry_limit is not None and counts[industry] >= industry_limit:
            continue
        selected.append(c)
        symbols.add(c["symbol"])
        counts[industry] += 1
        if len(selected) >= limit:
            break
    return selected
