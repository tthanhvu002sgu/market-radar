"""Versioned review gates. Scores are priorities, never win probabilities.

Uses only supplied snapshot evidence; does not fetch prices or mutate candidates.
"""
from collections import Counter
from dataclasses import dataclass
from math import isfinite
from typing import Any, Dict, List, Optional


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
        result.append({
            **c,
            "quality": q,
            "quality_tier": q["tier"],
            "quality_version": q["version"],
            "quality_reasons": "; ".join(q["reasons"]),
            "entry_reference": q["entry_reference"],
            "risk_pct": q["risk_pct"],
            "risk_atr": q["risk_atr"],
            "room_risk": q["room_risk"],
            "market_context_alignment": c.get("market_context_alignment", "chưa đủ dữ liệu"),
            "market_context_summary": c.get("market_context_summary", "")
        })
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


def calculate_trade_plan(
    entry_price: float,
    invalidation_price: float,
    account_capital: float,
    risk_budget_pct: float = 1.0,
    risk_budget_usd: Optional[float] = None,
    current_exposure_usd: float = 0.0,
    max_capital_pct: float = 20.0,
    side: int = 1,
    shares: Optional[int] = None
) -> Dict[str, Any]:
    """
    Trade risk & position sizing plan [D-3].
    Calculates planned share count based on user-chosen capital and risk budget,
    or validates custom planned shares entered by the user.
    Explicitly distinguishes setup price risk from account portfolio risk.
    Disclaimer: Does not prescribe or assign suitable risk levels for user accounts.
    """
    capital = number(account_capital) or 0.0
    entry = number(entry_price) or 0.0
    inv = number(invalidation_price) or 0.0
    curr_exposure = number(current_exposure_usd) or 0.0
    max_cap_pct = number(max_capital_pct) if max_capital_pct is not None else 20.0

    if capital <= 0 or entry <= 0 or inv <= 0:
        return {
            "is_valid": False,
            "error": "Thiếu hoặc sai lệch vốn, giá vào hoặc mức vô hiệu.",
            "planned_shares": 0,
            "planned_position_val": 0.0,
            "capital_allocation_pct": 0.0,
            "per_share_risk": 0.0,
            "setup_risk_pct": 0.0,
            "dollar_risk": 0.0,
            "account_risk_pct": 0.0,
            "new_total_exposure": curr_exposure,
            "total_exposure_pct": 0.0,
            "is_over_capital_limit": False,
            "warnings": ["Thông số vốn hoặc giá không hợp lệ."],
            "disclaimer": "Hệ thống Market Radar không tự gán mức rủi ro phù hợp cho tài khoản. Mọi thông số vốn và ngân sách rủi ro do người dùng tự chủ động xác định."
        }

    per_share_risk = side * (entry - inv)
    setup_risk_pct = round(per_share_risk / entry * 100.0, 2)

    if per_share_risk <= 0:
        return {
            "is_valid": False,
            "error": "Mức vô hiệu nằm sai chiều so với giá vào.",
            "planned_shares": 0,
            "planned_position_val": 0.0,
            "capital_allocation_pct": 0.0,
            "per_share_risk": per_share_risk,
            "setup_risk_pct": setup_risk_pct,
            "dollar_risk": 0.0,
            "account_risk_pct": 0.0,
            "new_total_exposure": curr_exposure,
            "total_exposure_pct": round(curr_exposure / capital * 100.0, 2),
            "is_over_capital_limit": False,
            "warnings": ["Mức dừng lỗ vô hiệu sai chiều."],
            "disclaimer": "Hệ thống Market Radar không tự gán mức rủi ro phù hợp cho tài khoản. Mọi thông số vốn và ngân sách rủi ro do người dùng tự chủ động xác định."
        }

    if risk_budget_usd is not None and risk_budget_usd > 0:
        budget_usd = float(risk_budget_usd)
        budget_pct = round(budget_usd / capital * 100.0, 2)
    else:
        budget_pct = float(risk_budget_pct) if (risk_budget_pct and risk_budget_pct > 0) else 1.0
        budget_usd = round(capital * (budget_pct / 100.0), 2)

    if shares is not None and shares > 0:
        planned_shares = int(shares)
    else:
        planned_shares = int(budget_usd // per_share_risk)

    planned_position_val = round(planned_shares * entry, 2)
    capital_alloc_pct = round(planned_position_val / capital * 100.0, 2)
    actual_dollar_risk = round(planned_shares * per_share_risk, 2)
    actual_account_risk_pct = round(actual_dollar_risk / capital * 100.0, 2)
    new_total_exp = round(curr_exposure + planned_position_val, 2)
    total_exp_pct = round(new_total_exp / capital * 100.0, 2)

    warnings = []
    is_over_limit = False
    if shares is not None and shares > 0 and actual_dollar_risk > budget_usd:
        warnings.append(
            f"Rủi ro thực tế theo số lượng cổ phiếu đã nhập (${actual_dollar_risk:,.2f} hay {actual_account_risk_pct}% vốn) vượt ngân sách rủi ro đã định (${budget_usd:,.2f} hay {budget_pct}% vốn)."
        )

    if max_cap_pct is not None and capital_alloc_pct > max_cap_pct:
        is_over_limit = True
        warnings.append(f"Vị thế dự kiến chiếm {capital_alloc_pct}% vốn, vượt trần phân bổ {max_cap_pct}%.")

    if new_total_exp > capital:
        warnings.append(f"Tổng exposure sau khi giải ngân (${new_total_exp:,.2f}) vượt quá 100% vốn tài khoản.")

    if setup_risk_pct > 8.0:
        warnings.append(f"Khoảng dừng lỗ kỹ thuật rộng ({setup_risk_pct}%), cân nhắc giảm tỷ trọng hoặc đợi pullback hẹp hơn.")

    return {
        "is_valid": True,
        "error": None,
        "account_capital": capital,
        "entry_price": entry,
        "invalidation_price": inv,
        "per_share_risk": round(per_share_risk, 2),
        "setup_risk_pct": setup_risk_pct,
        "risk_budget_usd": budget_usd,
        "risk_budget_pct": budget_pct,
        "planned_shares": planned_shares,
        "planned_position_val": planned_position_val,
        "capital_allocation_pct": capital_alloc_pct,
        "dollar_risk": actual_dollar_risk,
        "account_risk_pct": actual_account_risk_pct,
        "current_exposure_usd": curr_exposure,
        "new_total_exposure": new_total_exp,
        "total_exposure_pct": total_exp_pct,
        "max_capital_pct": max_cap_pct,
        "is_over_capital_limit": is_over_limit,
        "warnings": warnings,
        "disclaimer": "Hệ thống Market Radar không tự gán mức rủi ro phù hợp cho tài khoản. Mọi thông số vốn và ngân sách rủi ro do người dùng tự chủ động xác định."
    }


def summarize_playbook_quality(candidates: List[Dict[str, Any]], policy: QualityPolicy = DEFAULT_POLICY) -> Dict[str, Any]:
    """
    Audit and summarize quality pass/wait/reject rates and bottleneck reasons per playbook [D-5].
    Groups by tactical playbook group_type and setup_type.
    Fact-grounded analysis: Reports barrier presence and price location without fabricating targets.
    """
    by_playbook = {}
    by_group = {}
    overall = {"total": 0, "ready": 0, "wait": 0, "reject": 0}

    for c in candidates:
        g = c.get("group_type", "unknown")
        s = c.get("setup_type", "unspecified")
        playbook_key = f"{g}:{s}"

        if "quality_tier" in c and c.get("quality_tier") in ("ready", "wait", "reject"):
            tier = c["quality_tier"]
            reasons_raw = c.get("quality_reasons", "")
            reasons = [r.strip() for r in reasons_raw.split(";") if r.strip()] if isinstance(reasons_raw, str) else (c.get("quality_reasons") or [])
        else:
            q = evaluate_quality(c, policy)
            tier = q["tier"]
            reasons = q["reasons"]

        for key, store in [(playbook_key, by_playbook), (g, by_group)]:
            if key not in store:
                store[key] = {
                    "total": 0,
                    "ready": 0,
                    "wait": 0,
                    "reject": 0,
                    "wait_reasons": Counter(),
                    "reject_reasons": Counter(),
                    "barrier_missing_count": 0,
                    "barrier_present_count": 0
                }
            store[key]["total"] += 1
            store[key][tier] += 1
            if tier == "wait":
                for r in reasons:
                    store[key]["wait_reasons"][r] += 1
            elif tier == "reject":
                for r in reasons:
                    store[key]["reject_reasons"][r] += 1

            side = -1 if g.startswith("short") else 1
            barrier = number(c.get("resistance_level" if side == 1 else "support_level"))
            if barrier is None or barrier <= 0:
                store[key]["barrier_missing_count"] += 1
            else:
                store[key]["barrier_present_count"] += 1

        overall["total"] += 1
        overall[tier] += 1

    def _calc_pcts(d):
        tot = d["total"]
        return {
            **d,
            "ready_pct": round(d["ready"] / tot * 100.0, 1) if tot > 0 else 0.0,
            "wait_pct": round(d["wait"] / tot * 100.0, 1) if tot > 0 else 0.0,
            "reject_pct": round(d["reject"] / tot * 100.0, 1) if tot > 0 else 0.0,
            "top_wait_reasons": d["wait_reasons"].most_common(3),
            "top_reject_reasons": d["reject_reasons"].most_common(3),
        }

    formatted_by_playbook = {k: _calc_pcts(v) for k, v in by_playbook.items()}
    formatted_by_group = {k: _calc_pcts(v) for k, v in by_group.items()}

    return {
        "policy_version": policy.version,
        "overall": {
            **overall,
            "ready_pct": round(overall["ready"] / overall["total"] * 100.0, 1) if overall["total"] > 0 else 0.0,
            "wait_pct": round(overall["wait"] / overall["total"] * 100.0, 1) if overall["total"] > 0 else 0.0,
            "reject_pct": round(overall["reject"] / overall["total"] * 100.0, 1) if overall["total"] > 0 else 0.0,
        },
        "by_playbook": formatted_by_playbook,
        "by_group": formatted_by_group,
        "note": "Xác minh mốc cản và vị trí giá trước khi thay ngưỡng. Không dựng target tùy ý để làm đẹp room/risk, không nới ngưỡng để ép có mã."
    }

