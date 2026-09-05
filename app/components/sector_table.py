import streamlit as st
import plotly.express as px
import pandas as pd
from typing import Any, Dict, List

STATUS_COLORS = {
    "Dẫn đầu (Leading)": "background-color: #c6f6d5; color: #22543d; font-weight: bold; padding: 4px 8px; border-radius: 4px;",
    "Đang cải thiện (Improving)": "background-color: #bee3f8; color: #2a4365; font-weight: bold; padding: 4px 8px; border-radius: 4px;",
    "Suy yếu (Weakening)": "background-color: #feebc8; color: #744210; font-weight: bold; padding: 4px 8px; border-radius: 4px;",
    "Tụt hậu (Lagging)": "background-color: #fed7d7; color: #742a2a; font-weight: bold; padding: 4px 8px; border-radius: 4px;",
}

def render_sector_section(sector_metrics: List[Dict[str, Any]]):
    """Render Sector rankings, RS comparison, and Sub-industry breakdown."""
    if not sector_metrics:
        st.warning("Chưa có dữ liệu xếp hạng ngành.")
        return

    st.subheader("🗺️ Xếp hạng 11 Ngành GICS (Relative Strength & Breadth)", divider="gray")

    # 1. Sector Bar Chart: Relative Strength vs SPY over 1M
    chart_data = []
    for s in sector_metrics:
        chart_data.append({
            "Ngành": f"{s['sector']} ({s['etf']})",
            "RS vs SPY (1M)": s["rs_1m"],
            "Trạng thái": s["status"],
            "Độ rộng MA50 (%)": s["breadth_ma50_pct"]
        })
    df_chart = pd.DataFrame(chart_data)

    fig = px.bar(
        df_chart,
        x="RS vs SPY (1M)",
        y="Ngành",
        color="Trạng thái",
        orientation="h",
        title="Sức mạnh tương đối (RS) 1 Tháng so với SPY",
        text_auto=True,
        color_discrete_map={
            "Dẫn đầu (Leading)": "#38a169",
            "Đang cải thiện (Improving)": "#3182ce",
            "Suy yếu (Weakening)": "#d69e2e",
            "Tụt hậu (Lagging)": "#e53e3e",
        }
    )
    fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'}, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # 2. Detailed Sector Table
    table_rows = []
    for s in sector_metrics:
        table_rows.append({
            "Hạng": s.get("rank", 0),
            "Ngành GICS": s["sector"],
            "Tên tiếng Việt": s["sector_vi"],
            "ETF": s["etf"],
            "1 Tuần": f"{s['etf_1w']:+.2f}%",
            "1 Tháng": f"{s['etf_1m']:+.2f}%",
            "3 Tháng": f"{s['etf_3m']:+.2f}%",
            "RS 1M vs SPY": f"{s['rs_1m']:+.2f}%",
            "RS 3M vs SPY": f"{s['rs_3m']:+.2f}%",
            "Độ rộng (Trên MA50)": f"{s['breadth_ma50_pct']}%",
            "Số mã": s["member_count"],
            "Trạng thái": s["status"]
        })
    df_table = pd.DataFrame(table_rows)
    st.dataframe(df_table, use_container_width=True, hide_index=True)

    # 3. Drill-down: Sub-industries breakdown
    st.subheader("🔍 Chi tiết Nhóm ngành nhỏ (Sub-Industry Breakdown)", divider="gray")
    selected_sector = st.selectbox(
        "Chọn ngành để xem nhóm ngành nhỏ:",
        options=[s["sector"] for s in sector_metrics],
        format_func=lambda x: f"{x} ({next((s['sector_vi'] for s in sector_metrics if s['sector'] == x), '')})"
    )

    chosen_sector_data = next((s for s in sector_metrics if s["sector"] == selected_sector), None)
    if chosen_sector_data:
        st.info(f"**Đánh giá:** {chosen_sector_data['status_desc']}")
        sub_inds = chosen_sector_data.get("sub_industries", [])
        if sub_inds:
            sub_df = pd.DataFrame([
                {
                    "Nhóm ngành nhỏ (Sub-Industry)": sub["sub_industry"],
                    "Số lượng mã": sub["count"],
                    "Lợi suất TB 1 Tháng": f"{sub['avg_perf_20d']:+.2f}%",
                    "Mã dẫn đầu": sub["top_stock"],
                    "Hiệu suất mã tốt nhất (1M)": f"{sub['top_stock_perf']:+.2f}%"
                }
                for sub in sub_inds
            ])
            st.dataframe(sub_df, use_container_width=True, hide_index=True)
        else:
            st.write("Không có dữ liệu nhóm ngành nhỏ cho ngành này.")
