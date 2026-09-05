import streamlit as st
import plotly.graph_objects as go
from typing import Any, Dict

def render_market_overview(market_metrics: Dict[str, Any], as_of: str, coverage_pct: float, total_universe: int, valid_universe: int):
    """Render high-level market breadth, advance/decline, and concentration metrics."""
    if not market_metrics:
        st.warning("Chưa có số liệu tổng quan thị trường.")
        return

    # 1. Summary banner
    summary_text = market_metrics.get("market_summary", "")
    divergence_text = market_metrics.get("concentration_divergence", "")

    st.markdown(f"""
    <div style="background-color: #f0f4f8; padding: 16px 20px; border-radius: 8px; border-left: 5px solid #2b6cb0; margin-bottom: 20px;">
        <h4 style="margin: 0 0 8px 0; color: #1a365d;">📊 Bức tranh thị trường S&P 500 (Ngày dữ liệu: {as_of})</h4>
        <p style="margin: 0 0 6px 0; font-size: 15px; color: #2d3748; line-height: 1.5;">{summary_text}</p>
        <p style="margin: 0; font-size: 13px; color: #4a5568;"><b>Mức độ tập trung đà tăng:</b> {divergence_text}</p>
    </div>
    """, unsafe_allow_html=True)

    # 2. Key Metrics Columns
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        pct_ma50 = market_metrics.get("pct_above_ma50", 0.0)
        st.metric(
            label="Cổ phiếu trên MA50",
            value=f"{pct_ma50}%",
            delta=f"{market_metrics.get('pct_above_ma20', 0.0)}% trên MA20",
            help="Tỷ lệ cổ phiếu S&P 500 duy trì giá đóng cửa trên đường MA50 ngày."
        )

    with c2:
        pct_ma200 = market_metrics.get("pct_above_ma200", 0.0)
        st.metric(
            label="Cổ phiếu trên MA200",
            value=f"{pct_ma200}%",
            delta="Xu hướng dài hạn",
            help="Tỷ lệ cổ phiếu duy trì giá trên đường trung bình 200 ngày (cấu trúc Bull/Bear thị trường)."
        )

    with c3:
        adv = market_metrics.get("advances", 0)
        dec = market_metrics.get("declines", 0)
        ad_ratio = market_metrics.get("ad_ratio", 0.0)
        st.metric(
            label="Số mã Tăng / Giảm",
            value=f"{adv} / {dec}",
            delta=f"Tỷ lệ A/D: {ad_ratio}x",
            help="Số lượng mã cổ phiếu S&P 500 tăng giá so với giảm giá trong phiên gần nhất."
        )

    with c4:
        new_highs = market_metrics.get("new_20d_highs", 0)
        new_lows = market_metrics.get("new_20d_lows", 0)
        st.metric(
            label="Đỉnh / Đáy 20 phiên",
            value=f"{new_highs} / {new_lows}",
            delta=f"Net: {new_highs - new_lows:+d}",
            help="Số lượng cổ phiếu tiệm cận đỉnh 20 ngày so với thủng đáy 20 ngày."
        )

    # 3. SPY vs RSP Benchmark Comparison Card
    st.subheader("⚖️ So sánh SPY (Vốn hóa) vs RSP (Bình quân)", divider="gray")
    col_bench1, col_bench2 = st.columns(2)

    with col_bench1:
        st.markdown("**Hiệu suất gần đây**")
        bench_data = {
            "Chỉ số": ["SPY (S&P 500 Cap-Weighted)", "RSP (S&P 500 Equal-Weighted)", "Chênh lệch (SPY - RSP)"],
            "1 Ngày": [
                f"{market_metrics.get('spy_1d', 0):+.2f}%",
                f"{market_metrics.get('rsp_1d', 0):+.2f}%",
                f"{market_metrics.get('spy_1d', 0) - market_metrics.get('rsp_1d', 0):+.2f}%"
            ],
            "1 Tuần (5d)": [
                f"{market_metrics.get('spy_5d', 0):+.2f}%",
                f"{market_metrics.get('rsp_5d', 0):+.2f}%",
                f"{market_metrics.get('spy_5d', 0) - market_metrics.get('rsp_5d', 0):+.2f}%"
            ],
            "1 Tháng (20d)": [
                f"{market_metrics.get('spy_20d', 0):+.2f}%",
                f"{market_metrics.get('rsp_20d', 0):+.2f}%",
                f"{market_metrics.get('spy_20d', 0) - market_metrics.get('rsp_20d', 0):+.2f}%"
            ],
        }
        st.table(bench_data)

    with col_bench2:
        # Gauge chart for Breadth
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=pct_ma50,
            title={'text': "Độ rộng thị trường (% trên MA50)", 'font': {'size': 14}},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#2b6cb0"},
                'steps': [
                    {'range': [0, 40], 'color': "#fed7d7"},
                    {'range': [40, 60], 'color': "#feebc8"},
                    {'range': [60, 100], 'color': "#c6f6d5"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 3},
                    'thickness': 0.75,
                    'value': 50.0
                }
            }
        ))
        fig.update_layout(height=220, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)
