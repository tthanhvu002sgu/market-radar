import streamlit as st
from typing import Any, Dict, List

GROUP_TITLES = {
    "long_cont": ("🚀 Long Tiếp Diễn (Trend Continuation)", "Cổ phiếu trong xu hướng tăng mạnh, vượt trội thị trường và đang có điểm pullback hoặc breakout kèm volume."),
    "short_cont": ("🔻 Short Tiếp Diễn (Downtrend Continuation)", "Cổ phiếu trong xu hướng giảm rõ rệt, yếu hơn thị trường, xuất hiện nhịp hồi chạm kháng cự hoặc breakdown tiếp diễn."),
    "long_rev": ("🔄 Long Đảo Chiều (Mean Reversion / Reversal)", "Cổ phiếu có dấu hiệu tạo đáy kỹ thuật sau chuỗi giảm sâu hoặc vượt trở lại trên MA20."),
    "short_rev": ("⚠️ Short Đảo Chiều (Top Breakdown)", "Cổ phiếu tăng quá đà, xuất hiện suy yếu hoặc gãy MA20 báo hiệu đảo chiều giảm."),
    "watchlist": ("👁️ Danh sách Theo Dõi (Watchlist)", "Mã có tín hiệu mâu thuẫn hoặc đang hình thành mẫu hình nhưng chưa đủ xác nhận kỹ thuật.")
}

def render_candidate_card(cand: Dict[str, Any]):
    """Render an individual candidate card with TA evidence, FA flags, and TradingView link."""
    sym = cand["symbol"]
    company = cand.get("company_name", sym)
    sector = cand.get("sector", "")
    price = cand.get("close_price", 0.0)
    p1d = cand.get("perf_1d", 0.0)
    p5d = cand.get("perf_5d", 0.0)
    p20d = cand.get("perf_20d", 0.0)
    status = cand.get("status", "confirmed")
    reasons = cand.get("technical_reasons", [])
    fa_flags = cand.get("fa_flags", {})
    short_caveat = cand.get("short_caveat", "")
    tv_url = cand.get("tv_url", f"https://www.tradingview.com/chart/?symbol={sym}")

    status_badge = "✅ Đã xác nhận kỹ thuật" if status == "confirmed" else "⏳ Đang theo dõi"
    status_bg = "#c6f6d5" if status == "confirmed" else "#feebc8"
    status_color = "#22543d" if status == "confirmed" else "#744210"

    with st.container():
        st.markdown(f"""
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; margin-bottom: 15px; background: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div>
                    <span style="font-size: 20px; font-weight: bold; color: #1a202c;">{sym}</span>
                    <span style="font-size: 14px; color: #718096; margin-left: 8px;">{company}</span>
                    <span style="font-size: 12px; background: #edf2f7; color: #4a5568; padding: 2px 8px; border-radius: 12px; margin-left: 8px;">{sector}</span>
                </div>
                <div>
                    <span style="font-size: 12px; font-weight: bold; background: {status_bg}; color: {status_color}; padding: 3px 8px; border-radius: 6px;">{status_badge}</span>
                </div>
            </div>
            <div style="font-size: 14px; color: #4a5568; margin-bottom: 10px;">
                <b>Giá:</b> ${price:.2f} | 
                <b>1D:</b> <span style="color: {'#38a169' if p1d >= 0 else '#e53e3e'}">{p1d:+.2f}%</span> | 
                <b>1W:</b> <span style="color: {'#38a169' if p5d >= 0 else '#e53e3e'}">{p5d:+.2f}%</span> | 
                <b>1M:</b> <span style="color: {'#38a169' if p20d >= 0 else '#e53e3e'}">{p20d:+.2f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_ta, col_fa, col_action = st.columns([5, 5, 2])

        with col_ta:
            st.markdown("**📌 Bằng chứng Kỹ thuật (TA):**")
            if reasons:
                for r in reasons:
                    st.markdown(f"- {r}")
            else:
                st.markdown("- Đạt tiêu chuẩn cấu trúc giá và sức mạnh tương đối.")

            if short_caveat:
                st.caption(f"⚠️ *Lưu ý Short: {short_caveat}*")

        with col_fa:
            st.markdown("**🏢 Bối cảnh Doanh nghiệp & FA:**")
            if fa_flags and isinstance(fa_flags, dict) and "next_earnings_date" in fa_flags:
                earnings_date = fa_flags.get("next_earnings_date", "Chưa xác minh")
                rev_g = fa_flags.get("revenue_growth")
                eps_g = fa_flags.get("earnings_growth")
                is_fin = fa_flags.get("is_financial", False)

                st.markdown(f"- **Kỳ Earnings tiếp theo:** `{earnings_date}`")
                if rev_g is not None:
                    st.markdown(f"- Tăng trưởng Doanh thu: `{rev_g * 100:+.1f}%`")
                if eps_g is not None:
                    st.markdown(f"- Tăng trưởng EPS: `{eps_g * 100:+.1f}%`")
                if is_fin:
                    st.markdown("- *Định chế Tài chính / Ngân hàng (cơ cấu vốn đặc thù)*")
            else:
                st.markdown("- *Thông tin FA chưa nạp hoặc đang ở chế độ cache.*")

        with col_action:
            st.markdown("<br>", unsafe_allow_html=True)
            st.link_button(f"📈 TradingView {sym}", tv_url, type="primary")

        st.divider()

def render_candidates_section(candidates: List[Dict[str, Any]]):
    """Render candidates partitioned by the 4 groups + watchlist."""
    st.subheader("🎯 4 Nhóm Ứng Viên Giao Dịch (Swing Candidates)", divider="gray")

    if not candidates:
        st.info("ℹ️ **Không có mã nào đạt điều kiện trong kỳ phân tích này.** Thị trường đang ở pha phân hóa hoặc không thỏa mãn tiêu chí kỹ thuật. (Hệ thống không ép đủ số lượng mã).")
        return

    # Group candidates
    grouped: Dict[str, List[Dict[str, Any]]] = {
        "long_cont": [],
        "short_cont": [],
        "long_rev": [],
        "short_rev": [],
        "watchlist": []
    }
    for c in candidates:
        g = c.get("group_type", "watchlist")
        if g in grouped:
            grouped[g].append(c)
        else:
            grouped["watchlist"].append(c)

    tabs = st.tabs([
        f"🚀 Long Tiếp Diễn ({len(grouped['long_cont'])})",
        f"🔻 Short Tiếp Diễn ({len(grouped['short_cont'])})",
        f"🔄 Long Đảo Chiều ({len(grouped['long_rev'])})",
        f"⚠️ Short Đảo Chiều ({len(grouped['short_rev'])})",
        f"👁️ Watchlist ({len(grouped['watchlist'])})"
    ])

    for i, (g_key, tab) in enumerate(zip(["long_cont", "short_cont", "long_rev", "short_rev", "watchlist"], tabs)):
        with tab:
            title, desc = GROUP_TITLES[g_key]
            st.markdown(f"**{desc}**")
            group_cands = grouped[g_key]
            if not group_cands:
                st.info(f"Không có cổ phiếu nào thỏa mãn điều kiện cho nhóm **{title}** trong snapshot hiện tại.")
            else:
                for c in group_cands:
                    render_candidate_card(c)
