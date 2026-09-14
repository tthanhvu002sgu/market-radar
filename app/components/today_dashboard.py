"""
Today Dashboard Component (Trang Hôm Nay).
Presents 4 core event groups for the current trading session:
1. Cơ hội mới: Mã vừa xuất hiện, phân theo setup
2. Thay đổi setup: Vừa kích hoạt, mất điều kiện hoặc hết hiệu lực
3. Sự kiện sắp tới: Lịch công bố BCTC (Earnings) kèm mức độ xác minh
4. Thay đổi thị trường/ngành: Biến động thứ hạng và độ rộng thị trường

Each event item provides:
Điều gì thay đổi -> Bằng chứng số liệu -> Mở chi tiết setup -> TradingView link.
Supports filtering by setup, sector, event category, and mark-as-read.
"""
from typing import Any, Dict, List, Optional
import streamlit as st

from storage.repository import MarketRadarRepository
from app.components.setup_detail import render_setup_detail_modal, show_setup_detail_dialog

def render_event_item(
    ev: Dict[str, Any],
    candidate_map: Dict[str, Dict[str, Any]],
    as_of: str,
    repo: MarketRadarRepository
):
    """Render a single event row with what changed, evidence, details, and TradingView."""
    ev_id = ev["id"]
    sym = ev["symbol"]
    ev_type = ev.get("event_type", "")
    title = ev["title"]
    summary = ev["summary"]
    evidence = ev.get("evidence", {})
    severity = ev.get("severity", "info")
    is_read = bool(ev.get("is_read", 0))
    tv_url = f"https://www.tradingview.com/chart/?symbol={sym}&interval=D" if sym and sym != "SPY" else "https://www.tradingview.com/chart/?symbol=SPY&interval=D"

    # Severity badge
    if severity == "opportunity":
        sev_badge = '<span style="background: #EDF3EC; color: #346538; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 9999px; letter-spacing: 0.04em;">CƠ HỘI</span>'
    elif severity == "warning":
        sev_badge = '<span style="background: #FEF3D6; color: #8F6B00; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 9999px; letter-spacing: 0.04em;">LƯU Ý</span>'
    elif severity == "critical":
        sev_badge = '<span style="background: #FDEBEC; color: #9F2F2D; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 9999px; letter-spacing: 0.04em;">RỦI RO</span>'
    else:
        sev_badge = '<span style="background: #F7F6F3; color: #787774; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 9999px; letter-spacing: 0.04em;">THÔNG TIN</span>'

    read_badge = '<span style="color: #787774; font-size: 12px;">Đã đọc</span>' if is_read else '<span style="color: #2962FF; font-weight: 600; font-size: 12px;">MỚI</span>'

    # Format evidence string
    ev_parts = []
    if isinstance(evidence, dict):
        for k, v in evidence.items():
            if k == "reasons" and isinstance(v, list):
                for r in v:
                    ev_parts.append(f"&bull; {r}")
            elif v is not None:
                ev_parts.append(f"<b>{k}:</b> {v}")
    elif evidence:
        ev_parts.append(str(evidence))
    evidence_str = " &middot; ".join(ev_parts[:3]) if ev_parts else "Đạt điều kiện phân tích chuẩn."

    card_bg = "#FFFFFF" if not is_read else "#FCFCFB"
    border_color = "#EAEAEA" if is_read else "#D4D4D4"

    # Source and verification metadata [R-01]
    is_external_event = (ev_type == "earnings_upcoming" or ev.get("event_category") == "external_company_event")
    
    if is_external_event:
        source_name = ev.get("source_name") or "Yahoo Finance Calendar (Ước tính / Estimate)"
        source_url = ev.get("source_url") or (f"https://www.sec.gov/edgar/browse/?CIK={sym}" if sym and sym != "SPY" else "https://www.sec.gov/edgar/searchedgar/companysearch")
        time_label = "Dự kiến"
        time_val = ev.get("published_at") or ev.get("session_date", "")
        status_badge = '<span style="background: #FEF3D6; color: #8F6B00; font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px;">⚠️ Lịch ước tính (Chưa xác minh SEC/IR)</span>'
        unverified_warning_html = '<div style="font-size: 12.5px; color: #9F2F2D; background: #FFF5F5; border: 1px solid #FED7D7; border-radius: 4px; padding: 6px 10px; margin-top: 6px;"><b>Cảnh báo nguồn tin:</b> Lịch sự kiện/BCTC chưa xác minh được accession/filing chính thức; đối chiếu trang IR công ty trước khi giải ngân.</div>'
    else:
        # Internal analytic event from price/volume scanner [R-01]
        source_name = ev.get("source_name") or "Market Radar Scanner (EOD OHLCV)"
        source_url = ev.get("source_url") or tv_url
        time_label = "Quan sát lúc"
        time_val = ev.get("observed_at") or ev.get("session_date") or as_of
        status_badge = '<span style="background: #F0F4F8; color: #1E3A8A; font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px;">Tín hiệu Scanner EOD</span>'
        unverified_warning_html = ""

    received_at = ev.get("received_at") or as_of

    st.markdown(f"""
    <div style="background-color: {card_bg}; border: 1px solid {border_color}; border-radius: 6px; padding: 16px 20px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                {sev_badge}
                <span style="font-weight: 600; font-size: 16px; color: #111111;">{title}</span>
            </div>
            <div>{read_badge}</div>
        </div>
        <div style="font-size: 14.5px; color: #2F3437; margin-bottom: 8px; line-height: 1.6;">
            {summary}
        </div>
        <div style="font-size: 13.5px; color: #787774; background: #F7F6F3; border-radius: 4px; padding: 8px 12px; margin-bottom: 8px;">
            <b>Bằng chứng số liệu:</b> {evidence_str}
        </div>
        <div style="font-size: 12.5px; color: #787774; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;">
            <span><b>Nguồn:</b> {source_name}</span>
            <span>&bull;</span>
            <span><b>{time_label}:</b> {time_val}</span>
            <span>&bull;</span>
            <span><b>Ghi nhận:</b> {received_at}</span>
            <span>&bull;</span>
            {status_badge}
        </div>
        {unverified_warning_html}
    </div>
    """, unsafe_allow_html=True)

    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([3, 3, 2, 4])
    with btn_col1:
        st.link_button(f"TradingView ({sym})", tv_url, use_container_width=True)
    with btn_col2:
        if is_external_event:
            st.link_button("Tra cứu SEC EDGAR ↗", source_url, use_container_width=True)
        else:
            st.link_button("Nguồn Scanner EOD ↗", source_url, use_container_width=True)
    with btn_col3:
        if not is_read:
            if st.button("Đã đọc ✓", key=f"read_{ev_id}", use_container_width=True):
                repo.mark_event_read(ev_id)
                st.rerun()
        else:
            st.button("Đã đọc", key=f"read_done_{ev_id}", disabled=True, use_container_width=True)
    with btn_col4:
        cand_data = candidate_map.get(sym)
        if cand_data:
            if st.button(f"Chi tiết setup {sym} 🔍", key=f"btn_detail_ev_{ev_id}_{sym}", use_container_width=True):
                show_setup_detail_dialog(cand_data, as_of=as_of, repo=repo, key_suffix=f"ev_{ev_id}")

def _render_paginated_events(
    events_list: List[Dict[str, Any]],
    candidate_map: Dict[str, Dict[str, Any]],
    as_of: str,
    repo: MarketRadarRepository,
    page_key: str,
    label: str,
    page_size: int = 20
):
    """Helper to render events with clean pagination."""
    if not events_list:
        return
    total_pages = (len(events_list) + page_size - 1) // page_size
    page_options = [
        f"Trang {p}/{total_pages} ({label} {(p-1)*page_size + 1} - {min(p*page_size, len(events_list))})"
        for p in range(1, total_pages + 1)
    ]
    if total_pages > 1:
        c_p1, c_p2 = st.columns([2, 3])
        with c_p1:
            chosen_label = st.selectbox(
                f"Trang ({len(events_list)} mục):",
                page_options,
                key=page_key
            )
            cur_page = page_options.index(chosen_label) + 1
        start_idx = (cur_page - 1) * page_size
        page_items = events_list[start_idx : start_idx + page_size]
    else:
        page_items = events_list

    for ev in page_items:
        render_event_item(ev, candidate_map, as_of, repo)

def render_today_dashboard(
    as_of: str,
    candidates: List[Dict[str, Any]],
    repo: MarketRadarRepository
):
    """Render the Today Dashboard section."""
    st.markdown('<div class="editorial-hero" style="font-size: 22px; margin-bottom: 4px;">Hôm Nay: Cơ Hội & Sự Kiện Đáng Chú Ý</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="editorial-sub">Tổng hợp các tín hiệu mới xuất hiện, thay đổi trạng thái setup, sự kiện BCTC và biến động thị trường của phiên <code>{as_of}</code>.</div>', unsafe_allow_html=True)

    # Candidate map for quick detail lookup
    candidate_map = {c["symbol"]: c for c in candidates}

    # Fetch events for current session
    events = repo.get_signal_events(session_date=as_of, limit=300)
    # If no events for this specific session date, fetch latest available events
    if not events:
        events = repo.get_signal_events(limit=100)

    unread_count = sum(1 for e in events if not e.get("is_read"))

    # Top control bar
    top_c1, top_c2, top_c3 = st.columns([3, 2, 2])
    with top_c1:
        st.markdown(f"<b>Tổng cộng:</b> {len(events)} sự kiện &middot; <b>Chưa đọc:</b> <span style='color: #2962FF; font-weight: 600;'>{unread_count}</span>", unsafe_allow_html=True)
    with top_c2:
        if unread_count > 0:
            if st.button("Đánh dấu tất cả đã đọc ✓", use_container_width=True):
                event_sessions = {e["session_date"] for e in events if e.get("session_date")}
                if as_of and as_of in event_sessions:
                    repo.mark_all_events_read(as_of)
                elif event_sessions:
                    for s_date in event_sessions:
                        repo.mark_all_events_read(s_date)
                else:
                    repo.mark_all_events_read()
                st.rerun()
    with top_c3:
        filter_status = st.selectbox("Lọc trạng thái đọc:", ["Tất cả", "Chỉ sự kiện Mới (Chưa đọc)", "Đã đọc"], label_visibility="collapsed")

    if not events:
        st.info(f"Chưa có sự kiện nào được ghi nhận cho phiên {as_of}. Cập nhật snapshot tiếp theo để bắt đầu theo dõi biến động giữa các phiên.")
        return

    # Filter events
    if filter_status == "Chỉ sự kiện Mới (Chưa đọc)":
        display_events = [e for e in events if not e.get("is_read")]
    elif filter_status == "Đã đọc":
        display_events = [e for e in events if e.get("is_read")]
    else:
        display_events = events

    # Partition by the 4 required functional groups
    group_new = [e for e in display_events if e.get("event_type") == "new_candidate"]
    group_trans = [e for e in display_events if e.get("event_type") in ("setup_triggered", "setup_invalidated")]
    group_earnings = [e for e in display_events if e.get("event_type") == "earnings_upcoming"]
    group_market = [e for e in display_events if e.get("event_type") in ("sector_rank_shift", "market_breadth_shift")]

    sub_keys = ["new", "trans", "earnings", "market"]
    today_sub_labels = {
        "new": f"01 Cơ Hội Mới ({len(group_new)})",
        "trans": f"02 Thay Đổi Setup ({len(group_trans)})",
        "earnings": f"03 Sự Kiện Sắp Tới ({len(group_earnings)})",
        "market": f"04 Biến Động Thị Trường & Ngành ({len(group_market)})"
    }

    selected_today_sub = st.segmented_control(
        "Phân loại sự kiện hôm nay",
        options=sub_keys,
        format_func=lambda k: today_sub_labels[k],
        default="new",
        label_visibility="collapsed",
        key="today_subgroup_nav"
    ) if hasattr(st, "segmented_control") else st.radio(
        "Phân loại sự kiện hôm nay",
        options=sub_keys,
        format_func=lambda k: today_sub_labels[k],
        horizontal=True,
        label_visibility="collapsed",
        key="today_subgroup_nav"
    )
    if not selected_today_sub:
        selected_today_sub = "new"

    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)

    if selected_today_sub == "new":
        st.markdown("<div style='font-size: 14.5px; color: #787774; margin-bottom: 12px;'>Các mã cổ phiếu mới xuất hiện trong danh sách sàng lọc của phiên hôm nay.</div>", unsafe_allow_html=True)
        if group_new:
            _render_paginated_events(group_new, candidate_map, as_of, repo, "page_today_new", "Mã")
        else:
            st.info("Không có mã mới nào xuất hiện trong phiên này.")

    elif selected_today_sub == "trans":
        st.markdown("<div style='font-size: 14.5px; color: #787774; margin-bottom: 12px;'>Các setup vừa kích hoạt điểm vào lệnh (Triggered) hoặc mất điều kiện kỹ thuật.</div>", unsafe_allow_html=True)
        if group_trans:
            _render_paginated_events(group_trans, candidate_map, as_of, repo, "page_today_trans", "Mã")
        else:
            st.info("Không có thay đổi trạng thái setup nào so với phiên trước.")

    elif selected_today_sub == "earnings":
        st.markdown("<div style='font-size: 14.5px; color: #787774; margin-bottom: 8px;'>Lịch công bố báo cáo tài chính (BCTC) trong vòng 14 ngày tới của các ứng viên.</div>", unsafe_allow_html=True)
        st.info("💡 Bạn có thể xem toàn bộ lịch báo cáo tài chính S&P 500, phân loại phiên BMO/AMC và lịch tuần tại tab **'03 Lịch Báo Cáo Tài Chính (Earnings)'** ở thanh điều hướng phía trên.")
        if group_earnings:
            _render_paginated_events(group_earnings, candidate_map, as_of, repo, "page_today_earnings", "Mã")
        else:
            st.info("Không có ứng viên nào sắp công bố BCTC trong 14 ngày tới.")

    elif selected_today_sub == "market":
        st.markdown("<div style='font-size: 14.5px; color: #787774; margin-bottom: 12px;'>Biến động đáng chú ý về độ rộng thị trường (Breadth) và thứ hạng các ngành dẫn dắt (Sectors).</div>", unsafe_allow_html=True)
        if group_market:
            _render_paginated_events(group_market, candidate_map, as_of, repo, "page_today_market", "Mục")
        else:
            st.info("Không có biến động độ rộng hoặc thứ hạng ngành đáng kể (&ge;2 bậc).")

