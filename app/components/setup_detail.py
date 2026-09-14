"""
Setup Detail Component.
Renders deep analytical drill-down for a selected candidate setup:
- Multi-timeframe context (Daily + Weekly with unclosed week badge)
- Technical reference levels (Trigger, Invalidation, Support, Resistance) and methods
- Volatility (ATR14, ATR%, distances in % and ATR units)
- Liquidity (20d average volume, 20d dollar volume, relative volume)
- Checklist of rules (Pass / Fail / N/A)
- Point-in-time compact chart with MAs and key levels (No lookahead into future bars)
- Direct TradingView link and analytical export table for Excel
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from storage.repository import MarketRadarRepository

def _format_val(val: Optional[float], prefix: str = "", suffix: str = "", digits: int = 2) -> str:
    if val is None or pd.isna(val):
        return "N/A"
    return f"{prefix}{val:.{digits}f}{suffix}"

def _render_html(html_str: str):
    if hasattr(st, "html"):
        st.html(html_str)
    else:
        st.markdown(html_str, unsafe_allow_html=True)

def render_setup_detail_modal(
    candidate: Dict[str, Any],
    as_of: str,
    repo: Optional[MarketRadarRepository] = None,
    key_suffix: str = ""
):
    """Render setup detail drill-down."""
    if not candidate:
        st.info("Chưa có ứng viên nào được chọn.")
        return

    sym = candidate["symbol"]
    company_name = candidate.get("company_name", sym)
    sector = candidate.get("sector", "N/A")
    sub_industry = candidate.get("sub_industry", "N/A")
    group_type = candidate.get("group_type", "N/A")
    setup_type = candidate.get("setup_type", "Chưa phân loại")
    status = candidate.get("status", "N/A")
    close_price = candidate.get("close_price")
    score = candidate.get("score", 0.0)
    tv_url = candidate.get("tv_url") or f"https://www.tradingview.com/chart/?symbol={sym}&interval=D"
    if "interval=" not in tv_url:
        tv_url = f"{tv_url}{'&' if '?' in tv_url else '?'}interval=D"

    group_labels = {
        "long_cont": "Long Tiếp Diễn (Trend Continuation)",
        "short_cont": "Short Tiếp Diễn (Downtrend Continuation)",
        "long_rev": "Long Đảo Chiều (Reversal / Mean Reversion)",
        "short_rev": "Short Đảo Chiều (Short Reversal)",
        "watchlist": "Danh sách Theo dõi (Watchlist / Contradiction)"
    }
    group_title = group_labels.get(group_type, group_type)

    # Header section
    _render_html(f"""
    <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 8px; padding: 20px 24px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
            <div>
                <div style="display: flex; align-items: baseline; gap: 10px;">
                    <span style="font-family: 'Geist Mono', monospace; font-size: 30px; font-weight: 700; color: #111111;">{sym}</span>
                    <span style="font-size: 16px; color: #787774; font-weight: 500;">{company_name}</span>
                </div>
                <div style="font-size: 13.5px; color: #787774; margin-top: 5px;">
                    <span><b>Ngành:</b> {sector} &middot; {sub_industry}</span>
                    <span style="margin-left: 12px;"><b>Nhóm:</b> {group_title}</span>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <a href="{tv_url}" target="_blank" style="text-decoration: none;">
                    <button style="background-color: #111111; color: #FFFFFF; border: none; border-radius: 4px; padding: 9px 18px; font-size: 14px; font-weight: 500; cursor: pointer;">
                        Mở trên TradingView ↗
                    </button>
                </a>
            </div>
        </div>
    </div>
    """)

    # 1. Multi-timeframe context & Volatility overview cards
    weekly_ctx = candidate.get("weekly_context", {})
    w_trend = weekly_ctx.get("weekly_trend", "Chưa đủ dữ liệu")
    is_week_closed = weekly_ctx.get("is_week_closed", True)
    w_note = weekly_ctx.get("provisional_note", "")

    w_badge = '<span style="background: #EDF3EC; color: #346538; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">Đã đóng tuần</span>' if is_week_closed else '<span style="background: #FEF3D6; color: #8F6B00; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">Tuần chưa đóng (Tạm thời)</span>'

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _render_html("""
        <div style="background: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 14px 16px;">
            <div style="font-size: 12.5px; text-transform: uppercase; color: #787774; font-weight: 600;">Giá & Điểm số</div>
            <div style="font-family: 'Geist Mono', monospace; font-size: 24px; font-weight: 700; color: #111111; margin: 4px 0;">
                ${:.2f}
            </div>
            <div style="font-size: 13px; color: #787774;">Score: <b>{:.1f}</b> &middot; Rank: <b>#{}</b></div>
        </div>
        """.format(
            close_price or 0.0,
            score,
            candidate.get("rank") or "N/A"
        ))

    with c2:
        atr_val = candidate.get("atr14")
        atr_p = candidate.get("atr_pct")
        _render_html(f"""
        <div style="background: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 14px 16px;">
            <div style="font-size: 12.5px; text-transform: uppercase; color: #787774; font-weight: 600;">Biến động (ATR 14)</div>
            <div style="font-family: 'Geist Mono', monospace; font-size: 24px; font-weight: 700; color: #111111; margin: 4px 0;">
                {_format_val(atr_val, prefix='$')}
            </div>
            <div style="font-size: 13px; color: #787774;">ATR%: <b>{_format_val(atr_p, suffix='%')}</b></div>
        </div>
        """)

    with c3:
        d_vol = candidate.get("avg_dollar_vol20")
        r_vol = candidate.get("rel_volume")
        d_vol_str = f"${(d_vol/1e6):.1f}M" if d_vol else "N/A"
        _render_html(f"""
        <div style="background: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 14px 16px;">
            <div style="font-size: 12.5px; text-transform: uppercase; color: #787774; font-weight: 600;">Thanh khoản (20D)</div>
            <div style="font-family: 'Geist Mono', monospace; font-size: 24px; font-weight: 700; color: #111111; margin: 4px 0;">
                {d_vol_str}
            </div>
            <div style="font-size: 13px; color: #787774;">Relative Vol: <b>{_format_val(r_vol, suffix='x')}</b></div>
        </div>
        """)

    with c4:
        _render_html(f"""
        <div style="background: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 14px 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 12.5px; text-transform: uppercase; color: #787774; font-weight: 600;">Khung Tuần</span>
                {w_badge}
            </div>
            <div style="font-size: 15px; font-weight: 600; color: #111111; margin: 6px 0 2px 0;">
                {w_trend}
            </div>
            <div style="font-size: 12.5px; color: #787774;">MA10w: {_format_val(weekly_ctx.get('weekly_ma10'), prefix='$')} &middot; MA30w: {_format_val(weekly_ctx.get('weekly_ma30'), prefix='$')}</div>
        </div>
        """)

    # Pre-fetch data for all modal tabs
    as_of_clean = str(as_of).split()[0] if as_of else ""
    full_bars = pd.DataFrame()
    chart_bars = pd.DataFrame()
    if repo:
        raw_bars = repo.get_daily_bars(symbols=[sym])
        if not raw_bars.empty:
            # Strictly filter bars up to snapshot as_of (NO LOOKAHEAD!)
            full_bars = raw_bars[raw_bars["date"].dt.strftime("%Y-%m-%d") <= as_of_clean].sort_values("date").copy()
            if len(full_bars) >= 10:
                full_bars["ma20"] = full_bars["close"].rolling(20).mean()
                full_bars["ma50"] = full_bars["close"].rolling(50).mean()
                # Compute true MA200 on full historical window
                if len(full_bars) >= 200:
                    full_bars["ma200"] = full_bars["close"].rolling(200).mean()
                elif len(full_bars) >= 100:
                    full_bars["ma200"] = full_bars["close"].rolling(200, min_periods=100).mean()
                else:
                    full_bars["ma200"] = None
                chart_bars = full_bars.tail(90).copy()

    candlestick_data = candidate.get("candlestick_analysis") or candidate.get("evidence_json", {}).get("candlestick", {})
    if not candlestick_data and not full_bars.empty and len(full_bars) >= 2:
        from analytics.setup_analyzer import analyze_candlestick, interpret_candlestick_in_setup, CANDLESTICK_THRESHOLDS
        last_b = full_bars.iloc[-1]
        p_b = full_bars.iloc[-2]
        c_res = analyze_candlestick(
            open_p=float(last_b["open"]),
            high_p=float(last_b["high"]),
            low_p=float(last_b["low"]),
            close_p=float(last_b["close"]),
            atr14=candidate.get("atr14"),
            prev_open=float(p_b["open"]),
            prev_high=float(p_b["high"]),
            prev_low=float(p_b["low"]),
            prev_close=float(p_b["close"]),
            bar_date=last_b["date"].strftime("%Y-%m-%d")
        )
        c_int = interpret_candlestick_in_setup(
            candle=c_res,
            setup_subtype=setup_type,
            group_type=group_type,
            close_price=float(last_b["close"]),
            ma20=float(last_b.get("ma20")) if pd.notna(last_b.get("ma20")) else candidate.get("support_level"),
            ma50=float(last_b.get("ma50")) if pd.notna(last_b.get("ma50")) else None,
            prev_high20=candidate.get("resistance_level"),
            prev_low20=candidate.get("support_level"),
            trigger_price=candidate.get("trigger_price"),
            invalidation_price=candidate.get("invalidation_price"),
            dist_ma20_atr=candidate.get("dist_ma20_atr"),
            extension_status=candidate.get("evidence_json", {}).get("volatility", {}).get("extension_status", "Bình thường"),
            bar_date=last_b["date"].strftime("%Y-%m-%d")
        )
        candlestick_data = {
            "features": c_res,
            "interpretation": c_int,
            "thresholds": CANDLESTICK_THRESHOLDS
        }

    fa_flags = candidate.get("fa_flags", {})
    if (not fa_flags or not isinstance(fa_flags, dict) or not fa_flags.get("has_data")) and repo:
        try:
            from analytics.company_fa import evaluate_fa_flags
            fa_df = repo.get_fundamentals([sym])
            if not fa_df.empty:
                fa_raw = fa_df.iloc[0].to_dict()
                ref_d = as_of_clean if as_of_clean else None
                fa_flags = evaluate_fa_flags(sym, fa_raw, ref_date=ref_d)
        except Exception:
            pass

    pressure_data = candidate.get("multi_session_pressure") or candidate.get("evidence_json", {}).get("multi_session_pressure")
    if (not pressure_data or pressure_data.get("n_sessions", 0) < 5) and not full_bars.empty:
        try:
            from analytics.setup_analyzer import analyze_multi_session_pressure
            side_val = "short" if "short" in group_type else "long"
            pressure_data = analyze_multi_session_pressure(
                symbol=sym,
                bars=full_bars,
                atr14=candidate.get("atr14"),
                side=side_val,
                stock_dict=candidate,
                as_of=as_of_clean
            )
        except Exception:
            pass

    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

    # 3-Tab internal navigation: Technical & Candle, Company & FA, Checklist
    tab_tech, tab_fa, tab_check = st.tabs([
        "📈 Kỹ Thuật & Mẫu Nến",
        "🏢 Doanh Nghiệp & BCTC",
        "✅ Checklist Điều Kiện"
    ])

    # --- TAB 1: KỸ THUẬT & MẪU NẾN ---
    with tab_tech:
        st.markdown('<div style="font-size: 14.5px; font-weight: 600; color: #111111; margin: 12px 0 8px 0;">Biểu đồ Kỹ thuật & Các Mức Setup Tham chiếu (Point-in-Time)</div>', unsafe_allow_html=True)

        if not chart_bars.empty and len(chart_bars) >= 10:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.04,
                row_heights=[0.72, 0.28]
            )

            # Candlestick
            fig.add_trace(
                go.Candlestick(
                    x=chart_bars["date"],
                    open=chart_bars["open"],
                    high=chart_bars["high"],
                    low=chart_bars["low"],
                    close=chart_bars["close"],
                    name="OHLC",
                    increasing_line_color="#26A69A",
                    decreasing_line_color="#EF5350"
                ),
                row=1, col=1
            )

            # Moving averages
            fig.add_trace(go.Scatter(x=chart_bars["date"], y=chart_bars["ma20"], name="MA20", line=dict(color="#2962FF", width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_bars["date"], y=chart_bars["ma50"], name="MA50", line=dict(color="#FF6D00", width=1.5)), row=1, col=1)
            if "ma200" in chart_bars.columns and chart_bars["ma200"].notna().any():
                fig.add_trace(go.Scatter(x=chart_bars["date"], y=chart_bars["ma200"], name="MA200", line=dict(color="#9E9E9E", width=1.5, dash="dot")), row=1, col=1)

            # Horizontal reference lines
            trig_p = candidate.get("trigger_price")
            inv_p = candidate.get("invalidation_price")
            sup_p = candidate.get("support_level")
            res_p = candidate.get("resistance_level")

            if trig_p:
                fig.add_hline(y=trig_p, line_dash="dash", line_color="#2E7D32", annotation_text=f"Trigger ${trig_p:.2f}", annotation_position="top right", row=1, col=1)
            if inv_p:
                fig.add_hline(y=inv_p, line_dash="dot", line_color="#C62828", annotation_text=f"Invalidation ${inv_p:.2f}", annotation_position="bottom right", row=1, col=1)
            if sup_p and sup_p != inv_p:
                fig.add_hline(y=sup_p, line_dash="dot", line_color="#1565C0", opacity=0.5, annotation_text=f"Support ${sup_p:.2f}", annotation_position="bottom left", row=1, col=1)
            if res_p and res_p != trig_p:
                fig.add_hline(y=res_p, line_dash="dot", line_color="#E65100", opacity=0.5, annotation_text=f"Resistance ${res_p:.2f}", annotation_position="top left", row=1, col=1)

            # Volume bars
            vol_colors = ["#26A69A" if c >= o else "#EF5350" for c, o in zip(chart_bars["close"], chart_bars["open"])]
            fig.add_trace(go.Bar(x=chart_bars["date"], y=chart_bars["volume"], name="Volume", marker_color=vol_colors, opacity=0.8), row=2, col=1)

            # 20-day Volume MA
            if len(chart_bars) >= 20:
                vol_ma20 = chart_bars["volume"].rolling(20).mean()
                fig.add_trace(go.Scatter(x=chart_bars["date"], y=vol_ma20, name="Vol MA20", line=dict(color="#787774", width=1)), row=2, col=1)

            fig.update_layout(
                height=420,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_rangeslider_visible=False,
                template="plotly_white",
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=12)),
                font=dict(family="'Geist', 'Inter', -apple-system, sans-serif")
            )
            chart_key = f"chart_{sym}_{key_suffix}" if key_suffix else f"chart_{sym}"
            st.plotly_chart(fig, use_container_width=True, key=chart_key)
        else:
            st.info(f"Không có đủ dữ liệu nến lịch sử cho mã {sym} tính đến thời điểm {as_of}.")

        st.markdown('<div style="font-size: 16px; font-weight: 600; color: #111111; margin: 20px 0 8px 0;">Bảng Mức Tham Chiếu Phân Tích (Technical Reference Levels)</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 13.5px; color: #787774; margin-bottom: 12px;">Các mức giá được xác định theo quy tắc kỹ thuật khách quan để bạn đưa vào Excel theo dõi.</div>', unsafe_allow_html=True)

        levels_data = [
            {
                "Thông số": "Giá Đóng Cửa (Close)",
                "Mức giá": f"${candidate.get('close_price', 0.0):.2f}" if candidate.get('close_price') else "N/A",
                "Chênh lệch / Tỷ lệ": "0.00%",
                "Khoảng cách (ATR)": "0.00 ATR",
                "Phương pháp & Căn cứ xác định": f"Nến EOD chốt phiên giao dịch ngày {as_of}"
            },
            {
                "Thông số": "Giá Kích Hoạt (Trigger)",
                "Mức giá": _format_val(candidate.get("trigger_price"), prefix='$'),
                "Chênh lệch / Tỷ lệ": _format_val(candidate.get("dist_trigger_pct"), suffix='%'),
                "Khoảng cách (ATR)": _format_val(candidate.get("dist_trigger_atr"), suffix=' ATR'),
                "Phương pháp & Căn cứ xác định": candidate.get("trigger_condition") or "N/A"
            },
            {
                "Thông số": "Mức Vô Hiệu Hóa (Invalidation)",
                "Mức giá": _format_val(candidate.get("invalidation_price"), prefix='$'),
                "Chênh lệch / Tỷ lệ": f"{((candidate.get('invalidation_price') - close_price)/close_price*100):+.2f}%" if (candidate.get('invalidation_price') and close_price) else "N/A",
                "Khoảng cách (ATR)": f"{((candidate.get('invalidation_price') - close_price)/atr_val):+.2f} ATR" if (candidate.get('invalidation_price') and close_price and atr_val) else "N/A",
                "Phương pháp & Căn cứ xác định": candidate.get("invalidation_condition") or "N/A"
            },
            {
                "Thông số": "Hỗ Trợ Tham Chiếu (Support)",
                "Mức giá": _format_val(candidate.get("support_level"), prefix='$'),
                "Chênh lệch / Tỷ lệ": f"{((candidate.get('support_level') - close_price)/close_price*100):+.2f}%" if (candidate.get('support_level') and close_price) else "N/A",
                "Khoảng cách (ATR)": f"{((candidate.get('support_level') - close_price)/atr_val):+.2f} ATR" if (candidate.get('support_level') and close_price and atr_val) else "N/A",
                "Phương pháp & Căn cứ xác định": candidate.get("support_basis") or "N/A"
            },
            {
                "Thông số": "Kháng Cự Tham Chiếu (Resistance)",
                "Mức giá": _format_val(candidate.get("resistance_level"), prefix='$'),
                "Chênh lệch / Tỷ lệ": f"{((candidate.get('resistance_level') - close_price)/close_price*100):+.2f}%" if (candidate.get('resistance_level') and close_price) else "N/A",
                "Khoảng cách (ATR)": f"{((candidate.get('resistance_level') - close_price)/atr_val):+.2f} ATR" if (candidate.get('resistance_level') and close_price and atr_val) else "N/A",
                "Phương pháp & Căn cứ xác định": candidate.get("resistance_basis") or "N/A"
            },
            {
                "Thông số": "Đường Trung Bình MA20",
                "Mức giá": f"${(close_price / (1 + (candidate.get('dist_ma20_pct') or 0)/100)):.2f}" if candidate.get('dist_ma20_pct') is not None and close_price else "N/A",
                "Chênh lệch / Tỷ lệ": _format_val(candidate.get("dist_ma20_pct"), suffix='%'),
                "Khoảng cách (ATR)": _format_val(candidate.get("dist_ma20_atr"), suffix=' ATR'),
                "Phương pháp & Căn cứ xác định": "Đường trung bình động 20 phiên gần nhất (Short-term trend)"
            }
        ]

        df_levels = pd.DataFrame(levels_data)
        st.dataframe(df_levels, use_container_width=True, hide_index=True)

        # Download Excel/CSV button for these reference levels
        csv_ref = df_levels.to_csv(index=False)
        dl_key = f"dl_{sym}_{key_suffix}" if key_suffix else f"dl_{sym}"
        st.download_button(
            label=f"Xuất mức kỹ thuật {sym} (CSV cho Excel)",
            data=csv_ref,
            file_name=f"{sym}_setup_levels_{as_of}.csv",
            mime="text/csv",
            key=dl_key
        )

        st.markdown('<div style="height: 12px;"></div>', unsafe_allow_html=True)

        # Candlestick Recognition & Price Reaction (grouped into Technical)
        st.markdown('<div style="font-size: 16px; font-weight: 600; color: #111111; margin: 12px 0 8px 0;">Nhận Diện Nến Gần Nhất Đã Đóng & Phản Ứng Giá (Daily Candlestick)</div>', unsafe_allow_html=True)
        if candlestick_data:
            features = candlestick_data.get("features", {})
            interp = candlestick_data.get("interpretation", {})
            pattern_name = features.get("pattern", "Không rõ mẫu hình")
            bar_date = features.get("date", as_of_clean)
            react_stt = interp.get("reaction_status", "neutral")
            react_color = "#346538" if react_stt == "pass" else ("#9F2F2D" if react_stt == "fail" else "#8F6B00")

            # Layer 1 Metrics Formatting
            b_ratio = round((features.get("body_ratio") or 0.0) * 100)
            up_ratio = round((features.get("upper_shadow_ratio") or 0.0) * 100)
            low_ratio = round((features.get("lower_shadow_ratio") or 0.0) * 100)
            c_pos = round(features.get("close_position_pct", 50.0))
            r_atr_str = _format_val(features.get("range_to_atr"), suffix="x ATR")
            dir_label = features.get("direction", "Cân bằng")

            candlestick_html = (
                f'<div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 8px; padding: 18px 22px; margin-bottom: 16px;">'
                f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #F0F0F0; padding-bottom: 8px;">'
                f'<div style="font-size: 14px; font-weight: 600; color: #111111;">'
                f'Phiên giao dịch đã đóng: <span style="font-family: \'Geist Mono\', monospace; color: #2962FF;">{bar_date}</span>'
                f'</div>'
                f'<div>'
                f'<span style="background: #F0F4F8; color: #1E3A8A; padding: 3px 10px; border-radius: 4px; font-size: 13px; font-weight: 600;">{pattern_name}</span>'
                f'</div>'
                f'</div>'
                f'<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; padding: 12px 14px; background: #F7F6F3; border-radius: 6px;">'
                f'<div>'
                f'<div style="font-size: 12px; color: #787774; text-transform: uppercase; font-weight: 600;">Lớp 1: Chiều & Thân</div>'
                f'<div style="font-size: 14.5px; font-weight: 600; color: #111111; margin-top: 2px;">{dir_label} ({b_ratio}% range)</div>'
                f'</div>'
                f'<div>'
                f'<div style="font-size: 12px; color: #787774; text-transform: uppercase; font-weight: 600;">Râu Trên / Râu Dưới</div>'
                f'<div style="font-size: 14.5px; font-weight: 600; color: #111111; margin-top: 2px;">{up_ratio}% / {low_ratio}%</div>'
                f'</div>'
                f'<div>'
                f'<div style="font-size: 12px; color: #787774; text-transform: uppercase; font-weight: 600;">Vị Trí Đóng Cửa</div>'
                f'<div style="font-size: 14.5px; font-weight: 600; color: #111111; margin-top: 2px;">{c_pos}% biên độ</div>'
                f'</div>'
                f'<div>'
                f'<div style="font-size: 12px; color: #787774; text-transform: uppercase; font-weight: 600;">Biên Độ / ATR14</div>'
                f'<div style="font-size: 14.5px; font-weight: 600; color: #111111; margin-top: 2px;">{r_atr_str}</div>'
                f'</div>'
                f'</div>'
                f'<div style="font-size: 12.5px; text-transform: uppercase; color: #787774; font-weight: 600; margin-bottom: 6px;">Lớp 2: Mẫu Hình & Bối Cảnh Phản Ứng Trong Setup</div>'
                f'<div style="font-size: 14.5px; color: #2F3437; line-height: 1.8;">'
                f'<div style="margin-bottom: 6px;">'
                f'<b style="color: #111111;">&bull; Nến gần nhất:</b> {interp.get("candle_summary", "N/A")}'
                f'</div>'
                f'<div style="margin-bottom: 6px;">'
                f'<b style="color: #111111;">&bull; Bối cảnh:</b> {interp.get("context_summary", "N/A")}'
                f'</div>'
                f'<div>'
                f'<b style="color: #111111;">&bull; Trạng thái phản ứng:</b> <span style="color: {react_color}; font-weight: 500;">{interp.get("reaction_summary", "N/A")}</span>'
                f'</div>'
                f'</div>'
                f'</div>'
            )
            _render_html(candlestick_html)

            with st.expander("Công bố ngưỡng nhận diện mẫu nến (Candlestick Rules & Thresholds)"):
                st.markdown(r"""
                - **Doji:** Thân nến co cụm $\le 10\%$ tổng biên độ phiên (`body / range <= 0.10`).
                - **Thân dài (Marubozu):** Thân nến áp đảo $\ge 70\%$ tổng biên độ phiên (`body / range >= 0.70`).
                - **Râu dưới dài (Hammer / Pinbar):** Râu dưới $\ge 55\%$ biên độ, râu trên $\le 25\%$ biên độ, đóng cửa ở nửa trên phiên ($\ge 55\%$ biên độ).
                - **Râu trên dài (Shooting Star):** Râu trên $\ge 55\%$ biên độ, râu dưới $\le 25\%$ biên độ, đóng cửa ở nửa dưới phiên ($\le 45\%$ biên độ).
                - **Nhấn chìm (Engulfing):** Thân nến bao trọn toàn bộ thân nến phiên trước và ngược chiều (Bullish / Bearish).
                - **Inside bar:** Toàn bộ biên độ (High - Low) nằm gọn bên trong biên độ phiên trước.
                - **Outside bar:** Biên độ mở rộng vượt cả Đỉnh và Đáy phiên trước.
                - **Không rõ mẫu hình:** Các nến tiêu chuẩn dao động bình thường không thỏa mãn các tiêu chí định lượng trên.
                - **Nguyên tắc bối cảnh:** Tách bạch hình thái nến khỏi vị trí xuất hiện (Ví dụ: Râu dưới dài tại MA20 trong pullback có ý nghĩa xác nhận phản ứng hỗ trợ; sau khi giá tăng xa MA20 $>1.5$ ATR thì tiềm ẩn rủi ro mua đuổi).
                """)
        else:
            st.info("Chưa có dữ liệu nến nhật gần nhất cho ứng viên này.")

        # Multi-Session Buying/Selling Pressure Profile
        st.markdown('<div style="font-size: 16px; font-weight: 600; color: #111111; margin: 20px 0 8px 0;">Hồ Sơ Áp Lực Mua/Bán Đa Phiên (Multi-Session Pressure Profile)</div>', unsafe_allow_html=True)
        if pressure_data:
            bias_label = pressure_data.get("pressure_bias", "Đang theo dõi")
            bias_bg = "#EDF3EC" if "mua" in bias_label.lower() else ("#FDEBEC" if "bán" in bias_label.lower() else "#F7F6F3")
            bias_color = "#346538" if "mua" in bias_label.lower() else ("#9F2F2D" if "bán" in bias_label.lower() else "#2F3437")

            _render_html(f"""
            <div style="background-color: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 8px; padding: 16px 20px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 12.5px; font-weight: 600; text-transform: uppercase; color: #787774;">Đánh Giá Áp Lực Đa Phiên (1/3/5 Phiên)</span>
                    <span style="background: {bias_bg}; color: {bias_color}; font-size: 12.5px; font-weight: 600; padding: 2px 8px; border-radius: 4px;">{bias_label}</span>
                </div>
                <div style="font-size: 13px; color: #787774; line-height: 1.5;">{pressure_data.get('methodology_note', '')}</div>
            </div>
            """)

            s_rows = pressure_data.get("sessions", [])
            if s_rows:
                tbl_records = []
                for s in s_rows:
                    ret_str = f"{s['return_1d']:+.2f}%" if s.get('return_1d') is not None else "N/A"
                    rvol_str = f"{s['rvol']:.2f}x" if s.get('rvol') is not None else "N/A"
                    cpos_str = f"{s['close_position_pct']:.1f}%" if s.get('close_position_pct') is not None else "Flat"
                    sp_str = f"{s['spread_to_atr']:.2f}x ATR" if s.get('spread_to_atr') is not None else "N/A"
                    tbl_records.append({
                        "Ngày": s["date"],
                        "Giá Đóng": f"${s['close']:.2f}",
                        "1D Return": ret_str,
                        "RVOL (20D Median)": rvol_str,
                        "Vị trí Đóng (% Biên độ)": cpos_str,
                        "Biên độ / ATR14": sp_str,
                        "Chiều Nến": s["direction"]
                    })
                st.dataframe(pd.DataFrame(tbl_records), use_container_width=True, hide_index=True)

            col_sup, col_contra, col_gaps = st.columns(3)
            with col_sup:
                st.markdown("<div style='font-size: 12.5px; font-weight: 600; color: #346538; margin-bottom: 6px;'>🟢 BẰNG CHỨNG HỖ TRỢ</div>", unsafe_allow_html=True)
                for sup in pressure_data.get("supporting_evidence", []):
                    st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; line-height: 1.5; margin-bottom: 4px;'>&bull; {sup}</div>", unsafe_allow_html=True)
            with col_contra:
                st.markdown("<div style='font-size: 12.5px; font-weight: 600; color: #9F2F2D; margin-bottom: 6px;'>🔴 BẰNG CHỨNG TRÁI CHIỀU</div>", unsafe_allow_html=True)
                for con in pressure_data.get("contradicting_evidence", []):
                    st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; line-height: 1.5; margin-bottom: 4px;'>&bull; {con}</div>", unsafe_allow_html=True)
            with col_gaps:
                st.markdown("<div style='font-size: 12.5px; font-weight: 600; color: #787774; margin-bottom: 6px;'>⚪ KHOẢNG TRỐNG / TRUNG TÍNH</div>", unsafe_allow_html=True)
                for gap in pressure_data.get("neutral_gaps", []):
                    st.markdown(f"<div style='font-size: 13.5px; color: #787774; line-height: 1.5; margin-bottom: 4px;'>&bull; {gap}</div>", unsafe_allow_html=True)
        else:
            st.info("Chưa có hồ sơ áp lực mua/bán đa phiên cho mã này.")

    # --- TAB 2: DOANH NGHIỆP & BCTC ---
    with tab_fa:
        st.markdown('<div style="font-size: 16px; font-weight: 600; color: #111111; margin: 12px 0 8px 0;">Bối Cảnh Doanh Nghiệp & Lịch Công Bố BCTC (Fundamental Context)</div>', unsafe_allow_html=True)
        if fa_flags and isinstance(fa_flags, dict) and fa_flags.get("has_data"):
            metrics = fa_flags.get("metrics", {})
            fiscal_period = fa_flags.get("fiscal_period") or metrics.get("fiscal_period", "Chưa xác minh kỳ")
            period_end = fa_flags.get("period_end") or metrics.get("period_end", "Chưa xác minh")
            period_type = fa_flags.get("period_type") or "Chỉ số tổng hợp Yahoo (YoY)"
            currency = fa_flags.get("currency") or "USD"
            retrieved_at = fa_flags.get("retrieved_at") or metrics.get("retrieved_at", "N/A")
            source = fa_flags.get("source") or "Yahoo Finance (Số liệu tổng hợp / Aggregate)"
            sec_filing_url = fa_flags.get("sec_filing_url") or f"https://www.sec.gov/edgar/browse/?CIK={sym}"

            _render_html(f"""
            <div style="background: #F7F6F3; border: 1px solid #EAEAEA; border-radius: 6px; padding: 12px 16px; font-size: 13.5px; color: #787774; margin-bottom: 12px; line-height: 1.6;">
                <b>Kỳ kết thúc (MRQ):</b> <span style="color: #111111; font-weight: 600;">{period_end}</span> &middot;
                <b>Cơ sở so sánh:</b> <span style="color: #111111; font-weight: 600;">{period_type}</span> &middot;
                <b>Đơn vị:</b> <span style="color: #111111; font-weight: 600;">{currency}</span> &middot;
                <b>Nguồn cấp:</b> <span style="color: #111111; font-weight: 600;">{source}</span> &middot;
                <b>Thu thập lúc:</b> <span style="color: #111111; font-weight: 600;">{retrieved_at}</span>
            </div>
            """)

            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Doanh thu YoY", metrics.get("rev_growth_str", "N/A"))
            f2.metric("EPS YoY", metrics.get("eps_growth_str", "N/A"))
            f3.metric("Biên Lợi Nhuận Ròng", metrics.get("profit_margin_str", "N/A"))
            f4.metric("Kỳ BCTC Tiếp Theo", fa_flags.get("earnings_status", "Chưa xác minh"))

            flags_list = fa_flags.get("flags", [])
            if flags_list:
                st.markdown("<div style='margin-top: 10px;'>", unsafe_allow_html=True)
                for f in flags_list:
                    if "Cảnh báo" in f or "⚠️" in f:
                        clean_f = f.replace("⚠️", "").strip()
                        st.markdown(f"<div style='font-size: 13.5px; color: #9F2F2D; background: #FDEBEC; padding: 4px 8px; border-radius: 4px; display: inline-block; margin-right: 8px; margin-bottom: 6px;'>⚠️ {clean_f}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='font-size: 14.5px; color: #2F3437; line-height: 1.6;'>&bull; {f}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
            st.link_button("Tra cứu hồ sơ BCTC trên SEC EDGAR ↗", sec_filing_url, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu cơ bản (FA) lưu trong cơ sở dữ liệu local cho mã này.")

    # --- TAB 3: CHECKLIST & ĐIỀU KIỆN ---
    with tab_check:
        st.markdown('<div style="font-size: 16px; font-weight: 600; color: #111111; margin: 12px 0 8px 0;">Checklist Kiểm Định Điều Kiện Setup</div>', unsafe_allow_html=True)
        checklist = candidate.get("checklist", [])
        if checklist:
            for item in checklist:
                stt = item.get("status", "pass")
                crit = item.get("criterion", "")
                detail = item.get("detail", "")

                if stt == "pass":
                    badge_html = '<span style="background: #EDF3EC; color: #346538; padding: 3px 9px; border-radius: 4px; font-size: 12.5px; font-weight: 600;">ĐẠT / PASS</span>'
                elif stt == "fail":
                    badge_html = '<span style="background: #FDEBEC; color: #9F2F2D; padding: 3px 9px; border-radius: 4px; font-size: 12.5px; font-weight: 600;">CHƯA ĐẠT / FAIL</span>'
                else:
                    badge_html = '<span style="background: #FEF3D6; color: #8F6B00; padding: 3px 9px; border-radius: 4px; font-size: 12.5px; font-weight: 600;">THIẾU DỮ LIỆU / N/A</span>'

                _render_html(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; background: #FFFFFF; border: 1px solid #EAEAEA; border-radius: 6px; padding: 12px 18px; margin-bottom: 6px;">
                    <div style="font-size: 14px; color: #111111; font-weight: 500;">
                        <b>{crit}:</b> <span style="color: #787774; font-weight: 400;">{detail}</span>
                    </div>
                    <div>{badge_html}</div>
                </div>
                """)
        else:
            tech_reasons = candidate.get("technical_reasons", [])
            for r in tech_reasons:
                st.markdown(f"- {r}")

        # Caveats & Notes
        if candidate.get("short_caveat"):
            st.markdown(f"<div style='margin-top: 12px; font-size: 13.5px; color: #9F2F2D; background: #FDEBEC; padding: 8px 12px; border-radius: 4px;'><b>⚠️ Lưu ý Short:</b> {candidate['short_caveat']}</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        st.link_button(f"Mở toàn màn hình biểu đồ {sym} trên TradingView ↗", tv_url, use_container_width=True)

def show_setup_detail_dialog(
    candidate: Dict[str, Any],
    as_of: str,
    repo: Optional[MarketRadarRepository] = None,
    key_suffix: str = ""
):
    """Unified modal dialog or expander for setup technical detail."""
    if hasattr(st, "dialog"):
        try:
            @st.dialog("Chi tiết Kỹ thuật Setup", width="large")
            def _dialog_view():
                render_setup_detail_modal(candidate, as_of=as_of, repo=repo, key_suffix=key_suffix)
            _dialog_view()
            return
        except Exception:
            pass

    render_setup_detail_modal(candidate, as_of=as_of, repo=repo, key_suffix=key_suffix)
