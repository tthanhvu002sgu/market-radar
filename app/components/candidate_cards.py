import re
import textwrap
import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Optional
from analytics.market_calendar import get_remaining_trading_sessions_in_week
from analytics.candidate_quality import rank_for_review, select_shortlist, TIER_LABELS, DEFAULT_POLICY
from app.components.base_watchlist import (
    render_base_watchlist,
    render_base_metrics_grid,
    format_base_summary_line
)

def render_html_safe(html_str: str):
    """Render HTML safely without markdown code block indentation issues."""
    clean_html = textwrap.dedent(html_str).strip()
    if hasattr(st, "html"):
        st.html(clean_html)
    else:
        st.markdown(clean_html, unsafe_allow_html=True)

GROUP_TITLES = {
    "long_cont": ("Long Tiếp Diễn (Trend Continuation)", "Cổ phiếu trong xu hướng tăng mạnh, vượt trội thị trường và đang có điểm pullback hoặc breakout kèm volume."),
    "short_cont": ("Short Tiếp Diễn (Downtrend Continuation)", "Cổ phiếu trong xu hướng giảm rõ rệt, yếu hơn thị trường, xuất hiện nhịp hồi chạm kháng cự hoặc breakdown tiếp diễn."),
    "long_rev": ("Long Đảo Chiều (Mean Reversion / Reversal)", "Cổ phiếu có dấu hiệu tạo đáy kỹ thuật sau chuỗi giảm sâu hoặc vượt trở lại trên MA20."),
    "short_rev": ("Short Đảo Chiều (Top Breakdown)", "Cổ phiếu tăng quá đà, xuất hiện suy yếu hoặc gãy MA20 báo hiệu đảo chiều giảm."),
    "watchlist": ("Tín Hiệu Mâu Thuẫn (Contradiction)", "Mã có tín hiệu kỹ thuật trái chiều hoặc đang hình thành mẫu hình nhưng chưa đủ điều kiện đồng pha để giải ngân.")
}

def render_candidate_card(
    cand: Dict[str, Any],
    as_of: str = "",
    repo: Optional[Any] = None,
    key_suffix: str = "",
    base_info: Optional[Dict[str, Any]] = None
):
    """Render an individual candidate card in utilitarian minimalist bento style."""
    sym = cand["symbol"]
    company = cand.get("company_name", sym)
    sector = cand.get("sector", "")
    sub_ind = cand.get("sub_industry", "")
    price = cand.get("close_price", 0.0)
    p1d = cand.get("perf_1d", 0.0)
    p5d = cand.get("perf_5d", 0.0)
    p20d = cand.get("perf_20d", 0.0)
    status = cand.get("status", "confirmed")
    reasons = cand.get("technical_reasons", [])
    fa_flags = cand.get("fa_flags", {})
    if (not fa_flags or not isinstance(fa_flags, dict) or not fa_flags.get("has_data")) and repo is not None:
        try:
            from analytics.company_fa import evaluate_fa_flags
            fa_df = repo.get_fundamentals([sym])
            if not fa_df.empty:
                fa_raw = fa_df.iloc[0].to_dict()
                ref_d = as_of.split()[0] if as_of else None
                fa_flags = evaluate_fa_flags(sym, fa_raw, ref_date=ref_d)
        except Exception:
            pass
    if base_info is None and repo is not None:
        try:
            ref_d = as_of.split()[0] if as_of else None
            last_b = repo.get_last_base_by_symbol(sym, before_date=None)
            if last_b and (ref_d is None or str(last_b.get("as_of", "")) <= ref_d) and last_b.get("is_active"):
                base_info = last_b
        except Exception:
            pass
    short_caveat = cand.get("short_caveat", "")
    tv_url = cand.get("tv_url") or f"https://www.tradingview.com/chart/?symbol={sym}&interval=D"
    if "interval=" not in tv_url:
        tv_url = f"{tv_url}{'&' if '?' in tv_url else '?'}interval=D"
    score = cand.get("score", 0.0)
    rank = cand.get("rank")
    g_type = cand.get("group_type", "")
    setup_type = cand.get("setup_type", "")
    candle_pattern = cand.get("candle_pattern", "")
    trig = cand.get("trigger_price")
    inv = cand.get("invalidation_price")
    atr14 = cand.get("atr14")

    quality = cand.get("quality")
    if quality:
        st.caption(f"Ưu tiên #{cand.get('review_rank', '—')} · {quality['label']}")
        st.caption(" · ".join(quality["reasons"]))
        risk = quality.get("risk_pct")
        room = quality.get("room_risk")
        st.caption(
            f"Rủi ro tham chiếu: {f'{risk:.1f}%' if risk is not None else 'N/A'} · "
            f"Khoảng trống/rủi ro: {f'{room:.2f}' if room is not None else 'N/A'}"
        )

    # Risk % computation
    ref_entry = quality.get("entry_reference") if quality else (trig if (trig is not None and trig > 0) else price)
    risk_pct_str = "N/A"
    if ref_entry and inv and ref_entry > 0:
        side = "short" if "short" in g_type else "long"
        if side == "long" and ref_entry > inv:
            risk_pct = (ref_entry - inv) / ref_entry * 100.0
            risk_pct_str = f"{risk_pct:.1f}%"
        elif side == "short" and inv > ref_entry:
            risk_pct = (inv - ref_entry) / ref_entry * 100.0
            risk_pct_str = f"{risk_pct:.1f}%"

    is_oneil = cand.get("is_oneil_leader", False)
    oneil_badge_html = '<span style="font-size: 11.5px; font-weight: 600; background: #EDF3EC; color: #346538; border: 1px solid #D1E5D0; padding: 2px 8px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase; margin-left: 6px;">Leader</span>' if is_oneil else ''

    if status == "confirmed":
        status_badge = "Triggered"
        status_bg = "#EDF3EC"
        status_color = "#346538"
    elif status == "setup":
        status_badge = "Setup"
        status_bg = "#FBF3DB"
        status_color = "#956400"
    else:
        status_badge = "Watchlist"
        status_bg = "#F7F6F3"
        status_color = "#787774"

    rank_str = f"#{rank} · " if rank else ""
    sub_ind_html = f'<span style="font-size: 12px; background: #F7F6F3; color: #787774; border: 1px solid #EAEAEA; padding: 2px 8px; border-radius: 9999px; margin-left: 6px;">{sub_ind}</span>' if sub_ind else ''
    sector_html = f'<span style="font-size: 12px; background: #F7F6F3; color: #555555; border: 1px solid #EAEAEA; padding: 2px 8px; border-radius: 9999px; margin-left: 8px;">{sector}</span>' if sector else ''
    setup_badge_html = f'<span style="font-size: 11.5px; font-weight: 600; background: #E1F3FE; color: #1F6C9F; border: 1px solid #BAE6FD; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.03em; text-transform: uppercase; margin-left: 6px;">{setup_type}</span>' if setup_type else ''
    candle_badge_html = f'<span style="font-size: 11.5px; color: #787774; background: #FAFAFA; border: 1px solid #EAEAEA; padding: 2px 7px; border-radius: 4px; margin-left: 6px;">{candle_pattern}</span>' if candle_pattern and candle_pattern != "-" else ''

    # Market context badge [D-1]
    ctx_align = cand.get("market_context_alignment", "chưa đủ dữ liệu")
    if ctx_align == "phù hợp":
        ctx_badge_html = '<span style="font-size: 11px; font-weight: 600; background: #EDF3EC; color: #346538; padding: 2px 7px; border-radius: 4px; margin-left: 6px;">Thuận TT</span>'
    elif ctx_align == "mâu thuẫn":
        ctx_badge_html = '<span style="font-size: 11px; font-weight: 600; background: #FDEBEC; color: #9F2F2D; padding: 2px 7px; border-radius: 4px; margin-left: 6px;">Nghịch TT</span>'
    elif ctx_align == "phân hóa / trung tính":
        ctx_badge_html = '<span style="font-size: 11px; font-weight: 600; background: #FEF3D6; color: #8F6B00; padding: 2px 7px; border-radius: 4px; margin-left: 6px;">TT phân hóa</span>'
    else:
        ctx_badge_html = ''

    # Themes badges [D-2]
    th_items = repo.get_symbol_themes(symbol=sym) if (repo and hasattr(repo, "get_symbol_themes")) else []
    themes_badge_html = " ".join([
        f'<span style="font-size: 11px; font-weight: 600; background: #EBF3FB; color: #1D6FB8; padding: 2px 7px; border-radius: 4px; margin-left: 4px;" title="Nguồn: {t.get("source")} | Ngày: {t.get("effective_date")} | Xác nhận: {t.get("verified_by")}">🏷️ {t.get("theme_name")}</span>'
        for t in th_items
    ])

    # User decision badge [D-4]
    as_of_clean = as_of.split()[0] if as_of else ""
    dec_recs = repo.get_trade_decisions(session_date=as_of_clean, symbol=sym) if (repo and hasattr(repo, "get_trade_decisions")) else []
    if dec_recs:
        u_dec = dec_recs[0].get("decision")
        if u_dec == "chon":
            dec_badge_html = '<span style="font-size: 11.5px; font-weight: 600; background: #EDF3EC; color: #346538; border: 1px solid #346538; padding: 2px 8px; border-radius: 4px; margin-left: 6px;">🟢 Đã Chọn</span>'
        elif u_dec == "cho":
            dec_badge_html = '<span style="font-size: 11.5px; font-weight: 600; background: #FEF3D6; color: #8F6B00; border: 1px solid #8F6B00; padding: 2px 8px; border-radius: 4px; margin-left: 6px;">🟡 Chờ</span>'
        else:
            dec_badge_html = '<span style="font-size: 11.5px; font-weight: 600; background: #FDEBEC; color: #9F2F2D; border: 1px solid #9F2F2D; padding: 2px 8px; border-radius: 4px; margin-left: 6px;">🔴 Bỏ Qua</span>'
    else:
        dec_badge_html = ''

    color_1d = "#346538" if p1d >= 0 else "#9F2F2D"
    color_5d = "#346538" if p5d >= 0 else "#9F2F2D"
    color_20d = "#346538" if p20d >= 0 else "#9F2F2D"

    trig_str = f"${trig:.2f}" if trig else "N/A"
    inv_str = f"${inv:.2f}" if inv else "N/A"
    atr_str = f"${atr14:.2f}" if atr14 else "N/A"
    risk_style = 'color: #9F2F2D; font-weight: 600;' if risk_pct_str != 'N/A' else 'color: #787774;'

    with st.container(border=True):
        header_html = (
            f'<div style="margin-bottom: 12px;">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">'
            f'<div style="display: flex; align-items: center; flex-wrap: wrap; gap: 4px;">'
            f'<span style="font-family: \'Geist Mono\', monospace; font-size: 20px; font-weight: 700; color: #111111;">{rank_str}{sym}</span>'
            f'<span style="font-size: 15px; color: #787774; margin-left: 6px; font-weight: 500;">{company}</span>'
            f'{sector_html}'
            f'{sub_ind_html}'
            f'{oneil_badge_html}'
            f'{setup_badge_html}'
            f'{candle_badge_html}'
            f'{ctx_badge_html}'
            f'{themes_badge_html}'
            f'{dec_badge_html}'
            f'</div>'
            f'<div style="display: flex; align-items: center; gap: 10px;">'
            f'<span style="font-family: \'Geist Mono\', monospace; font-size: 13.5px; color: #787774;">Score: <b style="color: #111111;">{score:+.1f}</b></span>'
            f'<span style="font-size: 12px; font-weight: 600; background: {status_bg}; color: {status_color}; border: 1px solid #EAEAEA; padding: 3px 10px; border-radius: 9999px; letter-spacing: 0.04em; text-transform: uppercase;">{status_badge}</span>'
            f'</div>'
            f'</div>'
            f'<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 12px; font-family: \'Geist Mono\', monospace; font-size: 13.5px; color: #787774; background: #F9F9F8; border: 1px solid #EAEAEA; border-radius: 6px; padding: 8px 14px;">'
            f'<span><span style="color: #2F3437; font-weight: 600;">Giá: ${price:.2f}</span> (1D: <span style="color: {color_1d}; font-weight: 600;">{p1d:+.2f}%</span> &middot; 1W: <span style="color: {color_5d}; font-weight: 600;">{p5d:+.2f}%</span> &middot; 1M: <span style="color: {color_20d}; font-weight: 600;">{p20d:+.2f}%</span>)</span>'
            f'<span style="color: #D1D5DB;">|</span>'
            f'<span>Trigger: <b style="color: #111111;">{trig_str}</b></span>'
            f'<span style="color: #D1D5DB;">&middot;</span>'
            f'<span>Dừng lỗ: <b style="color: #111111;">{inv_str}</b></span>'
            f'<span style="color: #D1D5DB;">&middot;</span>'
            f'<span>Rủi ro tham chiếu: <span style="{risk_style}">{risk_pct_str}</span></span>'
            f'<span style="color: #D1D5DB;">&middot;</span>'
            f'<span>ATR14: <b style="color: #2F3437;">{atr_str}</b></span>'
            f'</div>'
            f'</div>'
        )
        render_html_safe(header_html)

        if base_info:
            summary_line = format_base_summary_line(base_info)
            b_st_key = base_info.get("state", "forming")
            from app.components.base_watchlist import STATE_LABELS
            b_label = STATE_LABELS.get(b_st_key, (b_st_key,))[0]
            base_badge_html = f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 14px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                    <span style="font-size: 13px; font-weight: 600; color: #1E293B;">🧱 Thiết Lập Nền Giá (Base Building):</span>
                    <span style="font-size: 11.5px; background: #EFF6FF; color: #1D4ED8; padding: 1px 6px; border-radius: 4px; font-weight: 600;">{b_label}</span>
                </div>
                <div style="font-size: 12.5px; color: #64748B;">{summary_line}</div>
            </div>
            """
            render_html_safe(base_badge_html)
            render_base_metrics_grid(base_info)

        col_ta, col_fa, col_action = st.columns([4.6, 4.6, 2.8])

        with col_ta:
            st.markdown('<div class="editorial-label" style="margin-bottom: 8px;">Bằng chứng Kỹ thuật (TA)</div>', unsafe_allow_html=True)
            if reasons:
                for r in reasons:
                    if "O'Neil Leader" in r:
                        st.markdown(f"<div style='font-size: 13px; color: #166534; background: #EDF3EC; border: 1px solid #D1E5D0; padding: 4px 8px; border-radius: 4px; margin-bottom: 5px;'>{r}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; line-height: 1.55; margin-bottom: 4px;'>&bull; {r}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='font-size: 13.5px; color: #787774;'>&bull; Đạt tiêu chuẩn cấu trúc giá và sức mạnh tương đối.</div>", unsafe_allow_html=True)

            if short_caveat:
                st.markdown(f"<div style='font-size: 12.5px; color: #9F2F2D; background: #FDEBEC; border: 1px solid #F8D7DA; padding: 5px 10px; border-radius: 4px; margin-top: 6px;'><b>Lưu ý Short:</b> {short_caveat}</div>", unsafe_allow_html=True)

        with col_fa:
            st.markdown('<div class="editorial-label" style="margin-bottom: 8px;">Bối cảnh Doanh nghiệp & FA</div>', unsafe_allow_html=True)
            if fa_flags and isinstance(fa_flags, dict) and fa_flags.get("has_data"):
                days_earn = fa_flags.get("days_to_earnings")
                next_earn = fa_flags.get("next_earnings_date")

                # 1. Dedicated earnings schedule & risk tag
                if days_earn is not None and next_earn and next_earn != "Chưa xác minh":
                    if 0 <= days_earn <= 14:
                        earn_chip = f"<span style='background: #FDEBEC; color: #9F2F2D; border: 1px solid #F8D7DA; padding: 1px 6px; border-radius: 4px; font-weight: 600; font-size: 12px;'>⚠️ Còn {days_earn} ngày (Rủi ro biến động)</span>"
                    else:
                        earn_chip = f"<span style='background: #EDF3EC; color: #346538; border: 1px solid #D1E5D0; padding: 1px 6px; border-radius: 4px; font-weight: 500; font-size: 12px;'>Còn {days_earn} ngày (An toàn swing)</span>"
                    st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; margin-bottom: 6px;'><b>BCTC tới:</b> {next_earn} &middot; {earn_chip}</div>", unsafe_allow_html=True)
                elif next_earn and next_earn != "Chưa xác minh":
                    st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; margin-bottom: 6px;'><b>BCTC dự kiến:</b> {next_earn}</div>", unsafe_allow_html=True)

                # 2. Render flags without duplicate earnings or duplicate MRQ dates
                flags_list = fa_flags.get("flags", [])
                warning_chips = []
                bullet_flags = []
                for f in flags_list:
                    # Skip earnings flag as it is already rendered cleanly above
                    if any(kw in f for kw in ["Kỳ công bố Earnings", "RỦI RO BÁO CÁO TÀI CHÍNH", "Earnings: Lịch chưa"]):
                        continue
                    if "Cảnh báo" in f or "⚠️" in f:
                        clean_f = f.replace("⚠️", "").replace("Cảnh báo:", "").strip()
                        # Clean out redundant MRQ string
                        clean_f = re.sub(r',\s*Kỳ kết thúc\s*\([^)]*\):?\s*[\d\-]+', '', clean_f)
                        clean_f = re.sub(r',\s*nguồn\s*[^)]+', '', clean_f)
                        warning_chips.append(clean_f)
                    else:
                        bullet_flags.append(f)

                if warning_chips:
                    chips_html = "".join([
                        f"<span style='font-size: 12px; color: #9F2F2D; background: #FDEBEC; border: 1px solid #F8D7DA; padding: 2px 8px; border-radius: 4px; font-weight: 500; display: inline-block; margin: 2px 4px 4px 0;'>⚠️ {w}</span>"
                        for w in warning_chips
                    ])
                    st.markdown(f"<div style='margin-bottom: 6px;'>{chips_html}</div>", unsafe_allow_html=True)

                for bf in bullet_flags:
                    st.markdown(f"<div style='font-size: 13.5px; color: #2F3437; line-height: 1.55; margin-bottom: 3px;'>&bull; {bf}</div>", unsafe_allow_html=True)

                if not warning_chips and not bullet_flags and not next_earn:
                    st.markdown("<div style='font-size: 13.5px; color: #787774;'>&bull; Chưa ghi nhận bất thường cơ bản.</div>", unsafe_allow_html=True)

                # 3. Clean single metadata row
                period_end = fa_flags.get("period_end")
                fiscal_period = fa_flags.get("fiscal_period")
                src_str = fa_flags.get("source", "Yahoo Finance (Số liệu tổng hợp / Aggregate)")
                metrics = fa_flags.get("metrics", {})
                p_margin = metrics.get('profit_margin_str', 'N/A')

                period_label = period_end if (period_end and period_end != "Chưa xác minh") else fiscal_period
                meta_parts = []
                if period_label and period_label not in ("Chưa xác minh kỳ", "N/A"):
                    meta_parts.append(f"Kỳ MRQ: <b>{period_label}</b>")
                if p_margin and p_margin != "N/A":
                    meta_parts.append(f"Biên ròng: <b>{p_margin}</b>")
                meta_parts.append(f"Nguồn: {src_str}")

                st.markdown(f"<div style='font-size: 12px; color: #787774; margin-top: 6px; padding-top: 6px; border-top: 1px dashed #EAEAEA;'>{' &middot; '.join(meta_parts)}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='font-size: 13.5px; color: #787774;'>&bull; Chưa có dữ liệu FA trong cơ sở dữ liệu local (chờ chu kỳ cập nhật tiếp theo).</div>", unsafe_allow_html=True)

        with col_action:
            st.markdown('<div class="editorial-label" style="margin-bottom: 8px;">Thao tác</div>', unsafe_allow_html=True)
            card_btn_key = f"btn_card_detail_{sym}_{key_suffix}" if key_suffix else f"btn_card_detail_{sym}"
            if st.button(f"Chi tiết {sym} →", key=card_btn_key, type="primary", use_container_width=True):
                from app.components.setup_detail import show_setup_detail_dialog
                show_setup_detail_dialog(cand, as_of=as_of, repo=repo, key_suffix=f"card_{sym}_{key_suffix}")
            if base_info:
                base_btn_key = f"btn_card_base_{sym}_{key_suffix}" if key_suffix else f"btn_card_base_{sym}"
                if st.button("Nền giá 🧱", key=base_btn_key, use_container_width=True, help=f"Mở màn hình Nền giá & bứt phá với mã {sym}"):
                    st.session_state["active_page"] = "Nền giá & bứt phá"
                    st.session_state["base_search_input"] = sym
                    st.rerun()
            st.link_button(f"Chart {sym} ↗", tv_url, use_container_width=True)
            sec_url = (fa_flags.get("sec_filing_url") if isinstance(fa_flags, dict) else None) or f"https://www.sec.gov/edgar/browse/?CIK={sym}"
            st.link_button("Tra cứu SEC ↗", sec_url, use_container_width=True)

def render_candidates_table(candidates: List[Dict[str, Any]], as_of: str = "", repo: Any = None):
    """Render candidates as a compact, scannable table with proper numerical sorting."""
    if not candidates:
        return

    table_data = []
    for c in candidates:
        fa = c.get("fa_flags", {})
        earnings = fa.get("earnings_status", "Chưa xác minh") if isinstance(fa, dict) else "N/A"
        rank_val = c.get("rank")

        status_val = c.get("status")
        if status_val == "confirmed":
            status_label = "Triggered"
        elif status_val == "setup":
            status_label = "Setup"
        else:
            status_label = "Watchlist"

        as_of_d = as_of.split()[0] if as_of else ""
        th_list = repo.get_symbol_themes(symbol=c["symbol"]) if (repo and hasattr(repo, "get_symbol_themes")) else []
        th_str = ", ".join(t.get("theme_name", "") for t in th_list) if th_list else "-"
        dec_list = repo.get_trade_decisions(session_date=as_of_d, symbol=c["symbol"]) if (repo and hasattr(repo, "get_trade_decisions")) else []
        dec_str = dec_list[0]["decision"].upper() if dec_list else "-"

        table_data.append({
            "Ưu tiên": c.get("review_rank"),
            "Mã": c["symbol"],
            "Chất lượng": TIER_LABELS.get(c.get("quality_tier"), "Chưa đánh giá"),
            "Bối cảnh TT": c.get("market_context_alignment", "chưa đủ dữ liệu"),
            "Themes": th_str,
            "Quyết định": dec_str,
            "Lý do xét lọc": c.get("quality_reasons", ""),
            "Rủi ro (%)": c.get("risk_pct"),
            "Rủi ro (ATR)": c.get("risk_atr"),
            "Khoảng trống/R": c.get("room_risk"),
            "Hạng": rank_val if rank_val else 9999,
            "Doanh nghiệp": c.get("company_name", c["symbol"]),
            "Setup": c.get("setup_type", "-"),
            "Mẫu Nến": c.get("candle_pattern", "-"),
            "Ngành": c.get("sector", ""),
            "Nhóm nhỏ": c.get("sub_industry", ""),
            "Trạng thái": status_label,
            "Giá": float(c.get("close_price", 0.0)),
            "Trigger": float(c.get("trigger_price")) if c.get("trigger_price") is not None else None,
            "1D (%)": float(c.get("perf_1d", 0.0)),
            "1W (%)": float(c.get("perf_5d", 0.0)),
            "1M (%)": float(c.get("perf_20d", 0.0)),
            "ATR14": float(c.get("atr14")) if c.get("atr14") is not None else None,
            "Score": float(c.get("score", 0.0)),
            "Leader": "Có" if c.get("is_oneil_leader") else "-",
            "Kỳ Earnings": earnings,
            "Chart": f"https://www.tradingview.com/chart/?symbol={c['symbol']}&interval=D"
        })

    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ưu tiên": st.column_config.NumberColumn("Ưu tiên", format="%d"),
            "Bối cảnh TT": st.column_config.TextColumn("Bối cảnh TT"),
            "Themes": st.column_config.TextColumn("Themes"),
            "Quyết định": st.column_config.TextColumn("Quyết định"),
            "Lý do xét lọc": st.column_config.TextColumn("Lý do xét lọc", width="large"),
            "Rủi ro (%)": st.column_config.NumberColumn("Rủi ro (%)", format="%.2f"),
            "Rủi ro (ATR)": st.column_config.NumberColumn("Rủi ro (ATR)", format="%.2f"),
            "Khoảng trống/R": st.column_config.NumberColumn("Khoảng trống/R", format="%.2f"),
            "Hạng": st.column_config.NumberColumn("Hạng", format="%d"),
            "Giá": st.column_config.NumberColumn("Giá ($)", format="$%.2f"),
            "Trigger": st.column_config.NumberColumn("Trigger ($)", format="$%.2f"),
            "1D (%)": st.column_config.NumberColumn("1D (%)", format="%+.2f%%"),
            "1W (%)": st.column_config.NumberColumn("1W (%)", format="%+.2f%%"),
            "1M (%)": st.column_config.NumberColumn("1M (%)", format="%+.2f%%"),
            "ATR14": st.column_config.NumberColumn("ATR14 ($)", format="$%.2f"),
            "Score": st.column_config.NumberColumn("Score", format="%+.1f"),
            "Chart": st.column_config.LinkColumn("TradingView", display_text="Mở Chart")
        }
    )

def render_candidates_comparison(candidates: List[Dict[str, Any]], as_of: str = "", repo: Optional[Any] = None):
    """Render side-by-side comparative analysis of 2 to 5 selected candidates."""
    all_symbols = [c["symbol"] for c in candidates]
    if len(all_symbols) < 2:
        st.info("Cần ít nhất 2 ứng viên trong danh sách để so sánh.")
        return

    default_selected = all_symbols[:min(3, len(all_symbols))]
    selected_syms = st.multiselect(
        "Chọn 2 đến 5 mã cổ phiếu để so sánh trực diện:",
        options=all_symbols,
        default=default_selected,
        max_selections=5,
        key="cand_compare_multiselect"
    )

    if len(selected_syms) < 2:
        st.warning("Vui lòng chọn từ 2 đến 5 mã cổ phiếu để hiển thị bảng so sánh.")
        return

    selected_cands = [c for c in candidates if c["symbol"] in selected_syms]
    selected_cands.sort(key=lambda c: selected_syms.index(c["symbol"]))

    cols = st.columns(len(selected_cands))
    for idx, c in enumerate(selected_cands):
        with cols[idx]:
            sym = c["symbol"]
            co_name = c.get("company_name", sym)
            sec = c.get("sector", "")
            sub = c.get("sub_industry", "")
            g_type = c.get("group_type", "")
            setup = c.get("setup_type", "")
            is_leader = c.get("is_oneil_leader", False)
            price = c.get("close_price", 0.0)
            trig = c.get("trigger_price")
            inv = c.get("invalidation_price")
            p1d = c.get("perf_1d", 0.0)
            p5d = c.get("perf_5d", 0.0)
            p20d = c.get("perf_20d", 0.0)
            score = c.get("score", 0.0)
            atr14 = c.get("atr14")
            atr_pct = c.get("atr_pct")

            risk_pct_str = "N/A"
            if c.get("quality"):
                review_risk = c["quality"].get("risk_pct")
                risk_pct_str = f"{review_risk:.1f}%" if review_risk is not None else "N/A"
            elif trig and inv and trig > 0:
                side = "short" if "short" in g_type else "long"
                if side == "long" and trig > inv:
                    risk_pct = (trig - inv) / trig * 100.0
                    risk_pct_str = f"{risk_pct:.1f}%"
                elif side == "short" and inv > trig:
                    risk_pct = (inv - trig) / trig * 100.0
                    risk_pct_str = f"{risk_pct:.1f}%"

            fa_flags = c.get("fa_flags", {})
            if (not fa_flags or not isinstance(fa_flags, dict) or not fa_flags.get("has_data")) and repo is not None:
                try:
                    from analytics.company_fa import evaluate_fa_flags
                    fa_df = repo.get_fundamentals([sym])
                    if not fa_df.empty:
                        fa_raw = fa_df.iloc[0].to_dict()
                        ref_d = as_of.split()[0] if as_of else None
                        fa_flags = evaluate_fa_flags(sym, fa_raw, ref_date=ref_d)
                except Exception:
                    pass

            evidence = c.get("evidence", {}) or {}
            pressure = evidence.get("multi_session_pressure", {}) if isinstance(evidence, dict) else {}
            pressure_bias = pressure.get("pressure_bias", "Chưa tính")

            trig_str = f"${trig:.2f}" if (trig is not None and trig > 0) else "N/A"
            inv_str = f"${inv:.2f}" if (inv is not None and inv > 0) else "N/A"
            atr_pct_str = f"{atr_pct:.2f}%" if atr_pct is not None else "N/A"
            risk_style = 'color: #9F2F2D; font-weight: 600;' if risk_pct_str != 'N/A' else 'color: #787774;'
            leader_badge_html = '<span style="font-size: 11px; background: #EDF3EC; color: #346538; border: 1px solid #D1E5D0; padding: 2px 7px; border-radius: 4px; font-weight: 600; letter-spacing: 0.03em;">LEADER</span>' if is_leader else ''
            p1d_col = "#346538" if p1d >= 0 else "#9F2F2D"
            p5d_col = "#346538" if p5d >= 0 else "#9F2F2D"
            p20d_col = "#346538" if p20d >= 0 else "#9F2F2D"
            sub_info = f"{sec} &bull; {sub}" if (sec and sub) else (sec or sub or "-")

            fa_section_html = '<div style="font-size: 13px; color: #787774;">Chưa có dữ liệu FA.</div>'
            if fa_flags and isinstance(fa_flags, dict) and fa_flags.get("has_data"):
                m = fa_flags.get("metrics", {})
                rev_growth = m.get('rev_growth_str', 'N/A')
                eps_growth = m.get('eps_growth_str', 'N/A')
                p_margin = m.get('profit_margin_str', 'N/A')
                days_earn = fa_flags.get("days_to_earnings")
                next_earn = fa_flags.get("next_earnings_date")
                p_end = fa_flags.get("period_end", "")

                fa_parts = [
                    f'<div style="font-size: 13px; color: #2F3437; margin-bottom: 3px;"><b>Doanh thu YoY:</b> {rev_growth} &bull; <b>EPS YoY:</b> {eps_growth}</div>',
                    f'<div style="font-size: 13px; color: #2F3437; margin-bottom: 3px;"><b>Biên ròng:</b> {p_margin}</div>'
                ]
                if days_earn is not None and next_earn and next_earn != "Chưa xác minh":
                    if 0 <= days_earn <= 14:
                        earn_chip = f"<span style='background: #FDEBEC; color: #9F2F2D; border: 1px solid #F8D7DA; padding: 1px 6px; border-radius: 4px; font-weight: 600; font-size: 11.5px;'>⚠️ Còn {days_earn} ngày</span>"
                    else:
                        earn_chip = f"<span style='background: #EDF3EC; color: #346538; border: 1px solid #D1E5D0; padding: 1px 6px; border-radius: 4px; font-weight: 500; font-size: 11.5px;'>Còn {days_earn} ngày</span>"
                    fa_parts.append(f'<div style="font-size: 12.5px; color: #2F3437; margin-top: 4px;"><b>BCTC:</b> {next_earn} &middot; {earn_chip}</div>')
                elif p_end:
                    fa_parts.append(f'<div style="font-size: 12px; color: #787774; margin-top: 4px;">Kỳ BCTC: {p_end} (Yahoo Aggregate)</div>')

                fa_section_html = "".join(fa_parts)

            card_html = (
                f'<div style="border: 1px solid #EAEAEA; border-radius: 6px; padding: 14px; background: #FFFFFF; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">'
                f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">'
                f'<span style="font-family: \'Geist Mono\', monospace; font-size: 18px; font-weight: 700; color: #111111;">{sym}</span>'
                f'{leader_badge_html}'
                f'</div>'
                f'<div style="font-size: 13px; color: #787774; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{co_name}">{co_name}</div>'
                f'<div style="font-size: 12px; color: #555555; background: #F7F6F3; padding: 4px 8px; border-radius: 4px; margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{sub_info}</div>'
                f'<div style="font-size: 11.5px; font-weight: 600; color: #787774; text-transform: uppercase; margin-bottom: 5px; letter-spacing: 0.03em;">Kỹ Thuật &amp; Setup</div>'
                f'<div style="font-size: 13px; margin-bottom: 3px;"><b>Setup:</b> {setup} <span style="color: #787774;">({g_type})</span></div>'
                f'<div style="font-size: 13px; margin-bottom: 3px;"><b>Giá đóng cửa:</b> ${price:.2f}</div>'
                f'<div style="font-size: 13px; margin-bottom: 3px;"><b>Trigger:</b> <span style="font-weight: 600;">{trig_str}</span></div>'
                f'<div style="font-size: 13px; margin-bottom: 3px;"><b>Dừng lỗ:</b> <span style="font-weight: 600;">{inv_str}</span></div>'
                f'<div style="font-size: 13px; margin-bottom: 8px;"><b>Rủi ro tham chiếu:</b> <span style="{risk_style}">{risk_pct_str}</span></div>'
                f'<div style="font-size: 11.5px; font-weight: 600; color: #787774; text-transform: uppercase; margin-bottom: 5px; margin-top: 10px; letter-spacing: 0.03em;">Hiệu Suất &amp; Điểm Số</div>'
                f'<div style="font-size: 13px; margin-bottom: 3px;">'
                f'1D: <span style="color: {p1d_col}; font-weight: 600;">{p1d:+.2f}%</span> &bull; '
                f'1W: <span style="color: {p5d_col}; font-weight: 600;">{p5d:+.2f}%</span> &bull; '
                f'1M: <span style="color: {p20d_col}; font-weight: 600;">{p20d:+.2f}%</span>'
                f'</div>'
                f'<div style="font-size: 13px; margin-bottom: 8px;">Score: <b>{score:+.1f}</b> &bull; ATR%: <b>{atr_pct_str}</b></div>'
                f'<div style="font-size: 11.5px; font-weight: 600; color: #787774; text-transform: uppercase; margin-bottom: 5px; margin-top: 10px; letter-spacing: 0.03em;">Áp Lực Đa Phiên</div>'
                f'<div style="font-size: 13px; color: #2F3437; margin-bottom: 8px;">{pressure_bias}</div>'
                f'<div style="font-size: 11.5px; font-weight: 600; color: #787774; text-transform: uppercase; margin-bottom: 5px; margin-top: 10px; letter-spacing: 0.03em;">Bối Cảnh Doanh Nghiệp (FA)</div>'
                f'{fa_section_html}'
                f'</div>'
            )
            render_html_safe(card_html)

            if st.button(f"Chi tiết {sym} →", key=f"btn_cmp_detail_{sym}", type="primary", use_container_width=True):
                from app.components.setup_detail import show_setup_detail_dialog
                show_setup_detail_dialog(c, as_of=as_of, repo=repo, key_suffix=f"cmp_{sym}")

            tv_link = f"https://www.tradingview.com/chart/?symbol={sym}&interval=D"
            st.link_button(f"Mở Chart {sym} ↗", tv_link, use_container_width=True, key=f"btn_tv_cmp_{sym}")


def render_candidates_section(candidates: List[Dict[str, Any]], as_of: str = "", repo: Any = None, snapshot_id: Optional[int] = None):
    """Render candidates partitioned by the 4 groups + contradiction watchlist."""
    c_head1, c_head2 = st.columns([3.5, 1.5])
    with c_head1:
        st.markdown('<div class="editorial-hero" style="font-size: 22px; margin-bottom: 4px;">4 Nhóm Ứng Viên Giao Dịch (Swing Candidates)</div>', unsafe_allow_html=True)
        st.markdown('<div class="editorial-sub">Phân loại ứng viên theo pha chu kỳ và điểm kích hoạt vào lệnh (Continuation & Reversal).</div>', unsafe_allow_html=True)
    with c_head2:
        if st.button("🧱 Sang Nền giá & bứt phá →", key="btn_shortcut_to_bases", use_container_width=True, help="Chuyển đến màn hình theo dõi nền giá tích lũy"):
            st.session_state["active_page"] = "Nền giá & bứt phá"
            st.rerun()

    if not candidates:
        st.info("Không có mã nào đạt điều kiện trong kỳ phân tích này. Thị trường đang ở pha phân hóa hoặc không thỏa mãn tiêu chí kỹ thuật.")
        return

    # Remaining trading sessions in week check
    rem_sessions = get_remaining_trading_sessions_in_week(as_of)
    if rem_sessions <= 1:
        st.warning(
            f"⚠️ **Cảnh báo chu kỳ tuần ({as_of.split()[0] if as_of else 'Phiên này'}):** Tuần hiện tại chỉ còn **{rem_sessions} phiên giao dịch**. "
            f"Theo quy tắc giao dịch ngắn 'không giữ lệnh qua tuần', các vị thế mở mới cần ưu tiên chốt trước cuối tuần hoặc hoãn sang đầu tuần sau để tránh rủi ro vắt qua cuối tuần (`crosses_weekend`)."
        )

    # Cross-navigation context banner (from Ngành or Nhóm ngành)
    nav_from = st.session_state.get("cand_nav_from")
    sector_filter = st.session_state.get("cand_sector_filter")
    sub_ind_filter = st.session_state.get("cand_sub_industry_filter")

    if nav_from:
        c_n1, c_n2 = st.columns([4, 1.2])
        with c_n1:
            st.info(f"Đang hiển thị ứng viên lọc từ **{nav_from.get('page', 'Bối cảnh')}**: **{nav_from.get('label', '')}**")
        with c_n2:
            if st.button(f"← Quay lại {nav_from.get('page', 'trang trước')}", key="btn_cand_back_to_source", use_container_width=True):
                prev_p = nav_from.get("page")
                del st.session_state["cand_nav_from"]
                if "cand_sector_filter" in st.session_state:
                    del st.session_state["cand_sector_filter"]
                if "cand_sub_industry_filter" in st.session_state:
                    del st.session_state["cand_sub_industry_filter"]
                st.session_state["active_page"] = prev_p
                st.rerun()
    elif sector_filter or sub_ind_filter:
        lbl = sector_filter or sub_ind_filter
        c_n1, c_n2 = st.columns([4, 1.2])
        with c_n1:
            st.info(f"Đang áp dụng bộ lọc: **{lbl}**")
        with c_n2:
            if st.button("✕ Xóa bộ lọc", key="btn_clear_cand_filters", use_container_width=True):
                if "cand_sector_filter" in st.session_state:
                    del st.session_state["cand_sector_filter"]
                if "cand_sub_industry_filter" in st.session_state:
                    del st.session_state["cand_sub_industry_filter"]
                st.rerun()

    # Controls: Priority Table view by default
    candidates = rank_for_review(candidates)
    quality_counts = {tier: sum(c["quality_tier"] == tier for c in candidates) for tier in TIER_LABELS}
    st.caption(
        f"{len(candidates)} setup / {len({c['symbol'] for c in candidates})} mã → "
        + " · ".join(f"{TIER_LABELS[tier]}: {count}" for tier, count in quality_counts.items())
    )
    quality_col, diversity_col = st.columns([3, 2])
    with quality_col:
        quality_view = st.selectbox(
            "Mức chất lượng:",
            ["Ưu tiên (tối đa 10 mã)", "Đạt bộ lọc", "Chờ xác nhận", "Không ưu tiên", "Toàn bộ"],
            key="cand_quality_view",
        )
    with diversity_col:
        diversify = st.checkbox("Tối đa 2 mã mỗi nhóm ngành nhỏ", value=True, key="cand_quality_diversify",
                                  help="Áp dụng cho danh sách ưu tiên; giảm lặp ngành, chưa đo tương quan giá.")
    with st.expander("Tiêu chí chất lượng & cách đọc", expanded=False):
        p = DEFAULT_POLICY
        st.write(
            f"Xác nhận bằng OHLC/volume theo từng setup; giá chưa chạy quá {p.max_trigger_atr:g} ATR từ trigger "
            f"và {p.max_ma20_atr:g} ATR từ MA20 theo chiều giao dịch; giá trị giao dịch trung bình ≥ ${p.min_dollar_volume/1e6:g}M. "
            f"Khoảng tới vô hiệu ≤ {p.max_risk_atr:g} ATR và ≤ {p.max_risk_pct:g}%; "
            f"khoảng trống đến cản/rủi ro ≥ {p.min_room_risk:g}; BCTC cách hơn {p.earnings_days} ngày."
        )
        st.write("Điểm vào tham chiếu lấy giá bất lợi hơn giữa close và trigger. Thiếu cản phía trước hoặc lịch BCTC → chờ kiểm tra; không tự tạo target. Khoảng trống/R chưa tính phí và trượt giá, không phải lợi nhuận kỳ vọng.")
        st.caption(f"{p.version}: ngưỡng rà soát ban đầu, chưa kiểm định lợi nhuận. Áp dụng lại trên evidence của snapshot đang xem; hạng/score scanner gốc được giữ để đối chiếu. Xếp ưu tiên theo chất lượng, khoảng trống/R (chặn tại 5), risk ATR rồi score gốc.")

    f_col1, f_col2, f_col3, f_col4 = st.columns([2.0, 1.2, 1.1, 1.3])
    with f_col1:
        search_sym = st.text_input("Tìm kiếm mã hoặc công ty:", placeholder="Nhập AAPL, MSFT, NVDA...", key="cand_search_input").strip().lower()

    with f_col2:
        view_mode = st.selectbox("Chế độ hiển thị:", ["Bảng Rút Gọn", "Dạng Thẻ (Cards)"], index=0, key="cand_view_mode")

    with f_col3:
        only_leader = st.checkbox("Chỉ Leaders", value=False, key="cand_only_leaders", help="Chỉ hiển thị cổ phiếu thuộc nhóm ngành dẫn dắt (Top 20% Composite RS)")

    with f_col4:
        week_filter = st.selectbox(
            "Lọc Chu Kỳ Tuần:",
            ["Tất cả phiên", "Tuần còn ≥ 2 phiên", "Tuần còn ≥ 3 phiên"],
            index=0,
            key="cand_week_filter",
            help="Lọc cơ hội mở vị thế theo số phiên giao dịch còn lại của tuần để tránh rủi ro vắt qua cuối tuần (crosses_weekend)."
        )

    # Apply filters to form display_candidates
    display_candidates = candidates
    if sector_filter:
        display_candidates = [c for c in display_candidates if c.get("sector") == sector_filter]
    if sub_ind_filter:
        display_candidates = [c for c in display_candidates if c.get("sub_industry") == sub_ind_filter]
    if only_leader:
        display_candidates = [c for c in display_candidates if c.get("is_oneil_leader")]
    if search_sym:
        display_candidates = [
            c for c in display_candidates
            if search_sym in c["symbol"].lower() or search_sym in c.get("company_name", "").lower()
        ]

    # Resolve Shortlist: Frozen Snapshot Shortlist vs Dynamic Review [D-04]
    as_of_clean = as_of.split()[0] if as_of else ""
    effective_snapshot_id = snapshot_id or (candidates[0].get("snapshot_id") if candidates else None)

    frozen_shortlist = []
    is_frozen_run = False
    if repo and hasattr(repo, "get_frozen_shortlist"):
        try:
            frozen_shortlist = repo.get_frozen_shortlist(
                session_date=as_of_clean,
                snapshot_id=effective_snapshot_id,
                policy_version=DEFAULT_POLICY.version
            )
            if hasattr(repo, "has_frozen_shortlist"):
                is_frozen_run = repo.has_frozen_shortlist(
                    snapshot_id=effective_snapshot_id,
                    session_date=as_of_clean,
                    policy_version=DEFAULT_POLICY.version
                )
            else:
                is_frozen_run = bool(frozen_shortlist)
        except Exception:
            frozen_shortlist = []
            is_frozen_run = False

    if quality_view == "Ưu tiên (tối đa 10 mã)":
        if is_frozen_run or frozen_shortlist:
            def make_key(c_item):
                return (
                    c_item.get("symbol", ""),
                    c_item.get("group_type") or "",
                    c_item.get("setup_type") or ""
                )

            cand_by_exact = {make_key(c): c for c in display_candidates}

            matched_shortlist = []
            for f in sorted(frozen_shortlist, key=lambda x: x.get("review_rank", 999)):
                matched_c = cand_by_exact.get(make_key(f))
                if matched_c is None:
                    # The candidate may have been removed by a UI filter. A frozen
                    # row must not reintroduce it or borrow another setup's data.
                    continue
                merged = dict(matched_c)

                merged["review_rank"] = f.get("review_rank")
                merged["quality_tier"] = f.get("quality_tier", merged.get("quality_tier"))
                merged["quality_reasons"] = f.get("quality_reasons", merged.get("quality_reasons"))
                if f.get("entry_reference") is not None:
                    merged["entry_reference"] = f["entry_reference"]
                if f.get("trigger_price") is not None:
                    merged["trigger_price"] = f["trigger_price"]
                if f.get("invalidation_price") is not None:
                    merged["invalidation_price"] = f["invalidation_price"]
                if f.get("room_risk") is not None:
                    merged["room_risk"] = f["room_risk"]
                if f.get("market_context_alignment"):
                    merged["market_context_alignment"] = f["market_context_alignment"]

                matched_shortlist.append(merged)

            display_candidates = matched_shortlist[:10]
            st.caption(f"❄️ Đang hiển thị **Shortlist thực tế đã đóng băng** ({len(display_candidates)} mã) theo phiên {as_of_clean} (Version {DEFAULT_POLICY.version}).")
        else:
            display_candidates = select_shortlist(display_candidates, industry_limit=2 if diversify else None)
    elif quality_view in TIER_LABELS.values():
        display_candidates = [c for c in display_candidates if TIER_LABELS[c["quality_tier"]] == quality_view]

    # Apply remaining sessions filter
    if week_filter == "Tuần còn ≥ 2 phiên" and rem_sessions < 2:
        st.info(f"Tuần hiện tại chỉ còn {rem_sessions} phiên giao dịch (< 2 phiên). Các vị thế swing mới có nguy cơ vắt qua cuối tuần; danh sách đã được ẩn theo tiêu chí lọc.")
        return
    elif week_filter == "Tuần còn ≥ 3 phiên" and rem_sessions < 3:
        st.info(f"Tuần hiện tại chỉ còn {rem_sessions} phiên giao dịch (< 3 phiên). Đã lọc ẩn danh sách swing theo tiêu chí số phiên còn lại.")
        return

    # Dual CSV Exports with Standardized Columns
    as_of_tag = as_of.split()[0] if as_of else "latest"
    export_cols = [
        "rank", "symbol", "company_name", "sector", "sub_industry",
        "group_type", "setup_type", "status", "score", "is_oneil_leader",
        "close_price", "trigger_price", "invalidation_price", "atr14", "atr_pct",
        "perf_1d", "perf_5d", "perf_20d"
    ]
    export_cols += ["review_rank", "quality_tier", "quality_version", "quality_reasons",
                    "entry_reference", "risk_pct", "risk_atr", "room_risk"]

    def _build_csv_data(cand_list):
        if not cand_list:
            return ""
        available_cols = [col for col in export_cols if col in cand_list[0]]
        return pd.DataFrame(cand_list)[available_cols].to_csv(index=False)

    c_csv1, c_csv2, c_csv_space = st.columns([1.8, 1.8, 2.4])
    with c_csv1:
        st.download_button(
            label=f"Xuất kết quả đang lọc ({len(display_candidates)} mã) 📥",
            data=_build_csv_data(display_candidates),
            file_name=f"market_radar_candidates_filtered_{as_of_tag}.csv",
            mime="text/csv",
            use_container_width=True,
            key="btn_dl_cand_filtered_csv",
            disabled=len(display_candidates) == 0
        )
    with c_csv2:
        st.download_button(
            label=f"Xuất toàn bộ ({len(candidates)} mã) 📥",
            data=_build_csv_data(candidates),
            file_name=f"market_radar_candidates_all_{as_of_tag}.csv",
            mime="text/csv",
            use_container_width=True,
            key="btn_dl_cand_all_csv"
        )

    # Side-by-side comparison expander scoped to current view
    with st.expander("⚖️ So sánh Trực diện 2–5 Ứng viên (Side-by-Side)", expanded=False):
        render_candidates_comparison(display_candidates, as_of=as_of, repo=repo)

    if not display_candidates:
        st.info("Không có ứng viên nào thỏa mãn điều kiện lọc hiện tại. Chọn ‘Chờ xác nhận’ hoặc ‘Toàn bộ’ để xem nguyên nhân; hệ thống không ép đủ số mã ưu tiên.")
        return

    # Group candidates into 4 tactical groups + contradiction watchlist
    grouped: Dict[str, List[Dict[str, Any]]] = {
        "long_cont": [],
        "short_cont": [],
        "long_rev": [],
        "short_rev": [],
        "watchlist": []
    }
    for c in display_candidates:
        g = c.get("group_type", "watchlist")
        if g in grouped:
            grouped[g].append(c)
        else:
            grouped["watchlist"].append(c)

    base_records = repo.get_base_snapshots(snapshot_id=snapshot_id, as_of=as_of) if (repo and hasattr(repo, "get_base_snapshots")) else []
    base_map = {b["symbol"]: b for b in base_records}

    sub_keys = ["long_cont", "short_cont", "long_rev", "short_rev", "watchlist"]
    sub_labels = {
        "long_cont": f"Long Tiếp Diễn ({len(grouped['long_cont'])})",
        "short_cont": f"Short Tiếp Diễn ({len(grouped['short_cont'])})",
        "long_rev": f"Long Đảo Chiều ({len(grouped['long_rev'])})",
        "short_rev": f"Short Đảo Chiều ({len(grouped['short_rev'])})",
        "watchlist": f"Tín Hiệu Mâu Thuẫn ({len(grouped['watchlist'])})"
    }

    selected_sub = st.segmented_control(
        "Nhóm Ứng Viên",
        options=sub_keys,
        format_func=lambda k: sub_labels[k],
        default="long_cont",
        label_visibility="collapsed",
        key="cand_subgroup_nav"
    ) if hasattr(st, "segmented_control") else st.radio(
        "Nhóm Ứng Viên",
        options=sub_keys,
        format_func=lambda k: sub_labels[k],
        horizontal=True,
        label_visibility="collapsed",
        key="cand_subgroup_nav"
    )
    if not selected_sub:
        selected_sub = "long_cont"

    g_key = selected_sub
    title, desc = GROUP_TITLES[g_key]

    st.markdown(f"<div style='font-size: 13.5px; color: #787774; margin-bottom: 16px; margin-top: 12px;'>{desc}</div>", unsafe_allow_html=True)
    group_cands = grouped[g_key]
    if not group_cands:
        st.info(f"Không có cổ phiếu nào thỏa mãn điều kiện cho nhóm {title} trong bộ lọc hiện tại.")
    else:
        if view_mode == "Bảng Rút Gọn":
            render_candidates_table(group_cands, as_of=as_of, repo=repo)
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            sel_sym = st.selectbox(
                f"Mở modal xem chi tiết Setup & Mức kỹ thuật ({title}):",
                ["-- Chọn mã để xem chi tiết kỹ thuật --"] + [c["symbol"] for c in group_cands],
                key=f"sel_detail_table_{g_key}"
            )
            if sel_sym and sel_sym != "-- Chọn mã để xem chi tiết kỹ thuật --":
                cand_item = next((c for c in group_cands if c["symbol"] == sel_sym), None)
                if cand_item:
                    from app.components.setup_detail import show_setup_detail_dialog
                    show_setup_detail_dialog(cand_item, as_of=as_of, repo=repo, key_suffix=f"tbl_{g_key}_{sel_sym}")
        else:
            # Quick selector for modal inspection in card mode
            sel_sym = st.selectbox(
                f"Mở modal xem chi tiết Setup & Mức kỹ thuật ({title}):",
                ["-- Chọn mã cần mở chi tiết --"] + [c["symbol"] for c in group_cands],
                key=f"sel_detail_cards_{g_key}"
            )
            if sel_sym and sel_sym != "-- Chọn mã cần mở chi tiết --":
                cand_item = next((c for c in group_cands if c["symbol"] == sel_sym), None)
                if cand_item:
                    from app.components.setup_detail import show_setup_detail_dialog
                    show_setup_detail_dialog(cand_item, as_of=as_of, repo=repo, key_suffix=f"sel_{g_key}_{sel_sym}")

            # Clean pagination for cards
            page_size = 15
            total_pages = (len(group_cands) + page_size - 1) // page_size
            page_options = [
                f"Trang {p}/{total_pages} (Mã {(p-1)*page_size + 1} - {min(p*page_size, len(group_cands))})"
                for p in range(1, total_pages + 1)
            ]
            if total_pages > 1:
                chosen_page_label = st.selectbox(
                    f"Trang hiển thị ({len(group_cands)} mã):",
                    page_options,
                    key=f"page_cards_{g_key}"
                )
                c_page = page_options.index(chosen_page_label) + 1
                start_i = (c_page - 1) * page_size
                page_cands = group_cands[start_i : start_i + page_size]
            else:
                page_cands = group_cands

            for idx, c in enumerate(page_cands):
                render_candidate_card(
                    c,
                    as_of=as_of,
                    repo=repo,
                    key_suffix=f"{g_key}_{idx}",
                    base_info=base_map.get(c["symbol"])
                )

    # Playbook Quality Breakdown [D-5]
    from analytics.candidate_quality import summarize_playbook_quality
    pb_summary = summarize_playbook_quality(candidates)
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    with st.expander("📊 Báo Cáo Phân Tích Chất Lượng Theo Từng Playbook (Playbook Quality Audit)", expanded=False):
        st.markdown('<div style="font-size: 14.5px; font-weight: 600; color: #111111; margin-bottom: 6px;">Tỷ Lệ Đạt / Chờ / Loại & Nguyên Nhân Nghẽn Theo Từng Playbook</div>', unsafe_allow_html=True)
        st.caption(f"Nguyên tắc kiểm định: {pb_summary.get('note', '')}")

        pb_rows = []
        for pb_k, stats in pb_summary.get("by_playbook", {}).items():
            parts = pb_k.split(":")
            g_name = parts[0]
            s_name = parts[1] if len(parts) > 1 else ""
            top_w = "; ".join([f"{r} ({cnt})" for r, cnt in stats.get("top_wait_reasons", [])[:2]])
            top_rej = "; ".join([f"{r} ({cnt})" for r, cnt in stats.get("top_reject_reasons", [])[:2]])
            bottleneck = top_w if stats["wait"] >= stats["reject"] else top_rej
            pb_rows.append({
                "Playbook": f"{g_name} / {s_name}",
                "Tổng số": stats["total"],
                "Đạt (Ready)": f"{stats['ready']} ({stats['ready_pct']}%)",
                "Chờ (Wait)": f"{stats['wait']} ({stats['wait_pct']}%)",
                "Loại (Reject)": f"{stats['reject']} ({stats['reject_pct']}%)",
                "Cản quan sát được": f"{stats['barrier_present_count']} / {stats['total']}",
                "Lý do nghẽn chủ đạo": bottleneck or "Không có"
            })
        if pb_rows:
            st.dataframe(pd.DataFrame(pb_rows), use_container_width=True, hide_index=True)
