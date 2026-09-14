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
from app.components.setup_detail import render_setup_detail_modal, show_setup_detail_dialog
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
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #787774;
        font-weight: 600;
    }

    .sidebar-nav-header {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #8C8B85;
        margin: 14px 0 4px 4px;
    }

    [data-testid="stSidebar"] .stButton > button {
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 6px 12px !important;
        font-size: 13.5px !important;
        border-radius: 5px !important;
        margin-bottom: 2px !important;
        width: 100% !important;
    }

    /* Dividers */
    hr {
        border-color: #EAEAEA !important;
        margin: 16px 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
init_db()
repo = MarketRadarRepository()

# Snapshot Selection & Data Loading
snapshots_list = repo.get_snapshots_list(limit=20)
selected_snapshot = None
selected_snapshot_id = None

if snapshots_list:
    options = {
        f"#{s['id']} ({s['as_of']}) · Phủ {s['coverage_pct']*100:.1f}%": s["id"]
        for s in snapshots_list
    }
    if "selected_snapshot_id" not in st.session_state or st.session_state["selected_snapshot_id"] not in [s["id"] for s in snapshots_list]:
        st.session_state["selected_snapshot_id"] = snapshots_list[0]["id"]
    selected_snapshot_id = st.session_state["selected_snapshot_id"]
    selected_snapshot = repo.get_snapshot_by_id(selected_snapshot_id)

# Evaluate Data Invariants & Freshness
is_invariant_violation = False
is_legacy = False
is_stale = False
session_age = None
as_of = ""
valid_u = 0
total_u = 0
status_badge_html = ""
status_note = ""

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

    if is_invariant_violation:
        status_badge_html = '<span style="background-color: #FDEBEC; color: #9F2F2D; font-size: 11.5px; font-weight: 600; padding: 2px 8px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Lỗi Bất Biến</span>'
        status_note = '<div style="color: #9F2F2D; font-size: 12.5px; margin-top: 4px; font-weight: 600;">⚠️ Vi phạm bất biến: Mã hợp lệ vượt tổng vũ trụ.</div>'
    elif is_legacy:
        status_badge_html = '<span style="background-color: #FEF3D6; color: #8F6B00; font-size: 11.5px; font-weight: 600; padding: 2px 8px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Legacy Snapshot</span>'
        status_note = '<div style="color: #8F6B00; font-size: 12.5px; margin-top: 4px;">Snapshot cũ trước đợt nâng cấp schema.</div>'
    elif is_stale:
        lag = session_age.get("lag_sessions", 1)
        stale_color = "#9F2F2D" if lag > 1 else "#8F6B00"
        stale_bg = "#FDEBEC" if lag > 1 else "#FEF3D6"
        status_badge_html = f'<span style="background-color: {stale_bg}; color: {stale_color}; font-size: 11.5px; font-weight: 600; padding: 2px 8px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Cũ ({lag} phiên)</span>'
        status_note = f'<div style="color: {stale_color}; font-size: 12.5px; margin-top: 4px;">Dữ liệu lịch sử (chậm {lag} phiên). Trạng thái: {snap_status}.</div>'
    elif snap_status == "complete":
        status_badge_html = '<span style="background-color: #EDF3EC; color: #346538; font-size: 11.5px; font-weight: 600; padding: 2px 8px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Complete</span>'
        status_note = '<div style="color: #346538; font-size: 12.5px; margin-top: 4px;">Đồng phiên và đạt chuẩn kiểm tra.</div>'
    else:
        status_badge_html = '<span style="background-color: #FDEBEC; color: #9F2F2D; font-size: 11.5px; font-weight: 600; padding: 2px 8px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Degraded</span>'
        status_note = '<div style="color: #9F2F2D; font-size: 12.5px; margin-top: 4px;">Độ bao phủ chưa đạt ngưỡng chuẩn.</div>'

# Navigation State Handling
VALID_PAGES = [
    "Tổng hợp phiên",
    "Lịch BCTC",
    "Ứng viên",
    "Nền giá & bứt phá",
    "Thị trường",
    "Ngành",
    "Nhóm ngành",
    "Chất lượng tín hiệu",
    "Thay đổi giữa phiên",
    "Dữ liệu & vận hành"
]

if "active_page" not in st.session_state or st.session_state["active_page"] not in VALID_PAGES:
    st.session_state["active_page"] = "Tổng hợp phiên"

# Snapshot Data Extraction
candidates = []
base_records = []
unread_cnt = 0

if selected_snapshot:
    current_snapshot_id = selected_snapshot["id"]
    candidates = repo.get_candidates_by_snapshot(current_snapshot_id)
    if hasattr(repo, "get_latest_base_snapshots"):
        base_records = repo.get_latest_base_snapshots(as_of=as_of)
    else:
        base_records = repo.get_base_snapshots(snapshot_id=current_snapshot_id, as_of=as_of)
    unread_cnt = repo.get_unread_event_count(session_date=as_of)
    if unread_cnt == 0 and not repo.get_signal_events(session_date=as_of, limit=1):
        unread_cnt = repo.get_unread_event_count()

# Sidebar: Brand Header
st.sidebar.markdown('<div class="editorial-hero" style="font-size: 20px; margin-bottom: 2px;">Market Radar</div>', unsafe_allow_html=True)
st.sidebar.markdown(f'<div class="editorial-label" style="margin-bottom: 14px;">S&P 500 Swing Architecture &middot; {RULE_VERSION}</div>', unsafe_allow_html=True)

# Sidebar: 1-Level Categorized Navigation
NAV_SECTIONS = [
    {
        "category": "THEO DÕI",
        "items": [
            ("Tổng hợp phiên", f"📌 Tổng hợp phiên" + (f" ({unread_cnt})" if unread_cnt > 0 else "")),
            ("Lịch BCTC", "📅 Lịch BCTC"),
        ]
    },
    {
        "category": "TÌM CƠ HỘI",
        "items": [
            ("Ứng viên", f"🎯 Ứng viên ({len(candidates)})"),
            ("Nền giá & bứt phá", f"🧱 Nền giá & bứt phá ({len(base_records)})"),
        ]
    },
    {
        "category": "BỐI CẢNH",
        "items": [
            ("Thị trường", "🌐 Thị trường"),
            ("Ngành", "📊 Ngành"),
            ("Nhóm ngành", "🗺️ Nhóm ngành"),
        ]
    },
    {
        "category": "ĐÁNH GIÁ",
        "items": [
            ("Chất lượng tín hiệu", "📈 Chất lượng tín hiệu"),
            ("Thay đổi giữa phiên", "🔄 Thay đổi giữa phiên"),
        ]
    },
    {
        "category": "HỆ THỐNG",
        "items": [
            ("Dữ liệu & vận hành", "⚙️ Dữ liệu & vận hành"),
        ]
    }
]

for section in NAV_SECTIONS:
    st.sidebar.markdown(f'<div class="sidebar-nav-header">{section["category"]}</div>', unsafe_allow_html=True)
    for page_id, page_label in section["items"]:
        is_active = (st.session_state["active_page"] == page_id)
        btn_type = "primary" if is_active else "secondary"
        if st.sidebar.button(page_label, key=f"nav_btn_{page_id}", use_container_width=True, type=btn_type):
            if not is_active:
                st.session_state["active_page"] = page_id
                st.rerun()

st.sidebar.divider()

# Sidebar: Snapshot Selector
if snapshots_list:
    snapshot_labels = list(options.keys())
    current_label_idx = 0
    for idx, (label, sid) in enumerate(options.items()):
        if sid == selected_snapshot_id:
            current_label_idx = idx
            break
    chosen_label = st.sidebar.selectbox("Lịch sử Snapshot:", snapshot_labels, index=current_label_idx)
    new_snapshot_id = options[chosen_label]
    if new_snapshot_id != selected_snapshot_id:
        st.session_state["selected_snapshot_id"] = new_snapshot_id
        st.rerun()
else:
    st.sidebar.info("Chưa có snapshot nào trong cơ sở dữ liệu.")

# Sidebar: Compact Status Card
if selected_snapshot:
    st.sidebar.markdown(f"""
    <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 12px 14px; font-size: 13px; line-height: 1.6; margin-top: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span class="editorial-label">Phiên {as_of}</span>
            {status_badge_html}
        </div>
        <div>Phủ đồng phiên: <b>{valid_u}/{total_u}</b> ({cov:.1f}%)</div>
        <div>Lịch sử 1Y: <b>{cov_252:.1f}%</b></div>
        {status_note}
    </div>
    """, unsafe_allow_html=True)

# Sidebar: Quick Manual Update Button
st.sidebar.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
if st.sidebar.button("Cập nhật dữ liệu ngay", key="sidebar_run_update_btn", use_container_width=True, type="secondary"):
    with st.spinner("Đang tải dữ liệu S&P 500, ETF và tính toán chỉ số..."):
        res = run_update_pipeline()
        if res.get("success"):
            st.sidebar.success(f"Hoàn thành. Snapshot #{res.get('snapshot_id')}")
            st.session_state["selected_snapshot_id"] = res.get("snapshot_id")
            st.rerun()
        else:
            st.sidebar.error(res.get("message", "Lỗi cập nhật"))

# Sidebar: Quick Export Candidates CSV
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
        label="Xuất Ứng viên (CSV)",
        data=csv_data,
        file_name=f"market_radar_candidates_{as_of}.csv",
        mime="text/csv",
        use_container_width=True
    )

if not selected_snapshot:
    st.warning("Cơ sở dữ liệu hiện chưa có dữ liệu. Vui lòng bấm nút 'Cập nhật dữ liệu ngay' ở thanh bên trái để khởi chạy tiến trình nạp dữ liệu lần đầu.")
    st.stop()

# Get Market Status and Clock
mkt_status = get_market_status_now()

# Map Active Page to Display Title
PAGE_TITLES = {
    "Tổng hợp phiên": "📌 Tổng Hợp Phiên (Daily Synthesis)",
    "Lịch BCTC": "📅 Lịch Báo Cáo Tài Chính (Earnings Calendar)",
    "Ứng viên": "🎯 Trạm Làm Việc Ứng Viên Giao Dịch",
    "Nền giá & bứt phá": "🧱 Nền Giá & Bứt Phá (Base Building & Breakout)",
    "Thị trường": "🌐 Bức Tranh Thị Trường (Market Breadth)",
    "Ngành": "📊 Phân Tích 11 Ngành GICS (Sector Rotation)",
    "Nhóm ngành": "🗺️ Ma Trận 127 Nhóm Ngành O'Neil (Industry Heatmap)",
    "Chất lượng tín hiệu": "📈 Đo Lường & Hiệu Quả Tín Hiệu (Alpha Audit)",
    "Thay đổi giữa phiên": "🔄 So Sánh Biến Động Snapshot (Delta)",
    "Dữ liệu & vận hành": "⚙️ Giám Sát Dữ Liệu & Vận Hành",
}

active_page = st.session_state["active_page"]
page_title_display = PAGE_TITLES.get(active_page, active_page)

# Unified Top Header Bar (Compact 1-Line Header)
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1px solid #EAEAEA; padding-bottom: 10px; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
    <div>
        <div style="font-size: 11.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #8C8B85; margin-bottom: 2px;">Market Radar &bull; S&P 500</div>
        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
            <span class="editorial-hero" style="font-size: 24px; margin: 0;">{page_title_display}</span>
            <span style="font-family: 'Geist Mono', monospace; font-size: 12px; background: #F0F0EE; color: #37352F; padding: 2px 7px; border-radius: 4px; border: 1px solid #E2E1DE;">Phiên {as_of}</span>
            {status_badge_html}
        </div>
    </div>
    <div style="text-align: right; font-size: 12.5px; color: #787774; line-height: 1.5;">
        <div><b>ET:</b> <code style="font-family: 'Geist Mono', monospace; font-size: 12px; background: #F7F6F3; padding: 1px 5px; border-radius: 3px;">{mkt_status['et_str']}</code> &nbsp;|&nbsp; <b>ICT:</b> <code style="font-family: 'Geist Mono', monospace; font-size: 12px; background: #F7F6F3; padding: 1px 5px; border-radius: 3px;">{mkt_status['ict_str']}</code></div>
        <div style="margin-top: 2px;">
            <span style="background-color: {mkt_status['status_badge_color']}15; color: {mkt_status['status_badge_color']}; font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 9999px;">
                {mkt_status['status_badge']}
            </span>
            &nbsp;Mục tiêu phiên: <b>{mkt_status['target_session']}</b>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Compatibility & Stale Hard-Gate Warning Banners
if is_invariant_violation or is_legacy:
    st.markdown(f"""
    <div style="background-color: #FFF8E6; border: 1px solid #FFE082; border-radius: 6px; padding: 10px 16px; margin-bottom: 12px; font-size: 13.5px; color: #795548; line-height: 1.5;">
        <b>⚠️ Cảnh báo Snapshot Legacy / Không Tương Thích:</b> Snapshot <code>{as_of}</code> ({'Số mã hợp lệ ' + str(valid_u) + '/' + str(total_u) + ' vi phạm bất biến vũ trụ' if is_invariant_violation else 'Thiếu metadata chuẩn hóa hoặc chưa đủ độ bao phủ 1Y'}). Bấm <b>Cập nhật dữ liệu ngay</b> ở thanh bên để tạo snapshot mới đồng bộ chuẩn hóa.
    </div>
    """, unsafe_allow_html=True)
elif is_stale and session_age:
    lag = session_age.get("lag_sessions", 1)
    target_s = session_age.get("target_session", "")
    st.markdown(f"""
    <div style="background-color: #FFF8E6; border: 1px solid #FFE082; border-radius: 6px; padding: 10px 16px; margin-bottom: 12px; font-size: 13.5px; color: #795548; line-height: 1.5;">
        <b>⚠️ Chú ý: Dữ liệu Lịch sử (Chậm {lag} phiên):</b> Snapshot đang hiển thị là phiên <code>{as_of}</code> (phiên gần nhất thị trường: <code>{target_s}</code>). Dữ liệu phản ánh góc nhìn lịch sử tại phiên {as_of}.
    </div>
    """, unsafe_allow_html=True)

# Detailed Operational Info Expander (Saves vertical space)
with st.expander("ℹ️ Thông tin phiên, đồng hồ thị trường & phạm vi dữ liệu", expanded=False):
    exp_c1, exp_c2 = st.columns(2)
    with exp_c1:
        st.markdown(f"""
        <div style="font-size: 13px; line-height: 1.7;">
            <div><b>Trạng thái NYSE:</b> <span style="font-weight: 600; color: {mkt_status['status_badge_color']};">{mkt_status['status_badge']}</span></div>
            <div><b>Giờ New York (ET):</b> <code style="font-family: 'Geist Mono', monospace; background: #F7F6F3; padding: 1px 5px; border-radius: 3px;">{mkt_status['et_str']}</code></div>
            <div><b>Giờ Việt Nam (ICT):</b> <code style="font-family: 'Geist Mono', monospace; background: #F7F6F3; padding: 1px 5px; border-radius: 3px;">{mkt_status['ict_str']}</code></div>
            <div><b>Chi tiết:</b> {mkt_status['status_detail']}</div>
            <div><b>Mục tiêu phiên:</b> {mkt_status['target_session']}</div>
        </div>
        """, unsafe_allow_html=True)
    with exp_c2:
        freshness_label = session_age['freshness_label'] if session_age else "N/A"
        freshness_color = session_age['freshness_badge_color'] if session_age else "#787774"
        st.markdown(f"""
        <div style="font-size: 13px; line-height: 1.7;">
            <div><b>Độ tươi dữ liệu:</b> <span style="font-weight: 600; color: {freshness_color};">{freshness_label}</span></div>
            <div><b>Độ bao phủ đồng phiên:</b> <span style="font-family: 'Geist Mono', monospace;">{valid_u}/{total_u}</span> ({cov:.1f}%)</div>
            <div><b>Đủ lịch sử 1Y (&ge;250 nến):</b> <span style="font-family: 'Geist Mono', monospace;">{cov_252:.1f}%</span></div>
            <div><b>Phạm vi vũ trụ:</b> 503 cổ phiếu S&P 500 (Large Cap). Không quét penny/OTC.</div>
            <div><b>Nguồn dữ liệu:</b> Wikipedia + Yahoo Finance ($0). Giá EOD đã điều chỉnh.</div>
        </div>
        """, unsafe_allow_html=True)

# Snapshot Data Extraction
market_metrics = selected_snapshot.get("market_metrics", {})
sector_metrics = selected_snapshot.get("sector_metrics", [])
industry_metrics = selected_snapshot.get("industry_metrics", [])
market_history = selected_snapshot.get("market_history")
sector_rotation = selected_snapshot.get("sector_rotation")
sector_health = selected_snapshot.get("sector_health")

def render_diff_section(selected_snapshot, snapshots_list, repo):
    st.markdown('<div class="editorial-hero" style="font-size: 20px; margin-bottom: 4px;">So Sánh Biến Động Giữa Các Phiên (Snapshot Diff)</div>', unsafe_allow_html=True)
    current_snapshot_id = selected_snapshot["id"]
    curr_idx = next((i for i, s in enumerate(snapshots_list) if s["id"] == current_snapshot_id), -1)
    if curr_idx != -1 and curr_idx + 1 < len(snapshots_list):
        prev_snap_id = snapshots_list[curr_idx + 1]["id"]
        prev_snap = repo.get_snapshot_by_id(prev_snap_id)
        diff = repo.get_snapshot_diff(current_snapshot_id, prev_snap_id)

        st.markdown(f"<div style='font-size: 14px; color: #787774; margin-bottom: 16px;'>Đối chiếu giữa Snapshot <b>#{current_snapshot_id}</b> (<code>{selected_snapshot['as_of']}</code>) và Snapshot <b>#{prev_snap_id}</b> (<code>{prev_snap['as_of']}</code>):</div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Mã mới lọt danh sách", len(diff["added"]))
        c2.metric("Mã rời danh sách", len(diff["removed"]))
        c3.metric("Mã duy trì", len(diff["retained"]))

        if diff["added"]:
            st.markdown('<div class="editorial-label" style="margin: 16px 0 8px 0; color: #346538;">Cổ phiếu mới xuất hiện:</div>', unsafe_allow_html=True)
            add_df = pd.DataFrame([{"Mã": a["symbol"], "Công ty": a["company_name"], "Nhóm": a["group_type"], "Giá": f"${a['close_price']:.2f}"} for a in diff["added"]])
            st.dataframe(add_df, use_container_width=True, hide_index=True)

        if diff["removed"]:
            st.markdown('<div class="editorial-label" style="margin: 16px 0 8px 0; color: #9F2F2D;">Cổ phiếu rời danh sách:</div>', unsafe_allow_html=True)
            rem_df = pd.DataFrame([{"Mã": r["symbol"], "Công ty": r["company_name"], "Nhóm cũ": r["group_type"]} for r in diff["removed"]])
            st.dataframe(rem_df, use_container_width=True, hide_index=True)

        if diff["sector_moves"]:
            st.markdown('<div class="editorial-label" style="margin: 16px 0 8px 0;">Biến động thứ hạng ngành:</div>', unsafe_allow_html=True)
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

def render_audit_section(selected_snapshot, repo=None):
    st.markdown('<div class="editorial-hero" style="font-size: 20px; margin-bottom: 4px;">Giám Sát Chất Lượng Dữ Liệu & Vận Hành Pipeline</div>', unsafe_allow_html=True)
    st.markdown('<div class="editorial-sub">Báo cáo kiểm toán độ bao phủ, số lượng nến, cập nhật pipeline và các nguyên tắc vận hành không chi phí.</div>', unsafe_allow_html=True)

    # Pipeline Operation Box
    st.markdown("""
    <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 16px 18px; margin-bottom: 16px;">
        <div class="editorial-label" style="margin-bottom: 8px;">Vận hành Cập nhật Thủ công</div>
        <div style="font-size: 13.5px; color: #787774; margin-bottom: 12px;">
            Nhấn nút bên dưới để kích hoạt pipeline cập nhật: lấy danh sách S&P 500 từ Wikipedia, tải giá EOD mới nhất từ Yahoo Finance, kiểm toán độ bao phủ, tính toán chỉ số kỹ thuật, phát hiện mẫu hình và tạo snapshot mới.
        </div>
    </div>
    """, unsafe_allow_html=True)

    op_c1, op_c2 = st.columns([1, 2])
    with op_c1:
        if st.button("🚀 Khởi chạy Pipeline Cập nhật Dữ liệu", key="audit_page_update_btn", type="primary", use_container_width=True):
            with st.spinner("Đang thực thi update pipeline toàn diện..."):
                res = run_update_pipeline()
                if res.get("success"):
                    st.success(f"Cập nhật thành công! Snapshot #{res.get('snapshot_id')} đã được khởi tạo.")
                    st.session_state["selected_snapshot_id"] = res.get("snapshot_id")
                    st.rerun()
                else:
                    st.error(res.get("message", "Lỗi cập nhật"))

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Quality Metrics
    q1, q2 = st.columns(2)
    with q1:
        cov_252 = selected_snapshot.get('coverage_252d', 0.0) * 100.0
        snap_st = selected_snapshot.get('status', 'complete')
        st_badge = '<span style="background-color: #EDF3EC; color: #346538; font-size: 11.5px; font-weight: 600; padding: 2px 7px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Hoàn chỉnh (Complete)</span>' if snap_st == 'complete' else '<span style="background-color: #FDEBEC; color: #9F2F2D; font-size: 11.5px; font-weight: 600; padding: 2px 7px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">Cảnh báo (Degraded)</span>'

        st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 16px 18px; font-size: 13.5px; line-height: 1.8;">
            <div class="editorial-label" style="margin-bottom: 8px;">Thông số Snapshot Hiện Tại</div>
            <div><b>Quy tắc phiên bản:</b> <code style="font-family: 'Geist Mono', monospace; font-size: 12.5px; background: #F7F6F3; padding: 2px 6px; border-radius: 3px;">{selected_snapshot.get('rule_version')}</code></div>
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
        <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 16px 18px; font-size: 13.5px; line-height: 1.8;">
            <div class="editorial-label" style="margin-bottom: 8px;">Kiểm toán Mã Thiếu / Ngoại Lệ</div>
            <div style="font-size: 14px; margin-bottom: 6px;">Số lượng mã thiếu: <b style="font-family: 'Geist Mono', monospace;">{len(missing)}</b> mã</div>
        </div>
        """, unsafe_allow_html=True)
        if missing:
            st.markdown("<div style='font-size: 12.5px; color: #787774; margin-top: 6px;'>Danh sách mã thiếu hoặc không đủ lịch sử 200 ngày:</div>", unsafe_allow_html=True)
            st.code(", ".join(missing))
        else:
            st.markdown("<div style='background-color: #EDF3EC; color: #346538; border: 1px solid #EAEAEA; padding: 10px 14px; border-radius: 4px; font-size: 13.5px; margin-top: 8px;'>Tất cả các mã trong universe đều được tải dữ liệu đầy đủ.</div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 16px 18px; font-size: 13.5px; line-height: 1.8;">
        <div class="editorial-label" style="margin-bottom: 8px;">Nguyên tắc Vận hành Dữ liệu</div>
        <ol style="margin: 0; padding-left: 20px; color: #2F3437;">
            <li><b>Chi phí 0 đồng:</b> Sử dụng Wikipedia và Yahoo Finance công khai.</li>
            <li><b>Xử lý ngoại lệ:</b> Mã thiếu dữ liệu bị loại trừ khỏi điểm số (không nhận điểm hợp lệ hoặc bị gán giá trị 0 giả).</li>
            <li><b>Ngân hàng & Định chế tài chính:</b> Cơ cấu đòn bẩy và dòng tiền được gắn nhãn riêng, không áp dụng máy móc chỉ số nợ/dòng tiền phi tài chính.</li>
            <li><b>Short:</b> Luôn gắn nhãn cảnh báo <em>'Chưa xác minh khả năng short / phí vay'</em> tại broker của người dùng.</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

# Main Page Router (Renders ONLY the active page)
if active_page == "Tổng hợp phiên":
    render_today_dashboard(
        as_of=as_of,
        candidates=candidates,
        repo=repo
    )
elif active_page == "Lịch BCTC":
    render_earnings_calendar_section(
        as_of=as_of,
        candidates=candidates,
        repo=repo
    )
elif active_page == "Ứng viên":
    render_candidates_section(
        candidates,
        as_of=as_of,
        repo=repo,
        snapshot_id=current_snapshot_id
    )
elif active_page == "Nền giá & bứt phá":
    render_base_watchlist(
        base_records=base_records,
        as_of=as_of,
        repo=repo,
        snapshot_id=current_snapshot_id,
        candidates=candidates
    )
elif active_page == "Thị trường":
    render_market_overview(
        market_metrics,
        as_of=as_of,
        coverage_pct=selected_snapshot.get("coverage_pct", 0.0),
        total_universe=total_u,
        valid_universe=valid_u,
        market_history=market_history,
        snapshot_id=current_snapshot_id,
        repo=repo
    )
elif active_page == "Ngành":
    render_sector_section(
        sector_metrics,
        industry_metrics,
        view_mode="macro",
        sector_rotation=sector_rotation,
        sector_health=sector_health
    )
elif active_page == "Nhóm ngành":
    render_sector_section(
        sector_metrics,
        industry_metrics,
        view_mode="heatmap"
    )
elif active_page == "Chất lượng tín hiệu":
    render_signal_performance_section(
        repo,
        rule_version=selected_snapshot.get("rule_version")
    )
elif active_page == "Thay đổi giữa phiên":
    render_diff_section(selected_snapshot, snapshots_list, repo)
elif active_page == "Dữ liệu & vận hành":
    render_audit_section(selected_snapshot, repo)
