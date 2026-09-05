import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
from datetime import datetime

from config.settings import APP_TITLE, RULE_VERSION
from storage.database import init_db
from storage.repository import MarketRadarRepository
from jobs.update_pipeline import run_update_pipeline
from app.components.metrics_cards import render_market_overview
from app.components.sector_table import render_sector_section
from app.components.candidate_cards import render_candidates_section

# Page config
st.set_page_config(
    page_title="Market Radar | S&P 500",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-title {
        font-size: 26px;
        font-weight: bold;
        color: #1a365d;
        margin-bottom: 4px;
    }
    .sub-title {
        font-size: 14px;
        color: #718096;
        margin-bottom: 20px;
    }
    .stButton>button {
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
init_db()
repo = MarketRadarRepository()

# Sidebar: Data Quality & Controls
st.sidebar.title("📡 Market Radar")
st.sidebar.caption(f"S&P 500 Top-Down Swing Radar ({RULE_VERSION})")

# Manual Update Button
if st.sidebar.button("🔄 Cập nhật dữ liệu ngay", use_container_width=True, type="primary"):
    with st.spinner("Đang tải dữ liệu S&P 500, ETF và tính toán lại toàn bộ chỉ số... Vui lòng đợi trong giây lát."):
        res = run_update_pipeline()
        if res.get("success"):
            st.sidebar.success(f"Hoàn thành! Snapshot #{res.get('snapshot_id')}")
            st.rerun()
        else:
            st.sidebar.error(res.get("message", "Lỗi cập nhật"))

# Snapshot Selection
snapshots_list = repo.get_snapshots_list(limit=20)
selected_snapshot = None

if snapshots_list:
    options = {
        f"Snapshot #{s['id']} ({s['as_of']}) - Phủ {s['coverage_pct']*100:.1f}%": s["id"]
        for s in snapshots_list
    }
    chosen_label = st.sidebar.selectbox("Lịch sử Snapshot:", list(options.keys()))
    selected_snapshot_id = options[chosen_label]
    selected_snapshot = repo.get_snapshot_by_id(selected_snapshot_id)
else:
    st.sidebar.info("Chưa có snapshot nào trong cơ sở dữ liệu. Nhấn 'Cập nhật dữ liệu ngay' để nạp lần đầu.")

# Sidebar Data Status
if selected_snapshot:
    as_of = selected_snapshot.get("as_of", "N/A")
    cov = selected_snapshot.get("coverage_pct", 0.0) * 100.0
    valid_u = selected_snapshot.get("valid_universe", 0)
    total_u = selected_snapshot.get("total_universe", 0)

    st.sidebar.divider()
    st.sidebar.markdown(f"""
    **📊 Trạng thái Dữ liệu:**
    - **Thời điểm (As of):** `{as_of}`
    - **Độ bao phủ:** `{valid_u}/{total_u}` (**{cov:.1f}%**)
    - **Nguồn:** Wikipedia + Yahoo Finance ($0)
    """)

    # Export Tickers Button
    candidates = repo.get_candidates_by_snapshot(selected_snapshot["id"])
    if candidates:
        tickers = [c["symbol"] for c in candidates]
        csv_data = pd.DataFrame(candidates)[["symbol", "company_name", "sector", "group_type", "status", "close_price", "perf_1d", "perf_5d", "perf_20d"]].to_csv(index=False)
        st.sidebar.download_button(
            label="📥 Xuất danh sách Ticker (CSV)",
            data=csv_data,
            file_name=f"market_radar_candidates_{as_of}.csv",
            mime="text/csv",
            use_container_width=True
        )

# Main Area
st.markdown('<div class="main-title">🎯 Market Radar — Bức tranh S&P 500 & Ứng viên Swing Trading</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Top-Down Analysis: Toàn thị trường → 11 Ngành GICS → Ứng viên giao dịch → Biểu đồ TradingView. Chi phí dữ liệu 0đ.</div>', unsafe_allow_html=True)

if not selected_snapshot:
    st.warning("⚠️ Cơ sở dữ liệu hiện chưa có dữ liệu. Vui lòng bấm nút **'🔄 Cập nhật dữ liệu ngay'** ở thanh bên trái để khởi chạy tiến trình nạp dữ liệu lần đầu.")
    st.stop()

# Extract snapshot data
market_metrics = selected_snapshot.get("market_metrics", {})
sector_metrics = selected_snapshot.get("sector_metrics", [])
current_snapshot_id = selected_snapshot["id"]
candidates = repo.get_candidates_by_snapshot(current_snapshot_id)

# Main Navigation Tabs
tab_market, tab_sectors, tab_candidates, tab_history, tab_quality = st.tabs([
    "📊 1. Tổng quan Thị trường",
    "🗺️ 2. Xếp hạng Ngành",
    f"🎯 3. Ứng viên Giao dịch ({len(candidates)})",
    "⏱️ 4. Biến động & Lịch sử",
    "🛡️ 5. Chất lượng Dữ liệu"
])

with tab_market:
    render_market_overview(
        market_metrics,
        as_of=selected_snapshot.get("as_of", ""),
        coverage_pct=selected_snapshot.get("coverage_pct", 0.0),
        total_universe=selected_snapshot.get("total_universe", 0),
        valid_universe=selected_snapshot.get("valid_universe", 0)
    )

with tab_sectors:
    render_sector_section(sector_metrics)

with tab_candidates:
    render_candidates_section(candidates)

with tab_history:
    st.subheader("⏱️ So sánh Biến động với Snapshot Liền Trước", divider="gray")
    # Find previous snapshot
    curr_idx = next((i for i, s in enumerate(snapshots_list) if s["id"] == current_snapshot_id), -1)
    if curr_idx != -1 and curr_idx + 1 < len(snapshots_list):
        prev_snap_id = snapshots_list[curr_idx + 1]["id"]
        prev_snap = repo.get_snapshot_by_id(prev_snap_id)
        diff = repo.get_snapshot_diff(current_snapshot_id, prev_snap_id)

        st.markdown(f"So sánh giữa Snapshot **#{current_snapshot_id}** (`{selected_snapshot['as_of']}`) và Snapshot **#{prev_snap_id}** (`{prev_snap['as_of']}`):")

        c1, c2, c3 = st.columns(3)
        c1.metric("Mã mới lọt danh sách", len(diff["added"]))
        c2.metric("Mã rời danh sách", len(diff["removed"]))
        c3.metric("Mã duy trì", len(diff["retained"]))

        if diff["added"]:
            st.markdown("##### 🟢 Cổ phiếu MỚI xuất hiện:")
            add_df = pd.DataFrame([{"Mã": a["symbol"], "Công ty": a["company_name"], "Nhóm": a["group_type"], "Giá": f"${a['close_price']:.2f}"} for a in diff["added"]])
            st.dataframe(add_df, use_container_width=True, hide_index=True)

        if diff["removed"]:
            st.markdown("##### 🔴 Cổ phiếu RỜI danh sách:")
            rem_df = pd.DataFrame([{"Mã": r["symbol"], "Công ty": r["company_name"], "Nhóm cũ": r["group_type"]} for r in diff["removed"]])
            st.dataframe(rem_df, use_container_width=True, hide_index=True)

        if diff["sector_moves"]:
            st.markdown("##### 🔄 Biến động Thứ hạng Ngành:")
            sec_df = pd.DataFrame([
                {
                    "Ngành": m["sector"],
                    "Hạng cũ": m["old_rank"],
                    "Hạng mới": m["new_rank"],
                    "Thay đổi": f"{m['change']:+d}" if m['change'] != 0 else "0"
                }
                for m in diff["sector_moves"]
            ])
            st.dataframe(sec_df, use_container_width=True, hide_index=True)
    else:
        st.info("Đây là snapshot duy nhất hoặc cũ nhất hiện có. Cần ít nhất 2 snapshot để hiển thị so sánh biến động.")

with tab_quality:
    st.subheader("🛡️ Giám sát Chất lượng & Nguồn Dữ liệu (Audit & Coverage)", divider="gray")
    q1, q2 = st.columns(2)
    with q1:
        st.markdown(f"""
        - **Quy tắc phiên bản:** `{selected_snapshot.get('rule_version')}`
        - **Thời điểm phân tích:** `{selected_snapshot.get('created_at')}`
        - **Ngày chốt dữ liệu (As of):** `{selected_snapshot.get('as_of')}`
        - **Tổng vũ trụ S&P 500:** `{selected_snapshot.get('total_universe')}` mã
        - **Số mã đủ nến & tính được chỉ báo:** `{selected_snapshot.get('valid_universe')}` mã
        - **Tỷ lệ bao phủ thực tế:** `{selected_snapshot.get('coverage_pct', 0)*100:.2f}%`
        """)
    with q2:
        missing = selected_snapshot.get("missing_symbols", [])
        st.markdown(f"**Số mã thiếu dữ liệu:** `{len(missing)}` mã")
        if missing:
            st.write("Danh sách mã thiếu hoặc không đủ lịch sử 200 ngày:")
            st.code(", ".join(missing))
        else:
            st.success("Tất cả các mã trong universe đều tải đủ dữ liệu!")

    st.divider()
    st.markdown("""
    **Nguyên tắc vận hành dữ liệu:**
    1. **Chi phí 0 đồng:** Không sử dụng API trả phí; sử dụng Wikipedia và Yahoo Finance công khai.
    2. **Xử lý ngoại lệ:** Mã thiếu dữ liệu bị loại trừ khỏi điểm số (không nhận điểm hợp lệ hoặc bị gán giá trị 0 giả).
    3. **Ngân hàng & Định chế tài chính:** Cơ cấu đòn bẩy và dòng tiền được gắn nhãn riêng, không áp dụng máy móc chỉ số nợ/dòng tiền phi tài chính.
    4. **Short:** Luôn gắn nhãn cảnh báo *'Chưa xác minh khả năng short / phí vay'* tại broker của người dùng.
    """)
