"""
Signal Performance Component (Hiệu Quả Tín Hiệu).
Measures scanner filter quality independently of actual manual execution:
- Forward returns over 5, 10, 20 trading sessions.
- Excess return over SPY benchmark on identical observation windows.
- Maximum Favorable / Adverse Excursion (MFE / MAE).
- Categorized breakdowns: Setup type, Long/Short, Sector, Score Quartiles.
- Sample sizes, pending counts, and uncertainty reporting.
"""
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from storage.repository import MarketRadarRepository
from analytics.signal_outcomes import compute_quality_summary, evaluate_shortlist_and_decision_outcomes

def render_signal_performance_section(repo: MarketRadarRepository, rule_version: Optional[str] = None):
    """Render the Signal Performance audit tab."""
    st.markdown('<div class="editorial-hero" style="font-size: 24px; margin-bottom: 4px;">Hiệu Quả Tín Hiệu (Scanner Performance & Edge Audit)</div>', unsafe_allow_html=True)
    st.markdown('<div class="editorial-sub" style="font-size: 14.5px;">Đo lường năng lực phân loại của bộ lọc scanner theo các mốc giữ lệnh trong tuần (1-4 phiên, chốt cuối tuần) và bối cảnh vĩ mô (5, 10, 20 phiên). Điểm vào lệnh được ghi nhận bằng giá mở cửa (Open) của phiên tiếp theo để loại trừ rủi ro lookahead.</div>', unsafe_allow_html=True)

    # Methodology & Domain Disclaimer Banner [D-04]
    st.markdown("""
    <div style="background-color: #FDFBF7; border: 1px solid #F0E8D8; border-radius: 6px; padding: 14px 18px; font-size: 13.5px; color: #5C5042; line-height: 1.6; margin-bottom: 20px; font-family: 'Geist', 'Inter', sans-serif;">
        <b>⚠️ Khuyến Cáo Đo Lường Chất Lượng Bộ Lọc (Gross Filter Edge vs Real Trade P&L):</b><br/>
        Kết quả forward return ở đây là <i>lợi suất thô (Gross return)</i> dựa trên giá mở cửa phiên sau và giá đóng cửa của kỳ hạn quan sát. Thống kê này phản ánh độ phân hóa tín hiệu của thuật toán scanner, <b>không đại diện cho P&L giao dịch thực tế</b> của tài khoản vì:
        <ul style="margin: 6px 0 0 0; padding-left: 20px;">
            <li>Chưa tính chi phí trượt giá (slippage) và phí hoa hồng thực tế tại broker.</li>
            <li>Chưa bao gồm lãi suất/phí vay bán khống (short borrow fee/hard-to-borrow) đối với các lệnh Short.</li>
            <li>Bỏ qua rủi ro bị chạm ngưỡng dừng lỗ (intraday stop-out) trước khi kết thúc kỳ hạn quan sát.</li>
            <li>Đối với mốc <i>Chốt cuối tuần (Week Close)</i>: các tín hiệu xuất hiện vào phiên cuối tuần (không còn ngày giao dịch trong tuần) sẽ tự động được gắn cờ bỏ qua để tránh rủi ro giữ lệnh qua 2 ngày nghỉ cuối tuần.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # Horizon selector
    horizon_map = {
        1: "1 phiên (T+1 Swing)",
        2: "2 phiên (T+2 Swing)",
        3: "3 phiên (T+3 Swing)",
        4: "4 phiên (T+4 Swing)",
        99: "Chốt cuối tuần (Week Close)",
        5: "5 phiên (~1 tuần context)",
        10: "10 phiên (~2 tuần context)",
        20: "20 phiên (~1 tháng context)"
    }

    col_h1, col_h2 = st.columns([3, 3])
    with col_h1:
        horizon = st.selectbox(
            "Khoảng thời gian quan sát (Holding Horizon):",
            options=list(horizon_map.keys()),
            format_func=lambda x: horizon_map[x],
            index=4,  # Default to week-close
            key="perf_horizon_select"
        )
    with col_h2:
        weekend_filter = st.selectbox(
            "Biên cuối tuần (Weekend Boundary Filter):",
            options=["Tất cả tín hiệu", "Chỉ trong tuần (Không qua cuối tuần)", "Vắt qua cuối tuần"],
            key="perf_weekend_filter"
        )

    # Fetch outcomes for this horizon
    df_outcomes = repo.get_signal_outcomes(horizon_days=horizon, rule_version=rule_version)

    if df_outcomes.empty:
        st.info(f"Chưa có dữ liệu thống kê kết quả cho mốc '{horizon_map[horizon]}'. Hệ thống sẽ tự động cập nhật và tích lũy khi có phiên giao dịch mới.")
        return

    if weekend_filter == "Chỉ trong tuần (Không qua cuối tuần)" and "crosses_weekend" in df_outcomes.columns:
        df_outcomes = df_outcomes[df_outcomes["crosses_weekend"] == 0]
    elif weekend_filter == "Vắt qua cuối tuần" and "crosses_weekend" in df_outcomes.columns:
        df_outcomes = df_outcomes[df_outcomes["crosses_weekend"] == 1]

    if df_outcomes.empty:
        st.info(f"Không có tín hiệu nào thỏa mãn bộ lọc '{weekend_filter}' cho mốc '{horizon_map[horizon]}'.")
        return

    # Compute summary statistics
    stats = compute_quality_summary(df_outcomes)

    # Metric cards
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Tổng Tín Hiệu", stats["total_signals"])
    m2.metric("Đã Hoàn Tất", stats["completed"])
    m3.metric("Đang Chờ", stats["pending"])
    m4.metric("Tỷ Lệ Thắng", f"{stats['win_rate']:.1f}%")
    m5.metric("Lợi Suất TB", f"{stats['avg_return']:+.2f}%")
    m6.metric("Vượt SPY TB", f"{stats['avg_excess_spy']:+.2f}%")

    if stats.get("no_window_count", 0) > 0:
        st.caption(f"ℹ️ Có **{stats['no_window_count']}** tín hiệu vào lệnh vào phiên cuối tuần được gắn nhãn `no_window_in_week` (không còn ngày giao dịch trong tuần để giữ lệnh mà không mang rủi ro qua tuần).")

    if stats.get("crosses_weekend_count", 0) > 0 and horizon != 99:
        st.caption(f"⚠️ Có **{stats['crosses_weekend_count']}** tín hiệu vắt qua 2 ngày nghỉ cuối tuần (Weekend Cross). Khuyến nghị người dùng ưu tiên mốc 'Chốt cuối tuần' hoặc chọn lọc 'Chỉ trong tuần'.")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # MFE / MAE and Score Check Box
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 18px 22px;">
            <div style="font-size: 12.5px; text-transform: uppercase; color: #64748B; font-weight: 600; margin-bottom: 8px; font-family: 'Geist', 'Inter', sans-serif;">Diễn Biến Giá Tối Đa (Path Excursion)</div>
            <div style="font-size: 14.5px; color: #1E293B; line-height: 1.8; font-family: 'Geist', 'Inter', sans-serif;">
                <div><b>Lợi nhuận thuận lợi tối đa TB (MFE):</b> <span style="color: #16A34A; font-weight: 600; font-family: 'Geist Mono', monospace;">{stats['avg_mfe']:+.2f}%</span></div>
                <div><b>Mức sụt giảm bất lợi tối đa TB (MAE):</b> <span style="color: #DC2626; font-weight: 600; font-family: 'Geist Mono', monospace;">{stats['avg_mae']:+.2f}%</span></div>
                <div style="font-size: 12.5px; color: #64748B; margin-top: 4px;">MFE/MAE đo lường biên độ dao động trong suốt khung thời gian {horizon_map[horizon]}.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with sc2:
        score_check = stats.get("score_check", {})
        top_avg = score_check.get("top_quartile_avg")
        bot_avg = score_check.get("bottom_quartile_avg")
        is_mono = score_check.get("is_monotonic")

        if top_avg is not None and bot_avg is not None:
            status_text = "Đạt (Top điểm có kết quả tốt hơn)" if is_mono else "Chưa phân hóa rõ rệt"
            badge_color = "#16A34A" if is_mono else "#D97706"
        else:
            status_text = "Chưa đủ số mẫu hoàn tất (&ge;8 mẫu) để kiểm toán phân vị"
            badge_color = "#64748B"

        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 18px 22px;">
            <div style="font-size: 12.5px; text-transform: uppercase; color: #64748B; font-weight: 600; margin-bottom: 8px; font-family: 'Geist', 'Inter', sans-serif;">Kiểm Định Điểm Số (Score Validation)</div>
            <div style="font-size: 14.5px; color: #1E293B; line-height: 1.8; font-family: 'Geist', 'Inter', sans-serif;">
                <div><b>Top 25% Điểm Cao:</b> <span style="font-family: 'Geist Mono', monospace;">{f'{top_avg:+.2f}%' if top_avg is not None else 'N/A'}</span></div>
                <div><b>Bottom 25% Điểm Thấp:</b> <span style="font-family: 'Geist Mono', monospace;">{f'{bot_avg:+.2f}%' if bot_avg is not None else 'N/A'}</span></div>
                <div><b>Kết luận:</b> <span style="color: {badge_color}; font-weight: 600;">{status_text}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Breakdown by Weekday & Side (D-04)
    wb_col1, wb_col2 = st.columns(2)
    with wb_col1:
        st.markdown('<div style="font-size: 18px; font-weight: 700; color: #111111; margin: 24px 0 8px 0; font-family: \'Geist\', \'Inter\', sans-serif;">Thống Kê Theo Thứ Vào Lệnh (Day of Week)</div>', unsafe_allow_html=True)
        weekday_df = stats.get("weekday_breakdown", pd.DataFrame())
        if not weekday_df.empty:
            st.dataframe(
                weekday_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Mẫu Hoàn Tất": st.column_config.NumberColumn("Mẫu Hoàn Tất", format="%d"),
                    "Độ Tin Cậy": st.column_config.TextColumn("Độ Tin Cậy Mẫu"),
                    "Tỷ lệ thắng (%)": st.column_config.NumberColumn("Win Rate", format="%.1f%%"),
                    "Lợi suất TB (%)": st.column_config.NumberColumn("Lợi suất TB", format="%+.2f%%"),
                    "Vượt SPY (%)": st.column_config.NumberColumn("Excess vs SPY", format="%+.2f%%"),
                    "MFE TB (%)": st.column_config.NumberColumn("MFE TB", format="%+.2f%%"),
                    "MAE TB (%)": st.column_config.NumberColumn("MAE TB", format="%+.2f%%")
                }
            )
        else:
            st.info("Chưa có đủ mẫu hoàn tất để phân loại theo thứ trong tuần.")

    with wb_col2:
        st.markdown('<div style="font-size: 18px; font-weight: 700; color: #111111; margin: 24px 0 8px 0; font-family: \'Geist\', \'Inter\', sans-serif;">Thống Kê Theo Chiều Giao Dịch (Long vs Short)</div>', unsafe_allow_html=True)
        side_df = stats.get("side_breakdown", pd.DataFrame())
        if not side_df.empty:
            st.dataframe(
                side_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Mẫu Hoàn Tất": st.column_config.NumberColumn("Mẫu Hoàn Tất", format="%d"),
                    "Độ Tin Cậy": st.column_config.TextColumn("Độ Tin Cậy Mẫu"),
                    "Tỷ lệ thắng (%)": st.column_config.NumberColumn("Win Rate", format="%.1f%%"),
                    "Lợi suất TB (%)": st.column_config.NumberColumn("Lợi suất TB", format="%+.2f%%"),
                    "Vượt SPY (%)": st.column_config.NumberColumn("Excess vs SPY", format="%+.2f%%"),
                    "MFE TB (%)": st.column_config.NumberColumn("MFE TB", format="%+.2f%%"),
                    "MAE TB (%)": st.column_config.NumberColumn("MAE TB", format="%+.2f%%")
                }
            )
        else:
            st.info("Chưa có đủ mẫu hoàn tất để phân loại theo chiều giao dịch.")

    # Breakdown by Setup Type
    st.markdown('<div style="font-size: 18px; font-weight: 700; color: #111111; margin: 24px 0 8px 0; font-family: \'Geist\', \'Inter\', sans-serif;">Phân Nhóm Theo Loại Setup</div>', unsafe_allow_html=True)
    setup_df = stats.get("setup_breakdown", pd.DataFrame())
    if not setup_df.empty:
        st.dataframe(
            setup_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Mẫu Hoàn Tất": st.column_config.NumberColumn("Mẫu Hoàn Tất", format="%d"),
                "Mẫu Đang Chờ": st.column_config.NumberColumn("Đang Chờ", format="%d"),
                "Độ Tin Cậy": st.column_config.TextColumn("Độ Tin Cậy Mẫu"),
                "Tỷ lệ thắng (%)": st.column_config.NumberColumn("Win Rate", format="%.1f%%"),
                "Lợi suất TB (%)": st.column_config.NumberColumn("Lợi suất TB", format="%+.2f%%"),
                "Vượt SPY (%)": st.column_config.NumberColumn("Excess vs SPY", format="%+.2f%%"),
                "MFE TB (%)": st.column_config.NumberColumn("MFE TB", format="%+.2f%%"),
                "MAE TB (%)": st.column_config.NumberColumn("MAE TB", format="%+.2f%%")
            }
        )
    else:
        st.info("Chưa có đủ mẫu đã hoàn tất để phân tích theo từng setup.")

    # Breakdown by Candlestick Pattern Impact
    st.markdown('<div style="font-size: 18px; font-weight: 700; color: #111111; margin: 24px 0 8px 0; font-family: \'Geist\', \'Inter\', sans-serif;">Khảo Sát Mẫu Nến Trong Setup (Candlestick Edge Audit)</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 13.5px; color: #64748B; margin-bottom: 8px; font-family: \'Geist\', \'Inter\', sans-serif;">Kiểm tra giả thuyết: Trong cùng setup kỹ thuật, sự xuất hiện của mẫu nến phản ứng có tạo ra sự khác biệt về lợi suất và tỷ lệ thắng so với các nến không rõ mẫu hình hay không.</div>', unsafe_allow_html=True)

    setup_candle_df = stats.get("setup_candle_breakdown", pd.DataFrame())
    candle_df = stats.get("candle_breakdown", pd.DataFrame())

    if not setup_candle_df.empty:
        all_setups = ["Tất cả setup"] + sorted(list(setup_candle_df["Setup"].unique()))
        selected_setup = st.selectbox("Chọn setup để so sánh mẫu nến:", all_setups, key="perf_setup_filter")

        if selected_setup == "Tất cả setup":
            display_candle_df = candle_df if not candle_df.empty else setup_candle_df
        else:
            display_candle_df = setup_candle_df[setup_candle_df["Setup"] == selected_setup]

        st.dataframe(
            display_candle_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Mẫu Hoàn Tất": st.column_config.NumberColumn("Mẫu Hoàn Tất", format="%d"),
                "Mẫu Đang Chờ": st.column_config.NumberColumn("Đang Chờ", format="%d"),
                "Độ Tin Cậy": st.column_config.TextColumn("Độ Tin Cậy Mẫu"),
                "Tỷ lệ thắng (%)": st.column_config.NumberColumn("Win Rate", format="%.1f%%"),
                "Lợi suất TB (%)": st.column_config.NumberColumn("Lợi suất TB", format="%+.2f%%"),
                "Vượt SPY (%)": st.column_config.NumberColumn("Excess vs SPY", format="%+.2f%%"),
                "MFE TB (%)": st.column_config.NumberColumn("MFE TB", format="%+.2f%%"),
                "MAE TB (%)": st.column_config.NumberColumn("MAE TB", format="%+.2f%%")
            }
        )
    elif not candle_df.empty:
        st.dataframe(
            candle_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Mẫu Hoàn Tất": st.column_config.NumberColumn("Mẫu Hoàn Tất", format="%d"),
                "Mẫu Đang Chờ": st.column_config.NumberColumn("Đang Chờ", format="%d"),
                "Độ Tin Cậy": st.column_config.TextColumn("Độ Tin Cậy Mẫu"),
                "Tỷ lệ thắng (%)": st.column_config.NumberColumn("Win Rate", format="%.1f%%"),
                "Lợi suất TB (%)": st.column_config.NumberColumn("Lợi suất TB", format="%+.2f%%"),
                "Vượt SPY (%)": st.column_config.NumberColumn("Excess vs SPY", format="%+.2f%%"),
                "MFE TB (%)": st.column_config.NumberColumn("MFE TB", format="%+.2f%%"),
                "MAE TB (%)": st.column_config.NumberColumn("MAE TB", format="%+.2f%%")
            }
        )
    else:
        st.info("Chưa có đủ mẫu đã hoàn tất để phân tích tác động của từng mẫu nến.")

    # All Signals Log Table
    st.markdown(f'<div style="font-size: 18px; font-weight: 700; color: #111111; margin: 24px 0 8px 0; font-family: \'Geist\', \'Inter\', sans-serif;">Danh Sách Tín Hiệu & Diễn Biến ({horizon_map[horizon]})</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 13px; color: #64748B; margin-bottom: 8px; font-family: \'Geist\', \'Inter\', sans-serif;">* Các tín hiệu chưa đủ thời gian quan sát được đánh dấu là "Đang chờ". Tín hiệu vào phiên thứ Sáu trong mốc chốt tuần được đánh dấu "Không còn window tuần".</div>', unsafe_allow_html=True)

    log_rows = []
    for _, r in df_outcomes.iterrows():
        st_val = r.get("status", "pending")
        is_done = (st_val == "completed")
        is_nowin = (st_val == "no_window_in_week")

        status_text = "Hoàn tất" if is_done else ("Không window tuần" if is_nowin else "Đang chờ")

        log_rows.append({
            "Mã": r["symbol"],
            "Doanh nghiệp": r.get("company_name", r["symbol"]),
            "Chiều": r.get("side", "long").upper(),
            "Setup": r.get("setup_type", "-"),
            "Mẫu Nến": r.get("candle_pattern", "-"),
            "Ngành": r.get("sector", "-"),
            "Ngày Phát Hiện": r.get("first_detected_date"),
            "Thứ Vào Lệnh": r.get("entry_day_of_week") or "-",
            "Ngày Vào (Entry)": r.get("entry_date") or "Chờ phiên sau",
            "Giá Entry ($)": float(r["entry_price"]) if pd.notna(r.get("entry_price")) else None,
            "Ngày Thoát (Exit)": r.get("exit_date") if is_done else ("Bỏ qua" if is_nowin else "Đang chờ"),
            "Giá Exit ($)": float(r["exit_price"]) if is_done and pd.notna(r.get("exit_price")) else None,
            "Lợi Suất (%)": float(r["return_pct"]) if is_done and pd.notna(r.get("return_pct")) else None,
            "SPY (%)": float(r["spy_return_pct"]) if is_done and pd.notna(r.get("spy_return_pct")) else None,
            "Vượt SPY (%)": float(r["excess_return_spy"]) if is_done and pd.notna(r.get("excess_return_spy")) else None,
            "MFE (%)": float(r["mfe_pct"]) if is_done and pd.notna(r.get("mfe_pct")) else None,
            "MAE (%)": float(r["mae_pct"]) if is_done and pd.notna(r.get("mae_pct")) else None,
            "Vắt Cuối Tuần": "Có ⚠️" if r.get("crosses_weekend") else "Không",
            "Trạng Thái": status_text
        })

    df_log = pd.DataFrame(log_rows)
    st.dataframe(
        df_log,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Giá Entry ($)": st.column_config.NumberColumn(format="$%.2f"),
            "Giá Exit ($)": st.column_config.NumberColumn(format="$%.2f"),
            "Lợi Suất (%)": st.column_config.NumberColumn(format="%+.2f%%"),
            "SPY (%)": st.column_config.NumberColumn(format="%+.2f%%"),
            "Vượt SPY (%)": st.column_config.NumberColumn(format="%+.2f%%"),
            "MFE (%)": st.column_config.NumberColumn(format="%+.2f%%"),
            "MAE (%)": st.column_config.NumberColumn(format="%+.2f%%")
        }
    )

    # Download CSV
    csv_outcomes = df_log.to_csv(index=False)
    st.download_button(
        label=f"Xuất dữ liệu hiệu quả tín hiệu ({horizon_map[horizon]}) (CSV)",
        data=csv_outcomes,
        file_name=f"signal_performance_{horizon}d.csv",
        mime="text/csv"
    )

    # --- SHORTLIST & DECISION CLOSED-LOOP AUDIT [D-04] ---
    st.markdown('<div style="margin-top: 36px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="editorial-hero" style="font-size: 22px; margin-bottom: 4px;">Khảo Sát Quyết Định & Shortlist Thực Tế (Shortlist & Decision Audit)</div>', unsafe_allow_html=True)
    st.markdown('<div class="editorial-sub" style="font-size: 13.5px;">Phân tích vòng lặp đóng (Closed-Loop Review): So sánh diễn biến giữa các nhóm quyết định của Trader (Chọn vs Chờ vs Bỏ qua), đo lường độ xuyên phá Trigger và trượt giá (Slippage) từ Kế hoạch / Trigger đến Khớp thực tế.</div>', unsafe_allow_html=True)

    frozen_all = repo.get_frozen_shortlist() if (repo and hasattr(repo, "get_frozen_shortlist")) else []
    decisions_all = repo.get_trade_decisions() if (repo and hasattr(repo, "get_trade_decisions")) else []

    if frozen_all:
        f_symbols = list(set(f["symbol"] for f in frozen_all))
        min_date = min((f.get("session_date") for f in frozen_all if f.get("session_date")), default=None)
        shortlist_bars = repo.get_daily_bars(symbols=f_symbols, start_date=min_date) if min_date else pd.DataFrame()

        sh_eval = evaluate_shortlist_and_decision_outcomes(
            shortlist_items=frozen_all,
            decisions=decisions_all,
            daily_bars_df=shortlist_bars,
            horizons=[1, 3, 5]
        )

        dec_stats = sh_eval.get("decision_stats", {})
        slip = sh_eval.get("slippage_summary", {})

        s_col1, s_col2, s_col3, s_col4 = st.columns(4)
        s_col1.metric("Tổng Ứng Viên Shortlist", sh_eval.get("total_shortlist", 0))
        reviewed_count = sum(
            item["user_decision"] != "chưa ghi nhận"
            for item in sh_eval["evaluated_items"]
        )
        s_col2.metric("Số Quyết Định Trong Shortlist", reviewed_count)
        plan_slip = f"{slip['plan_to_fill_avg']:+.2f}%" if slip.get("plan_to_fill_avg") is not None else "-"
        s_col3.metric("Trượt Giá Plan → Fill", plan_slip, help="Mức chênh lệch trung bình giữa giá khớp thực tế và giá vào dự kiến trong kế hoạch.")
        trig_slip = f"{slip['trigger_to_fill_avg']:+.2f}%" if slip.get("trigger_to_fill_avg") is not None else "-"
        s_col4.metric("Trượt Giá Trigger → Fill", trig_slip, help="Mức chênh lệch trung bình giữa giá khớp thực tế và giá trigger quan sát.")

        if dec_stats:
            st.markdown("<div style='font-size: 15px; font-weight: 600; color: #111111; margin: 16px 0 6px 0;'>Thống Kê So Sánh Theo Quyết Định Của Trader:</div>", unsafe_allow_html=True)
            stat_rows = []
            dec_label_map = {
                "chon": "🟢 Chọn (Select & Plan)",
                "cho": "🟡 Chờ (Wait & Standby)",
                "bo_qua": "🔴 Bỏ qua (Pass / Reject)",
                "chưa ghi nhận": "⚪ Chưa ghi nhận quyết định"
            }
            for d_name, d_data in dec_stats.items():
                stat_rows.append({
                    "Quyết Định": dec_label_map.get(d_name, d_name),
                    "Số Ứng Viên": d_data.get("count", 0),
                    "Chạm Trigger (%)": f"{d_data.get('trigger_hit_pct', 0.0):.1f}%",
                    "Chạm SL (%)": f"{d_data.get('invalidation_hit_pct', 0.0):.1f}%",
                    "Lợi Suất Benchmark 1d": f"{d_data['avg_return_1d']:+.2f}%" if d_data.get("avg_return_1d") is not None else "-",
                    "Lợi Suất Benchmark 3d": f"{d_data['avg_return_3d']:+.2f}%" if d_data.get("avg_return_3d") is not None else "-",
                    "Lợi Suất Benchmark 5d": f"{d_data['avg_return_5d']:+.2f}%" if d_data.get("avg_return_5d") is not None else "-",
                    "Win Rate Benchmark 3d": f"{d_data['win_rate_3d']:.1f}%" if d_data.get("win_rate_3d") is not None else "-",
                    "Số Lệnh Khớp": d_data.get("fill_count", 0),
                    "Lợi Suất Khớp Thực Tế 3d": f"{d_data['avg_fill_return_3d']:+.2f}%" if d_data.get("avg_fill_return_3d") is not None else "-"
                })
            st.dataframe(pd.DataFrame(stat_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có ứng viên nào trong Shortlist đóng băng để đánh giá vòng lặp quyết định.")
