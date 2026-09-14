import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from typing import Any, Dict, Optional, List
from app.components.index_charts import render_major_indices_section

def _fmt_ret(val: Optional[float]) -> str:
    return f"{val:+.2f}%" if (val is not None and not pd.isna(val)) else "N/A"

def _fmt_diff(v1: Optional[float], v2: Optional[float]) -> str:
    return f"{v1 - v2:+.2f}% pts" if (v1 is not None and v2 is not None and not pd.isna(v1) and not pd.isna(v2)) else "N/A"

def render_html_safe(html_str: str):
    """Render HTML safely without markdown code block indentation issues."""
    if hasattr(st, "html"):
        st.html(html_str)
    else:
        import textwrap
        st.markdown(textwrap.dedent(html_str).strip(), unsafe_allow_html=True)

def render_contrast_bar_card(
    title_left: str,
    title_right: str,
    val_left_pct: float,
    val_left_count: int,
    val_right_pct: float,
    val_right_count: int,
    center_label: str = "",
    left_color: str = "#16A34A",
    right_color: str = "#DC2626"
) -> str:
    """Render a split horizontal comparison card with dual-colored progress bar (Light Theme)."""
    total_val = val_left_pct + val_right_pct
    if total_val > 0:
        bar_l = max(min((val_left_pct / total_val) * 100.0, 96.0), 4.0)
        bar_r = 100.0 - bar_l
    else:
        bar_l, bar_r = 50.0, 50.0

    center_html = f'<span style="color: #475569; font-family: \'Geist Mono\', monospace; font-size: 11.5px; font-weight: 600; background: #F1F5F9; border: 1px solid #E2E8F0; padding: 1px 6px; border-radius: 3px;">{center_label}</span>' if center_label else ""

    return (
        f'<div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 14px 16px; font-family: \'Geist\', \'Inter\', -apple-system, sans-serif; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; font-size: 13px; font-weight: 600;">'
        f'<span style="color: {left_color}; letter-spacing: 0.02em;">{title_left}</span>'
        f'{center_html}'
        f'<span style="color: {right_color}; letter-spacing: 0.02em;">{title_right}</span>'
        f'</div>'
        f'<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; font-family: \'Geist Mono\', monospace; font-size: 14.5px; font-weight: 600;">'
        f'<span style="color: #15803D;">{val_left_pct:.1f}% <span style="font-size: 12px; color: #64748B; font-weight: normal;">({val_left_count})</span></span>'
        f'<span style="color: #B91C1C;"><span style="font-size: 12px; color: #64748B; font-weight: normal;">({val_right_count})</span> {val_right_pct:.1f}%</span>'
        f'</div>'
        f'<div style="display: flex; width: 100%; height: 6px; background: #F1F5F9; border-radius: 3px; overflow: hidden; gap: 2px;">'
        f'<div style="width: {bar_l:.1f}%; background: {left_color}; height: 100%; border-radius: 2px 0 0 2px;"></div>'
        f'<div style="width: {bar_r:.1f}%; background: {right_color}; height: 100%; border-radius: 0 2px 2px 0;"></div>'
        f'</div>'
        f'</div>'
    )

def render_market_overview(
    market_metrics: Dict[str, Any],
    as_of: str,
    coverage_pct: float,
    total_universe: int,
    valid_universe: int,
    market_history: Optional[Dict[str, Any]] = None,
    snapshot_id: Optional[int] = None,
    repo: Optional[Any] = None
):
    """Render high-level market breadth, advance/decline, concentration, and historical participation metrics."""
    if not market_metrics:
        st.warning("Chưa có số liệu tổng quan thị trường.")
        return

    # 0. Major Market Indices (S&P 500, NASDAQ, DOW) [Image 1]
    render_major_indices_section()
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 1. Summary banner (Editorial minimalist block)
    summary_text = market_metrics.get("market_summary", "")
    divergence_text = market_metrics.get("concentration_divergence", "")
    methodology_ver = market_metrics.get("methodology_version", "v2.1")
    quality_flags = market_metrics.get("quality_flags", [])

    flags_html = ""
    if quality_flags:
        badges = " ".join(f'<span style="background: #FDEBEC; color: #9F2F2D; font-size: 12px; padding: 2px 7px; border-radius: 3px; font-family: \'Geist Mono\', monospace;">{f}</span>' for f in quality_flags)
        flags_html = f'<div style="margin-top: 8px; font-size: 13px; color: #787774;">Cảnh báo chất lượng: {badges}</div>'

    banner_html = (
        f'<div style="background-color: #FFFFFF; padding: 20px 24px; border: 1px solid #EAEAEA; border-left: 3px solid #111111; border-radius: 6px; margin-bottom: 20px;">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">'
        f'<div style="font-family: \'Geist\', \'Inter\', -apple-system, sans-serif; font-size: 21px; font-weight: 600; color: #111111; letter-spacing: -0.02em;">'
        f'Bức tranh thị trường S&P 500 &mdash; <span style="font-family: \'Geist Mono\', monospace; font-size: 15px; font-weight: normal; color: #787774;">As of {as_of}</span>'
        f'</div>'
        f'<span style="font-family: \'Geist Mono\', monospace; font-size: 12px; color: #787774; background: #F7F6F3; padding: 2px 7px; border-radius: 3px;">Methodology: {methodology_ver}</span>'
        f'</div>'
        f'<p style="margin: 0 0 10px 0; font-size: 15px; color: #2F3437; line-height: 1.65;">{summary_text}</p>'
        f'<div style="font-size: 13px; color: #787774; text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600;">'
        f'Mức độ tập trung đà tăng: <span style="text-transform: none; font-weight: 400; color: #2F3437; letter-spacing: normal;">{divergence_text}</span>'
        f'</div>'
        f'{flags_html}'
        f'</div>'
    )
    render_html_safe(banner_html)

    # 2. Key Contrast Bar Indicator Cards (5 Columns - Image 2 Style)
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        adv = int(market_metrics.get("advances", 0))
        dec = int(market_metrics.get("declines", 0))
        tot_ad = adv + dec
        adv_pct = round((adv / tot_ad) * 100.0, 1) if tot_ad > 0 else 0.0
        dec_pct = round((dec / tot_ad) * 100.0, 1) if tot_ad > 0 else 0.0
        card1_html = render_contrast_bar_card(
            title_left="Advancing",
            title_right="Declining",
            val_left_pct=adv_pct,
            val_left_count=adv,
            val_right_pct=dec_pct,
            val_right_count=dec
        )
        render_html_safe(card1_html)

    with c2:
        new_highs = int(market_metrics.get("near_20d_highs", market_metrics.get("new_20d_highs", 0)))
        new_lows = int(market_metrics.get("near_20d_lows", market_metrics.get("new_20d_lows", 0)))
        tot_hl = new_highs + new_lows
        highs_pct = round((new_highs / tot_hl) * 100.0, 1) if tot_hl > 0 else 0.0
        lows_pct = round((new_lows / tot_hl) * 100.0, 1) if tot_hl > 0 else 0.0
        card2_html = render_contrast_bar_card(
            title_left="New High",
            title_right="New Low",
            val_left_pct=highs_pct,
            val_left_count=new_highs,
            val_right_pct=lows_pct,
            val_right_count=new_lows
        )
        render_html_safe(card2_html)

    with c3:
        pct_ma50 = float(market_metrics.get("pct_above_ma50", 0.0) or 0.0)
        valid_50 = int(market_metrics.get("valid_ma50_count", valid_universe) or valid_universe)
        above_50 = int(round(valid_50 * (pct_ma50 / 100.0)))
        below_50 = max(valid_50 - above_50, 0)
        pct_below_50 = round(100.0 - pct_ma50, 1)
        card3_html = render_contrast_bar_card(
            title_left="Above",
            title_right="Below",
            val_left_pct=pct_ma50,
            val_left_count=above_50,
            val_right_pct=pct_below_50,
            val_right_count=below_50,
            center_label="SMA50"
        )
        render_html_safe(card3_html)

    with c4:
        pct_ma200 = float(market_metrics.get("pct_above_ma200", 0.0) or 0.0)
        valid_200 = int(market_metrics.get("valid_ma200_count", valid_universe) or valid_universe)
        above_200 = int(round(valid_200 * (pct_ma200 / 100.0)))
        below_200 = max(valid_200 - above_200, 0)
        pct_below_200 = round(100.0 - pct_ma200, 1)
        card4_html = render_contrast_bar_card(
            title_left="Above",
            title_right="Below",
            val_left_pct=pct_ma200,
            val_left_count=above_200,
            val_right_pct=pct_below_200,
            val_right_count=below_200,
            center_label="SMA200"
        )
        render_html_safe(card4_html)

    with c5:
        net_b = float(market_metrics.get("net_breadth", 0.0) or 0.0)
        net_pct = net_b * 100.0
        bull_ratio = int(round(min(max((net_b + 1.0) / 2.0 * 100.0, 0.0), 100.0)))
        bear_ratio = 100 - bull_ratio
        card5_html = (
            f'<div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 14px 16px; font-family: \'Geist\', \'Inter\', -apple-system, sans-serif; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; font-size: 13px; font-weight: 600;">'
            f'<span style="color: #64748B; text-transform: uppercase; letter-spacing: 0.03em;">Xung Lực (Net)</span>'
            f'<span style="background: #DCFCE7; color: #166534; border: 1px solid #BBF7D0; font-family: \'Geist Mono\', monospace; font-size: 11px; font-weight: 700; padding: 1px 6px; border-radius: 3px;">{bull_ratio}% BULL</span>'
            f'</div>'
            f'<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; font-family: \'Geist Mono\', monospace; font-size: 14.5px; font-weight: 600;">'
            f'<span style="color: {"#15803D" if net_pct >= 0 else "#B91C1C"}; font-weight: 700;">{net_pct:+.1f}% pts</span>'
            f'<span style="background: #FEE2E2; color: #991B1B; border: 1px solid #FECACA; font-family: \'Geist Mono\', monospace; font-size: 11px; font-weight: 700; padding: 1px 6px; border-radius: 3px;">{bear_ratio}% BEAR</span>'
            f'</div>'
            f'<div style="display: flex; width: 100%; height: 6px; background: #F1F5F9; border-radius: 3px; overflow: hidden; gap: 2px;">'
            f'<div style="width: {bull_ratio}%; background: #16A34A; height: 100%; border-radius: 2px 0 0 2px;"></div>'
            f'<div style="width: {bear_ratio}%; background: #DC2626; height: 100%; border-radius: 0 2px 2px 0;"></div>'
            f'</div>'
            f'</div>'
        )
        render_html_safe(card5_html)

    # 3. SPY vs RSP Benchmark Comparison Card
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="editorial-hero" style="font-size: 22px; margin-bottom: 4px;">So sánh SPY (Vốn hóa) vs RSP (Bình quân)</div>', unsafe_allow_html=True)
    st.markdown('<div class="editorial-sub" style="margin-bottom: 16px;">Đo lường mức độ đồng thuận của độ rộng thị trường giữa nhóm vốn hóa lớn (SPY) và toàn bộ 500 cổ phiếu (RSP).</div>', unsafe_allow_html=True)

    col_bench1, col_bench2 = st.columns([6, 5])

    with col_bench1:
        st.markdown('<div class="editorial-label" style="margin-bottom: 8px;">Hiệu suất & Chênh lệch (% pts)</div>', unsafe_allow_html=True)
        spy_1d = market_metrics.get('spy_1d')
        rsp_1d = market_metrics.get('rsp_1d')
        spy_5d = market_metrics.get('spy_5d')
        rsp_5d = market_metrics.get('rsp_5d')
        spy_20d = market_metrics.get('spy_20d')
        rsp_20d = market_metrics.get('rsp_20d')

        bench_df = pd.DataFrame([
            {
                "Chỉ số": "SPY (S&P 500 Cap-Weighted)",
                "1 Ngày": _fmt_ret(spy_1d),
                "1 Tuần (5D)": _fmt_ret(spy_5d),
                "1 Tháng (20D)": _fmt_ret(spy_20d)
            },
            {
                "Chỉ số": "RSP (S&P 500 Equal-Weighted)",
                "1 Ngày": _fmt_ret(rsp_1d),
                "1 Tuần (5D)": _fmt_ret(rsp_5d),
                "1 Tháng (20D)": _fmt_ret(rsp_20d)
            },
            {
                "Chỉ số": "Chênh lệch (SPY - RSP)",
                "1 Ngày": _fmt_diff(spy_1d, rsp_1d),
                "1 Tuần (5D)": _fmt_diff(spy_5d, rsp_5d),
                "1 Tháng (20D)": _fmt_diff(spy_20d, rsp_20d)
            }
        ])
        st.dataframe(bench_df, use_container_width=True, hide_index=True)

    with col_bench2:
        # Minimalist Gauge chart for Breadth
        gauge_val = pct_ma50 if pct_ma50 is not None else 0.0
        suffix_str = "%" if pct_ma50 is not None else "% (N/A)"
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=gauge_val,
            number={'suffix': suffix_str, 'font': {'size': 32, 'family': 'Geist Mono, monospace', 'color': '#111111'}},
            title={'text': "ĐỘ RỘNG THỊ TRƯỜNG (% TRÊN MA50)", 'font': {'size': 12.5, 'color': '#787774', 'family': 'Geist, Inter, sans-serif'}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#EAEAEA"},
                'bar': {'color': "#111111" if pct_ma50 is not None else "#BDBDBD", 'thickness': 0.25},
                'bgcolor': "#FFFFFF",
                'borderwidth': 1,
                'bordercolor': "#EAEAEA",
                'steps': [
                    {'range': [0, 40], 'color': "#FDEBEC"},    # Pale Red
                    {'range': [40, 60], 'color': "#FBF3DB"},   # Pale Yellow
                    {'range': [60, 100], 'color': "#EDF3EC"}   # Pale Green
                ],
                'threshold': {
                    'line': {'color': "#111111", 'width': 2},
                    'thickness': 0.7,
                    'value': 50.0
                }
            }
        ))
        fig.update_layout(
            height=200,
            margin=dict(l=20, r=20, t=30, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif")
        )
        st.plotly_chart(fig, use_container_width=True, key="chart_market_breadth_gauge")

    # 4. Historical Breadth & Participation Time-Series Charts [Step 2 & 5]
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="editorial-hero" style="font-size: 20px; margin-bottom: 4px;">Lịch sử Độ rộng & Thanh khoản (Time-Series Analytics)</div>', unsafe_allow_html=True)
    st.markdown('<div class="editorial-sub" style="margin-bottom: 16px;">Quan sát xu hướng dịch chuyển của thanh khoản giao dịch, đà tích lũy A/D Line và độ rộng MA qua các phiên giao dịch.</div>', unsafe_allow_html=True)

    if market_history and market_history.get("records"):
        hist_records = market_history["records"]
        df_hist = pd.DataFrame(hist_records)

        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 A/D Line & AD Volume Line",
            "📊 Tỷ lệ trên MA20 / MA50 / MA200",
            "⚖️ Net Breadth & AD Volume %",
            "🔄 So sánh Lợi suất (SPY vs RSP vs Trung vị)"
        ])

        with tab1:
            start_date = market_history.get("start_date", df_hist["date"].iloc[0])
            st.caption(f"A/D Line lũy kế tính từ ngày <b>{start_date}</b>. AD Volume Line là lũy kế (Khối lượng mã tăng - Khối lượng mã giảm).")

            fig_ad = go.Figure()
            fig_ad.add_trace(go.Scatter(
                x=df_hist["date"],
                y=df_hist["ad_line"],
                name="A/D Line (Lũy kế Net Advances)",
                line=dict(color="#111111", width=2.5),
                mode="lines"
            ))
            fig_ad.add_trace(go.Scatter(
                x=df_hist["date"],
                y=df_hist["ad_vol_line"],
                name="AD Volume Line",
                line=dict(color="#787774", width=1.5, dash="dot"),
                yaxis="y2",
                mode="lines"
            ))

            fig_ad.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(gridcolor="#EAEAEA", showgrid=True),
                yaxis=dict(title="A/D Line", gridcolor="#EAEAEA", showgrid=True),
                yaxis2=dict(title="AD Volume Line", overlaying="y", side="right", showgrid=False),
                font=dict(family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif")
            )
            st.plotly_chart(fig_ad, use_container_width=True, key="chart_ad_lines")
            st.caption("Ghi chú phương pháp: AD Volume là khối lượng của các mã tăng/giảm trong phiên, không phải dữ liệu mua/bán chủ động tick-level CVD.")

        with tab2:
            st.caption("Tỷ lệ phần trăm cổ phiếu đóng cửa trên đường MA20, MA50 và MA200 ngày. Mẫu số chỉ tính các mã đủ lịch sử nến tương ứng.")
            fig_ma = go.Figure()
            fig_ma.add_trace(go.Scatter(
                x=df_hist["date"],
                y=df_hist["pct_above_ma20"],
                name="% trên MA20 (Ngắn hạn)",
                line=dict(color="#1F6C9F", width=1.8),
                mode="lines"
            ))
            fig_ma.add_trace(go.Scatter(
                x=df_hist["date"],
                y=df_hist["pct_above_ma50"],
                name="% trên MA50 (Trung hạn)",
                line=dict(color="#346538", width=2.2),
                mode="lines"
            ))
            fig_ma.add_trace(go.Scatter(
                x=df_hist["date"],
                y=df_hist["pct_above_ma200"],
                name="% trên MA200 (Dài hạn)",
                line=dict(color="#956400", width=1.8),
                mode="lines"
            ))
            # 50% Threshold
            fig_ma.add_hline(y=50, line_dash="dash", line_color="#BDBDBD", line_width=1, annotation_text="Ngưỡng 50%", annotation_position="top right")

            fig_ma.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(gridcolor="#EAEAEA", showgrid=True),
                yaxis=dict(title="% Cổ phiếu", range=[0, 100], gridcolor="#EAEAEA", showgrid=True),
                font=dict(family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif")
            )
            st.plotly_chart(fig_ma, use_container_width=True, key="chart_ma_breadth_history")

        with tab3:
            st.caption("Net Breadth = (Số mã tăng - Số mã giảm) / Tổng số mã hợp lệ. AD Volume % = (Khối lượng tăng - Khối lượng giảm) / Tổng khối lượng A+D.")
            fig_net = go.Figure()
            df_hist["net_b_pct"] = df_hist["net_breadth"] * 100.0

            colors_nb = ["#346538" if x >= 0 else "#9F2F2D" for x in df_hist["net_b_pct"]]
            fig_net.add_trace(go.Bar(
                x=df_hist["date"],
                y=df_hist["net_b_pct"],
                name="Net Breadth (%)",
                marker_color=colors_nb
            ))
            fig_net.add_trace(go.Scatter(
                x=df_hist["date"],
                y=df_hist["ad_vol_pct"],
                name="AD Volume %",
                line=dict(color="#111111", width=1.5),
                mode="lines+markers",
                marker=dict(size=4)
            ))
            fig_net.add_hline(y=0, line_color="#111111", line_width=1)

            fig_net.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(gridcolor="#EAEAEA", showgrid=True),
                yaxis=dict(title="Biên độ (%)", gridcolor="#EAEAEA", showgrid=True),
                font=dict(family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif")
            )
            st.plotly_chart(fig_net, use_container_width=True, key="chart_net_breadth_bars")

        with tab4:
            st.caption("So sánh lợi suất 1 ngày giữa chỉ số vốn hóa (SPY), quỹ bình quân (RSP) và lợi suất trung vị của 500 cổ phiếu thành viên.")
            fig_ret = go.Figure()
            if "spy_return" in df_hist.columns:
                fig_ret.add_trace(go.Scatter(x=df_hist["date"], y=df_hist["spy_return"], name="SPY (Cap-Weighted)", line=dict(color="#111111", width=2)))
            if "rsp_return" in df_hist.columns:
                fig_ret.add_trace(go.Scatter(x=df_hist["date"], y=df_hist["rsp_return"], name="RSP (Equal-Weighted ETF)", line=dict(color="#1F6C9F", width=1.8, dash="dash")))
            if "median_return" in df_hist.columns:
                fig_ret.add_trace(go.Scatter(x=df_hist["date"], y=df_hist["median_return"], name="Trung vị 500 cổ phiếu", line=dict(color="#346538", width=1.8)))

            fig_ret.add_hline(y=0, line_color="#787774", line_width=0.8)
            fig_ret.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(gridcolor="#EAEAEA", showgrid=True),
                yaxis=dict(title="Lợi suất 1D (%)", gridcolor="#EAEAEA", showgrid=True),
                font=dict(family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif")
            )
            st.plotly_chart(fig_ret, use_container_width=True, key="chart_ret_comparison")

    else:
        st.info("Chưa tính chỉ số này (Snapshot cũ chưa có chuỗi lịch sử độ rộng & luân chuyển ngành).")
        if snapshot_id is not None and repo is not None:
            col_b1, col_b2 = st.columns([2, 3])
            with col_b1:
                if st.button("⚡ Tính toán bổ sung cho Snapshot này", key="btn_backfill_overview", help="Tính toán chuỗi độ rộng và luân chuyển ngành từ dữ liệu giá đã lưu trong database mà không cần tải lại dữ liệu."):
                    with st.spinner("Đang tính toán bổ sung chuỗi lịch sử độ rộng..."):
                        try:
                            from jobs.backfill_analytics import backfill_snapshot_analytics
                            ok = backfill_snapshot_analytics(snapshot_id=snapshot_id, repo=repo)
                            if ok:
                                st.success("Đã hoàn tất tính toán bổ sung!")
                                st.rerun()
                            else:
                                st.error("Không thể tính toán bổ sung do thiếu dữ liệu nến ngày.")
                        except Exception as ex:
                            st.error(f"Lỗi tính toán: {ex}")


