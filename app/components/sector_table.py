import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Any, Dict, List, Optional
from app.components.industry_heatmap import render_industry_heatmap
from config.sector_mappings import SECTOR_NAMES_VI

STATUS_COLORS = {
    "Dẫn đầu (Leading)": "background-color: #EDF3EC; color: #346538; font-weight: 600; padding: 2px 8px; border-radius: 9999px; font-size: 12.5px; font-family: 'Geist Mono', monospace;",
    "Đang cải thiện (Improving)": "background-color: #E1F3FE; color: #1F6C9F; font-weight: 600; padding: 2px 8px; border-radius: 9999px; font-size: 12.5px; font-family: 'Geist Mono', monospace;",
    "Suy yếu (Weakening)": "background-color: #FBF3DB; color: #956400; font-weight: 600; padding: 2px 8px; border-radius: 9999px; font-size: 12.5px; font-family: 'Geist Mono', monospace;",
    "Tụt hậu (Lagging)": "background-color: #FDEBEC; color: #9F2F2D; font-weight: 600; padding: 2px 8px; border-radius: 9999px; font-size: 12.5px; font-family: 'Geist Mono', monospace;",
    "Trung tính (Neutral)": "background-color: #F7F6F3; color: #787774; font-weight: 600; padding: 2px 8px; border-radius: 9999px; font-size: 12.5px; font-family: 'Geist Mono', monospace;",
    "Chưa xác minh (Thiếu SPY)": "background-color: #F7F6F3; color: #787774; font-weight: 600; padding: 2px 8px; border-radius: 9999px; font-size: 12.5px; font-family: 'Geist Mono', monospace;",
    "Chưa xác minh (Thiếu ETF)": "background-color: #F7F6F3; color: #787774; font-weight: 600; padding: 2px 8px; border-radius: 9999px; font-size: 12.5px; font-family: 'Geist Mono', monospace;",
    "Chưa xác minh (Dữ liệu cũ / Lệch phiên)": "background-color: #F7F6F3; color: #787774; font-weight: 600; padding: 2px 8px; border-radius: 9999px; font-size: 12.5px; font-family: 'Geist Mono', monospace;",
}

QUADRANT_PALETTE = {
    "Dẫn đầu (Leading)": "#346538",       # Forest green
    "Suy yếu (Weakening)": "#956400",     # Ochre yellow
    "Tụt hậu (Lagging)": "#9F2F2D",       # Brick red
    "Đang cải thiện (Improving)": "#1F6C9F", # Ocean blue
    "Trung tính (Neutral)": "#787774",    # Slate gray
}


def render_gics_sectors(
    sector_metrics: List[Dict[str, Any]],
    sector_rotation: Optional[Dict[str, Any]] = None,
    sector_health: Optional[List[Dict[str, Any]]] = None
):
    """
    Hiển thị phân tích 11 ngành GICS theo thứ tự chuẩn:
    1. Tóm tắt có số liệu (KPIs & Trạng thái phân bố)
    2. Luân chuyển sức mạnh tương đối (4 góc phần tư có đuôi lịch sử 10 phiên) & Ma trận bổ trợ
    3. Bảng so sánh sức khỏe ngành (RS, Lợi suất trung vị, Breadth, Thanh khoản, Tập trung)
    4. Chi tiết ngành được chọn (Top mã thanh khoản & Sub-industries)
    """
    if not sector_metrics:
        st.info("Chưa có dữ liệu 11 ngành GICS.")
        return

    # Map health and rotation by sector name
    health_map = {h["sector"]: h for h in (sector_health or [])}
    rotation_map = {r["sector"]: r for r in (sector_rotation.get("sectors", []) if sector_rotation else [])}

    st.markdown('<div class="editorial-hero" style="font-size: 26px; margin-bottom: 4px;">Phân Tích 11 Ngành GICS (S&P 500)</div>', unsafe_allow_html=True)
    st.markdown('<div class="editorial-sub" style="font-size: 14.5px;">Tách bạch <b>Luân chuyển sức mạnh tương đối so với SPY</b> khỏi <b>Sức khỏe nội tại và mức độ lan tỏa giao dịch / GTGD</b> của từng ngành.</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 1. TÓM TẮT CÓ SỐ LIỆU (KPI Summary)
    # -------------------------------------------------------------
    leading_cnt = sum(1 for s in sector_metrics if "Leading" in s.get("status", "") or "Dẫn đầu" in s.get("status", ""))
    improving_cnt = sum(1 for s in sector_metrics if "Improving" in s.get("status", "") or "cải thiện" in s.get("status", "").lower())
    weakening_cnt = sum(1 for s in sector_metrics if "Weakening" in s.get("status", "") or "Suy yếu" in s.get("status", ""))
    lagging_cnt = sum(1 for s in sector_metrics if "Lagging" in s.get("status", "") or "Tụt hậu" in s.get("status", ""))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ngành Dẫn đầu (Leading)", f"{leading_cnt} / 11", help="RS 1M & 3M dương và độ rộng MA50 >= 50%.")
    c2.metric("Ngành Đang cải thiện", f"{improving_cnt} / 11", help="RS ngắn hạn đang tăng tốc thoát đáy.")
    c3.metric("Ngành Suy yếu (Weakening)", f"{weakening_cnt} / 11", help="RS chững lại hoặc độ rộng nội bộ phân hóa.")
    c4.metric("Ngành Tụt hậu (Lagging)", f"{lagging_cnt} / 11", help="Yếu thế toàn diện so với benchmark SPY.")

    # High-level highlights banner
    divergent_sectors = [h for h in (sector_health or []) if h.get("is_divergent")]
    valid_turnover_secs = [h for h in (sector_health or []) if h.get("turnover_share_pct") is not None]
    top_turnover_sec = max(valid_turnover_secs, key=lambda h: h["turnover_share_pct"]) if valid_turnover_secs else None

    valid_breadth_secs = [s for s in (sector_metrics or []) if s.get("breadth_ma50_pct") is not None]
    best_breadth_sec = max(valid_breadth_secs, key=lambda s: s["breadth_ma50_pct"]) if valid_breadth_secs else None

    hl_parts = []
    if top_turnover_sec:
        hl_parts.append(f"Thanh khoản lớn nhất: <b>{top_turnover_sec['sector']}</b> ({top_turnover_sec['turnover_share_pct']:.1f}% S&P 500)")
    elif sector_health:
        hl_parts.append("Thanh khoản lớn nhất: <b>N/A</b>")

    if best_breadth_sec:
        hl_parts.append(f"Độ rộng tốt nhất: <b>{best_breadth_sec['sector']}</b> ({best_breadth_sec['breadth_ma50_pct']}% trên MA50)")
    else:
        hl_parts.append("Độ rộng tốt nhất: <b>N/A</b>")

    if divergent_sectors:
        hl_names = ", ".join(d["sector"] for d in divergent_sectors)
        hl_parts.append(f"<span style='color: #9F2F2D;'>Cảnh báo phân hóa đà tăng: <b>{hl_names}</b> (ETF tăng nhưng trung vị âm / độ rộng hẹp)</span>")

    if hl_parts:
        st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-left: 3px solid #111111; padding: 12px 18px; border-radius: 4px; margin: 12px 0 20px 0; font-size: 14px; line-height: 1.6; font-family: 'Geist', 'Inter', sans-serif;">
            {' &nbsp;&bull;&nbsp; '.join(hl_parts)}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 2. LUÂN CHUYỂN SỨC MẠNH TƯƠNG ĐỐI (Relative Strength Rotation)
    # -------------------------------------------------------------
    st.markdown('<div class="editorial-hero" style="font-size: 22px; margin-bottom: 4px;">Luân Chuyển Sức Mạnh Tương Đối (Relative Strength Rotation)</div>', unsafe_allow_html=True)
    st.markdown('<div class="editorial-sub" style="font-size: 14px; margin-bottom: 12px;">Đo lường quỹ đạo vận động 4 góc phần tư của ETF ngành so với SPY, kèm vệt động lượng lịch sử.</div>', unsafe_allow_html=True)

    col_rot_left, col_rot_right = st.columns([7, 5])

    with col_rot_left:
        if sector_rotation and sector_rotation.get("sectors"):
            rot_sectors = sector_rotation["sectors"]
            all_etf_options = [s["etf"] for s in rot_sectors if s.get("etf")]

            # Display Controls
            c_ctrl1, c_ctrl2 = st.columns([1, 1])
            with c_ctrl1:
                trail_mode = st.selectbox(
                    "Độ dài đuôi lịch sử:",
                    options=["5 phiên gần nhất (Gọn gàng)", "10 phiên (Đầy đủ)", "Tắt đuôi (Chỉ hiện vị trí hiện tại)"],
                    index=0,
                    key="rot_trail_mode"
                )
            with c_ctrl2:
                selected_etfs = st.multiselect(
                    "Lọc ngành hiển thị:",
                    options=all_etf_options,
                    default=[],
                    placeholder="Tất cả 11 ngành",
                    key="rot_sector_filter"
                )

            # Map trail length
            if "Tắt đuôi" in trail_mode:
                trail_len = 0
            elif "10 phiên" in trail_mode:
                trail_len = 10
            else:
                trail_len = 5

            active_etfs = set(selected_etfs) if selected_etfs else set(all_etf_options)

            fig_rot = go.Figure()

            # Filter valid sectors for coordinates
            valid_sectors = [s for s in rot_sectors if s.get("current_x") is not None and s.get("current_y") is not None]
            display_sectors = [s for s in valid_sectors if s["etf"] in active_etfs]

            # Quadrant boundary guides (calculating range from all valid sectors to maintain stable axes)
            all_x = [s["current_x"] for s in valid_sectors]
            all_y = [s["current_y"] for s in valid_sectors]
            for s in valid_sectors:
                for t in s.get("trail", [])[-10:]:
                    if t.get("x") is not None:
                        all_x.append(t["x"])
                    if t.get("y") is not None:
                        all_y.append(t["y"])
            max_x = max([abs(x) for x in all_x] + [3.0]) * 1.25
            max_y = max([abs(y) for y in all_y] + [1.5]) * 1.25

            # Background Quadrant Tinting
            fig_rot.add_shape(type="rect", x0=0, y0=0, x1=max_x, y1=max_y, fillcolor="rgba(52, 101, 56, 0.035)", line_width=0, layer="below")
            fig_rot.add_shape(type="rect", x0=-max_x, y0=0, x1=0, y1=max_y, fillcolor="rgba(31, 108, 159, 0.035)", line_width=0, layer="below")
            fig_rot.add_shape(type="rect", x0=-max_x, y0=-max_y, x1=0, y1=0, fillcolor="rgba(159, 47, 45, 0.035)", line_width=0, layer="below")
            fig_rot.add_shape(type="rect", x0=0, y0=-max_y, x1=max_x, y1=0, fillcolor="rgba(149, 100, 0, 0.035)", line_width=0, layer="below")

            # Historical Trails (if trail_len > 0)
            if trail_len > 0:
                for s in display_sectors:
                    trail = s.get("trail", [])
                    if len(trail) >= 2:
                        trail_sub = trail[-trail_len:]
                        tr_x = [t["x"] for t in trail_sub]
                        tr_y = [t["y"] for t in trail_sub]
                        color = QUADRANT_PALETTE.get(s.get("rotation_state"), "#787774")

                        # Smooth spline line trail
                        fig_rot.add_trace(go.Scatter(
                            x=tr_x,
                            y=tr_y,
                            mode="lines",
                            line=dict(color=color, width=1.8, shape="spline", smoothing=0.8),
                            opacity=0.45,
                            hoverinfo="skip",
                            showlegend=False
                        ))

                        # Progressive step dots showing direction of motion
                        if len(tr_x) > 2:
                            n_pts = len(tr_x) - 1
                            fig_rot.add_trace(go.Scatter(
                                x=tr_x[:-1],
                                y=tr_y[:-1],
                                mode="markers",
                                marker=dict(
                                    size=[3.0 + i * (5.5 / max(n_pts, 1)) for i in range(n_pts)],
                                    color=color,
                                    opacity=[0.18 + i * (0.35 / max(n_pts, 1)) for i in range(n_pts)]
                                ),
                                hoverinfo="skip",
                                showlegend=False
                            ))

            # Proximity collision avoidance for label positions
            pos_cycle = ["top center", "bottom center", "top right", "bottom left", "middle right", "middle left"]
            assigned_positions = {}
            for i, s in enumerate(display_sectors):
                cur_x, cur_y = s["current_x"], s["current_y"]
                has_close_neighbor = any(
                    other["etf"] != s["etf"] and
                    ((other["current_x"] - cur_x)**2 + (other["current_y"] - cur_y)**2)**0.5 < 0.4
                    for other in display_sectors
                )
                if has_close_neighbor:
                    assigned_positions[s["etf"]] = pos_cycle[i % len(pos_cycle)]
                else:
                    assigned_positions[s["etf"]] = "top center"

            # Current Markers
            for s in display_sectors:
                cur_x = s["current_x"]
                cur_y = s["current_y"]
                etf = s["etf"]
                sec = s["sector"]
                st_label = s.get("rotation_state", "")
                color = QUADRANT_PALETTE.get(st_label, "#111111")
                etf_ret = s.get("etf_20d", 0.0)
                spy_ret = s.get("spy_20d", 0.0)
                regime = s.get("regime", "")
                textpos = assigned_positions.get(etf, "top center")

                hover_text = (
                    f"<b>{sec} ({etf})</b><br>"
                    f"Trạng thái: <b>{st_label}</b><br>"
                    f"X (RS vs EMA20): {cur_x:+.2f}%<br>"
                    f"Y (Gia tốc 5D): {cur_y:+.2f}% pts<br>"
                    f"Hiệu suất ETF 1M: {etf_ret:+.2f}%<br>"
                    f"Hiệu suất SPY 1M: {spy_ret:+.2f}%<br>"
                    f"Bối cảnh: {regime}"
                )

                fig_rot.add_trace(go.Scatter(
                    x=[cur_x],
                    y=[cur_y],
                    mode="markers+text",
                    text=[etf],
                    textposition=textpos,
                    textfont=dict(size=12, family="'Geist Mono', monospace", color="#111111"),
                    marker=dict(size=11, color=color, line=dict(width=1.8, color="#111111")),
                    name=f"{etf} ({st_label})",
                    hovertext=hover_text,
                    hoverinfo="text",
                    showlegend=False
                ))

            # Add zero lines
            fig_rot.add_hline(y=0, line_color="#111111", line_width=1.2)
            fig_rot.add_vline(x=0, line_color="#111111", line_width=1.2)

            # Add corner quadrant annotations
            fig_rot.add_annotation(x=max_x*0.75, y=max_y*0.85, text="<b>DẪN ĐẦU (LEADING)</b><br><span style='font-size:11.5px; color:#346538;'>Mạnh & Gia tốc tăng</span>", showarrow=False, font=dict(size=11.5, family="'Geist', 'Inter', sans-serif", color="#346538"))
            fig_rot.add_annotation(x=max_x*0.75, y=-max_y*0.85, text="<b>SUY YẾU (WEAKENING)</b><br><span style='font-size:11.5px; color:#956400;'>Mạnh nhưng mất đà</span>", showarrow=False, font=dict(size=11.5, family="'Geist', 'Inter', sans-serif", color="#956400"))
            fig_rot.add_annotation(x=-max_x*0.75, y=-max_y*0.85, text="<b>TỤT HẬU (LAGGING)</b><br><span style='font-size:11.5px; color:#9F2F2D;'>Yếu & Mất đà</span>", showarrow=False, font=dict(size=11.5, family="'Geist', 'Inter', sans-serif", color="#9F2F2D"))
            fig_rot.add_annotation(x=-max_x*0.75, y=max_y*0.85, text="<b>CẢI THIỆN (IMPROVING)</b><br><span style='font-size:11.5px; color:#1F6C9F;'>Yếu nhưng đang phục hồi</span>", showarrow=False, font=dict(size=11.5, family="'Geist', 'Inter', sans-serif", color="#1F6C9F"))

            fig_rot.update_layout(
                height=450,
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#FFFFFF",
                xaxis=dict(
                    title=dict(text="X: Sức mạnh RS so với EMA20 (%)", font=dict(size=12, family="'Geist', 'Inter', sans-serif")),
                    range=[-max_x, max_x],
                    gridcolor="#EAEAEA",
                    zeroline=False,
                    tickfont=dict(size=11, family="'Geist Mono', monospace")
                ),
                yaxis=dict(
                    title=dict(text="Y: Gia tốc RS 5 phiên (X<sub>t</sub> - X<sub>t-5</sub>) (% pts)", font=dict(size=12, family="'Geist', 'Inter', sans-serif")),
                    range=[-max_y, max_y],
                    gridcolor="#EAEAEA",
                    zeroline=False,
                    tickfont=dict(size=11, family="'Geist Mono', monospace")
                ),
                font=dict(family="'Geist', 'Inter', sans-serif")
            )
            st.plotly_chart(fig_rot, use_container_width=True, key="chart_sector_rotation_quadrant")
            st.caption("Công thức: R = P_ETF / P_SPY; X = 100 * (R / EMA20(R) - 1); Y = X_t - X_{t-5}. Vệt đuôi thể hiện quỹ đạo vận động theo thời gian (đậm dần về phiên hiện tại). Heuristic độc lập của Market Radar, không phải bản quyền JdK RRG.")
        else:
            st.info("Chưa tính chỉ số này (Snapshot cũ chưa có chuỗi luân chuyển ngành).")

    with col_rot_right:
        # Auxiliary Matrix: Net Breadth 1D vs ETF 1D Return (Size by estimated turnover)
        st.markdown('<div class="editorial-label" style="font-size: 13px; margin-bottom: 6px;">Ma Trận Bổ Trợ: Độ Lan Tỏa & Phản Ứng Giá (1D)</div>', unsafe_allow_html=True)
        matrix_rows = []
        for s in sector_metrics:
            sec_name = s["sector"]
            h = health_map.get(sec_name, {})
            net_b = h.get("net_breadth")
            etf_1d_val = h.get("etf_1d") if h.get("etf_1d") is not None else s.get("etf_1d")
            med_1d_val = h.get("median_return_1d")
            t_share = h.get("turnover_share_pct")

            matrix_rows.append({
                "sector": sec_name,
                "etf": s["etf"],
                "status": s.get("status", "Unknown"),
                "net_breadth_pct": round(net_b * 100.0, 1) if net_b is not None else None,
                "etf_1d": round(etf_1d_val, 2) if etf_1d_val is not None else None,
                "median_1d": round(med_1d_val, 2) if med_1d_val is not None else None,
                "turnover_est": h.get("turnover_est"),
                "turnover_share": t_share,
                "top5_pct": h.get("top5_concentration_pct")
            })
        df_mat = pd.DataFrame(matrix_rows)
        # Drop rows where net_breadth_pct or etf_1d is missing to keep N/A without plotting fake (0,0) dots
        df_plot = df_mat.dropna(subset=["net_breadth_pct", "etf_1d"]).copy() if not df_mat.empty else pd.DataFrame()

        if not df_plot.empty:
            df_plot["bubble_size"] = df_plot["turnover_share"].apply(lambda v: max(float(v), 1.0) if pd.notna(v) else 1.0)

            fig_mat = px.scatter(
                df_plot,
                x="net_breadth_pct",
                y="etf_1d",
                size="bubble_size",
                color="status",
                text="etf",
                color_discrete_map={
                    "Dẫn đầu (Leading)": "#346538",
                    "Đang cải thiện (Improving)": "#1F6C9F",
                    "Suy yếu (Weakening)": "#956400",
                    "Tụt hậu (Lagging)": "#9F2F2D",
                    "Trung tính (Neutral)": "#787774",
                    "Chưa xác minh (Thiếu SPY)": "#787774",
                    "Chưa xác minh (Thiếu ETF)": "#787774",
                    "Chưa xác minh (Dữ liệu cũ / Lệch phiên)": "#787774",
                },
                labels={
                    "net_breadth_pct": "Net Breadth 1D (%)",
                    "etf_1d": "Lợi suất ETF 1D (%)",
                    "bubble_size": "Tỷ trọng GTGD (%)"
                }
            )
            fig_mat.add_hline(y=0, line_color="#BDBDBD", line_dash="dot", line_width=1)
            fig_mat.add_vline(x=0, line_color="#BDBDBD", line_dash="dot", line_width=1)
            fig_mat.update_traces(textposition='top center', textfont=dict(size=12, family="'Geist Mono', monospace"))
            fig_mat.update_layout(
                height=430,
                margin=dict(l=10, r=10, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#FFFFFF",
                showlegend=False,
                xaxis=dict(gridcolor="#EAEAEA", tickfont=dict(size=11, family="'Geist Mono', monospace")),
                yaxis=dict(gridcolor="#EAEAEA", tickfont=dict(size=11, family="'Geist Mono', monospace")),
                font=dict(family="'Geist', 'Inter', sans-serif")
            )
            st.plotly_chart(fig_mat, use_container_width=True, key="chart_aux_breadth_return_matrix")
            st.caption("Nhãn biểu đồ: 'Độ lan tỏa và phản ứng giá (1D)'. Đối chiếu Net Breadth 1D với Lợi suất ETF 1D cùng khung thời gian. Kích thước điểm theo tỷ trọng GTGD ước lượng.")

            missing_sectors = [r["sector"] for r in matrix_rows if r["net_breadth_pct"] is None or r["etf_1d"] is None]
            if missing_sectors:
                st.caption(f"Ngành thiếu dữ liệu 1D (giữ N/A, loại khỏi tọa độ phân tán): {', '.join(missing_sectors)}")
        else:
            st.info("Chưa có đủ dữ liệu độ lan tỏa và phản ứng giá 1D để hiển thị ma trận.")

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 3. BẢNG SO SÁNH SỨC KHỎE NGÀNH (Sector Health Comparison Table)
    # -------------------------------------------------------------
    st.markdown('<div class="editorial-hero" style="font-size: 22px; margin-bottom: 4px;">Bảng So Sánh Sức Khỏe & Thanh Khoản 11 Ngành</div>', unsafe_allow_html=True)
    st.markdown('<div class="editorial-sub" style="font-size: 14px; margin-bottom: 12px;">Đối chiếu lợi suất ETF, lợi suất trung vị thành viên, tỷ trọng thanh khoản và mức tập trung vốn hóa.</div>', unsafe_allow_html=True)

    has_health_data = bool(sector_health)
    has_rotation_data = bool(sector_rotation and sector_rotation.get("sectors"))

    table_rows = []
    for s in sector_metrics:
        sec_name = s["sector"]
        h = health_map.get(sec_name, {})
        rot = rotation_map.get(sec_name, {})

        rs_1m_str = f"{s['rs_1m']:+.2f}% pts" if s.get('rs_1m') is not None else "N/A"
        rs_3m_str = f"{s['rs_3m']:+.2f}% pts" if s.get('rs_3m') is not None else "N/A"
        etf_1m_val = s.get("etf_1m")
        etf_1m_str = f"{etf_1m_val:+.2f}%" if etf_1m_val is not None else "N/A"

        med_1m_val = h.get("median_return_1m")
        med_1m_str = f"{med_1m_val:+.2f}%" if med_1m_val is not None else "N/A"

        # Divergence tag
        top5_pct_val = h.get("top5_concentration_pct")
        if not has_health_data or not h:
            divergence_tag = "Chưa tính chỉ số này"
        elif h.get("is_divergent"):
            divergence_tag = "⚠️ Phân hóa lớn"
        elif top5_pct_val is not None and top5_pct_val > 60.0:
            divergence_tag = "⚡ Tập trung cao"
        else:
            divergence_tag = "Đồng thuận"

        # Rotation state
        if not has_rotation_data or not rot:
            rot_state = "Chưa tính chỉ số này"
        else:
            rot_state = rot.get("rotation_state", "N/A")

        # Estimated turnover in Billions / Millions USD
        if not has_health_data or not h:
            t_str = "Chưa tính"
            share_str = "N/A"
            top5_str = "N/A"
        else:
            t_est = h.get("turnover_est")
            if t_est is None:
                t_str = "N/A"
            elif t_est >= 1e9:
                t_str = f"${t_est/1e9:.2f}B"
            else:
                t_str = f"${t_est/1e6:.1f}M"

            share_val = h.get("turnover_share_pct")
            share_str = f"{share_val:.1f}%" if share_val is not None else "N/A"

            top5_val = h.get("top5_concentration_pct")
            top5_str = f"{top5_val:.1f}%" if top5_val is not None else "N/A"

        # Valid denominator note for breadth
        valid_50 = s.get("valid_ma50_count", 0)
        tot_mem = s.get("member_count", 0)
        b_50 = s.get("breadth_ma50_pct")
        breadth_display = f"{b_50}% ({valid_50}/{tot_mem})" if (b_50 is not None and valid_50 > 0) else f"N/A (0/{tot_mem})"

        b_20 = s.get("breadth_ma20_pct")
        b_20_display = f"{b_20}%" if b_20 is not None else "N/A"

        table_rows.append({
            "Hạng": s.get("rank", 0),
            "Ngành GICS": s["sector"],
            "ETF": s["etf"],
            "Luân chuyển (RS vs SPY)": rot_state,
            "RS 1M": rs_1m_str,
            "RS 3M": rs_3m_str,
            "Lợi suất ETF 1M": etf_1m_str,
            "Trung vị CP 1M": med_1m_str,
            "Trên MA50 (Đủ mẫu)": breadth_display,
            "Trên MA20": b_20_display,
            "GTGD Ước tính": t_str,
            "Tỷ trọng GTGD": share_str,
            "Tập trung Top 5": top5_str,
            "Đánh giá": divergence_tag
        })

    df_table = pd.DataFrame(table_rows)
    st.dataframe(df_table, use_container_width=True, hide_index=True)
    st.caption("Ghi chú: Cột 'Trên MA50 (Đủ mẫu)' hiển thị tỷ lệ % kèm số mã có dữ liệu MA50 hợp lệ trên tổng số thành viên. Mẫu số chỉ tính các mã đủ điều kiện, tránh làm méo mó độ rộng.")

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 4. CHI TIẾT NGÀNH ĐƯỢC CHỌN (Selected Sector Drill-down)
    # -------------------------------------------------------------
    st.markdown('<div class="editorial-hero" style="font-size: 22px; margin-bottom: 4px;">Chi Tiết Ngành Được Chọn & Cổ Phiếu Đóng Góp Thanh Khoản</div>', unsafe_allow_html=True)

    selected_sector = st.selectbox(
        "Chọn ngành để phân tích chuyên sâu:",
        options=[s["sector"] for s in sector_metrics],
        format_func=lambda x: f"{x} ({next((s['sector_vi'] for s in sector_metrics if s['sector'] == x), '')}) &middot; ETF: {next((s['etf'] for s in sector_metrics if s['sector'] == x), '')}"
    )

    chosen_sector_data = next((s for s in sector_metrics if s["sector"] == selected_sector), None)
    chosen_health = health_map.get(selected_sector, {})

    if chosen_sector_data:
        # General sector narrative & divergence alert
        st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-left: 3px solid #111111; padding: 14px 18px; border-radius: 4px; margin-bottom: 16px; font-size: 14.5px; line-height: 1.6; font-family: 'Geist', 'Inter', sans-serif;">
            <div><b>Đánh giá trạng thái:</b> {chosen_sector_data['status_desc']}</div>
            <div style="margin-top: 6px; color: #787774;"><b>Cơ cấu thanh khoản & phân kỳ:</b> {chosen_health.get('divergence_desc', 'Chưa có thông tin phân kỳ.')}</div>
        </div>
        """, unsafe_allow_html=True)

        tab_sec1, tab_sec2 = st.tabs([
            "🏆 Top 5 Cổ Phiếu Đóng Góp Thanh Khoản Lớn Nhất",
            "🏢 Chi Tiết Nhóm Ngành Nhỏ (Sub-Industries)"
        ])

        with tab_sec1:
            top5 = chosen_health.get("top5_stocks", [])
            if top5:
                top5_rows = []
                for stk in top5:
                    sym = stk["symbol"]
                    tv_link = f"https://www.tradingview.com/chart/?symbol={sym}&interval=D"
                    t_val = stk.get("turnover_est")
                    if t_val is None:
                        t_val_str = "N/A"
                    elif t_val >= 1e9:
                        t_val_str = f"${t_val/1e9:.2f}B"
                    else:
                        t_val_str = f"${t_val/1e6:.1f}M"

                    close_val = stk.get("close")
                    close_str = f"${close_val:.2f}" if close_val is not None else "N/A"
                    vol_val = stk.get("volume")
                    vol_str = f"{int(vol_val):,}" if vol_val is not None else "N/A"
                    share_val = stk.get("share_in_sector")
                    share_str = f"{share_val:.1f}%" if share_val is not None else "N/A"
                    p1d_str = f"{stk['perf_1d']:+.2f}%" if stk.get('perf_1d') is not None else "N/A"
                    p20d_str = f"{stk['perf_20d']:+.2f}%" if stk.get('perf_20d') is not None else "N/A"

                    top5_rows.append({
                        "Mã": sym,
                        "Doanh nghiệp": stk.get("security", sym),
                        "Giá đóng cửa": close_str,
                        "Khối lượng": vol_str,
                        "GTGD Ước tính": t_val_str,
                        "Tỷ trọng trong ngành": share_str,
                        "Lợi suất 1D": p1d_str,
                        "Lợi suất 1M": p20d_str,
                        "Biểu đồ": tv_link
                    })
                df_top5 = pd.DataFrame(top5_rows)
                st.dataframe(
                    df_top5,
                    column_config={"Biểu đồ": st.column_config.LinkColumn("TradingView", display_text="Mở TV")},
                    use_container_width=True,
                    hide_index=True
                )
                st.caption("Cơ sở tính toán: GTGD ước lượng = Giá đóng cửa điều chỉnh * Khối lượng phiên. Dữ liệu mang tính tham chiếu thanh khoản tương đối, không phải số liệu khớp lệnh thực tế từ tape.")
            else:
                st.write("Chưa có danh sách top mã thanh khoản cho ngành này.")

        with tab_sec2:
            sub_inds = chosen_sector_data.get("sub_industries", [])
            if sub_inds:
                sub_df = pd.DataFrame([
                    {
                        "Nhóm ngành nhỏ (Sub-Industry)": sub["sub_industry"],
                        "Số lượng mã": f"{sub['count']}*" if sub.get("is_small_sample") else str(sub["count"]),
                        "Lợi suất TB (1M)": f"{sub['avg_perf_20d']:+.2f}%",
                        "Lợi suất Trung vị (1M)": f"{sub.get('median_perf_20d', sub['avg_perf_20d']):+.2f}%",
                        "Mã dẫn đầu": sub["top_stock"],
                        "Hiệu suất mã tốt nhất (1M)": f"{sub['top_stock_perf']:+.2f}%"
                    }
                    for sub in sub_inds
                ])
                st.dataframe(sub_df, use_container_width=True, hide_index=True)
                st.caption("*: Nhóm ngành nhỏ có mẫu nhỏ (≤ 2 mã trong S&P 500). Đối chiếu lợi suất trung vị để tránh méo mó do một cổ phiếu cá biệt.")
            else:
                st.write("Không có dữ liệu nhóm ngành nhỏ cho ngành này.")


def render_sector_section(
    sector_metrics: List[Dict[str, Any]],
    industry_metrics: Optional[List[Dict[str, Any]]] = None,
    view_mode: Optional[str] = None,
    sector_rotation: Optional[Dict[str, Any]] = None,
    sector_health: Optional[List[Dict[str, Any]]] = None
):
    """Render Sector rankings, Relative Strength rotation, Sub-industry breakdown, and O'Neil Heatmap."""
    if not sector_metrics and not industry_metrics:
        st.warning("Chưa có dữ liệu xếp hạng ngành.")
        return

    if view_mode == "macro":
        render_gics_sectors(
            sector_metrics or [],
            sector_rotation=sector_rotation,
            sector_health=sector_health
        )
        return
    elif view_mode == "heatmap":
        render_industry_heatmap(industry_metrics or [])
        return

    # Fallback to internal segmented control if view_mode is not explicitly specified
    sector_sub_keys = ["macro", "heatmap"]
    sector_sub_labels = {
        "macro": "11 Ngành GICS (Luân Chuyển Sức Mạnh & Sức Khỏe Ngành)",
        "heatmap": "Ma trận 127 Nhóm Ngành & Cổ Phiếu Dẫn Đầu (CANSLIM / O'Neil)"
    }

    selected_sec_sub = st.segmented_control(
        "Phân mục Ngành",
        options=sector_sub_keys,
        format_func=lambda k: sector_sub_labels[k],
        default="macro",
        label_visibility="collapsed",
        key="sector_sub_nav"
    ) if hasattr(st, "segmented_control") else st.radio(
        "Phân mục Ngành",
        options=sector_sub_keys,
        format_func=lambda k: sector_sub_labels[k],
        horizontal=True,
        label_visibility="collapsed",
        key="sector_sub_nav"
    )
    if not selected_sec_sub:
        selected_sec_sub = "macro"

    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)

    if selected_sec_sub == "macro":
        render_gics_sectors(
            sector_metrics or [],
            sector_rotation=sector_rotation,
            sector_health=sector_health
        )
    elif selected_sec_sub == "heatmap":
        render_industry_heatmap(industry_metrics or [])
