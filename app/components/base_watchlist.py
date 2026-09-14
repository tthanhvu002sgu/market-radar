"""
Base Watchlist Component (Đang Xây Nền).
Renders consolidation base screening with 4 lifecycle filter boxes, candidate data cards,
2-column 6-metric grid, summary lines, structured checklists, and historical base setups.
Chart visualization is removed from the section; _create_base_figure is retained for test compatibility.
"""
import re
import textwrap
from datetime import datetime
import json
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from storage.repository import MarketRadarRepository

def render_html_safe(html_str: str):
    """Render HTML safely without markdown code block indentation issues."""
    clean_html = textwrap.dedent(html_str).strip()
    if hasattr(st, "html"):
        st.html(clean_html)
    else:
        st.markdown(clean_html, unsafe_allow_html=True)


STATE_LABELS = {
    "tight": ("Nền co chặt", "#EDF3EC", "#346538", "Co hẹp biến động & Volume cạn"),
    "forming": ("Đang xây nền", "#EBF3FB", "#2383E2", "Cấu trúc đi ngang hẹp"),
    "breakout_unconfirmed": ("Vượt nền thiếu volume", "#FEF7E6", "#D97706", "Close > Biên trên, Vol chưa đạt"),
    "breakout_confirmed": ("Breakout xác nhận", "#D1FAE5", "#065F46", "Bứt phá biên trên kèm Volume lớn"),
    "fresh_breakout": ("Mới bứt phá", "#D1FAE5", "#065F46", "Bứt phá biên trên (phiên 1–5)"),
    "climbing": ("Tiếp tục tăng", "#E0F2FE", "#0369A1", "Duy trì đà tăng sau breakout (phiên 6+)"),
    "played_out": ("Hoàn tất chu kỳ", "#F3F4F6", "#4B5563", "Kết thúc chu kỳ theo dõi sau breakout"),
    "broken_down": ("Thủng nền", "#FEE2E2", "#991B1B", "Close < Biên dưới"),
    "weakening": ("Suy yếu", "#F3F4F6", "#4B5563", "Tạm mất độ hẹp / ER"),
    "lost_structure": ("Mất cấu trúc", "#E5E7EB", "#374151", "Suy yếu 2 phiên liên tiếp"),
    "none": ("Không rõ", "#F7F6F3", "#787774", "Chưa xác định")
}


def get_base_lifecycle(b: Dict[str, Any]) -> str:
    """Classify base record into one of the 4 lifecycle categories or failure."""
    lp = b.get("lifecycle_phase")
    if lp and lp not in ("none", ""):
        return lp
    st_val = b.get("state", "none")
    bc = int(b.get("breakout_bar_count") or 0)
    if st_val == "played_out":
        return "played_out"
    if st_val in ("broken_down", "lost_structure"):
        return "failed_before_breakout"
    if st_val in ("fresh_breakout", "breakout_confirmed") or (1 <= bc <= 5):
        return "fresh_breakout"
    if st_val == "climbing" or bc >= 6:
        return "climbing"
    return "forming"


def format_base_summary_line(b: Dict[str, Any]) -> str:
    """Format standard base summary line."""
    width_val = b.get("width_pct")
    width_str = f"sâu {width_val:.1f}%" if width_val is not None else "sâu N/A"
    pivot_val = b.get("upper")
    pivot_str = f"Pivot ${pivot_val:.2f}" if pivot_val is not None else "Pivot N/A"
    return f"Nền đi ngang &middot; 20 phiên / khoảng 4 tuần &middot; {width_str} &middot; {pivot_str}"


def render_base_metrics_grid(base_info: Dict[str, Any]):
    """
    Render standardized 2-column, 6-metric base quality grid.
    Exported for reuse across Base Watchlist cards and Candidate Cards.
    Includes rich tooltips (formula, window, interpretation), missing data reasons,
    and timing labels distinguishing frozen pre-breakout metrics from current session metrics.
    """
    # Timing provenance
    lp = base_info.get("lifecycle_phase") or ""
    bo_date = base_info.get("breakout_date")
    is_post_breakout = bool(lp in ("fresh_breakout", "climbing", "played_out") or bo_date)
    as_of_date = base_info.get("as_of", "")

    timing_tag_pre = '<span style="font-size: 10px; color: #956400; font-weight: 500; text-transform: none; margin-left: 4px;">[Tại nền]</span>' if is_post_breakout else ''
    timing_tag_curr = '<span style="font-size: 10px; color: #0369A1; font-weight: 500; text-transform: none; margin-left: 4px;">[Hiện tại]</span>' if is_post_breakout else ''

    if is_post_breakout and bo_date:
        banner_html = (
            f'<div style="font-size: 11.5px; color: #475569; background: #F1F5F9; border-radius: 4px; padding: 4px 8px; margin-bottom: 6px; display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px;">'
            f'<span>⚡ <b>Đã breakout ({bo_date}):</b> Chỉ số chất lượng nền đóng băng trước breakout</span>'
            f'<span><b>Giá & Pivot:</b> Cập nhật phiên {as_of_date}</span>'
            f'</div>'
        )
    else:
        banner_html = (
            '<div style="font-size: 11.5px; color: #475569; background: #F1F5F9; border-radius: 4px; padding: 4px 8px; margin-bottom: 6px;">'
            '<span>🧱 <b>Đang hình thành:</b> Đánh giá chất lượng nén biến động & dòng tiền trên cửa sổ 20 phiên</span>'
            '</div>'
        )

    # 1. RS rating (1-99)
    rs = base_info.get("rs_rating")
    if rs is not None:
        rs_str = f"{rs}"
        rs_color = "#346538" if rs >= 80 else "#111111"
    else:
        rs_str = "— <span style='font-size: 11px; font-weight: normal; color: #787774;'>(Thiếu dữ liệu)</span>"
        rs_color = "#787774"
    rs_tip = (
        "RS rating (1–99)&#10;"
        "• Ý nghĩa: Xếp hạng sức mạnh giá tương đối theo percentile trong vũ trụ S&P 500 đủ dữ liệu.&#10;"
        "• Công thức: Điểm hiệu suất có trọng số đa khung thời gian: 3 tháng (40%), 6 tháng (20%), 1 tháng/9 tháng (20%), 12 tháng (20%).&#10;"
        "• Cách đọc: Thang 1–99. >= 80 là nhóm dẫn dắt (Leader), < 50 là yếu hơn mặt bằng chung."
    )

    # 2. Now vs pivot (%)
    nvp = base_info.get("now_vs_pivot_pct")
    if nvp is not None:
        nvp_str = f"{nvp:+.1f}%"
        nvp_color = "#346538" if nvp >= 0 else "#9F2F2D"
    else:
        nvp_str = "— <span style='font-size: 11px; font-weight: normal; color: #787774;'>(Chưa có Pivot)</span>"
        nvp_color = "#787774"
    nvp_tip = (
        "Now vs pivot (%)&#10;"
        "• Ý nghĩa: Vị trí giá đóng cửa hiện tại so với điểm Pivot (biên trên của nền).&#10;"
        "• Công thức: 100 × (Close / Pivot − 1).&#10;"
        "• Cách đọc: Âm (< 0%) là giá đang tích lũy dưới pivot; Dương (> 0%) là giá đã vượt qua điểm pivot."
    )

    # 3. Tightening (ATR ratio)
    tr = base_info.get("tr_contraction")
    if tr is not None:
        tr_str = f"{tr:.2f}x"
        tr_color = "#346538" if tr <= 0.75 else "#111111"
    else:
        tr_str = "— <span style='font-size: 11px; font-weight: normal; color: #787774;'>(Thiếu dữ liệu)</span>"
        tr_color = "#787774"
    tr_tip = (
        "Tightening (ATR ratio)&#10;"
        "• Ý nghĩa: Tỷ lệ co hẹp biên độ dao động giữa hai nửa nền giá.&#10;"
        "• Công thức: Trung bình True Range 10 phiên cuối / 10 phiên đầu của cửa sổ đánh giá.&#10;"
        "• Lưu ý: Đây là tỷ lệ TR trung bình, tránh gọi nhầm thành chỉ báo ATR14.&#10;"
        "• Cách đọc: Tỷ số < 1.0 (đặc biệt <= 0.75) cho thấy biên độ nến siết chặt dần, cung bán cạn kiệt."
    )

    # 4. Volume dry-up
    vol = base_info.get("vol_contraction")
    if vol is not None:
        vol_str = f"{vol:.2f}x"
        vol_color = "#346538" if vol <= 0.75 else "#111111"
    else:
        vol_str = "— <span style='font-size: 11px; font-weight: normal; color: #787774;'>(Thiếu dữ liệu)</span>"
        vol_color = "#787774"
    vol_tip = (
        "Volume dry-up&#10;"
        "• Ý nghĩa: Đo lường mức độ cạn kiệt thanh khoản trong nền giá.&#10;"
        "• Công thức: Volume trung bình 10 phiên cuối / 10 phiên đầu của nền.&#10;"
        "• Cách đọc: Nhỏ hơn 1.0 nghĩa là volume giảm giữa hai giai đoạn; <= 0.75 thể hiện nguồn cung cạn kiệt rõ rệt trước bứt phá."
    )

    # 5. Up/down volume, net
    svb = base_info.get("signed_volume_balance")
    if svb is not None:
        svb_str = f"{svb:+.2f}"
        svb_color = "#346538" if svb > 0.1 else ("#9F2F2D" if svb < -0.1 else "#111111")
    else:
        svb_str = "— <span style='font-size: 11px; font-weight: normal; color: #787774;'>(Thiếu dữ liệu)</span>"
        svb_color = "#787774"
    svb_tip = (
        "Up/down volume, net&#10;"
        "• Ý nghĩa: Cân bằng khối lượng có dấu trong cửa sổ 20 phiên.&#10;"
        "• Công thức: Tổng volume các phiên tăng trừ tổng volume các phiên giảm / Tổng volume toàn bộ cửa sổ. Miền giá trị [-1.0, +1.0]. Phiên đi ngang (Close không đổi) đóng góp 0 vào tử số.&#10;"
        "• Cách đọc: Dương thể hiện phe mua gom hàng chủ động (Accumulation); Âm cảnh báo áp lực phân phối."
    )

    # 6. From 52-week high
    f52 = base_info.get("from_52w_high_pct")
    if f52 is not None:
        f52_str = f"Thấp hơn đỉnh {f52:.1f}%"
        f52_color = "#346538" if f52 <= 15.0 else "#111111"
    else:
        f52_str = "— <span style='font-size: 11px; font-weight: normal; color: #787774;'>(Chưa đủ 252 phiên)</span>"
        f52_color = "#787774"
    f52_tip = (
        "From 52-week high&#10;"
        "• Ý nghĩa: Khoảng cách từ đỉnh cao nhất trong 252 phiên gần nhất (khoảng 1 năm).&#10;"
        "• Công thức: 100 × (High252 − Close) / High252.&#10;"
        "• Cách đọc: Thể hiện mức thấp hơn đỉnh bao nhiêu %; các cổ phiếu dẫn dắt thường cách đỉnh <= 15%. Yêu cầu đủ 252 phiên dữ liệu."
    )

    grid_html = f"""
    <div style="background: #FAFAFA; border: 1px solid #EAEAEA; border-radius: 6px; padding: 10px 14px; margin: 10px 0;">
        {banner_html}
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px 16px;">
            <div>
                <div style="font-size: 11px; color: #787774; text-transform: uppercase; font-weight: 600; letter-spacing: 0.03em; cursor: help;" title="{rs_tip}">RS rating (1-99)</div>
                <div style="font-family: 'Geist Mono', monospace; font-size: 15px; font-weight: 700; color: {rs_color}; margin-top: 2px;">{rs_str}</div>
            </div>
            <div>
                <div style="font-size: 11px; color: #787774; text-transform: uppercase; font-weight: 600; letter-spacing: 0.03em; cursor: help;" title="{vol_tip}">Volume dry-up {timing_tag_pre}</div>
                <div style="font-family: 'Geist Mono', monospace; font-size: 15px; font-weight: 700; color: {vol_color}; margin-top: 2px;">{vol_str}</div>
            </div>
            <div>
                <div style="font-size: 11px; color: #787774; text-transform: uppercase; font-weight: 600; letter-spacing: 0.03em; cursor: help;" title="{nvp_tip}">Now vs pivot {timing_tag_curr}</div>
                <div style="font-family: 'Geist Mono', monospace; font-size: 15px; font-weight: 700; color: {nvp_color}; margin-top: 2px;">{nvp_str}</div>
            </div>
            <div>
                <div style="font-size: 11px; color: #787774; text-transform: uppercase; font-weight: 600; letter-spacing: 0.03em; cursor: help;" title="{svb_tip}">Up/down volume, net {timing_tag_pre}</div>
                <div style="font-family: 'Geist Mono', monospace; font-size: 15px; font-weight: 700; color: {svb_color}; margin-top: 2px;">{svb_str}</div>
            </div>
            <div>
                <div style="font-size: 11px; color: #787774; text-transform: uppercase; font-weight: 600; letter-spacing: 0.03em; cursor: help;" title="{tr_tip}">Tightening (ATR ratio) {timing_tag_pre}</div>
                <div style="font-family: 'Geist Mono', monospace; font-size: 15px; font-weight: 700; color: {tr_color}; margin-top: 2px;">{tr_str}</div>
            </div>
            <div>
                <div style="font-size: 11px; color: #787774; text-transform: uppercase; font-weight: 600; letter-spacing: 0.03em; cursor: help;" title="{f52_tip}">From 52-week high {timing_tag_curr}</div>
                <div style="font-family: 'Geist Mono', monospace; font-size: 15px; font-weight: 700; color: {f52_color}; margin-top: 2px;">{f52_str}</div>
            </div>
        </div>
    </div>
    """
    if hasattr(st, "html"):
        st.html(grid_html)
    else:
        st.markdown(grid_html, unsafe_allow_html=True)


def render_base_watchlist(
    base_records: Optional[List[Dict[str, Any]]] = None,
    as_of: str = "",
    repo: Optional[MarketRadarRepository] = None,
    snapshot_id: Optional[int] = None,
    candidates: Optional[List[Dict[str, Any]]] = None
):
    """
    Render the 'Nền Giá & Bứt Phá' (Base Building & Breakout) section.
    Supports two data scopes:
    1. 'Trong snapshot hiện tại' (point-in-time snapshot records)
    2. 'Tất cả các đợt đến phiên chọn' (latest record per base setup including ended/played_out)
    Always clearly distinguishes symbol counts from setup counts.
    """
    st.markdown('<div class="editorial-hero" style="font-size: 22px; margin-bottom: 4px;">🧱 Nền Giá & Bứt Phá (Base Building & Breakout)</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="editorial-sub" style="margin-bottom: 16px;">'
        'Nhận diện các cổ phiếu tích lũy trong nền giá hẹp trước và sau điểm bứt phá. '
        'Theo dõi vòng đời nền qua 4 giai đoạn với 6 chỉ số định lượng trọng yếu; phân biệt rõ số mã với số đợt nền.'
        '</div>',
        unsafe_allow_html=True
    )

    # Dual Data Scopes Selection
    scope_options = [
        "Trong snapshot hiện tại",
        "Tất cả các đợt đến phiên chọn (gồm đã kết thúc)"
    ]
    scope_selected = st.radio(
        "Phạm vi dữ liệu nền giá:",
        options=scope_options,
        index=0,
        horizontal=True,
        key="base_data_scope_radio",
        help="Trong snapshot: chỉ lấy các bản ghi nền thuộc phiên snapshot. Tất cả các đợt: lấy trạng thái mới nhất của mọi đợt nền tính đến phiên này kể cả đã hoàn tất."
    )

    # Resolve records based on selected scope
    effective_records = base_records or []
    if repo:
        try:
            if scope_selected == "Trong snapshot hiện tại":
                if snapshot_id is not None:
                    effective_records = repo.get_base_snapshots(snapshot_id=snapshot_id, as_of=as_of)
                else:
                    effective_records = repo.get_base_snapshots(as_of=as_of)
            else:
                if hasattr(repo, "get_latest_base_snapshots"):
                    effective_records = repo.get_latest_base_snapshots(as_of=as_of)
                else:
                    effective_records = repo.get_base_snapshots(as_of=as_of)
        except Exception:
            effective_records = base_records or []

    if not effective_records:
        st.info("ℹ️ Chưa có dữ liệu nền giá cho phạm vi này (phiên trước khi kích hoạt bộ nhận diện hoặc không có mã nào thỏa mãn tiêu chí).")
        return

    # 1. Universal Filter Controls (Search & Sector)
    f_col1, f_col2, f_col3 = st.columns([2.2, 1.8, 1.2])

    with f_col1:
        search_sym = st.text_input("Tìm kiếm mã hoặc công ty:", placeholder="Nhập AAPL, MSFT...", key="base_search_input").strip().lower()

    with f_col2:
        all_sectors = ["Tất cả các ngành"] + sorted(list(set(b.get("sector") for b in effective_records if b.get("sector"))))
        selected_sector = st.selectbox("Lọc theo ngành:", all_sectors, index=0, key="base_sector_filter")

    # Scope records by search and sector first so box counts reflect filters
    scoped_records = effective_records
    if search_sym:
        scoped_records = [
            b for b in scoped_records
            if search_sym in b.get("symbol", "").lower() or search_sym in b.get("company_name", "").lower()
        ]
    if selected_sector != "Tất cả các ngành":
        scoped_records = [b for b in scoped_records if b.get("sector") == selected_sector]

    # Calculate distinct symbol counts and setup counts for 4 lifecycle filter boxes
    def _get_counts(records, phase):
        matched = [b for b in records if get_base_lifecycle(b) == phase]
        distinct_symbols = len(set(b.get("symbol", "") for b in matched))
        return distinct_symbols, len(matched)

    sym_forming, cnt_forming = _get_counts(scoped_records, "forming")
    sym_fresh, cnt_fresh = _get_counts(scoped_records, "fresh_breakout")
    sym_climbing, cnt_climbing = _get_counts(scoped_records, "climbing")
    sym_played_out, cnt_played_out = _get_counts(scoped_records, "played_out")

    # 2. 4 Lifecycle Filter Boxes with explicit symbol and setup counts
    lifecycle_options = ["forming", "fresh_breakout", "climbing", "played_out"]
    lifecycle_labels = {
        "forming": f"🧱 Đang hình thành ({sym_forming} mã / {cnt_forming} đợt)",
        "fresh_breakout": f"🚀 Mới bứt phá ({sym_fresh} mã / {cnt_fresh} đợt)",
        "climbing": f"📈 Tiếp tục tăng ({sym_climbing} mã / {cnt_climbing} đợt)",
        "played_out": f"🏁 Hoàn tất chu kỳ ({sym_played_out} mã / {cnt_played_out} đợt)"
    }

    selected_lifecycle = st.segmented_control(
        "Vòng đời nền giá",
        options=lifecycle_options,
        format_func=lambda k: lifecycle_labels[k],
        default="forming",
        label_visibility="collapsed",
        key="base_lifecycle_selector"
    ) if hasattr(st, "segmented_control") else st.radio(
        "Vòng đời nền giá",
        options=lifecycle_options,
        format_func=lambda k: lifecycle_labels[k],
        horizontal=True,
        label_visibility="collapsed",
        key="base_lifecycle_selector"
    )
    if not selected_lifecycle:
        selected_lifecycle = "forming"

    # Contextual guidance for Climbing lifecycle
    if selected_lifecycle == "climbing":
        st.caption("ℹ️ **Tiếp tục tăng (Climbing)**: Từ phiên thứ 6 sau breakout, đợt breakout vẫn còn hiệu lực cấu trúc (không có nghĩa giá tăng mỗi ngày).")

    # Filter by selected lifecycle
    display_records = [b for b in scoped_records if get_base_lifecycle(b) == selected_lifecycle]

    # Export CSV reflecting the current filtered dataset
    with f_col3:
        as_of_tag = as_of.split()[0] if as_of else "latest"
        export_cols = [
            "symbol", "company_name", "sector", "sub_industry", "lifecycle_phase", "state", "is_active",
            "as_of", "detected_at", "window_start", "window_end",
            "close_price", "perf_1d", "upper", "lower", "width_pct", "now_vs_pivot_pct",
            "rs_rating", "high_52w", "from_52w_high_pct",
            "tr_contraction", "vol_contraction", "signed_volume_balance", "volume_balance_label",
            "breakout_date", "breakout_price", "breakout_bar_count", "consecutive_below_ma50",
            "ended_at", "end_reason", "efficiency_ratio", "center_shift",
            "ma50", "ma200", "price_vs_ma50_pct", "price_vs_ma200_pct", "trend_context", "pressure_bias"
        ]
        export_df = pd.DataFrame(display_records)
        valid_export_cols = [c for c in export_cols if c in export_df.columns]
        csv_data = export_df[valid_export_cols].to_csv(index=False) if not export_df.empty else ""
        st.download_button(
            label="Xuất CSV 📥",
            data=csv_data,
            file_name=f"market_radar_bases_{selected_lifecycle}_{as_of_tag}.csv",
            mime="text/csv",
            use_container_width=True,
            key="btn_dl_base_cards_csv"
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    if not display_records:
        st.info(f"Không có cổ phiếu nào trong nhóm '{lifecycle_labels[selected_lifecycle]}' thỏa mãn điều kiện tìm kiếm và ngành.")
        return

    # 3. Group setups by symbol (gom các đợt nền của cùng 1 mã trong một thẻ)
    from collections import OrderedDict
    grouped_by_symbol: OrderedDict[str, List[Dict[str, Any]]] = OrderedDict()
    for b in display_records:
        sym_key = str(b.get("symbol", ""))
        if sym_key not in grouped_by_symbol:
            grouped_by_symbol[sym_key] = []
        grouped_by_symbol[sym_key].append(b)

    unique_symbols = list(grouped_by_symbol.keys())

    # 4. Card Pagination by Symbol
    page_size = 12
    total_pages = (len(unique_symbols) + page_size - 1) // page_size
    if total_pages > 1:
        page_options = [
            f"Trang {p}/{total_pages} (Mã {(p-1)*page_size + 1} - {min(p*page_size, len(unique_symbols))})"
            for p in range(1, total_pages + 1)
        ]
        chosen_page_label = st.selectbox(
            f"Trang hiển thị ({len(unique_symbols)} mã / {len(display_records)} đợt nền):",
            page_options,
            key=f"page_base_cards_{selected_lifecycle}"
        )
        c_page = page_options.index(chosen_page_label) + 1
        start_i = (c_page - 1) * page_size
        page_symbols = unique_symbols[start_i : start_i + page_size]
    else:
        page_symbols = unique_symbols

    st.markdown(f"<div style='font-size: 13px; color: #787774; margin-bottom: 12px;'>Đang hiển thị: <b>{len(page_symbols)}</b> / <b>{len(unique_symbols)}</b> mã (tổng <b>{len(display_records)}</b> đợt nền) &middot; Nhóm <b>{lifecycle_labels[selected_lifecycle]}</b></div>", unsafe_allow_html=True)

    # 5. Render Data Cards
    candidate_map = {c["symbol"]: c for c in candidates} if candidates else {}
    if not candidate_map and repo and snapshot_id:
        try:
            cands_list = repo.get_candidates_by_snapshot(snapshot_id)
            candidate_map = {c["symbol"]: c for c in cands_list}
        except Exception:
            candidate_map = {}

    for idx, s in enumerate(page_symbols):
        setups = grouped_by_symbol[s]
        if len(setups) == 1:
            _render_individual_base_card(
                setups[0],
                as_of=as_of,
                repo=repo,
                key_suffix=f"{selected_lifecycle}_{idx}",
                candidate_map=candidate_map
            )
        else:
            _render_grouped_base_card(
                s,
                setups,
                as_of=as_of,
                repo=repo,
                key_suffix=f"{selected_lifecycle}_{idx}",
                candidate_map=candidate_map
            )


def _get_badge_html(lifecycle: str, state_key: str, bo_bars: int = 0) -> str:
    """Generate HTML badges for base lifecycle and secondary status."""
    if lifecycle == "forming":
        main_badge = '<span style="font-size: 12px; font-weight: 600; background: #EBF3FB; color: #2383E2; border: 1px solid #BAE6FD; padding: 3px 8px; border-radius: 9999px;">Đang hình thành</span>'
        if state_key == "tight":
            sec_badge = '<span style="font-size: 12px; font-weight: 600; background: #EDF3EC; color: #346538; border: 1px solid #D1E5D0; padding: 3px 8px; border-radius: 9999px; margin-left: 5px;" title="Nền co hẹp biến động và volume cạn kiệt">Co chặt</span>'
        elif state_key == "weakening":
            sec_badge = '<span style="font-size: 12px; font-weight: 600; background: #F3F4F6; color: #4B5563; border: 1px solid #E5E7EB; padding: 3px 8px; border-radius: 9999px; margin-left: 5px;" title="Cấu trúc nền suy yếu ở cửa sổ 20 phiên">Suy yếu</span>'
        elif state_key == "breakout_unconfirmed":
            sec_badge = '<span style="font-size: 12px; font-weight: 600; background: #FEF7E6; color: #D97706; border: 1px solid #FDE68A; padding: 3px 8px; border-radius: 9999px; margin-left: 5px;" title="Vượt pivot biên trên nhưng volume chưa đạt chuẩn">Vượt pivot thiếu volume</span>'
        else:
            sec_badge = ''
        return f'{main_badge}{sec_badge}'
    elif lifecycle == "fresh_breakout":
        bar_text = f"Phiên {bo_bars}/5" if bo_bars > 0 else "Phiên 1–5"
        return f'<span style="font-size: 12px; font-weight: 600; background: #D1FAE5; color: #065F46; border: 1px solid #A7F3D0; padding: 3px 10px; border-radius: 9999px;" title="Breakout xác nhận trong 5 phiên giao dịch gần nhất">Mới bứt phá ({bar_text})</span>'
    elif lifecycle == "climbing":
        bar_text = f"Phiên {bo_bars}" if bo_bars > 0 else "Phiên 6+"
        return f'<span style="font-size: 12px; font-weight: 600; background: #E0F2FE; color: #0369A1; border: 1px solid #BAE6FD; padding: 3px 10px; border-radius: 9999px; cursor: help;" title="Từ phiên thứ 6, đợt breakout vẫn còn hiệu lực cấu trúc (không có nghĩa giá tăng mỗi ngày)">Tiếp tục tăng ({bar_text}) ℹ️</span>'
    elif lifecycle == "played_out":
        return '<span style="font-size: 12px; font-weight: 600; background: #F3F4F6; color: #4B5563; border: 1px solid #E5E7EB; padding: 3px 10px; border-radius: 9999px;" title="Đợt đã breakout nhưng sau đó chạm điều kiện kết thúc">Hoàn tất chu kỳ (Đã kết thúc)</span>'
    else:
        return '<span style="font-size: 12px; font-weight: 600; background: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5; padding: 3px 10px; border-radius: 9999px;">Hỏng trước breakout</span>'


def _render_card_fa_column(
    sym: str,
    fa_flags: Optional[Dict[str, Any]],
    as_of: str = "",
    repo: Optional[MarketRadarRepository] = None
):
    """Render standardized fundamental (FA) column for stock cards."""
    st.markdown('<div class="editorial-label" style="margin-bottom: 8px;">Bối cảnh Doanh nghiệp & FA</div>', unsafe_allow_html=True)
    if (not fa_flags or not isinstance(fa_flags, dict) or not fa_flags.get("has_data")) and repo is not None:
        try:
            from analytics.company_fa import evaluate_fa_flags
            fa_df = repo.get_fundamentals([sym])
            if not fa_df.empty:
                fa_raw = fa_df.iloc[0].to_dict()
                ref_d = as_of.split()[0] if as_of else None
                fa_flags = evaluate_fa_flags(sym, fa_raw, ref_date=ref_d)
        except Exception:
            pass

    if fa_flags and isinstance(fa_flags, dict) and fa_flags.get("has_data"):
        days_earn = fa_flags.get("days_to_earnings")
        next_earn = fa_flags.get("next_earnings_date")

        # 1. Dedicated earnings schedule & risk tag
        if days_earn is not None and next_earn and next_earn != "Chưa xác minh":
            if 0 <= days_earn <= 14:
                earn_chip = f"<span style='background: #FDEBEC; color: #9F2F2D; border: 1px solid #F8D7DA; padding: 1px 6px; border-radius: 4px; font-weight: 600; font-size: 12px;'>⚠️ Còn {days_earn} ngày (Rủi ro biến động)</span>"
            else:
                earn_chip = f"<span style='background: #EDF3EC; color: #346538; border: 1px solid #D1E5D0; padding: 1px 6px; border-radius: 4px; font-weight: 500; font-size: 12px;'>Còn {days_earn} ngày (An toàn swing)</span>"
            st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; margin-bottom: 6px;'><b>BCTC tới:</b> {next_earn} &middot; {earn_chip}</div>", unsafe_allow_html=True)
        elif next_earn and next_earn != "Chưa xác minh":
            st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; margin-bottom: 6px;'><b>BCTC dự kiến:</b> {next_earn}</div>", unsafe_allow_html=True)

        # 2. Render flags without duplicate earnings or duplicate MRQ dates
        flags_list = fa_flags.get("flags", [])
        warning_chips = []
        bullet_flags = []
        for f in flags_list:
            if any(kw in f for kw in ["Kỳ công bố Earnings", "RỦI RO BÁO CÁO TÀI CHÍNH", "Earnings: Lịch chưa"]):
                continue
            if "Cảnh báo" in f or "⚠️" in f:
                clean_f = f.replace("⚠️", "").replace("Cảnh báo:", "").strip()
                clean_f = re.sub(r',\s*Kỳ kết thúc\s*\([^)]*\):?\s*[\d\-]+', '', clean_f)
                clean_f = re.sub(r',\s*nguồn\s*[^)]+', '', clean_f)
                warning_chips.append(clean_f)
            else:
                bullet_flags.append(f)

        if warning_chips:
            chips_html = "".join([
                f"<span style='font-size: 12px; color: #9F2F2D; background: #FDEBEC; border: 1px solid #F8D7DA; padding: 2px 8px; border-radius: 4px; font-weight: 500; display: inline-block; margin: 2px 4px 4px 0;'>⚠️ {w}</span>"
                for w in warning_chips
            ])
            st.markdown(f"<div style='margin-bottom: 6px;'>{chips_html}</div>", unsafe_allow_html=True)

        for bf in bullet_flags:
            st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; line-height: 1.55; margin-bottom: 3px;'>&bull; {bf}</div>", unsafe_allow_html=True)

        if not warning_chips and not bullet_flags and not next_earn:
            st.markdown("<div style='font-size: 13.5px; color: #787774;'>&bull; Chưa ghi nhận bất thường cơ bản.</div>", unsafe_allow_html=True)

        # 3. Clean single metadata row
        period_end = fa_flags.get("period_end")
        fiscal_period = fa_flags.get("fiscal_period")
        src_str = fa_flags.get("source", "Yahoo Finance (Số liệu tổng hợp / Aggregate)")
        metrics = fa_flags.get("metrics", {})
        p_margin = metrics.get('profit_margin_str', 'N/A')

        period_label = period_end if (period_end and period_end != "Chưa xác minh") else fiscal_period
        meta_parts = []
        if period_label and period_label not in ("Chưa xác minh kỳ", "N/A"):
            meta_parts.append(f"Kỳ MRQ: <b>{period_label}</b>")
        if p_margin and p_margin != "N/A":
            meta_parts.append(f"Biên ròng: <b>{p_margin}</b>")
        meta_parts.append(f"Nguồn: {src_str}")

        st.markdown(f"<div style='font-size: 12px; color: #787774; margin-top: 6px; padding-top: 6px; border-top: 1px dashed #EAEAEA;'>{' &middot; '.join(meta_parts)}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='font-size: 13.5px; color: #787774;'>&bull; Chưa có dữ liệu FA trong cơ sở dữ liệu local (chờ chu kỳ cập nhật tiếp theo).</div>", unsafe_allow_html=True)


def _render_card_action_column(
    sym: str,
    cand_obj: Dict[str, Any],
    fa_flags: Optional[Dict[str, Any]],
    as_of: str = "",
    repo: Optional[MarketRadarRepository] = None,
    key_suffix: str = ""
):
    """Render standardized action buttons column."""
    st.markdown('<div class="editorial-label" style="margin-bottom: 8px;">Thao tác</div>', unsafe_allow_html=True)
    card_btn_key = f"btn_base_card_detail_{sym}_{key_suffix}" if key_suffix else f"btn_base_card_detail_{sym}"
    if st.button(f"Chi tiết {sym} →", key=card_btn_key, type="primary", use_container_width=True):
        from app.components.setup_detail import show_setup_detail_dialog
        show_setup_detail_dialog(cand_obj, as_of=as_of, repo=repo, key_suffix=f"base_dlg_{sym}_{key_suffix}")

    tv_url = f"https://www.tradingview.com/chart/?symbol={sym}&interval=D"
    st.link_button(f"Chart {sym} ↗", tv_url, use_container_width=True)

    sec_url = (fa_flags.get("sec_filing_url") if isinstance(fa_flags, dict) else None) or f"https://www.sec.gov/edgar/browse/?CIK={sym}"
    st.link_button("Tra cứu SEC ↗", sec_url, use_container_width=True)


def _render_individual_base_card(
    b: Dict[str, Any],
    as_of: str = "",
    repo: Optional[MarketRadarRepository] = None,
    key_suffix: str = "",
    candidate_map: Optional[Dict[str, Dict[str, Any]]] = None
):
    """Render single base candidate data card synchronized with app design."""
    sym = b.get("symbol", "")
    company = b.get("company_name", sym)
    sector = b.get("sector", "")
    sub_ind = b.get("sub_industry", "")
    price = b.get("close_price", 0.0)
    p1d = b.get("perf_1d")
    upper = b.get("upper")
    lower = b.get("lower")
    width = b.get("width_pct")
    now_vs_pivot = b.get("now_vs_pivot_pct")
    rs = b.get("rs_rating")
    f52 = b.get("from_52w_high_pct")

    if p1d is not None:
        color_1d = "#346538" if p1d >= 0 else "#9F2F2D"
        p1d_str = f"{p1d:+.2f}%"
    else:
        color_1d = "#787774"
        p1d_str = "—"

    # Leader badge
    cand_match = candidate_map.get(sym) if candidate_map else None
    is_oneil = bool(rs is not None and rs >= 80)
    if cand_match and cand_match.get("is_oneil_leader"):
        is_oneil = True
    oneil_badge_html = '<span style="font-size: 11.5px; font-weight: 600; background: #EDF3EC; color: #346538; border: 1px solid #D1E5D0; padding: 2px 8px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase; margin-left: 6px;">Leader</span>' if is_oneil else ''

    # Setup badge
    setup_label = "NỀN GIÁ" if not b.get("breakout_date") else "BREAKOUT NỀN"
    setup_badge_html = f'<span style="font-size: 11.5px; font-weight: 600; background: #E1F3FE; color: #1F6C9F; border: 1px solid #BAE6FD; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.03em; text-transform: uppercase; margin-left: 6px;">{setup_label}</span>'

    # Lifecycle & status badges
    state_key = b.get("state", "none")
    lifecycle = b.get("lifecycle_phase") or get_base_lifecycle(b)
    bo_bars = b.get("breakout_bar_count", 0)
    badges_html = _get_badge_html(lifecycle, state_key, bo_bars)

    sub_ind_html = f'<span style="font-size: 12px; background: #F7F6F3; color: #787774; border: 1px solid #EAEAEA; padding: 2px 8px; border-radius: 9999px; margin-left: 6px;">{sub_ind}</span>' if sub_ind else ''
    sector_html = f'<span style="font-size: 12px; background: #F7F6F3; color: #555555; border: 1px solid #EAEAEA; padding: 2px 8px; border-radius: 9999px; margin-left: 8px;">{sector}</span>' if sector else ''

    rs_str = f"{rs}" if rs is not None else "—"
    rs_color = "#346538" if (rs is not None and rs >= 80) else "#111111"

    pivot_str = f"${upper:.2f}" if upper is not None else "N/A"
    lower_str = f"${lower:.2f}" if lower is not None else "N/A"
    width_str = f"{width:.1f}%" if width is not None else "N/A"

    if now_vs_pivot is not None:
        nvp_color = "#346538" if now_vs_pivot >= 0 else "#9F2F2D"
        nvp_str = f"{now_vs_pivot:+.1f}%"
    else:
        nvp_color = "#787774"
        nvp_str = "N/A"

    f52_str = f"-{f52:.1f}%" if f52 is not None else "N/A"

    # End reason banner if ended
    end_reason = b.get("end_reason")
    ended_at = b.get("ended_at")
    if end_reason:
        date_str = f"Ngày {ended_at} &middot; " if ended_at else ""
        end_reason_html = f'<div style="font-size: 12px; color: #991B1B; background: #FEE2E2; border: 1px solid #FCA5A5; border-radius: 4px; padding: 6px 10px; margin-top: 8px;"><b>Đã kết thúc:</b> {date_str}<b>Nguyên nhân:</b> {end_reason}</div>'
    else:
        end_reason_html = ''

    # Base state label
    b_st_key = b.get("state", "forming")
    b_label = STATE_LABELS.get(b_st_key, (b_st_key,))[0]
    summary_line = format_base_summary_line(b)

    with st.container(border=True):
        header_html = (
            f'<div style="margin-bottom: 12px;">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">'
            f'<div style="display: flex; align-items: center; flex-wrap: wrap; gap: 4px;">'
            f'<span style="font-family: \'Geist Mono\', monospace; font-size: 20px; font-weight: 700; color: #111111;">{sym}</span>'
            f'<span style="font-size: 15px; color: #787774; margin-left: 6px; font-weight: 500;">{company}</span>'
            f'{sector_html}'
            f'{sub_ind_html}'
            f'{oneil_badge_html}'
            f'{setup_badge_html}'
            f'</div>'
            f'<div style="display: flex; align-items: center; gap: 10px;">'
            f'<span style="font-family: \'Geist Mono\', monospace; font-size: 13.5px; color: #787774;">RS: <b style="color: {rs_color};">{rs_str}</b></span>'
            f'{badges_html}'
            f'</div>'
            f'</div>'
            f'<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 12px; font-family: \'Geist Mono\', monospace; font-size: 13.5px; color: #787774; background: #F9F9F8; border: 1px solid #EAEAEA; border-radius: 6px; padding: 8px 14px;">'
            f'<span><span style="color: #2F3437; font-weight: 600;">Giá: ${price:.2f}</span> (1D: <span style="color: {color_1d}; font-weight: 600;">{p1d_str}</span>)</span>'
            f'<span style="color: #D1D5DB;">|</span>'
            f'<span>Pivot: <b style="color: #111111;">{pivot_str}</b></span>'
            f'<span style="color: #D1D5DB;">&middot;</span>'
            f'<span>Biên dưới: <b style="color: #111111;">{lower_str}</b></span>'
            f'<span style="color: #D1D5DB;">&middot;</span>'
            f'<span>Cách Pivot: <span style="color: {nvp_color}; font-weight: 600;">{nvp_str}</span></span>'
            f'<span style="color: #D1D5DB;">&middot;</span>'
            f'<span>Độ rộng: <b style="color: #2F3437;">{width_str}</b></span>'
            f'<span style="color: #D1D5DB;">&middot;</span>'
            f'<span>Đỉnh 52W: <b style="color: #2F3437;">{f52_str}</b></span>'
            f'</div>'
            f'</div>'
        )
        render_html_safe(header_html)

        # Base banner (matching candidate cards base section)
        base_badge_html = f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 14px; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                <span style="font-size: 13px; font-weight: 600; color: #1E293B;">🧱 Thiết Lập Nền Giá (Base Building):</span>
                <span style="font-size: 11.5px; background: #EFF6FF; color: #1D4ED8; padding: 1px 6px; border-radius: 4px; font-weight: 600;">{b_label}</span>
            </div>
            <div style="font-size: 12.5px; color: #64748B;">{summary_line}</div>
            {end_reason_html}
        </div>
        """
        render_html_safe(base_badge_html)

        # 6 Core Metrics Grid
        render_base_metrics_grid(b)

        # Build candidate object for detail dialog
        cand_obj = dict(cand_match) if cand_match else {
            "symbol": sym,
            "company_name": company,
            "sector": sector,
            "sub_industry": sub_ind,
            "close_price": price,
            "perf_1d": p1d or 0.0,
            "perf_5d": b.get("perf_5d", 0.0),
            "perf_20d": b.get("perf_20d", 0.0),
            "trigger_price": upper,
            "invalidation_price": lower,
            "status": "confirmed" if lifecycle in ("fresh_breakout", "breakout_confirmed") else ("setup" if state_key in ("tight", "forming") else "watchlist"),
            "score": float(rs or 0.0),
            "setup_type": setup_label,
            "group_type": "base_building",
            "is_oneil_leader": is_oneil,
            "atr14": b.get("atr14"),
            "atr_pct": b.get("atr_pct"),
            "tv_url": f"https://www.tradingview.com/chart/?symbol={sym}&interval=D",
            "fa_flags": b.get("fa_flags"),
            "base_info": b
        }
        cand_obj["base_info"] = b

        # 3-Column Bento Section
        col_ta, col_fa, col_action = st.columns([4.6, 4.6, 2.8])

        with col_ta:
            st.markdown('<div class="editorial-label" style="margin-bottom: 8px;">Bằng chứng Kỹ thuật (TA)</div>', unsafe_allow_html=True)
            win_start = b.get("window_start", "")
            win_end = b.get("window_end", "")
            if win_start and win_end:
                st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; line-height: 1.55; margin-bottom: 3px;'>&bull; Cửa sổ 20 phiên: <b>{win_start}</b> &rarr; <b>{win_end}</b>.</div>", unsafe_allow_html=True)

            st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; line-height: 1.55; margin-bottom: 3px;'>&bull; Cấu trúc: Pivot <b>{pivot_str}</b> &middot; Biên dưới <b>{lower_str}</b> &middot; Độ sâu <b>{width_str}</b>.</div>", unsafe_allow_html=True)

            t_ctx = b.get("trend_context")
            ma50 = b.get("ma50")
            ma200 = b.get("ma200")
            if t_ctx or ma50 or ma200:
                ctx_parts = []
                if t_ctx:
                    ctx_parts.append(f"Bối cảnh: <b>{t_ctx}</b>")
                if ma50:
                    ctx_parts.append(f"MA50: <b>${ma50:.2f}</b>")
                if ma200:
                    ctx_parts.append(f"MA200: <b>${ma200:.2f}</b>")
                st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; line-height: 1.55; margin-bottom: 3px;'>&bull; {' &middot; '.join(ctx_parts)}.</div>", unsafe_allow_html=True)

            bo_date = b.get("breakout_date")
            bo_price = b.get("breakout_price")
            bo_count = b.get("breakout_bar_count", 0)
            if bo_date and bo_price:
                st.markdown(f"<div style='font-size: 13.5px; color: #065F46; line-height: 1.55; margin-bottom: 3px;'>&bull; ⚡ Breakout xác nhận ngày <b>{bo_date}</b> tại <b>${bo_price:.2f}</b> (Phiên thứ {bo_count}).</div>", unsafe_allow_html=True)
            elif now_vs_pivot is not None:
                st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; line-height: 1.55; margin-bottom: 3px;'>&bull; Tích lũy dưới Pivot: cách đỉnh nền <b style='color: {nvp_color};'>{nvp_str}</b>.</div>", unsafe_allow_html=True)

            checks = b.get("checks", [])
            if checks:
                pass_cnt = sum(1 for chk in checks if chk.get("pass"))
                st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; line-height: 1.55; margin-bottom: 3px;'>&bull; Checklist: Đạt <b>{pass_cnt}/{len(checks)}</b> tiêu chí cấu trúc nền.</div>", unsafe_allow_html=True)

            if is_oneil:
                st.markdown(f"<div style='font-size: 13px; color: #166534; background: #EDF3EC; border: 1px solid #D1E5D0; padding: 4px 8px; border-radius: 4px; margin-top: 5px;'>★ O'Neil Leader: Top 20% sức mạnh giá RS ({rs_str})</div>", unsafe_allow_html=True)

        with col_fa:
            fa_data = b.get("fa_flags") or (cand_match.get("fa_flags") if cand_match else None)
            _render_card_fa_column(sym=sym, fa_flags=fa_data, as_of=as_of, repo=repo)

        with col_action:
            fa_data = b.get("fa_flags") or (cand_match.get("fa_flags") if cand_match else None)
            _render_card_action_column(
                sym=sym,
                cand_obj=cand_obj,
                fa_flags=fa_data,
                as_of=as_of,
                repo=repo,
                key_suffix=key_suffix
            )

        # Technical details & history expander inside the card
        _render_technical_details_expander(b, sym=sym, as_of=as_of, repo=repo, key_suffix=key_suffix)


def _render_grouped_base_card(
    sym: str,
    setups: List[Dict[str, Any]],
    as_of: str = "",
    repo: Optional[MarketRadarRepository] = None,
    key_suffix: str = "",
    candidate_map: Optional[Dict[str, Dict[str, Any]]] = None
):
    """Render a unified card for a symbol with multiple base setups grouped together."""
    first_b = setups[0]
    company = first_b.get("company_name", sym)
    sector = first_b.get("sector", "")
    sub_ind = first_b.get("sub_industry", "")
    price = first_b.get("close_price", 0.0)
    data_date = first_b.get("as_of", as_of)
    p1d = first_b.get("perf_1d")
    rs = first_b.get("rs_rating")

    if p1d is not None:
        p1d_color = "#346538" if p1d >= 0 else "#9F2F2D"
        p1d_str = f"{p1d:+.2f}%"
    else:
        p1d_color = "#787774"
        p1d_str = "—"

    cand_match = candidate_map.get(sym) if candidate_map else None
    is_oneil = bool(rs is not None and rs >= 80)
    if cand_match and cand_match.get("is_oneil_leader"):
        is_oneil = True
    oneil_badge_html = '<span style="font-size: 11.5px; font-weight: 600; background: #EDF3EC; color: #346538; border: 1px solid #D1E5D0; padding: 2px 8px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase; margin-left: 6px;">Leader</span>' if is_oneil else ''

    sub_ind_html = f'<span style="font-size: 12px; background: #F7F6F3; color: #787774; border: 1px solid #EAEAEA; padding: 2px 8px; border-radius: 9999px; margin-left: 6px;">{sub_ind}</span>' if sub_ind else ''
    sector_html = f'<span style="font-size: 12px; background: #F7F6F3; color: #555555; border: 1px solid #EAEAEA; padding: 2px 8px; border-radius: 9999px; margin-left: 8px;">{sector}</span>' if sector else ''

    rs_str = f"{rs}" if rs is not None else "—"
    rs_color = "#346538" if (rs is not None and rs >= 80) else "#111111"

    with st.container(border=True):
        header_html = (
            f'<div style="margin-bottom: 12px;">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">'
            f'<div style="display: flex; align-items: center; flex-wrap: wrap; gap: 4px;">'
            f'<span style="font-family: \'Geist Mono\', monospace; font-size: 20px; font-weight: 700; color: #111111;">{sym}</span>'
            f'<span style="font-size: 15px; color: #787774; margin-left: 6px; font-weight: 500;">{company}</span>'
            f'{sector_html}'
            f'{sub_ind_html}'
            f'{oneil_badge_html}'
            f'</div>'
            f'<div style="display: flex; align-items: center; gap: 10px;">'
            f'<span style="font-family: \'Geist Mono\', monospace; font-size: 13.5px; color: #787774;">RS: <b style="color: {rs_color};">{rs_str}</b></span>'
            f'<span style="font-size: 12px; font-weight: 600; background: #EEF2FF; color: #4F46E5; border: 1px solid #C7D2FE; padding: 3px 10px; border-radius: 9999px; letter-spacing: 0.04em;">{len(setups)} setups</span>'
            f'</div>'
            f'</div>'
            f'<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 12px; font-family: \'Geist Mono\', monospace; font-size: 13.5px; color: #787774; background: #F9F9F8; border: 1px solid #EAEAEA; border-radius: 6px; padding: 8px 14px;">'
            f'<span><span style="color: #2F3437; font-weight: 600;">Giá: ${price:.2f}</span> (1D: <span style="color: {p1d_color}; font-weight: 600;">{p1d_str}</span>)</span>'
            f'<span style="color: #D1D5DB;">|</span>'
            f'<span>Số đợt nền: <b style="color: #111111;">{len(setups)}</b></span>'
            f'<span style="color: #D1D5DB;">&middot;</span>'
            f'<span>Phiên dữ liệu: <code style="font-family: \'Geist Mono\', monospace;">{data_date}</code></span>'
            f'</div>'
            f'</div>'
        )
        render_html_safe(header_html)

        for s_idx, b in enumerate(setups):
            b_id = b.get("base_id", f"Setup #{s_idx + 1}")
            lifecycle = b.get("lifecycle_phase") or get_base_lifecycle(b)
            st_key = b.get("state", "none")
            bo_bars = b.get("breakout_bar_count", 0)

            badge_html = _get_badge_html(lifecycle, st_key, bo_bars)
            end_reason = b.get("end_reason")
            ended_at = b.get("ended_at")
            end_str = f"Ngày {ended_at} &middot; " if ended_at else ""
            end_html = f'<div style="font-size: 12px; color: #991B1B; background: #FEE2E2; border: 1px solid #FCA5A5; border-radius: 4px; padding: 5px 8px; margin-top: 6px;"><b>Đã kết thúc:</b> {end_str}<b>Nguyên nhân:</b> {end_reason}</div>' if end_reason else ''

            sub_card_html = f"""
            <div style="border-left: 3px solid #3B82F6; background: #F8FAFC; padding: 8px 12px; margin: 8px 0 4px 0; border-radius: 0 4px 4px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-family: 'Geist Mono', monospace; font-size: 12px; font-weight: 600; color: #334155;">Đợt nền: {b_id}</span>
                    <div>{badge_html}</div>
                </div>
                <div style="font-size: 12.5px; color: #374151; font-weight: 500;">{format_base_summary_line(b)}</div>
                {end_html}
            </div>
            """
            render_html_safe(sub_card_html)
            render_base_metrics_grid(b)

        # Build candidate object for detail dialog
        cand_obj = dict(cand_match) if cand_match else {
            "symbol": sym,
            "company_name": company,
            "sector": sector,
            "sub_industry": sub_ind,
            "close_price": price,
            "perf_1d": p1d or 0.0,
            "perf_5d": first_b.get("perf_5d", 0.0),
            "perf_20d": first_b.get("perf_20d", 0.0),
            "trigger_price": first_b.get("upper"),
            "invalidation_price": first_b.get("lower"),
            "status": "setup",
            "score": float(rs or 0.0),
            "setup_type": "Nền giá",
            "group_type": "base_building",
            "is_oneil_leader": is_oneil,
            "atr14": first_b.get("atr14"),
            "atr_pct": first_b.get("atr_pct"),
            "tv_url": f"https://www.tradingview.com/chart/?symbol={sym}&interval=D",
            "fa_flags": first_b.get("fa_flags"),
            "base_info": first_b
        }
        cand_obj["base_info"] = first_b

        # 3-Column Bento Section
        col_ta, col_fa, col_action = st.columns([4.6, 4.6, 2.8])

        with col_ta:
            st.markdown('<div class="editorial-label" style="margin-bottom: 8px;">Bằng chứng Kỹ thuật (TA)</div>', unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; line-height: 1.55; margin-bottom: 3px;'>&bull; Tổng số đợt nền được ghi nhận: <b>{len(setups)} đợt</b>.</div>", unsafe_allow_html=True)
            for s_i, sb in enumerate(setups[:3]):
                p_val = sb.get("upper")
                p_str = f"${p_val:.2f}" if p_val is not None else "N/A"
                st.markdown(f"<div style='font-size: 13px; color: #555555; margin-bottom: 2px;'>- Đợt {sb.get('base_id', f'#{s_i+1}')}: Pivot {p_str}, sâu {sb.get('width_pct', 0):.1f}% ({sb.get('lifecycle_phase', 'forming')})</div>", unsafe_allow_html=True)
            if is_oneil:
                st.markdown(f"<div style='font-size: 13px; color: #166534; background: #EDF3EC; border: 1px solid #D1E5D0; padding: 4px 8px; border-radius: 4px; margin-top: 5px;'>★ O'Neil Leader: Top 20% sức mạnh giá RS ({rs_str})</div>", unsafe_allow_html=True)

        with col_fa:
            fa_data = first_b.get("fa_flags") or (cand_match.get("fa_flags") if cand_match else None)
            _render_card_fa_column(sym=sym, fa_flags=fa_data, as_of=as_of, repo=repo)

        with col_action:
            fa_data = first_b.get("fa_flags") or (cand_match.get("fa_flags") if cand_match else None)
            _render_card_action_column(
                sym=sym,
                cand_obj=cand_obj,
                fa_flags=fa_data,
                as_of=as_of,
                repo=repo,
                key_suffix=key_suffix
            )

        # Technical details & history expander inside the card
        _render_technical_details_expander(first_b, sym=sym, as_of=as_of, repo=repo, key_suffix=key_suffix)


def _render_technical_details_expander(
    b: Dict[str, Any],
    sym: str,
    as_of: str = "",
    repo: Optional[MarketRadarRepository] = None,
    key_suffix: str = ""
):
    """Render technical expander with bounds, timeframe, checklist, and point-in-time setup history."""
    b_id = b.get("base_id", sym)
    with st.expander(f"🔍 Chi tiết kỹ thuật & Lịch sử nền: {sym} ({b_id})", expanded=False):
        c_left, c_right = st.columns(2)

        with c_left:
            st.markdown("<div style='font-size: 13px; font-weight: 600; color: #111111; margin-bottom: 4px;'>Cấu Trúc & Biên Độ:</div>", unsafe_allow_html=True)
            upper = b.get("upper")
            lower = b.get("lower")
            width = b.get("width_pct")
            er = b.get("efficiency_ratio")
            cshift = b.get("center_shift")
            win_start = b.get("window_start", "")
            win_end = b.get("window_end", "")
            detected_at = b.get("detected_at", "")

            st.caption(f"• Biên trên (Pivot): ${upper:.2f}" if upper is not None else "• Biên trên: N/A")
            st.caption(f"• Biên dưới: ${lower:.2f}" if lower is not None else "• Biên dưới: N/A")
            st.caption(f"• Độ rộng nền: {width:.1f}%" if width is not None else "• Độ rộng: N/A")
            st.caption(f"• Cửa sổ 20 phiên: {win_start} → {win_end}")
            st.caption(f"• Phát hiện ban đầu: {detected_at}")
            st.caption(f"• ER: {er:.3f}" if er is not None else "• ER: N/A")
            st.caption(f"• Center Shift: {cshift:.3f}" if cshift is not None else "• Center Shift: N/A")

        with c_right:
            st.markdown("<div style='font-size: 13px; font-weight: 600; color: #111111; margin-bottom: 4px;'>Breakout & Bối Cảnh:</div>", unsafe_allow_html=True)
            bo_date = b.get("breakout_date")
            bo_price = b.get("breakout_price")
            bo_count = b.get("breakout_bar_count", 0)
            consec_ma50 = b.get("consecutive_below_ma50", 0)
            ma50 = b.get("ma50")
            ma200 = b.get("ma200")
            t_ctx = b.get("trend_context", "Trung tính")

            st.caption(f"• Breakout: {bo_date} tại ${bo_price:.2f}" if bo_date and bo_price else "• Breakout: Chưa có")
            st.caption(f"• Số phiên sau breakout: {bo_count} phiên")
            st.caption(f"• Đóng cửa dưới MA50: {consec_ma50} phiên")
            st.caption(f"• Bối cảnh: {t_ctx}")
            st.caption(f"• MA50: ${ma50:.2f}" if ma50 else "• MA50: N/A")
            st.caption(f"• MA200: ${ma200:.2f}" if ma200 else "• MA200: N/A")

        # Checklist Table
        checks = b.get("checks", [])
        if checks:
            st.markdown("<div style='font-size: 13px; font-weight: 600; color: #111111; margin: 8px 0 4px 0;'>Checklist Tiêu Chuẩn Nền:</div>", unsafe_allow_html=True)
            for chk in checks:
                is_pass = chk.get("pass", False)
                icon = "✅ Đạt" if is_pass else "❌ Chưa đạt"
                color = "#16A34A" if is_pass else "#DC2626"
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #F5F5F5; padding: 4px 0; font-size: 12px;">
                        <div>
                            <span style="color: #2F3437; font-weight: 500;">{chk.get('name', '')}</span>
                            <span style="color: #9CA3AF; font-size: 11px; margin-left: 6px;">({chk.get('threshold', '')})</span>
                        </div>
                        <div>
                            <span style="font-weight: 600; margin-right: 8px;">{chk.get('value', '')}</span>
                            <span style="color: {color}; font-weight: 600;">{icon}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # Base History Table (via repo)
        if repo:
            try:
                ref_as_of = b.get("as_of") or as_of
                hist_records = repo.get_base_history_by_symbol(sym, as_of=ref_as_of)
                if hist_records:
                    st.markdown("<div style='font-size: 13px; font-weight: 600; color: #111111; margin: 10px 0 4px 0;'>Lịch Sử Các Nền Giá Của Mã:</div>", unsafe_allow_html=True)
                    hist_rows = []
                    for h in hist_records:
                        h_state = h.get("state", "none")
                        h_st_label = STATE_LABELS.get(h_state, (h_state,))[0]
                        hist_rows.append({
                            "Phát Hiện": h.get("detected_at", ""),
                            "Phiên Cuối": h.get("as_of", ""),
                            "Vòng Đời": h.get("lifecycle_phase", "forming"),
                            "Trạng Thái": h_st_label,
                            "Pivot ($)": f"${h.get('upper', 0):.2f}" if h.get("upper") else "-",
                            "Biên Dưới ($)": f"${h.get('lower', 0):.2f}" if h.get("lower") else "-",
                            "Breakout": h.get("breakout_date") or "-",
                            "Kết Thúc": h.get("ended_at") or "-",
                            "Lý Do Kết Thúc": h.get("end_reason") or "-"
                        })
                    st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)
            except Exception:
                pass

        # TradingView external link
        tv_link = f"https://www.tradingview.com/chart/?symbol={sym}&interval=D"
        st.link_button(f"Mở Biểu Đồ {sym} trên TradingView ↗", tv_link, use_container_width=True)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)


def _create_base_figure(df_bars: pd.DataFrame, base_info: Dict[str, Any]) -> go.Figure:
    """
    Generate candlestick chart highlighting the 20-bar base rectangle and frozen boundaries.
    Preserved as a private helper for test compatibility; not rendered in base watchlist UI.
    """
    df = df_bars.copy()
    col_map = {c: c.lower() for c in df.columns}
    df.rename(columns=col_map, inplace=True)
    df["date_dt"] = pd.to_datetime(df["date"])
    df.sort_values("date_dt", inplace=True)

    as_of = base_info.get("as_of")
    if as_of:
        as_of_dt = pd.to_datetime(as_of)
        df = df[df["date_dt"] <= as_of_dt]

    plot_df = df.tail(60).copy()
    plot_df["date_str"] = plot_df["date_dt"].dt.strftime("%Y-%m-%d")

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3]
    )

    fig.add_trace(
        go.Candlestick(
            x=plot_df["date_str"],
            open=plot_df["open"],
            high=plot_df["high"],
            low=plot_df["low"],
            close=plot_df["close"],
            increasing_line_color="#26A69A",
            decreasing_line_color="#EF5350",
            name="OHLC",
            showlegend=False
        ),
        row=1,
        col=1
    )

    upper = base_info.get("upper")
    lower = base_info.get("lower")
    win_start = base_info.get("window_start")
    win_end = base_info.get("window_end")

    if upper is not None and lower is not None:
        fig.add_hline(
            y=upper,
            line_dash="dash",
            line_color="#2563EB",
            line_width=1.5,
            annotation_text=f"Kháng cự biên trên: ${upper:.2f}",
            annotation_position="top left",
            row=1,
            col=1
        )
        fig.add_hline(
            y=lower,
            line_dash="dash",
            line_color="#DC2626",
            line_width=1.5,
            annotation_text=f"Hỗ trợ biên dưới: ${lower:.2f}",
            annotation_position="bottom left",
            row=1,
            col=1
        )

        if win_start and win_end:
            win_start_str = str(win_start).split("T")[0].split(" ")[0]
            win_end_str = str(win_end).split("T")[0].split(" ")[0]
            fig.add_vrect(
                x0=win_start_str,
                x1=win_end_str,
                fillcolor="rgba(37, 99, 235, 0.08)",
                layer="below",
                line_width=1,
                line_color="rgba(37, 99, 235, 0.3)",
                annotation_text="Vùng nền 20 phiên",
                annotation_position="top right",
                row=1,
                col=1
            )

    colors = ["#26A69A" if c >= o else "#EF5350" for c, o in zip(plot_df["close"], plot_df["open"])]
    fig.add_trace(
        go.Bar(
            x=plot_df["date_str"],
            y=plot_df["volume"],
            marker_color=colors,
            name="Volume",
            showlegend=False
        ),
        row=2,
        col=1
    )

    vol_sma20 = plot_df["volume"].rolling(20, min_periods=1).mean()
    fig.add_trace(
        go.Scatter(
            x=plot_df["date_str"],
            y=vol_sma20,
            line=dict(color="#F59E0B", width=1.2),
            name="SMA20 Vol",
            showlegend=False
        ),
        row=2,
        col=1
    )

    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        height=400,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        xaxis_rangeslider_visible=False,
        hovermode="x unified"
    )
    fig.update_xaxes(showgrid=True, gridcolor="#F0F0F0", type="category")
    fig.update_yaxes(showgrid=True, gridcolor="#F0F0F0")

    return fig
