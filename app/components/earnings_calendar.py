"""
Earnings Calendar Component (Phân hệ Lịch Báo Cáo Tài Chính).
Enables traders to track upcoming earnings announcements:
- Date horizon: This Week, Next Week, Next 14 Days, This Month, or Custom Date Range
- Scope toggle: All Earnings, S&P 500 Only, Radar Candidates Only
- Timing filter: BMO (Before Market Open ☀️), AMC (After Market Close 🌙), TNS
- Dual views: Weekly Schedule (Calendar Grid) & Interactive Full Data Table
- Direct 1-click links to TradingView & SEC EDGAR
"""
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from providers.yfinance_provider import YFinanceProvider
from storage.repository import MarketRadarRepository

def render_html_safe(html_str: str):
    """Render HTML safely without markdown code block indentation issues."""
    if hasattr(st, "html"):
        st.html(html_str)
    else:
        import textwrap
        st.markdown(textwrap.dedent(html_str).strip(), unsafe_allow_html=True)

@st.cache_data(ttl=3600, show_spinner=False)
def load_earnings_data(start_str: str, end_str: str) -> List[Dict[str, Any]]:
    """Cached loader for earnings announcements."""
    provider = YFinanceProvider()
    return provider.fetch_earnings_calendar(start_date=start_str, end_date=end_str, limit=200)

def render_earnings_calendar_section(
    as_of: str,
    candidates: List[Dict[str, Any]],
    repo: MarketRadarRepository
):
    """Render the full-featured Earnings Calendar station."""
    st.markdown('<div class="editorial-hero" style="font-size: 22px; margin-bottom: 4px;">Lịch Báo Cáo Tài Chính (Earnings Calendar)</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="editorial-sub" style="margin-bottom: 16px;">'
        f'Theo dõi sự kiện công bố doanh thu & lợi nhuận định kỳ. Nhận diện rủi ro biến động giá lớn trước giờ mở cửa (BMO) và sau giờ đóng cửa (AMC) cho các cổ phiếu S&P 500 và ứng viên Radar.'
        f'</div>',
        unsafe_allow_html=True
    )

    # Reference date
    ref_date = date.today()
    if as_of:
        try:
            ref_date = datetime.strptime(as_of, "%Y-%m-%d").date()
        except Exception:
            pass

    # Candidate symbol lookup
    candidate_map = {c["symbol"]: c for c in candidates} if candidates else {}

    # Universe constituents lookup for sector & company name
    constituents_df = repo.get_constituents()
    sp500_symbols = set(constituents_df["symbol"].tolist()) if not constituents_df.empty else set()
    sp500_meta = {}
    if not constituents_df.empty:
        for _, row in constituents_df.iterrows():
            sp500_meta[row["symbol"]] = {
                "company_name": row.get("security", ""),
                "sector": row.get("sector", ""),
                "sub_industry": row.get("sub_industry", "")
            }

    # Top Control Bar (Bento Filter Card)
    st.markdown("""
    <style>
    .earnings-badge-bmo {
        background: #FEF3D6;
        color: #8F6B00;
        font-family: 'Geist Mono', monospace;
        font-size: 12px;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 4px;
        letter-spacing: 0.03em;
    }
    .earnings-badge-amc {
        background: #EDE9FE;
        color: #5B21B6;
        font-family: 'Geist Mono', monospace;
        font-size: 12px;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 4px;
        letter-spacing: 0.03em;
    }
    .earnings-badge-tns {
        background: #F1F5F9;
        color: #64748B;
        font-family: 'Geist Mono', monospace;
        font-size: 12px;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 4px;
    }
    .earnings-radar-pill {
        background: #DCFCE7;
        color: #166534;
        font-family: 'Geist Mono', monospace;
        font-size: 12px;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns([3, 3, 3])

    with fc1:
        time_options = ["Tuần này (This Week)", "Tuần tới (Next Week)", "14 ngày tới", "30 ngày tới", "Tùy chọn ngày"]
        chosen_time = st.selectbox("Khoảng thời gian:", time_options, index=0)

    # Calculate date range
    weekday = ref_date.weekday()  # Mon=0, Sun=6
    monday_this_week = ref_date - timedelta(days=weekday)
    friday_this_week = monday_this_week + timedelta(days=4)
    monday_next_week = monday_this_week + timedelta(days=7)
    friday_next_week = monday_next_week + timedelta(days=4)

    if chosen_time == "Tuần này (This Week)":
        start_d = monday_this_week
        end_d = friday_this_week
    elif chosen_time == "Tuần tới (Next Week)":
        start_d = monday_next_week
        end_d = friday_next_week
    elif chosen_time == "14 ngày tới":
        start_d = ref_date
        end_d = ref_date + timedelta(days=14)
    elif chosen_time == "30 ngày tới":
        start_d = ref_date
        end_d = ref_date + timedelta(days=30)
    else:
        custom_cols = st.columns(2)
        with custom_cols[0]:
            start_d = st.date_input("Từ ngày:", ref_date)
        with custom_cols[1]:
            end_d = st.date_input("Đến ngày:", ref_date + timedelta(days=14))

    start_str = start_d.strftime("%Y-%m-%d")
    end_str = end_d.strftime("%Y-%m-%d")

    with fc2:
        scope_options = ["Chỉ cổ phiếu S&P 500", "⭐ Chỉ Ứng Viên Radar", "Tất cả mã có lịch BCTC"]
        chosen_scope = st.selectbox("Phạm vi lọc:", scope_options, index=0)

    with fc3:
        timing_options = ["Tất cả phiên (BMO + AMC + TNS)", "Chỉ trước giờ mở cửa (BMO ☀️)", "Chỉ sau giờ đóng cửa (AMC 🌙)"]
        chosen_timing = st.selectbox("Thời điểm công bố:", timing_options, index=0)

    # Sub-filters: Sector & Search
    sub_c1, sub_c2 = st.columns([2, 2])
    with sub_c1:
        search_kw = st.text_input("Tìm kiếm mã hoặc tên công ty:", placeholder="VD: AAPL, NVDA, Microsoft...").strip().upper()
    with sub_c2:
        sectors_list = ["Tất cả các ngành"] + sorted(list(set(m["sector"] for m in sp500_meta.values() if m.get("sector"))))
        selected_sector = st.selectbox("Lọc theo ngành GICS:", sectors_list)

    # Load data from provider
    with st.spinner(f"Đang tải lịch BCTC từ {start_str} đến {end_str}..."):
        events_raw = load_earnings_data(start_str, end_str)

    # Also augment with DB stored fundamentals if not present
    stored_fundamentals = repo.get_fundamentals()
    if not stored_fundamentals.empty and "next_earnings_date" in stored_fundamentals.columns:
        existing_syms = {e["symbol"] for e in events_raw}
        for _, f_row in stored_fundamentals.iterrows():
            f_sym = str(f_row["symbol"]).strip().upper()
            f_date = str(f_row.get("next_earnings_date") or "").strip()
            if f_date and f_date != "Chưa xác minh" and f_date >= start_str and f_date <= end_str:
                if f_sym not in existing_syms:
                    meta = sp500_meta.get(f_sym, {})
                    events_raw.append({
                        "symbol": f_sym,
                        "company_name": meta.get("company_name", f_sym),
                        "market_cap": None,
                        "event_name": "Quarterly Earnings Announcement",
                        "earnings_date": f_date,
                        "timing": "TNS",
                        "eps_estimate": None,
                        "reported_eps": None,
                        "surprise_pct": None
                    })
                    existing_syms.add(f_sym)

    # Enrich events with S&P 500 & Radar candidate info
    enriched_events = []
    for ev in events_raw:
        sym = ev["symbol"]
        is_sp = (sym in sp500_symbols)
        cand = candidate_map.get(sym)
        is_cand = (cand is not None)

        meta = sp500_meta.get(sym, {})
        sector = meta.get("sector", "N/A")
        sub_ind = meta.get("sub_industry", "N/A")
        company = ev.get("company_name") or meta.get("company_name", sym)

        # Filters
        if chosen_scope == "Chỉ cổ phiếu S&P 500" and not is_sp:
            continue
        if chosen_scope == "⭐ Chỉ Ứng Viên Radar" and not is_cand:
            continue

        timing = ev.get("timing", "TNS")
        if chosen_timing.startswith("Chỉ trước giờ") and timing != "BMO":
            continue
        if chosen_timing.startswith("Chỉ sau giờ") and timing != "AMC":
            continue

        if selected_sector != "Tất cả các ngành" and sector != selected_sector:
            continue

        if search_kw:
            if search_kw not in sym and search_kw not in company.upper():
                continue

        enriched_events.append({
            **ev,
            "company_name": company,
            "sector": sector,
            "sub_industry": sub_ind,
            "is_sp500": is_sp,
            "is_candidate": is_cand,
            "candidate_info": cand
        })

    # Sort events chronologically, then by market cap or candidate priority
    enriched_events.sort(key=lambda x: (
        x.get("earnings_date", "9999"),
        0 if x.get("is_candidate") else (1 if x.get("is_sp500") else 2),
        -(x.get("market_cap") or 0.0)
    ))

    # Metric counts banner
    total_found = len(enriched_events)
    cand_count = sum(1 for e in enriched_events if e["is_candidate"])
    sp_count = sum(1 for e in enriched_events if e["is_sp500"])

    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    stat_col1.metric("Tổng sự kiện BCTC", f"{total_found} sự kiện")
    stat_col2.metric("Thuộc S&P 500", f"{sp_count} mã")
    stat_col3.metric("Ứng Viên Radar Sắp Ra Tin", f"{cand_count} mã", delta="Cảnh báo biến động" if cand_count > 0 else "An toàn", delta_color="inverse" if cand_count > 0 else "normal")
    stat_col4.metric("Khoảng thời gian", f"{start_str} ~ {end_str}")

    # View Mode: Calendar Grid vs Full Table
    v1, v2 = st.columns([7, 3])
    with v1:
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    with v2:
        view_mode = st.radio(
            "Chế độ hiển thị:",
            ["📅 Lịch Tuần (Weekly Schedule)", "📋 Bảng Dữ Liệu (Data Table)"],
            horizontal=True,
            label_visibility="collapsed",
            key="earnings_view_mode"
        )

    if not enriched_events:
        st.info(f"Không tìm thấy sự kiện công bố BCTC nào phù hợp với bộ lọc trong khoảng thời gian {start_str} đến {end_str}.")
        return

    # Render: Mode 1 - Weekly Calendar Grid
    if view_mode.startswith("📅"):
        # Group by date
        by_date: Dict[str, List[Dict[str, Any]]] = {}
        for ev in enriched_events:
            d_str = ev.get("earnings_date", "Chưa rõ ngày")
            by_date.setdefault(d_str, []).append(ev)

        sorted_dates = sorted(by_date.keys())
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        for d_str in sorted_dates:
            day_events = by_date[d_str]
            try:
                dt_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                day_name_vi = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"][dt_obj.weekday()]
                date_header = f"{day_name_vi}, Ngày {d_str} &middot; <span style='font-size: 13px; font-weight: normal; color: #787774;'>({len(day_events)} công ty)</span>"
            except Exception:
                date_header = f"Ngày {d_str} &middot; ({len(day_events)} công ty)"

            date_header_html = (
                f'<div style="background-color: #F7F6F3; border-left: 3px solid #111111; padding: 10px 16px; border-radius: 4px; margin: 16px 0 10px 0; font-family: \'Geist\', \'Inter\', -apple-system, sans-serif; font-size: 18px; font-weight: 600; color: #111111;">'
                f'{date_header}'
                f'</div>'
            )
            render_html_safe(date_header_html)

            # Split BMO and AMC
            bmo_list = [e for e in day_events if e["timing"] == "BMO"]
            amc_list = [e for e in day_events if e["timing"] == "AMC"]
            tns_list = [e for e in day_events if e["timing"] not in ("BMO", "AMC")]

            day_c1, day_c2, day_c3 = st.columns(3)

            with day_c1:
                st.markdown(f'<div class="editorial-label" style="margin-bottom: 8px; color: #8F6B00;">☀️ Trước Giờ Mở Cửa (BMO &middot; {len(bmo_list)})</div>', unsafe_allow_html=True)
                if bmo_list:
                    for item in bmo_list:
                        _render_calendar_card(item)
                else:
                    st.caption("Không có mã BMO.")

            with day_c2:
                st.markdown(f'<div class="editorial-label" style="margin-bottom: 8px; color: #5B21B6;">🌙 Sau Giờ Đóng Cửa (AMC &middot; {len(amc_list)})</div>', unsafe_allow_html=True)
                if amc_list:
                    for item in amc_list:
                        _render_calendar_card(item)
                else:
                    st.caption("Không có mã AMC.")

            with day_c3:
                st.markdown(f'<div class="editorial-label" style="margin-bottom: 8px; color: #64748B;">⏱️ Chưa Ấn Định Giờ (TNS &middot; {len(tns_list)})</div>', unsafe_allow_html=True)
                if tns_list:
                    for item in tns_list:
                        _render_calendar_card(item)
                else:
                    st.caption("Không có mã TNS.")

    # Render: Mode 2 - Interactive Data Table
    else:
        table_rows = []
        for ev in enriched_events:
            sym = ev["symbol"]
            cand = ev.get("candidate_info")
            timing_label = "BMO ☀️" if ev["timing"] == "BMO" else ("AMC 🌙" if ev["timing"] == "AMC" else "TNS")

            radar_tag = "⭐ ỨNG VIÊN" if ev["is_candidate"] else ("S&P 500" if ev["is_sp500"] else "Khác")
            setup_str = f"[{cand.get('setup_type', '')}]" if cand else ""

            mcap = ev.get("market_cap")
            if mcap and mcap >= 1e12:
                mcap_str = f"${mcap/1e12:.2f}T"
            elif mcap and mcap >= 1e9:
                mcap_str = f"${mcap/1e9:.1f}B"
            else:
                mcap_str = "N/A"

            eps_est = ev.get("eps_estimate")
            eps_str = f"${eps_est:.2f}" if eps_est is not None else "N/A"

            rep_eps = ev.get("reported_eps")
            rep_str = f"${rep_eps:.2f}" if rep_eps is not None else "-"

            surp = ev.get("surprise_pct")
            surp_str = f"{surp:+.1f}%" if surp is not None else "-"

            table_rows.append({
                "Ngày BCTC": ev["earnings_date"],
                "Phiên": timing_label,
                "Mã CP": sym,
                "Tên Doanh Nghiệp": ev["company_name"],
                "Ngành GICS": ev["sector"],
                "Vốn Hóa": mcap_str,
                "Ước Tính EPS": eps_str,
                "EPS Thực Tế": rep_str,
                "Bất Ngờ (%)": surp_str,
                "Trạng Thái Radar": f"{radar_tag} {setup_str}".strip()
            })

        df_table = pd.DataFrame(table_rows)
        st.dataframe(
            df_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Mã CP": st.column_config.TextColumn("Mã CP", width="small"),
                "Ngày BCTC": st.column_config.TextColumn("Ngày BCTC", width="small"),
                "Phiên": st.column_config.TextColumn("Phiên", width="small"),
                "Trạng Thái Radar": st.column_config.TextColumn("Trạng Thái Radar", width="medium"),
            }
        )

    # Regulatory & Risk Disclaimer (R-01)
    st.markdown("""
    <div style="background-color: #FFF8E6; border: 1px solid #FFE082; border-radius: 6px; padding: 14px 18px; margin-top: 24px; font-size: 13.5px; color: #795548; line-height: 1.6;">
        <b>⚠️ Nguyên tắc Quản trị Rủi ro Sự kiện Doanh nghiệp:</b><br/>
        - Lịch BCTC trên được tổng hợp tự động từ nguồn dữ liệu mở Yahoo Finance Calendar (dạng ước tính). Doanh nghiệp có thể điều chỉnh ngày/giờ công bố mà không báo trước.<br/>
        - Đối với các chiến thuật Swing Trading, biến động sau báo cáo tài chính thường mang tính nhị phân (Binary Event Risk). Nhà đầu tư cần chủ động kiểm tra thông cáo báo chí trên cổng Quan hệ Cổ đông (IR) hoặc hồ sơ Form 8-K/10-Q trên SEC EDGAR trước khi quyết định mở vị thế.
    </div>
    """, unsafe_allow_html=True)

def _render_calendar_card(item: Dict[str, Any]):
    """Render an individual company card inside the weekly calendar grid."""
    sym = item["symbol"]
    company = item["company_name"]
    sector = item["sector"]
    is_cand = item.get("is_candidate", False)
    cand = item.get("candidate_info")
    timing = item["timing"]

    timing_badge = '<span class="earnings-badge-bmo">BMO ☀️</span>' if timing == "BMO" else ('<span class="earnings-badge-amc">AMC 🌙</span>' if timing == "AMC" else '<span class="earnings-badge-tns">TNS</span>')
    radar_badge = ""
    if is_cand and cand:
        setup = cand.get("setup_type", "SETUP")
        radar_badge = f'<span class="earnings-radar-pill">⭐ {setup}</span>'

    eps_est = item.get("eps_estimate")
    eps_str = f"EPS Est: <b>${eps_est:.2f}</b>" if eps_est is not None else "EPS Est: N/A"

    mcap = item.get("market_cap")
    if mcap and mcap >= 1e9:
        mcap_str = f"Cap: ${mcap/1e9:.1f}B"
    else:
        mcap_str = ""

    border_color = "#346538" if is_cand else "#EAEAEA"
    bg_color = "#F0FDF4" if is_cand else "#FFFFFF"

    tv_link = f"https://www.tradingview.com/chart/?symbol={sym}&interval=D"
    sec_link = f"https://www.sec.gov/edgar/browse/?CIK={sym}"

    card_html = (
        f'<div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 12px 14px; margin-bottom: 8px;">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">'
        f'<div style="display: flex; align-items: center; gap: 8px;">'
        f'<span style="font-family: \'Geist Mono\', monospace; font-size: 15px; font-weight: 700; color: #111111;">{sym}</span>'
        f'{timing_badge}'
        f'</div>'
        f'<div>{radar_badge}</div>'
        f'</div>'
        f'<div style="font-size: 13.5px; color: #2F3437; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 5px;" title="{company}">'
        f'{company}'
        f'</div>'
        f'<div style="font-size: 12px; color: #787774; display: flex; justify-content: space-between; margin-bottom: 6px;">'
        f'<span>{sector}</span>'
        f'<span>{mcap_str}</span>'
        f'</div>'
        f'<div style="font-size: 13px; color: #111111; margin-bottom: 6px;">'
        f'{eps_str}'
        f'</div>'
        f'<div style="display: flex; gap: 10px; font-size: 12.5px; border-top: 1px solid #F0F0F0; padding-top: 7px;">'
        f'<a href="{tv_link}" target="_blank" style="color: #2563EB; text-decoration: none; font-weight: 500;">TradingView ↗</a>'
        f'<span style="color: #D4D4D4;">&bull;</span>'
        f'<a href="{sec_link}" target="_blank" style="color: #787774; text-decoration: none;">SEC EDGAR ↗</a>'
        f'</div>'
        f'</div>'
    )
    render_html_safe(card_html)
