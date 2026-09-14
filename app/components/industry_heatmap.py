import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Optional

def _get_rank_cell_style(val: Optional[int]) -> str:
    """Return CSS styling for percentile rank cells (1 - 99) in muted pastel minimalist palette."""
    base = "text-align: center; border-radius: 3px; padding: 4px 6px; font-family: 'Geist Mono', monospace; font-size: 13px; "
    if val is None or pd.isna(val):
        return base + "background-color: #F7F6F3; color: #BDBDBD;"
    if val >= 90:
        # Muted Pale Green (High Leader)
        return base + "background-color: #EDF3EC; color: #346538; font-weight: 600; border: 1px solid #D1E5D0;"
    elif val >= 70:
        # Soft Green
        return base + "background-color: #F3F8F3; color: #487D4C; font-weight: 500;"
    elif val >= 40:
        # Neutral Slate/Bone
        return base + "background-color: #F7F6F3; color: #787774;"
    else:
        # Muted Pale Red (Lagging)
        return base + "background-color: #FDEBEC; color: #9F2F2D; font-weight: 600; border: 1px solid #F5D2D4;"

def _render_stock_pills(stocks: List[Dict[str, Any]], limit: int = 5) -> str:
    """Generate HTML inline pills for leading stocks with TradingView links."""
    if not stocks:
        return "<span style='color: #BDBDBD; font-size: 12px;'>Không có mã</span>"

    displayed_stocks = stocks[:limit] if limit > 0 else stocks
    pills_html = []

    for s in displayed_stocks:
        sym = s["symbol"]
        perf = s.get("perf_1d", 0.0)
        tv_url = s.get("tv_url") or f"https://www.tradingview.com/chart/?symbol={sym}&interval=D"
        if "interval=" not in tv_url:
            tv_url = f"{tv_url}{'&' if '?' in tv_url else '?'}interval=D"
        rs = s.get("rs_rating", 50)

        perf_str = f"{perf:+.1f}%"
        if perf > 0:
            bg_color = "#EDF3EC"
            text_color = "#346538"
            border_color = "#D1E5D0"
        elif perf < 0:
            bg_color = "#FDEBEC"
            text_color = "#9F2F2D"
            border_color = "#F5D2D4"
        else:
            bg_color = "#F7F6F3"
            text_color = "#787774"
            border_color = "#EAEAEA"

        pill = (
            f"<a href='{tv_url}' target='_blank' title='{s.get('security', sym)} | RS Rating: {rs}' "
            f"style='background-color: {bg_color}; color: {text_color}; border: 1px solid {border_color}; "
            f"border-radius: 4px; padding: 2.5px 7px; margin: 2px 3px 2px 0; text-decoration: none; "
            f"display: inline-block; font-size: 12.5px; font-family: \"Geist Mono\", monospace; white-space: nowrap;'>"
            f"<strong>{sym}</strong> <span style='font-size: 11.5px;'>{perf_str}</span></a>"
        )
        pills_html.append(pill)

    if limit > 0 and len(stocks) > limit:
        pills_html.append(f"<span style='color: #787774; font-size: 12px; margin-left: 4px;'>+{len(stocks) - limit} mã</span>")

    return "".join(pills_html)

def render_industry_heatmap(industry_metrics: List[Dict[str, Any]]):
    """
    Render William O'Neil CANSLIM Industry Groups Ranking Matrix & Heatmap.
    Styled according to the Utilitarian Minimalism & Editorial protocol.
    """
    if not industry_metrics:
        st.info("Chưa có dữ liệu xếp hạng nhóm ngành trong snapshot này. Vui lòng nhấn 'Cập nhật dữ liệu ngay' để tính toán.")
        return

    banner_html = (
        '<div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-left: 3px solid #111111; padding: 18px 22px; border-radius: 6px; margin-bottom: 20px;">'
        '<div style="font-family: \'Geist\', \'Inter\', sans-serif; font-size: 22px; font-weight: 700; color: #111111; margin-bottom: 6px; letter-spacing: -0.01em;">'
        'Ma trận Xếp hạng Nhóm ngành & Cổ phiếu Dẫn đầu (CANSLIM / O\'Neil Architecture)'
        '</div>'
        '<div style="font-size: 14.5px; color: #64748B; line-height: 1.6; font-family: \'Geist\', \'Inter\', sans-serif;">'
        'Đo lường sức mạnh giá đa khung thời gian trên 127 nhóm ngành GICS S&P 500. '
        'Xếp hạng Percentile từ <b>1</b> (yếu nhất) đến <b>99</b> (mạnh nhất). '
        'Cột 1Y hiển thị <em>N/A</em> nếu lịch sử niêm yết chưa đủ 253 phiên đóng cửa.'
        '</div>'
        '</div>'
    )
    if hasattr(st, "html"):
        st.html(banner_html)
    else:
        st.markdown(banner_html, unsafe_allow_html=True)

    # 1. Summary KPI Metrics
    total_groups = len(industry_metrics)
    leading_groups = [g for g in industry_metrics if g.get("is_leading", False)]
    top_group = industry_metrics[0] if industry_metrics else {}

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tổng số nhóm ngành", total_groups)
    col2.metric("Nhóm ngành Dẫn dắt (COMP ≥ 80)", f"{len(leading_groups)} ({len(leading_groups)/total_groups*100:.0f}%)")
    col3.metric("Nhóm quán quân (#1 COMP)", f"{top_group.get('industry', 'N/A')[:22]}", f"COMP: {top_group.get('comp_score', 0)}")
    
    # Biggest weekly mover
    best_wk_mover = max(industry_metrics, key=lambda x: (x.get("wk_rank") or 0)) if industry_metrics else {}
    col4.metric("Bứt phá 1 tuần mạnh nhất", f"{best_wk_mover.get('industry', 'N/A')[:22]}", f"WK: {best_wk_mover.get('wk_rank', 'N/A')}")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Controls & Filters
    fc1, fc2, fc3, fc4 = st.columns([2, 1.5, 1.5, 1])

    with fc1:
        search_query = st.text_input("Tìm kiếm nhóm ngành:", placeholder="Nhập tên ngành: Oil, Software, Hardware...").strip().lower()

    with fc2:
        sectors_list = ["Tất cả Sector"] + sorted(list(set(g.get("parent_sector", "") for g in industry_metrics if g.get("parent_sector"))))
        selected_sector = st.selectbox("Lọc theo Sector cha:", sectors_list)

    with fc3:
        sort_by = st.selectbox(
            "Sắp xếp theo:",
            options=["COMP (Tổng hợp)", "BLEND (Xu hướng)", "1W (1 Tuần)", "1M (1 Tháng)", "3M (1 Quý)", "6M (6 Tháng)", "1Y (1 Năm)", "DAY (Trong ngày)", "GTGD (Thanh khoản)"]
        )

    with fc4:
        limit_options = {"Top 5 mã": 5, "Top 10 mã": 10, "Tất cả mã": -1}
        stock_limit_label = st.selectbox("Số mã hiển thị:", list(limit_options.keys()))
        stock_limit = limit_options[stock_limit_label]

    only_leading = st.checkbox("Chỉ hiển thị Top 20% Nhóm ngành Dẫn đầu (COMP ≥ 80)", value=False)

    # Filter data
    filtered_data = industry_metrics.copy()

    if only_leading:
        filtered_data = [g for g in filtered_data if g.get("is_leading", False)]

    if selected_sector != "Tất cả Sector":
        filtered_data = [g for g in filtered_data if g.get("parent_sector") == selected_sector]

    if search_query:
        filtered_data = [
            g for g in filtered_data
            if search_query in g.get("industry", "").lower() or search_query in g.get("parent_sector", "").lower()
        ]

    # Sorting
    sort_key_map = {
        "COMP (Tổng hợp)": "comp_score",
        "BLEND (Xu hướng)": "blend_score",
        "1W (1 Tuần)": "wk_rank",
        "1M (1 Tháng)": "mth_rank",
        "3M (1 Quý)": "qtr_rank",
        "6M (6 Tháng)": "rank_6m",
        "1Y (1 Năm)": "rank_1y",
        "DAY (Trong ngày)": "day_rank",
        "GTGD (Thanh khoản)": "turnover_est"
    }
    sort_col = sort_key_map.get(sort_by, "comp_score")
    filtered_data.sort(key=lambda x: (x.get(sort_col) if x.get(sort_col) is not None and not pd.isna(x.get(sort_col)) else -1), reverse=True)

    st.caption(f"Hiển thị {len(filtered_data)} / {total_groups} nhóm ngành.")

    if not filtered_data:
        st.warning("Không tìm thấy nhóm ngành nào thỏa mãn điều kiện lọc.")
        return

    # View Mode Selector
    view_modes = ["Xếp hạng Sức mạnh Giá (COMP / BLEND)", "Độ rộng, Thanh khoản & Lợi suất Trung vị"]
    selected_view = st.segmented_control(
        "Góc nhìn Ma trận:",
        options=view_modes,
        default=view_modes[0],
        key="industry_heatmap_view_mode"
    ) if hasattr(st, "segmented_control") else st.radio(
        "Góc nhìn Ma trận:",
        options=view_modes,
        horizontal=True,
        key="industry_heatmap_view_mode"
    )

    # 3. Render HTML Heatmap Table in Editorial Monochrome
    html_rows = []

    if selected_view in ("Độ rộng, Thanh khoản & Lợi suất Trung vị", "Độ rộng & Lợi suất Trung vị"):
        for idx, g in enumerate(filtered_data):
            ind_name = g["industry"]
            stk_count = g["stk_count"]
            is_small = g.get("is_small_sample", False)
            stk_display = f"{stk_count}*" if is_small else str(stk_count)

            b_50 = g.get("breadth_ma50_pct")
            b_20 = g.get("breadth_ma20_pct")
            med_1m = g.get("median_perf_20d", g.get("perf_20d_median"))
            avg_1m = g.get("perf_20d")
            std_1m = g.get("perf_20d_std", 0.0)
            t_est = g.get("turnover_est")
            stocks_html = _render_stock_pills(g.get("stocks", []), limit=stock_limit)

            if b_50 is None or pd.isna(b_50):
                b_50_str = "N/A"
                b_50_style = "background-color: #F7F6F3; color: #BDBDBD;"
            else:
                b_50_str = f"{b_50:.1f}%"
                b_50_style = "background-color: #EDF3EC; color: #346538;" if b_50 >= 60.0 else ("background-color: #FDEBEC; color: #9F2F2D;" if b_50 < 40.0 else "background-color: #FBF3DB; color: #956400;")

            if b_20 is None or pd.isna(b_20):
                b_20_str = "N/A"
                b_20_style = "background-color: #F7F6F3; color: #BDBDBD;"
            else:
                b_20_str = f"{b_20:.1f}%"
                b_20_style = "background-color: #EDF3EC; color: #346538;" if b_20 >= 60.0 else ("background-color: #FDEBEC; color: #9F2F2D;" if b_20 < 40.0 else "background-color: #FBF3DB; color: #956400;")

            if t_est is None or pd.isna(t_est):
                t_str = "N/A"
            elif t_est >= 1e9:
                t_str = f"${t_est / 1e9:.2f}B"
            elif t_est >= 1e6:
                t_str = f"${t_est / 1e6:.1f}M"
            else:
                t_str = f"${t_est:,.0f}"

            med_str = f"{med_1m:+.2f}%" if med_1m is not None and not pd.isna(med_1m) else "N/A"
            avg_str = f"{avg_1m:+.2f}%" if avg_1m is not None and not pd.isna(avg_1m) else "N/A"
            std_str = f"{std_1m:.2f}%" if std_1m is not None and not pd.isna(std_1m) else "0.00%"

            row_bg = "#FFFFFF" if idx % 2 == 0 else "#FBFBFA"
            row_html = (
                f'<tr style="border-bottom: 1px solid #EAEAEA; background-color: {row_bg};">'
                f'<td style="padding: 8px 10px; font-weight: 500; color: #111111; white-space: nowrap; font-size: 13.5px; font-family: \'Geist\', \'Inter\', sans-serif;">{ind_name}</td>'
                f'<td style="padding: 8px 10px; text-align: center; color: {"#956400" if is_small else "#787774"}; font-family: \'Geist Mono\', monospace; font-size: 13px;">{stk_display}</td>'
                f'<td style="padding: 6px 6px; text-align: center;"><span style="padding: 3px 8px; border-radius: 3px; font-family: \'Geist Mono\', monospace; font-size: 12.5px; {b_50_style}">{b_50_str}</span></td>'
                f'<td style="padding: 6px 6px; text-align: center;"><span style="padding: 3px 8px; border-radius: 3px; font-family: \'Geist Mono\', monospace; font-size: 12.5px; {b_20_style}">{b_20_str}</span></td>'
                f'<td style="padding: 6px 8px; text-align: right; font-family: \'Geist Mono\', monospace; font-size: 13px; color: #111111; font-weight: 500;">{t_str}</td>'
                f'<td style="padding: 6px 8px; text-align: right; font-family: \'Geist Mono\', monospace; font-size: 13px; font-weight: 500;">{med_str}</td>'
                f'<td style="padding: 6px 8px; text-align: right; font-family: \'Geist Mono\', monospace; font-size: 13px; color: #787774;">{avg_str}</td>'
                f'<td style="padding: 6px 8px; text-align: right; font-family: \'Geist Mono\', monospace; font-size: 13px; color: #787774;">{std_str}</td>'
                f'<td style="padding: 8px 10px; min-width: 320px;">{stocks_html}</td>'
                f'</tr>'
            )
            html_rows.append(row_html)

        table_header = (
            '<tr style="background-color: #F7F6F3; border-bottom: 1px solid #EAEAEA; position: sticky; top: 0; z-index: 10;">'
            '<th style="padding: 10px 10px; text-align: left; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">INDUSTRY</th>'
            '<th style="padding: 10px 10px; text-align: center; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;"># STK</th>'
            '<th style="padding: 10px 6px; text-align: center; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">% TRÊN MA50</th>'
            '<th style="padding: 10px 6px; text-align: center; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">% TRÊN MA20</th>'
            '<th style="padding: 10px 8px; text-align: right; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">GTGD ƯỚC TÍNH</th>'
            '<th style="padding: 10px 8px; text-align: right; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">TRUNG VỊ 1M</th>'
            '<th style="padding: 10px 8px; text-align: right; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">TB 1M</th>'
            '<th style="padding: 10px 8px; text-align: right; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">ĐỘ PHÂN HÓA</th>'
            '<th style="padding: 10px 10px; text-align: left; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">STOCKS &middot; LEADING TICKERS (TRADINGVIEW)</th>'
            '</tr>'
        )

    else:
        for idx, g in enumerate(filtered_data):
            ind_name = g["industry"]
            stk_count = g["stk_count"]
            is_small = g.get("is_small_sample", False)
            stk_display = f"{stk_count}*" if is_small else str(stk_count)

            day_val = g.get("day_rank")
            wk_val = g.get("wk_rank")
            mth_val = g.get("mth_rank")
            qtr_val = g.get("qtr_rank")
            val_6m = g.get("rank_6m")
            val_1y = g.get("rank_1y")
            comp_val = g.get("comp_score")
            blend_val = g.get("blend_score")
            stocks_html = _render_stock_pills(g.get("stocks", []), limit=stock_limit)

            day_txt = str(day_val) if day_val is not None else "N/A"
            wk_txt = str(wk_val) if wk_val is not None else "N/A"
            mth_txt = str(mth_val) if mth_val is not None else "N/A"
            qtr_txt = str(qtr_val) if qtr_val is not None else "N/A"
            val_6m_txt = str(val_6m) if val_6m is not None else "N/A"
            val_1y_txt = str(val_1y) if val_1y is not None else "N/A"
            comp_txt = str(comp_val) if comp_val is not None else "N/A"
            blend_txt = str(blend_val) if blend_val is not None else "N/A"

            row_bg = "#FFFFFF" if idx % 2 == 0 else "#FBFBFA"
            row_html = (
                f'<tr style="border-bottom: 1px solid #EAEAEA; background-color: {row_bg};">'
                f'<td style="padding: 8px 10px; font-weight: 500; color: #111111; white-space: nowrap; font-size: 13.5px; font-family: \'Geist\', \'Inter\', sans-serif;">{ind_name}</td>'
                f'<td style="padding: 8px 10px; text-align: center; color: {"#956400" if is_small else "#787774"}; font-family: \'Geist Mono\', monospace; font-size: 13px;" title="{"Mẫu nhỏ: ≤2 mã" if is_small else ""}">{stk_display}</td>'
                f'<td style="padding: 6px 6px;"><div style="{_get_rank_cell_style(day_val)}">{day_txt}</div></td>'
                f'<td style="padding: 6px 6px;"><div style="{_get_rank_cell_style(wk_val)}">{wk_txt}</div></td>'
                f'<td style="padding: 6px 6px;"><div style="{_get_rank_cell_style(mth_val)}">{mth_txt}</div></td>'
                f'<td style="padding: 6px 6px;"><div style="{_get_rank_cell_style(qtr_val)}">{qtr_txt}</div></td>'
                f'<td style="padding: 6px 6px;"><div style="{_get_rank_cell_style(val_6m)}">{val_6m_txt}</div></td>'
                f'<td style="padding: 6px 6px;"><div style="{_get_rank_cell_style(val_1y)}">{val_1y_txt}</div></td>'
                f'<td style="padding: 6px 6px;"><div style="{_get_rank_cell_style(comp_val)}">{comp_txt}</div></td>'
                f'<td style="padding: 6px 6px;"><div style="{_get_rank_cell_style(blend_val)}">{blend_txt}</div></td>'
                f'<td style="padding: 8px 10px; min-width: 320px;">{stocks_html}</td>'
                f'</tr>'
            )
            html_rows.append(row_html)

        table_header = (
            '<tr style="background-color: #F7F6F3; border-bottom: 1px solid #EAEAEA; position: sticky; top: 0; z-index: 10;">'
            '<th style="padding: 10px 10px; text-align: left; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">INDUSTRY</th>'
            '<th style="padding: 10px 10px; text-align: center; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;"># STK</th>'
            '<th style="padding: 10px 6px; text-align: center; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">DAY</th>'
            '<th style="padding: 10px 6px; text-align: center; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">WK</th>'
            '<th style="padding: 10px 6px; text-align: center; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">MTH</th>'
            '<th style="padding: 10px 6px; text-align: center; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">QTR</th>'
            '<th style="padding: 10px 6px; text-align: center; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">6M</th>'
            '<th style="padding: 10px 6px; text-align: center; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">1Y</th>'
            '<th style="padding: 10px 6px; text-align: center; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">COMP</th>'
            '<th style="padding: 10px 6px; text-align: center; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">BLEND</th>'
            '<th style="padding: 10px 10px; text-align: left; color: #64748B; font-weight: 600; text-transform: uppercase; font-size: 11.5px; letter-spacing: 0.05em; font-family: \'Geist\', \'Inter\', sans-serif;">STOCKS &middot; LEADING TICKERS (TRADINGVIEW)</th>'
            '</tr>'
        )

    table_html = (
        '<div style="overflow-x: auto; max-height: 680px; border: 1px solid #EAEAEA; border-radius: 6px; margin-top: 10px; background: #FFFFFF;">'
        '<table style="width: 100%; border-collapse: collapse; font-family: \'Geist\', \'Inter\', -apple-system, sans-serif; font-size: 13.5px;">'
        '<thead>'
        f'{table_header}'
        '</thead>'
        f'<tbody>{"".join(html_rows)}</tbody>'
        '</table>'
        '</div>'
    )

    if hasattr(st, "html"):
        st.html(table_html)
    else:
        st.markdown(table_html, unsafe_allow_html=True)

    st.caption("*: Nhóm ngành có mẫu nhỏ (≤ 2 cổ phiếu trong S&P 500). Cột 1Y hiển thị N/A khi chưa đủ 253 phiên đóng cửa.")
