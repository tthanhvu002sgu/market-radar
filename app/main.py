import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
from config.settings import APP_TITLE, RULE_VERSION
from storage.database import init_db
from storage.repository import MarketRadarRepository
from jobs.update_pipeline import run_update_pipeline
from app.components.metrics_cards import render_market_overview
from app.components.sector_table import render_sector_section
from app.components.candidate_cards import render_candidates_section
from app.components.today_dashboard import render_today_dashboard
from app.components.setup_detail import render_setup_detail_modal
from app.components.signal_performance import render_signal_performance_section
from app.components.earnings_calendar import render_earnings_calendar_section
from app.components.base_watchlist import render_base_watchlist
from analytics.market_calendar import get_market_status_now, compute_session_age

# Page config
st.set_page_config(
    page_title="Market Radar | S&P 500",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Editorial Utilitarian Minimalism
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    /* Global typography */
    html, body, [class*="css"] {
        font-family: 'Geist', 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #2F3437;
        background-color: #FBFBFA;
        font-variant-numeric: tabular-nums;
        font-feature-settings: "cv02", "cv03", "cv04", "cv11", "tnum";
    }

    /* Editorial / Terminal headings */
    .editorial-hero {
        font-family: 'Geist', 'Inter', -apple-system, sans-serif;
        font-size: 34px;
        font-weight: 600;
        letter-spacing: -0.03em;
        line-height: 1.2;
        color: #111111;
        margin: 0 0 6px 0;
    }

    .editorial-sub {
        font-size: 15px;
        color: #787774;
        line-height: 1.6;
        margin: 0 0 24px 0;
        font-weight: 400;
    }

    .editorial-label {
        font-size: 12.5px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #787774;
        font-weight: 600;
    }

    /* Minimalist primary and secondary buttons */
    .stButton>button {
        border-radius: 4px !important;
        font-size: 14.5px !important;
        font-weight: 500 !important;
        padding: 7px 16px !important;
        transition: all 0.15s ease !important;
        box-shadow: none !important;
    }

    .stButton>button[kind="primary"] {
        background-color: #111111 !important;
        color: #FFFFFF !important;
        border: 1px solid #111111 !important;
    }

    .stButton>button[kind="primary"]:hover {
        background-color: #333333 !important;
        border-color: #333333 !important;
        transform: scale(0.99);
    }

    .stButton>button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #111111 !important;
        border: 1px solid #EAEAEA !important;
    }

    .stButton>button[kind="secondary"]:hover {
        background-color: #F7F6F3 !important;
        border-color: #D4D4D4 !important;
    }

    /* Minimalist tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #EAEAEA;
        padding-bottom: 4px;
        margin-bottom: 20px;
    }

    .stTabs [data-baseweb="tab"] {
        font-size: 14.5px;
        font-weight: 500;
        color: #787774;
        padding: 7px 14px;
        border-radius: 4px;
        background-color: transparent;
        border: none;
    }

    .stTabs [aria-selected="true"] {
        color: #111111 !important;
        background-color: #F7F6F3 !important;
        font-weight: 600 !important;
    }

    /* Minimalist Segmented Control (Resilient Top Navigation) */
    [data-testid="stSegmentedControl"] {
        gap: 4px;
        background-color: #F7F6F3;
        padding: 4px;
        border-radius: 6px;
        border: 1px solid #EAEAEA;
        margin-bottom: 24px;
        display: inline-flex;
        flex-wrap: wrap;
    }

    [data-testid="stSegmentedControl"] button {
        font-size: 14px !important;
        font-weight: 500 !important;
        color: #787774 !important;
        border: none !important;
        background-color: transparent !important;
        border-radius: 4px !important;
        padding: 7px 16px !important;
        transition: all 0.15s ease !important;
    }

    [data-testid="stSegmentedControl"] button:hover {
        color: #111111 !important;
        background-color: #EFEFEF !important;
    }

    [data-testid="stSegmentedControl"] button[aria-checked="true"] {
        color: #111111 !important;
        background-color: #FFFFFF !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    }

    /* Metric cards styling */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #EAEAEA;
        border-radius: 6px;
        padding: 14px 18px;
        box-shadow: none;
    }

    /* Container border wrapper styling (Light theme cards) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #EAEAEA !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 12.5px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: #787774 !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] {
        font-family: 'Geist Mono', 'SF Mono', monospace !important;
        font-size: 26px !important;
        font-weight: 600 !important;
        color: #111111 !important;
    }

    div[data-testid="stMetricDelta"] {
        font-family: 'Geist Mono', 'SF Mono', monospace !important;
        font-size: 13.5px !important;
    }

    /* Sidebar aesthetics */
    [data-testid="stSidebar"] {
        background-color: #F7F6F3;
        border-right: 1px solid #EAEAEA;
    }

    [data-testid="stSidebar"] .stSelectbox label {
        font-size: 12.5px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #787774;
        font-weight: 600;
    }

    /* Dividers */
    hr {
        border-color: #EAEAEA !important;
        margin: 20px 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
init_db()
repo = MarketRadarRepository()

# Sidebar: Data Quality & Controls
st.sidebar.markdown('<div class="editorial-hero" style="font-size: 20px; margin-bottom: 2px;">Market Radar</div>', unsafe_allow_html=True)
st.sidebar.markdown(f'<div class="editorial-label" style="margin-bottom: 16px;">S&P 500 Swing Architecture &middot; {RULE_VERSION}</div>', unsafe_allow_html=True)

# Manual Update Button
if st.sidebar.button("Cập nhật dữ liệu ngay", use_container_width=True, type="primary"):
    with st.spinner("Đang tải dữ liệu S&P 500, ETF và tính toán chỉ số..."):
        res = run_update_pipeline()
        if res.get("success"):
            st.sidebar.success(f"Hoàn thành. Snapshot #{res.get('snapshot_id')}")
            st.rerun()
        else:
            st.sidebar.error(res.get("message", "Lỗi cập nhật"))

# Snapshot Selection
snapshots_list = repo.get_snapshots_list(limit=20)
selected_snapshot = None

if snapshots_list:
    options = {
        f"#{s['id']} ({s['as_of']}) · Phủ {s['coverage_pct']*100:.1f}%": s["id"]
        for s in snapshots_list
    }
    chosen_label = st.sidebar.selectbox("Lịch sử Snapshot:", list(options.keys()))
    selected_snapshot_id = options[chosen_label]
    selected_snapshot = repo.get_snapshot_by_id(selected_snapshot_id)
else:
    st.sidebar.info("Chưa có snapshot nào trong cơ sở dữ liệu. Nhấn 'Cập nhật dữ liệu ngay' để nạp lần đầu.")

# Sidebar Data Status
is_invariant_violation = False
is_legacy = False
is_stale = False
session_age = None
as_of = ""
valid_u = 0
total_u = 0

if selected_snapshot:
    as_of = selected_snapshot.get("as_of", "N/A")
    cov = selected_snapshot.get("coverage_pct", 0.0) * 100.0
    cov_252 = selected_snapshot.get("coverage_252d", 0.0) * 100.0
    snap_status = selected_snapshot.get("status", "complete")
    valid_u = selected_snapshot.get("valid_universe", 0)
    total_u = selected_snapshot.get("total_universe", 0)

    # Invariant checks and freshness evaluation [R-04]
    is_invariant_violation = (total_u > 0 and valid_u > total_u)
    session_age = compute_session_age(as_of)
    is_stale = bool(session_age and (session_age.get("is_stale") or session_age.get("lag_sessions", 0) > 0 or not session_age.get("is_latest", True)))
    is_legacy = (snap_status in ("legacy", "legacy_incompatible") or is_invariant_violation or cov_252 < 0.5)

    # Determine overall status badge (FAIL CLOSED!)
    if is_invariant_violation:
        status_badge_html = '<span style="background-color: #FDEBEC; color: #9F2F2D; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Lỗi Bất Biến (Legacy)</span>'
        status_note = '<div style="color: #9F2F2D; font-size: 13px; margin-top: 5px; font-weight: 600;">⚠️ Vi phạm bất biến: Mã hợp lệ vượt tổng vũ trụ.</div>'
    elif is_legacy:
        status_badge_html = '<span style="background-color: #FEF3D6; color: #8F6B00; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Legacy Snapshot</span>'
        status_note = '<div style="color: #8F6B00; font-size: 13px; margin-top: 5px;">Snapshot cũ trước đợt nâng cấp schema.</div>'
    elif is_stale:
        lag = session_age.get("lag_sessions", 1)
        stale_color = "#9F2F2D" if lag > 1 else "#8F6B00"
        stale_bg = "#FDEBEC" if lag > 1 else "#FEF3D6"
        status_badge_html = f'<span style="background-color: {stale_bg}; color: {stale_color}; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Cũ ({lag} phiên)</span>'
        status_note = f'<div style="color: {stale_color}; font-size: 13px; margin-top: 5px;">Dữ liệu lịch sử (chậm {lag} phiên). Trạng thái nạp ban đầu: {snap_status}.</div>'
    elif snap_status == "complete":
        status_badge_html = '<span style="background-color: #EDF3EC; color: #346538; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Complete (Đồng phiên)</span>'
        status_note = '<div style="color: #346538; font-size: 13px; margin-top: 5px;">Đồng phiên và đạt chuẩn kiểm tra.</div>'
    else:
        status_badge_html = '<span style="background-color: #FDEBEC; color: #9F2F2D; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Degraded</span>'
        status_note = '<div style="color: #9F2F2D; font-size: 13px; margin-top: 5px;">Độ bao phủ chưa đạt ngưỡng chuẩn.</div>'

    st.sidebar.divider()
    st.sidebar.markdown(f"""
    <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 14px 16px; font-size: 13.5px; line-height: 1.65;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span class="editorial-label">Trạng thái Dữ liệu</span>
            {status_badge_html}
        </div>
        <div><b>Thời điểm (As of):</b> <code style="font-family: 'Geist Mono', monospace; font-size: 13px; background: #F7F6F3; padding: 1px 5px; border-radius: 3px;">{as_of}</code></div>
        <div><b>Độ bao phủ đồng phiên:</b> <span style="font-family: 'Geist Mono', monospace;">{valid_u}/{total_u}</span> (<b>{cov:.1f}%</b>{' ⚠️ Lỗi' if is_invariant_violation else ''})</div>
        <div><b>Đủ lịch sử 1Y (&ge;250 nến):</b> <span style="font-family: 'Geist Mono', monospace;"><b>{cov_252:.1f}%</b></span></div>
        <div><b>Trạng thái nạp ban đầu:</b> <span style="font-family: 'Geist Mono', monospace; font-size: 12.5px;">{snap_status}</span></div>
        {status_note}
        <div style="color: #787774; font-size: 12.5px; margin-top: 6px;">Nguồn: Wikipedia + Yahoo Finance ($0)</div>
        <div style="color: #787774; font-size: 12px; margin-top: 6px; border-top: 1px dashed #EAEAEA; padding-top: 6px; line-height: 1.45;">Phạm vi: <b>503 cổ phiếu S&P 500 (Large Cap)</b>. Không quét mid/small-cap ngoài chỉ số hoặc OTC.</div>
    </div>
    """, unsafe_allow_html=True)

    # Export Tickers Button
    candidates = repo.get_candidates_by_snapshot(selected_snapshot["id"])
    if candidates:
        export_cols = [
            "rank", "symbol", "company_name", "sector", "sub_industry",
            "group_type", "setup_type", "status", "score", "is_oneil_leader",
            "close_price", "trigger_price", "invalidation_price", "atr14", "atr_pct",
            "perf_1d", "perf_5d", "perf_20d"
        ]
        available_cols = [col for col in export_cols if col in candidates[0]]
        csv_data = pd.DataFrame(candidates)[available_cols].to_csv(index=False)
        st.sidebar.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        st.sidebar.download_button(
            label="Xuất danh sách Ứng viên (CSV cho Excel)",
            data=csv_data,
            file_name=f"market_radar_candidates_{as_of}.csv",
            mime="text/csv",
            use_container_width=True
        )

# Main Area
st.markdown('<h1 class="editorial-hero">Market Radar</h1>', unsafe_allow_html=True)
st.markdown('<div class="editorial-sub">S&P 500 Top-Down Swing Trading Architecture &mdash; Phân tích đa tầng từ cơ hội hôm nay, bối cảnh thị trường, xếp hạng ngành GICS đến chi tiết kỹ thuật setup và đo lường hiệu quả bộ lọc.</div>', unsafe_allow_html=True)

# Compatibility & Stale Hard-Gate Banners [R-04]
if selected_snapshot:
    if is_invariant_violation or is_legacy:
        st.markdown(f"""
        <div style="background-color: #FFF8E6; border: 1px solid #FFE082; border-radius: 6px; padding: 14px 20px; margin-bottom: 16px; font-size: 14px; color: #795548; line-height: 1.6;">
            <b>⚠️ Cảnh báo Snapshot Legacy / Không Tương Thích:</b> Snapshot <code>{as_of}</code> được tạo trước đợt nâng cấp schema/contract ({'Số mã hợp lệ ' + str(valid_u) + '/' + str(total_u) + ' vi phạm bất biến vũ trụ' if is_invariant_violation else 'Thiếu metadata chuẩn hóa hoặc chưa đủ độ bao phủ lịch sử 1Y'}). Trạng thái 'Complete' của snapshot chỉ phản ánh thời điểm tạo; ở thời điểm hiện tại dữ liệu đã chậm phiên hoặc chưa đồng bộ tính năng mới. Vui lòng bấm nút <b>Cập nhật dữ liệu ngay</b> ở thanh bên trái để tạo snapshot mới đồng bộ chuẩn hóa.
        </div>
        """, unsafe_allow_html=True)
    elif is_stale and session_age:
        lag = session_age.get("lag_sessions", 1)
        target_s = session_age.get("target_session", "")
        st.markdown(f"""
        <div style="background-color: #FFF8E6; border: 1px solid #FFE082; border-radius: 6px; padding: 14px 20px; margin-bottom: 16px; font-size: 14px; color: #795548; line-height: 1.6;">
            <b>⚠️ Chú ý: Dữ liệu Lịch sử (Chậm {lag} phiên):</b> Snapshot đang hiển thị là phiên <code>{as_of}</code>, trong khi phiên đóng cửa gần nhất của thị trường là <code>{target_s}</code>. Các sự kiện tại tab <b>Hôm Nay</b> và danh sách <b>Ứng Viên</b> phản ánh góc nhìn lịch sử tại phiên {as_of}, không đại diện cho phiên hôm nay. Bấm <b>Cập nhật dữ liệu ngay</b> ở thanh bên trái để tải dữ liệu phiên mới nhất.
        </div>
        """, unsafe_allow_html=True)


# Executive Market Clock, Freshness & Universe Scope Banner [D-05, D-06]
mkt_status = get_market_status_now()

c_clk1, c_clk2 = st.columns([1, 1])
with c_clk1:
    st.markdown(f"""
    <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 14px 18px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span class="editorial-label">Đồng Hồ Thị Trường & Trạng Thái NYSE</span>
            <span style="background-color: {mkt_status['status_badge_color']}15; color: {mkt_status['status_badge_color']}; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">
                {mkt_status['status_badge']}
            </span>
        </div>
        <div style="font-size: 14px; color: #2F3437; line-height: 1.6;">
            <div><b>New York (ET):</b> <code style="font-family: 'Geist Mono', monospace; font-size: 13px; background: #F7F6F3; padding: 2px 6px; border-radius: 3px;">{mkt_status['et_str']}</code> &nbsp;|&nbsp; <b>Việt Nam (ICT):</b> <code style="font-family: 'Geist Mono', monospace; font-size: 13px; background: #F7F6F3; padding: 2px 6px; border-radius: 3px;">{mkt_status['ict_str']}</code></div>
            <div style="font-size: 12.5px; color: #787774; margin-top: 5px;">{mkt_status['status_detail']} (Mục tiêu phiên: <b>{mkt_status['target_session']}</b>)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c_clk2:
    if session_age:
        st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 14px 18px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span class="editorial-label">Độ Tươi Dữ Liệu & Phạm Vi Vũ Trụ (Scope)</span>
                <span style="background-color: {session_age['freshness_badge_color']}15; color: {session_age['freshness_badge_color']}; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">
                    {session_age['freshness_label']}
                </span>
            </div>
            <div style="font-size: 13px; color: #2F3437; line-height: 1.6;">
                <div><b>Phiên dữ liệu:</b> <code style="font-family: 'Geist Mono', monospace; font-size: 11.5px; background: #F7F6F3; padding: 1px 5px; border-radius: 3px;">{session_age['as_of']}</code> &nbsp;|&nbsp; <b>Vũ trụ:</b> <span style="font-weight: 600;">503 mã S&P 500 (Large Cap)</span></div>
                <div style="font-size: 11.5px; color: #787774; margin-top: 4px;">Giá EOD đã điều chỉnh. Không bao gồm penny/OTC hay toàn bộ ~8.000 mã Mỹ ngoài chỉ số.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 14px 18px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span class="editorial-label">Độ Tươi Dữ Liệu</span>
                <span style="background-color: #FEF3D6; color: #8F6B00; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Chưa có dữ liệu</span>
            </div>
            <div style="font-size: 13px; color: #787774; line-height: 1.6;">
                Hệ thống chưa có snapshot nào. Nhấn <b>Cập nhật dữ liệu ngay</b> ở thanh bên trái để khởi tạo.
            </div>
        </div>
        """, unsafe_allow_html=True)

if not selected_snapshot:
    st.warning("Cơ sở dữ liệu hiện chưa có dữ liệu. Vui lòng bấm nút 'Cập nhật dữ liệu ngay' ở thanh bên trái để khởi chạy tiến trình nạp dữ liệu lần đầu.")
    st.stop()

# Extract snapshot data
market_metrics = selected_snapshot.get("market_metrics", {})
sector_metrics = selected_snapshot.get("sector_metrics", [])
industry_metrics = selected_snapshot.get("industry_metrics", [])
market_history = selected_snapshot.get("market_history")
sector_rotation = selected_snapshot.get("sector_rotation")
sector_health = selected_snapshot.get("sector_health")
current_snapshot_id = selected_snapshot["id"]
candidates = repo.get_candidates_by_snapshot(current_snapshot_id)

current_as_of = selected_snapshot.get("as_of", "")
unread_cnt = repo.get_unread_event_count(session_date=current_as_of)
if unread_cnt == 0 and not repo.get_signal_events(session_date=current_as_of, limit=1):
    unread_cnt = repo.get_unread_event_count()
unread_label = f" ({unread_cnt} mới)" if unread_cnt > 0 else ""

def render_diff_section(selected_snapshot, snapshots_list, repo):
    st.markdown('<div class="editorial-hero" style="font-size: 22px; margin-bottom: 4px;">So sánh Biến động với Snapshot Liền Trước</div>', unsafe_allow_html=True)
    current_snapshot_id = selected_snapshot["id"]
    curr_idx = next((i for i, s in enumerate(snapshots_list) if s["id"] == current_snapshot_id), -1)
    if curr_idx != -1 and curr_idx + 1 < len(snapshots_list):
        prev_snap_id = snapshots_list[curr_idx + 1]["id"]
        prev_snap = repo.get_snapshot_by_id(prev_snap_id)
        diff = repo.get_snapshot_diff(current_snapshot_id, prev_snap_id)

        st.markdown(f"<div style='font-size: 15px; color: #787774; margin-bottom: 16px;'>Đối chiếu giữa Snapshot <b>#{current_snapshot_id}</b> (<code>{selected_snapshot['as_of']}</code>) và Snapshot <b>#{prev_snap_id}</b> (<code>{prev_snap['as_of']}</code>):</div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Mã mới lọt danh sách", len(diff["added"]))
        c2.metric("Mã rời danh sách", len(diff["removed"]))
        c3.metric("Mã duy trì", len(diff["retained"]))

        if diff["added"]:
            st.markdown('<div class="editorial-label" style="margin: 20px 0 8px 0; color: #346538;">Cổ phiếu mới xuất hiện:</div>', unsafe_allow_html=True)
            add_df = pd.DataFrame([{"Mã": a["symbol"], "Công ty": a["company_name"], "Nhóm": a["group_type"], "Giá": f"${a['close_price']:.2f}"} for a in diff["added"]])
            st.dataframe(add_df, use_container_width=True, hide_index=True)

        if diff["removed"]:
            st.markdown('<div class="editorial-label" style="margin: 20px 0 8px 0; color: #9F2F2D;">Cổ phiếu rời danh sách:</div>', unsafe_allow_html=True)
            rem_df = pd.DataFrame([{"Mã": r["symbol"], "Công ty": r["company_name"], "Nhóm cũ": r["group_type"]} for r in diff["removed"]])
            st.dataframe(rem_df, use_container_width=True, hide_index=True)

        if diff["sector_moves"]:
            st.markdown('<div class="editorial-label" style="margin: 20px 0 8px 0;">Biến động thứ hạng ngành:</div>', unsafe_allow_html=True)
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

def render_audit_section(selected_snapshot):
    st.markdown('<div class="editorial-hero" style="font-size: 22px; margin-bottom: 4px;">Giám sát Chất lượng & Nguồn Dữ liệu</div>', unsafe_allow_html=True)
    st.markdown('<div class="editorial-sub">Báo cáo kiểm toán độ bao phủ, số lượng nến và các nguyên tắc vận hành không chi phí.</div>', unsafe_allow_html=True)

    q1, q2 = st.columns(2)
    with q1:
        cov_252 = selected_snapshot.get('coverage_252d', 0.0) * 100.0
        snap_st = selected_snapshot.get('status', 'complete')
        st_badge = '<span style="background-color: #EDF3EC; color: #346538; font-size: 12px; font-weight: 600; padding: 3px 8px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Hoàn chỉnh (Complete)</span>' if snap_st == 'complete' else '<span style="background-color: #FDEBEC; color: #9F2F2D; font-size: 12px; font-weight: 600; padding: 3px 8px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Cảnh báo (Degraded)</span>'

        st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 18px 20px; font-size: 14.5px; line-height: 1.8;">
            <div><b>Quy tắc phiên bản:</b> <code style="font-family: 'Geist Mono', monospace; font-size: 13px; background: #F7F6F3; padding: 2px 6px; border-radius: 3px;">{selected_snapshot.get('rule_version')}</code></div>
            <div><b>Trạng thái Snapshot:</b> {st_badge}</div>
            <div><b>Thời điểm phân tích:</b> <span style="font-family: 'Geist Mono', monospace;">{selected_snapshot.get('created_at')}</span></div>
            <div><b>Phiên giao dịch (As of):</b> <span style="font-family: 'Geist Mono', monospace;">{selected_snapshot.get('as_of')}</span></div>
            <div><b>Tổng vũ trụ S&P 500:</b> <span style="font-family: 'Geist Mono', monospace;">{selected_snapshot.get('total_universe')}</span> mã</div>
            <div><b>Số mã đồng phiên & đủ nến:</b> <span style="font-family: 'Geist Mono', monospace;">{selected_snapshot.get('valid_universe')}</span> mã</div>
            <div><b>Tỷ lệ bao phủ đồng phiên:</b> <span style="font-family: 'Geist Mono', monospace;"><b>{selected_snapshot.get('coverage_pct', 0)*100:.2f}%</b></span></div>
            <div><b>Tỷ lệ đủ lịch sử 1Y (&ge;253 nến):</b> <span style="font-family: 'Geist Mono', monospace;"><b>{cov_252:.2f}%</b></span></div>
        </div>
        """, unsafe_allow_html=True)

    with q2:
        missing = selected_snapshot.get("missing_symbols", [])
        st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 18px 20px; font-size: 14.5px; line-height: 1.8;">
            <div class="editorial-label" style="margin-bottom: 6px;">Mã thiếu dữ liệu</div>
            <div style="font-size: 15px; margin-bottom: 8px;">Số lượng mã thiếu: <b style="font-family: 'Geist Mono', monospace;">{len(missing)}</b> mã</div>
        </div>
        """, unsafe_allow_html=True)
        if missing:
            st.markdown("<div style='font-size: 13px; color: #787774; margin-top: 8px;'>Danh sách mã thiếu hoặc không đủ lịch sử 200 ngày:</div>", unsafe_allow_html=True)
            st.code(", ".join(missing))
        else:
            st.markdown("<div style='background-color: #EDF3EC; color: #346538; border: 1px solid #EAEAEA; padding: 10px 14px; border-radius: 4px; font-size: 14px; margin-top: 8px;'>Tất cả các mã trong universe đều được tải dữ liệu đầy đủ.</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("""
    <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 18px 20px; font-size: 14.5px; line-height: 1.8;">
        <div class="editorial-label" style="margin-bottom: 8px;">Nguyên tắc vận hành dữ liệu</div>
        <ol style="margin: 0; padding-left: 20px; color: #2F3437;">
            <li><b>Chi phí 0 đồng:</b> Không sử dụng API trả phí; sử dụng Wikipedia và Yahoo Finance công khai.</li>
            <li><b>Xử lý ngoại lệ:</b> Mã thiếu dữ liệu bị loại trừ khỏi điểm số (không nhận điểm hợp lệ hoặc bị gán giá trị 0 giả).</li>
            <li><b>Ngân hàng & Định chế tài chính:</b> Cơ cấu đòn bẩy và dòng tiền được gắn nhãn riêng, không áp dụng máy móc chỉ số nợ/dòng tiền phi tài chính.</li>
            <li><b>Short:</b> Luôn gắn nhãn cảnh báo <em>'Chưa xác minh khả năng short / phí vay'</em> tại broker của người dùng.</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

# Main Navigation (Two-tier Utilitarian Architecture - Renders ONLY active view)
pillar_options = [
    f"🎯 Hôm Nay & Ứng Viên{unread_label}",
    "🌐 Bản Đồ Thị Trường & Ngành",
    "📊 Đo Lường & Kiểm Toán"
]

if hasattr(st, "segmented_control"):
    selected_pillar = st.segmented_control(
        "Trạm làm việc chính:",
        options=pillar_options,
        default=pillar_options[0],
        label_visibility="collapsed",
        key="main_pillar_nav"
    )
else:
    selected_pillar = st.radio(
        "Trạm làm việc chính:",
        options=pillar_options,
        horizontal=True,
        label_visibility="collapsed",
        key="main_pillar_nav"
    )

if not selected_pillar:
    selected_pillar = pillar_options[0]

# Sub-navigation per active Pillar
if selected_pillar.startswith("🎯 Hôm Nay"):
    as_of_dt_str = selected_snapshot.get("as_of", "") if selected_snapshot else ""
    if repo:
        if hasattr(repo, "get_latest_base_snapshots"):
            base_records = repo.get_latest_base_snapshots(as_of=as_of_dt_str)
        else:
            base_records = repo.get_base_snapshots(snapshot_id=selected_snapshot.get("id"), as_of=as_of_dt_str)
    else:
        base_records = []
    sub_views = [
        "01 Hôm Nay (Sự Kiện)",
        f"02 Ứng Viên Giao Dịch ({len(candidates)})",
        f"03 Đang Xây Nền ({len(base_records)}) 🧱",
        "04 Lịch Báo Cáo Tài Chính (Earnings) 📅"
    ]
    sub_selected = st.segmented_control(
        "Góc nhìn Hôm Nay & Ứng Viên:",
        options=sub_views,
        default=sub_views[0],
        label_visibility="collapsed",
        key="sub_pillar1_nav"
    ) if hasattr(st, "segmented_control") else st.radio("Góc nhìn:", sub_views, horizontal=True, label_visibility="collapsed", key="sub_pillar1_nav")

    if not sub_selected:
        sub_selected = sub_views[0]

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    if sub_selected.startswith("01 Hôm Nay"):
        render_today_dashboard(
            as_of=selected_snapshot.get("as_of", ""),
            candidates=candidates,
            repo=repo
        )
    elif sub_selected.startswith("02 Ứng Viên"):
        render_candidates_section(
            candidates,
            as_of=selected_snapshot.get("as_of", ""),
            repo=repo,
            snapshot_id=selected_snapshot.get("id")
        )
    elif sub_selected.startswith("03 Đang Xây Nền"):
        render_base_watchlist(
            base_records=base_records,
            as_of=selected_snapshot.get("as_of", ""),
            repo=repo
        )
    else:
        render_earnings_calendar_section(
            as_of=selected_snapshot.get("as_of", ""),
            candidates=candidates,
            repo=repo
        )

elif selected_pillar.startswith("🌐 Bản Đồ"):
    sub_views = [
        "01 Bức Tranh Thị Trường (Breadth)",
        "02 11 Ngành GICS (Sector Rotation)",
        "03 Ma Trận 127 Nhóm Ngành O'Neil"
    ]
    sub_selected = st.segmented_control(
        "Góc nhìn Thị Trường & Ngành:",
        options=sub_views,
        default=sub_views[0],
        label_visibility="collapsed",
        key="sub_pillar2_nav"
    ) if hasattr(st, "segmented_control") else st.radio("Góc nhìn:", sub_views, horizontal=True, label_visibility="collapsed", key="sub_pillar2_nav")

    if not sub_selected:
        sub_selected = sub_views[0]

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    if sub_selected.startswith("01 Bức Tranh"):
        render_market_overview(
            market_metrics,
            as_of=selected_snapshot.get("as_of", ""),
            coverage_pct=selected_snapshot.get("coverage_pct", 0.0),
            total_universe=selected_snapshot.get("total_universe", 0),
            valid_universe=selected_snapshot.get("valid_universe", 0),
            market_history=market_history,
            snapshot_id=selected_snapshot.get("id"),
            repo=repo
        )
    elif sub_selected.startswith("02 11 Ngành"):
        render_sector_section(
            sector_metrics,
            industry_metrics,
            view_mode="macro",
            sector_rotation=sector_rotation,
            sector_health=sector_health
        )
    else:
        render_sector_section(sector_metrics, industry_metrics, view_mode="heatmap")

elif selected_pillar.startswith("📊 Đo Lường"):
    sub_views = [
        "01 Hiệu Quả Tín Hiệu (Alpha Audit)",
        "02 So Sánh Snapshot (Delta)",
        "03 Kiểm Toán Dữ Liệu & Vận Hành"
    ]
    sub_selected = st.segmented_control(
        "Góc nhìn Đo Lường & Kiểm Toán:",
        options=sub_views,
        default=sub_views[0],
        label_visibility="collapsed",
        key="sub_pillar3_nav"
    ) if hasattr(st, "segmented_control") else st.radio("Góc nhìn:", sub_views, horizontal=True, label_visibility="collapsed", key="sub_pillar3_nav")

    if not sub_selected:
        sub_selected = sub_views[0]

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    if sub_selected.startswith("01 Hiệu Quả"):
        render_signal_performance_section(
            repo,
            rule_version=selected_snapshot.get("rule_version")
        )
    elif sub_selected.startswith("02 So Sánh"):
        render_diff_section(selected_snapshot, snapshots_list, repo)
    else:
        render_audit_section(selected_snapshot)
