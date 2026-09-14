"""
Signal Events Module.
Generates structured cross-session events for the Today Dashboard:
1. New Opportunities (Cơ hội mới)
2. Setup Changes / Transitions (Thay đổi setup: kích hoạt, mất điều kiện, vô hiệu)
3. Upcoming Events (Sự kiện sắp tới: BCTC / Earnings)
4. Market & Sector Shifts (Thay đổi độ rộng & thứ hạng ngành)

Features strict deduplication keys, session-awareness, and handles missing data gracefully.
"""
from typing import Any, Dict, List, Optional, Set

def generate_signal_events(
    current_snapshot: Dict[str, Any],
    current_candidates: List[Dict[str, Any]],
    prev_snapshot: Optional[Dict[str, Any]] = None,
    prev_candidates: Optional[List[Dict[str, Any]]] = None,
    missing_symbols: Optional[List[str]] = None,
    current_bases: Optional[List[Dict[str, Any]]] = None,
    prev_bases: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Generate event stream comparing current session against previous trading session.
    All events contain a deterministic event_key for zero-duplicate persistence.
    """
    events: List[Dict[str, Any]] = []
    as_of = current_snapshot.get("as_of", "")
    missing_set: Set[str] = set(missing_symbols or [])

    prev_cands = prev_candidates or []
    prev_snap = prev_snapshot or {}

    # Composite key for candidate: (symbol, setup_type or group_type)
    def cand_key(c: Dict[str, Any]) -> str:
        st = c.get("setup_type") or c.get("group_type") or "default"
        return f"{c['symbol']}:{st}"

    cur_map = {cand_key(c): c for c in current_candidates}
    prev_map = {cand_key(c): c for c in prev_cands}

    # --- 1. New Opportunities (Cơ hội mới) ---
    for k, c in cur_map.items():
        if k not in prev_map:
            sym = c["symbol"]
            setup_name = c.get("setup_type") or c.get("group_type")
            status = c.get("status", "setup")
            status_text = "Đã kích hoạt (Triggered)" if status == "confirmed" else "Đang hình thành (Setup)"

            events.append({
                "event_key": f"{as_of}:{sym}:{setup_name}:new_candidate",
                "session_date": as_of,
                "symbol": sym,
                "company_name": c.get("company_name", sym),
                "event_type": "new_candidate",
                "event_category": "analytic_event",
                "group_type": c.get("group_type", ""),
                "setup_type": setup_name,
                "title": f"Cơ hội mới: {sym} ({setup_name})",
                "summary": f"Mã vừa xuất hiện trong nhóm {c.get('group_type')} với trạng thái {status_text} tại giá ${c.get('close_price', 0.0):.2f}.",
                "evidence": {
                    "close_price": c.get("close_price"),
                    "trigger_price": c.get("trigger_price"),
                    "score": c.get("score"),
                    "reasons": c.get("technical_reasons", [])[:2]
                },
                "severity": "opportunity",
                "is_read": 0,
                "source_url": f"https://www.tradingview.com/chart/?symbol={sym}&interval=D",
                "source_name": "Market Radar Scanner (EOD OHLCV)",
                "observed_at": as_of,
                "published_at": as_of,
                "received_at": as_of,
                "source_status": "scanner_derived"
            })

    # --- 2. Setup Changes & Transitions (Thay đổi setup) ---
    for k, cur in cur_map.items():
        if k in prev_map:
            old = prev_map[k]
            sym = cur["symbol"]
            setup_name = cur.get("setup_type") or cur.get("group_type")

            # Setup just triggered
            if old.get("status") == "setup" and cur.get("status") == "confirmed":
                events.append({
                    "event_key": f"{as_of}:{sym}:{setup_name}:triggered",
                    "session_date": as_of,
                    "symbol": sym,
                    "company_name": cur.get("company_name", sym),
                    "event_type": "setup_triggered",
                    "event_category": "analytic_event",
                    "group_type": cur.get("group_type", ""),
                    "setup_type": setup_name,
                    "title": f"Setup kích hoạt: {sym} ({setup_name})",
                    "summary": f"Giá (${cur.get('close_price', 0.0):.2f}) đã kích hoạt điểm vào lệnh (Trigger: ${cur.get('trigger_price', 0.0):.2f}) kèm volume xác nhận.",
                    "evidence": {
                        "old_status": "setup",
                        "new_status": "confirmed",
                        "close_price": cur.get("close_price"),
                        "trigger_price": cur.get("trigger_price"),
                        "rel_volume": cur.get("rel_volume")
                    },
                    "severity": "opportunity",
                    "is_read": 0,
                    "source_url": f"https://www.tradingview.com/chart/?symbol={sym}&interval=D",
                    "source_name": "Market Radar Price Feed (EOD)",
                    "observed_at": as_of,
                    "published_at": as_of,
                    "received_at": as_of,
                    "source_status": "scanner_derived"
                })

    # Candidates removed / lost conditions (Check missing data guardrail!)
    for k, old in prev_map.items():
        if k not in cur_map:
            sym = old["symbol"]
            setup_name = old.get("setup_type") or old.get("group_type")

            # If symbol disappeared because data was missing/failed, DO NOT call it setup failed!
            if sym in missing_set:
                continue

            events.append({
                "event_key": f"{as_of}:{sym}:{setup_name}:lost_condition",
                "session_date": as_of,
                "symbol": sym,
                "company_name": old.get("company_name", sym),
                "event_type": "setup_invalidated",
                "event_category": "analytic_event",
                "group_type": old.get("group_type", ""),
                "setup_type": setup_name,
                "title": f"Mất điều kiện setup: {sym} ({setup_name})",
                "summary": f"Mã không còn duy trì đủ điều kiện kỹ thuật của nhóm {old.get('group_type')} so với phiên trước.",
                "evidence": {
                    "previous_status": old.get("status"),
                    "previous_score": old.get("score")
                },
                "severity": "info",
                "is_read": 0,
                "source_url": f"https://www.tradingview.com/chart/?symbol={sym}&interval=D",
                "source_name": "Market Radar Price Feed (EOD)",
                "observed_at": as_of,
                "published_at": as_of,
                "received_at": as_of,
                "source_status": "scanner_derived"
            })

    # --- 3. Upcoming Earnings Events (Sự kiện sắp tới) ---
    seen_earnings = set()
    for c in current_candidates:
        sym = c["symbol"]
        if sym in seen_earnings:
            continue
        fa = c.get("fa_flags", {})
        if fa and isinstance(fa, dict):
            days_to_e = fa.get("days_to_earnings")
            e_date = fa.get("next_earnings_date")
            e_status = fa.get("earnings_status", "Chưa xác minh")

            if days_to_e is not None and 0 <= days_to_e <= 14:
                seen_earnings.add(sym)
                is_urgent = days_to_e <= 5
                events.append({
                    "event_key": f"{as_of}:{sym}:earnings:{e_date}",
                    "session_date": as_of,
                    "symbol": sym,
                    "company_name": c.get("company_name", sym),
                    "event_type": "earnings_upcoming",
                    "event_category": "external_company_event",
                    "group_type": c.get("group_type", ""),
                    "setup_type": c.get("setup_type", ""),
                    "title": f"Sắp công bố BCTC: {sym} (còn {days_to_e} ngày)",
                    "summary": f"Ngày dự kiến: {e_date} ({e_status}). Rủi ro biến động gap trước/sau sự kiện.",
                    "evidence": {
                        "days_to_earnings": days_to_e,
                        "earnings_date": e_date,
                        "status": e_status,
                        "sec_filing_url": fa.get("sec_filing_url")
                    },
                    "severity": "warning" if is_urgent else "info",
                    "is_read": 0,
                    "source_url": fa.get("sec_filing_url") or f"https://www.sec.gov/edgar/browse/?CIK={sym}",
                    "source_name": "Yahoo Finance Calendar (Ước tính / Estimate)",
                    "observed_at": as_of,
                    "published_at": f"Dự kiến: {e_date}",
                    "received_at": as_of,
                    "source_status": "Chưa kiểm tra (Unverified / Ước tính)"
                })

    # --- 4. Market & Sector Shifts (Thay đổi thị trường & ngành) ---
    cur_sectors = {s["sector"]: s for s in current_snapshot.get("sector_metrics", [])}
    prev_sectors = {s["sector"]: s for s in prev_snap.get("sector_metrics", [])}

    for sec, cur_s in cur_sectors.items():
        if sec in prev_sectors:
            old_s = prev_sectors[sec]
            old_rank = old_s.get("rank", 0)
            cur_rank = cur_s.get("rank", 0)
            change = old_rank - cur_rank  # positive means improved rank

            if abs(change) >= 2:
                direction_str = f"thăng {change} bậc (#{old_rank} -> #{cur_rank})" if change > 0 else f"tụt {abs(change)} bậc (#{old_rank} -> #{cur_rank})"
                events.append({
                    "event_key": f"{as_of}:sector_shift:{sec}:{cur_rank}",
                    "session_date": as_of,
                    "symbol": cur_s.get("etf", sec),
                    "company_name": f"Ngành {sec}",
                    "event_type": "sector_rank_shift",
                    "event_category": "analytic_event",
                    "group_type": "sector",
                    "setup_type": "rotation",
                    "title": f"Xếp hạng ngành: {sec} {direction_str}",
                    "summary": f"ETF {cur_s.get('etf')} đạt hiệu suất 1M {cur_s.get('etf_1m', 0):+.2f}%. Trạng thái: {cur_s.get('status', 'Trung tính')}.",
                    "evidence": {
                        "old_rank": old_rank,
                        "new_rank": cur_rank,
                        "change": change,
                        "perf_1m": cur_s.get("etf_1m")
                    },
                    "severity": "opportunity" if change > 0 else "info",
                    "is_read": 0,
                    "source_url": "https://www.spglobal.com/spdji/en/indices/equity/sp-500/",
                    "source_name": "Market Radar Sector Rotation Engine",
                    "observed_at": as_of,
                    "published_at": as_of,
                    "received_at": as_of,
                    "source_status": "scanner_derived"
                })

    # Market Breadth Shift
    cur_m = current_snapshot.get("market_metrics", {})
    prev_m = prev_snap.get("market_metrics", {})
    if cur_m and prev_m:
        cur_pct50 = cur_m.get("pct_above_ma50", 0.0)
        prev_pct50 = prev_m.get("pct_above_ma50", 0.0)
        breadth_diff = round(cur_pct50 - prev_pct50, 1)

        if abs(breadth_diff) >= 5.0:
            events.append({
                "event_key": f"{as_of}:breadth_shift:{breadth_diff}",
                "session_date": as_of,
                "symbol": "SPY",
                "company_name": "S&P 500 Market Breadth",
                "event_type": "market_breadth_shift",
                "event_category": "analytic_event",
                "group_type": "market",
                "setup_type": "breadth",
                "title": f"Biến động độ rộng thị trường: {breadth_diff:+0.1f}% cp trên MA50",
                "summary": f"Tỷ lệ cổ phiếu S&P 500 trên MA50 thay đổi từ {prev_pct50:.1f}% sang {cur_pct50:.1f}%.",
                "evidence": {
                    "prev_pct_ma50": prev_pct50,
                    "cur_pct_ma50": cur_pct50,
                    "diff": breadth_diff
                },
                "severity": "opportunity" if breadth_diff > 0 else "warning",
                "is_read": 0,
                "source_url": "https://www.spglobal.com/spdji/en/indices/equity/sp-500/",
                "source_name": "Market Radar Participation & Breadth Engine",
                "observed_at": as_of,
                "published_at": as_of,
                "received_at": as_of,
                "source_status": "scanner_derived"
            })

    # --- 5. Base Building Events (Đang Xây Nền) ---
    if current_bases:
        base_events = generate_base_signal_events(
            current_bases=current_bases,
            prev_bases=prev_bases,
            as_of=as_of
        )
        events.extend(base_events)

    return events


def generate_base_signal_events(
    current_bases: List[Dict[str, Any]],
    prev_bases: Optional[List[Dict[str, Any]]] = None,
    as_of: str = ""
) -> List[Dict[str, Any]]:
    """
    Generate event stream for base lifecycle state transitions.
    Only fires an event when the state changes.
    Key format: {as_of}:{base_id}:{event_type} for deterministic deduplication.
    """
    events: List[Dict[str, Any]] = []
    prev_map: Dict[str, Dict[str, Any]] = {
        b["base_id"]: b for b in (prev_bases or []) if b.get("base_id")
    }

    for b in current_bases:
        base_id = b.get("base_id")
        state = b.get("state")
        data_status = b.get("data_status")
        # Do not fire transition events on unverified/stale observation records
        if not base_id or not state or state in ("none", "unknown") or data_status in ("stale_data", "insufficient_data", "invalid_data"):
            continue

        sym = b.get("symbol", "")
        co_name = b.get("company_name", sym)
        cur_as_of = b.get("as_of") or as_of
        upper = b.get("upper", 0.0)
        lower = b.get("lower", 0.0)
        close_p = b.get("close_price", 0.0)
        width = b.get("width_pct", 0.0)
        tr_c = b.get("tr_contraction")
        vol_c = b.get("vol_contraction")

        prev_b = prev_map.get(base_id)
        prev_state = prev_b.get("state") if prev_b else None

        event_type: Optional[str] = None
        title: str = ""
        summary: str = ""
        severity: str = "info"

        if prev_b is None:
            # Newly detected base: only emit event if detected on the current session
            detected_at = b.get("detected_at") or (b["base_id"].split(":")[1] if b.get("base_id") and ":" in b["base_id"] else None) or cur_as_of
            if detected_at == cur_as_of:
                if state == "forming":
                    event_type = "base_forming"
                    title = f"Nền giá mới: {sym} (Đang hình thành)"
                    summary = f"Mã {sym} hình thành nền giá 20 phiên (${lower:.2f} – ${upper:.2f}, độ rộng {width:.1f}%)."
                    severity = "info"
                elif state == "tight":
                    event_type = "base_tight"
                    tr_str = f"{tr_c:.2f}" if tr_c is not None else "N/A"
                    vol_str = f"{vol_c:.2f}" if vol_c is not None else "N/A"
                    title = f"Nền co chặt: {sym} (Biến động & Vol cạn)"
                    summary = f"Mã {sym} hình thành nền co chặt (${lower:.2f} – ${upper:.2f}, TR ratio {tr_str}, Vol ratio {vol_str})."
                    severity = "opportunity"
            elif state in ("breakout_confirmed", "breakout_unconfirmed", "broken_down", "lost_structure"):
                # Recovered base that broke out / down / lost structure after missing data
                if state == "breakout_confirmed":
                    event_type = "base_breakout_confirmed"
                    title = f"Breakout xác nhận: {sym} (${close_p:.2f})"
                    summary = f"Giá bứt phá qua biên trên ${upper:.2f} kèm khối lượng lớn xác nhận điểm phá vỡ."
                    severity = "opportunity"
                elif state == "breakout_unconfirmed":
                    event_type = "base_breakout_unconfirmed"
                    title = f"Vượt nền thiếu volume: {sym} (${close_p:.2f} > ${upper:.2f})"
                    summary = f"Giá đóng cửa vượt kháng cự biên trên ${upper:.2f} nhưng volume chưa đạt 1.2x SMA20 vol."
                    severity = "warning"
                elif state == "broken_down":
                    event_type = "base_broken_down"
                    title = f"Thủng nền giá: {sym} (${close_p:.2f} < ${lower:.2f})"
                    summary = f"Giá đóng cửa thủng dưới biên dưới ${lower:.2f}; đợt nền kết thúc."
                    severity = "warning"
                elif state == "lost_structure":
                    event_type = "base_lost_structure"
                    title = f"Mất cấu trúc nền: {sym}"
                    summary = f"Cổ phiếu suy yếu 2 phiên liên tiếp và mất cấu trúc đi ngang; đợt nền kết thúc."
                    severity = "info"
        else:
            # Existing base with potential state transition
            if state != prev_state:
                if state == "tight":
                    event_type = "base_tight"
                    title = f"Chuyển sang nền co chặt: {sym}"
                    summary = f"Nền giá {sym} đã co hẹp biến động và volume; chuẩn bị cho khả năng bứt phá."
                    severity = "opportunity"
                elif state == "breakout_unconfirmed":
                    event_type = "base_breakout_unconfirmed"
                    title = f"Vượt nền thiếu volume: {sym} (${close_p:.2f} > ${upper:.2f})"
                    summary = f"Giá đóng cửa vượt kháng cự biên trên ${upper:.2f} nhưng volume chưa đạt 1.2x SMA20 vol."
                    severity = "warning"
                elif state == "breakout_confirmed":
                    event_type = "base_breakout_confirmed"
                    title = f"Breakout xác nhận: {sym} (${close_p:.2f})"
                    summary = f"Giá bứt phá qua biên trên ${upper:.2f} kèm khối lượng lớn xác nhận điểm phá vỡ."
                    severity = "opportunity"
                elif state == "broken_down":
                    event_type = "base_broken_down"
                    title = f"Thủng nền giá: {sym} (${close_p:.2f} < ${lower:.2f})"
                    summary = f"Giá đóng cửa thủng dưới biên dưới ${lower:.2f}; đợt nền kết thúc."
                    severity = "warning"
                elif state == "lost_structure":
                    event_type = "base_lost_structure"
                    title = f"Mất cấu trúc nền: {sym}"
                    summary = f"Cổ phiếu suy yếu 2 phiên liên tiếp và mất cấu trúc đi ngang; đợt nền kết thúc."
                    severity = "info"

        if event_type:
            events.append({
                "event_key": f"{cur_as_of}:{base_id}:{event_type}",
                "session_date": cur_as_of,
                "symbol": sym,
                "company_name": co_name,
                "event_type": event_type,
                "event_category": "analytic_event",
                "group_type": "base",
                "setup_type": "base_building",
                "title": title,
                "summary": summary,
                "evidence": {
                    "base_id": base_id,
                    "state": state,
                    "prev_state": prev_state,
                    "upper": upper,
                    "lower": lower,
                    "close_price": close_p,
                    "width_pct": width,
                    "tr_contraction": tr_c,
                    "vol_contraction": vol_c,
                    "volume_balance": b.get("volume_balance_label", "Cân bằng"),
                    "trend_context": b.get("trend_context", "Trung tính"),
                },
                "severity": severity,
                "is_read": 0,
                "source_url": f"https://www.tradingview.com/chart/?symbol={sym}&interval=D",
                "source_name": "Market Radar Base Detector (EOD)",
                "observed_at": cur_as_of,
                "published_at": cur_as_of,
                "received_at": cur_as_of,
                "source_status": "scanner_derived"
            })

    return events

