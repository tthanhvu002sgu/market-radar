"""Snapshot-bound six-step review path through the existing analysis screens."""
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from analytics.candidate_quality import number, rank_for_review
from app.components.setup_detail import show_setup_detail_dialog


STAGES = ["Thị trường", "Ngành/nhóm", "Leadership/RS", "Setup", "Rủi ro", "Entry & repeat"]


def sync_review_context(state: Any, snapshot_id: int) -> None:
    """A selected path must never silently cross snapshots."""
    if state.get("wf_snapshot_id") == snapshot_id:
        return
    for key in ("wf_sector", "wf_industry", "wf_candidate", "wf_previous_sector", "wf_previous_industry",
                "wf_outcome", "wf_stop_stage", "wf_reason", "wf_active"):
        state.pop(key, None)
    state["wf_snapshot_id"] = snapshot_id


def candidate_key(candidate: Dict[str, Any]) -> Tuple[str, str, str]:
    return (candidate.get("symbol") or "", candidate.get("group_type") or "", candidate.get("setup_type") or "")


def candidates_in_group(candidates: List[Dict[str, Any]], sector: Optional[str], industry: Optional[str]) -> List[Dict[str, Any]]:
    if not sector:
        return []
    return [c for c in candidates if c.get("sector") == sector and (not industry or c.get("sub_industry") == industry)]


def rs_vs_spy(candidate: Dict[str, Any], market: Dict[str, Any]) -> Optional[float]:
    saved = number(candidate.get("rs_vs_spy"))
    if saved is not None:
        return saved
    stock_return, spy_return = number(candidate.get("perf_20d")), number(market.get("spy_20d"))
    return round(stock_return - spy_return, 2) if stock_return is not None and spy_return is not None else None


def saved_review_path(row: Dict[str, Any]) -> str:
    """Show only the stages reached by a saved wait/no-action review."""
    end = STAGES.index(row["stop_stage"]) if row.get("stop_stage") in STAGES else len(STAGES) - 1
    labels = ["Thị trường"]
    if end >= 1:
        labels.append("Ngành/nhóm: " + " / ".join(filter(None, [row.get("sector"), row.get("industry")])) if row.get("sector") else "Ngành/nhóm: chưa chọn")
    if end >= 2:
        labels.append("Leadership/RS: " + (row.get("symbol") or "chưa chọn mã"))
    if end >= 3:
        labels.append("Setup: " + (row.get("setup_type") or "chưa chọn"))
    if end >= 4:
        labels.append("Rủi ro")
    if end >= 5:
        labels.append("Entry & repeat")
    return " → ".join(labels)


def _format(value: Any, suffix: str = "", decimals: int = 1) -> str:
    parsed = number(value)
    return f"{parsed:.{decimals}f}{suffix}" if parsed is not None else "N/A"


def _navigate(page: str, sector: Optional[str] = None, industry: Optional[str] = None) -> None:
    if page == "Ứng viên":
        for key, value in (("cand_sector_filter", sector), ("cand_sub_industry_filter", industry)):
            if value:
                st.session_state[key] = value
            else:
                st.session_state.pop(key, None)
        st.session_state["cand_nav_from"] = {"page": "Luồng rà soát", "label": industry or sector or "Toàn thị trường"}
        st.session_state["cand_quality_view"] = "Toàn bộ"
    st.session_state["active_page"] = page
    st.rerun()


def render_review_workflow(
    snapshot: Dict[str, Any], candidates: List[Dict[str, Any]], repo: Any
) -> None:
    snapshot_id = snapshot["id"]
    as_of = snapshot.get("as_of", "")
    sync_review_context(st.session_state, snapshot_id)
    st.session_state["wf_active"] = True
    market = snapshot.get("market_metrics") or {}
    sectors = snapshot.get("sector_metrics") or []
    industries = snapshot.get("industry_metrics") or []

    st.caption(f"Snapshot #{snapshot_id} · Phiên {as_of} · Phủ đồng phiên {_format(number(snapshot.get('coverage_pct')) * 100 if number(snapshot.get('coverage_pct')) is not None else None, '%')} · {snapshot.get('status', 'N/A')}")
    st.write("Đi theo thứ tự từ bối cảnh đến quyết định. Mọi số liệu bên dưới thuộc snapshot đang chọn; thay snapshot sẽ bắt đầu một lượt rà soát mới.")

    st.subheader("1. Market / environment")
    st.write(market.get("market_summary") or "Chưa có nhận định độ rộng thị trường cho snapshot này.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Trên MA50", _format(market.get("pct_above_ma50"), "%"))
    c2.metric("Trên MA200", _format(market.get("pct_above_ma200"), "%"))
    c3.metric("Mã trong universe", str(snapshot.get("valid_universe") or 0))
    if market.get("quality_flags"):
        st.warning("Chất lượng dữ liệu: " + "; ".join(map(str, market["quality_flags"])))
    if st.button("Xem thị trường chi tiết →", key="wf_market_detail"):
        _navigate("Thị trường")

    st.divider()
    st.subheader("2. Groups / themes")
    sector_names = sorted({str(row["sector"]) for row in sectors if row.get("sector")} |
                          {str(c["sector"]) for c in candidates if c.get("sector")})
    sector = st.selectbox("Ngành GICS đang rà soát", [None, *sector_names],
                          format_func=lambda v: v or "Chưa chọn ngành", key="wf_sector")
    if st.session_state.get("wf_previous_sector") != sector:
        st.session_state["wf_industry"] = None
        st.session_state["wf_candidate"] = None
        st.session_state["wf_previous_sector"] = sector
    sector_row = next((row for row in sectors if row.get("sector") == sector), {})
    if sector:
        st.caption(f"Hạng ngành: {sector_row.get('rank') or 'N/A'} · Trạng thái: {sector_row.get('status') or 'N/A'} · Trên MA50: {_format(sector_row.get('breadth_ma50_pct'), '%')}")
    industry_names = sorted({str(row["industry"]) for row in industries if row.get("parent_sector") == sector and row.get("industry")} |
                            {str(c["sub_industry"]) for c in candidates if c.get("sector") == sector and c.get("sub_industry")})
    industry = st.selectbox("Nhóm ngành", [None, *industry_names],
                            format_func=lambda v: v or "Toàn ngành / chưa chọn nhóm", key="wf_industry", disabled=not sector)
    if st.session_state.get("wf_previous_industry") != industry:
        st.session_state["wf_candidate"] = None
        st.session_state["wf_previous_industry"] = industry
    industry_row = next((row for row in industries if row.get("parent_sector") == sector and row.get("industry") == industry), {})
    if industry:
        st.caption(f"Hạng nhóm: {industry_row.get('rank') or 'N/A'} · Số mã: {industry_row.get('stk_count') or 'N/A'} · Trên MA50: {_format(industry_row.get('breadth_ma50_pct'), '%')}")
        if industry_row.get("is_small_sample"):
            st.warning("Nhóm có mẫu nhỏ; không xem thứ hạng là bằng chứng đủ mạnh.")
    st.caption("Theme xuyên ngành chỉ hiển thị khi đã có mapping được xác minh cho mã ở bước 3.")
    group_links = st.columns(2)
    if group_links[0].button("Xem ngành →", key="wf_sector_detail"):
        _navigate("Ngành")
    if group_links[1].button("Xem nhóm ngành →", key="wf_industry_detail"):
        _navigate("Nhóm ngành")

    st.divider()
    st.subheader("3. Leadership / RS")
    ranked = rank_for_review(candidates_in_group(candidates, sector, industry))
    keyed = {candidate_key(c): c for c in ranked}
    keys = list(keyed)
    if not sector:
        st.info("Chọn ngành ở bước 2 để xem ứng viên và RS.")
    elif not keys:
        st.info("Không có ứng viên thuộc phạm vi đã chọn. Có thể ghi nhận không hành động ở bước 6.")
    selected_key = st.selectbox(
        "Ứng viên đang rà soát", [None, *keys], key="wf_candidate",
        format_func=lambda key: "Chưa chọn mã" if key is None else
        f"{key[0]} · {key[2]} · {keyed[key]['quality']['label']} · thứ tự trong phạm vi #{keyed[key]['review_rank']}",
        disabled=not keys,
    )
    candidate = keyed.get(selected_key)
    if candidate:
        st.write(f"**{candidate['symbol']}** · {candidate.get('company_name') or ''} · {candidate.get('group_type') or 'N/A'}")
        st.caption(f"RS rating: {candidate.get('rs_rating') if candidate.get('rs_rating') is not None else 'N/A'} · RS 20 phiên so SPY: {_format(rs_vs_spy(candidate, market), ' điểm %', 2)} · O’Neil leader: {'Có' if candidate.get('is_oneil_leader') else 'Chưa xác nhận'}")
        st.caption(f"Phù hợp độ rộng thị trường: {candidate.get('market_context_alignment') or 'chưa đủ dữ liệu'} · {candidate.get('market_context_summary') or ''}")
        themes = repo.get_symbol_themes(symbol=candidate["symbol"]) if hasattr(repo, "get_symbol_themes") else []
        if themes:
            st.caption("Theme đã xác minh: " + ", ".join(t["theme_name"] for t in themes))
    if st.button("Xem danh sách ứng viên →", key="wf_candidates_detail"):
        _navigate("Ứng viên", sector, industry)

    st.divider()
    st.subheader("4. Setup")
    if candidate:
        st.write(f"**{candidate.get('setup_type') or 'Chưa phân loại'}** · Trạng thái: {candidate.get('status') or 'N/A'}")
        st.caption(f"Trigger: {_format(candidate.get('trigger_price'), '$', 2)} · Mức vô hiệu: {_format(candidate.get('invalidation_price'), '$', 2)} · ATR14: {_format(candidate.get('atr14'), '$', 2)}")
        st.write(candidate.get("trigger_condition") or "Chưa có điều kiện trigger mô tả.")
    else:
        st.info("Chọn ứng viên ở bước 3 để xem setup.")

    st.divider()
    st.subheader("5. Risk")
    if candidate:
        quality = candidate["quality"]
        st.write(f"**{quality['label']}** · Bộ lọc {quality['version']}")
        st.caption("; ".join(quality["reasons"]))
        r1, r2, r3 = st.columns(3)
        r1.metric("Rủi ro giá tham chiếu", _format(quality.get("risk_pct"), "%"))
        r2.metric("Rủi ro theo ATR", _format(quality.get("risk_atr"), " ATR", 2))
        r3.metric("Khoảng trống / rủi ro", _format(quality.get("room_risk"), " R", 2))
        st.caption("Đây là rủi ro theo khoảng giá của setup. Số lượng cổ phiếu và rủi ro tài khoản cần được nhập trong phiếu kế hoạch.")
    else:
        st.info("Chọn ứng viên để kiểm tra rủi ro setup.")

    st.divider()
    st.subheader("6. Entry & repeat")
    if candidate:
        decisions = repo.get_trade_decisions(session_date=as_of, symbol=candidate["symbol"])
        current = next((d for d in decisions if d.get("snapshot_id") == snapshot_id), None)
        if current:
            st.write(f"Quyết định đã lưu: **{current['decision']}** · {current.get('decision_reason') or 'Chưa ghi lý do'}")
            st.caption(f"Kế hoạch: entry {_format(current.get('plan_entry_price'), '$', 2)} · stop {_format(current.get('plan_stop_price'), '$', 2)} · {current.get('plan_shares') or 'N/A'} cổ phiếu")
        else:
            st.info("Chưa có quyết định gắn với mã và snapshot này.")
        if st.button("Mở phiếu setup, kế hoạch & quyết định →", key="wf_open_setup"):
            show_setup_detail_dialog(candidate, as_of, repo, key_suffix=f"wf_{snapshot_id}")
    else:
        st.info("Không cần chọn mã nếu quyết định dừng ở bối cảnh hoặc nhóm ngành.")

    st.markdown("#### Ghi nhận lượt rà soát")
    outcome = st.selectbox("Kết luận", ["continue", "wait", "no_action"],
                           format_func=lambda v: {"continue": "Tiếp tục theo dõi / lập kế hoạch", "wait": "Chờ xác nhận", "no_action": "Không hành động"}[v], key="wf_outcome")
    stop_stage = st.selectbox("Dừng hoặc chờ tại bước", [None, *STAGES],
                              format_func=lambda v: v or "Đã đi hết sáu bước", key="wf_stop_stage")
    reason = st.text_area("Lý do (bắt buộc)", key="wf_reason", placeholder="Bằng chứng nào khiến bạn tiếp tục, chờ hoặc không hành động?")
    if st.button("Lưu đường đi rà soát", key="wf_save_review", type="primary"):
        if not reason.strip():
            st.error("Nhập lý do trước khi lưu.")
        elif outcome == "continue" and not candidate:
            st.error("Chọn ứng viên trước khi kết luận tiếp tục.")
        elif outcome == "continue" and stop_stage:
            st.error("Kết luận tiếp tục cần đi hết sáu bước; bỏ lựa chọn bước dừng.")
        elif outcome in {"wait", "no_action"} and not stop_stage:
            st.error("Chọn bước dừng hoặc chờ.")
        elif not candidate and stop_stage in STAGES[3:]:
            st.error("Chọn ứng viên trước khi ghi nhận dừng ở setup, rủi ro hoặc entry.")
        else:
            last_stage = STAGES.index(stop_stage) if stop_stage else len(STAGES) - 1
            reviewed_candidate = candidate if last_stage >= 2 else None
            evidence = {
                "market_summary": market.get("market_summary"),
                "market_ma50_pct": number(market.get("pct_above_ma50")),
                "market_ma200_pct": number(market.get("pct_above_ma200")),
                "coverage_pct": number(snapshot.get("coverage_pct")),
                "rule_version": snapshot.get("rule_version"),
            }
            if last_stage >= 1:
                evidence.update(sector_rank=sector_row.get("rank"), sector_status=sector_row.get("status"),
                                industry_rank=industry_row.get("rank"), industry_count=industry_row.get("stk_count"))
            if reviewed_candidate:
                evidence.update(rs_rating=reviewed_candidate.get("rs_rating"),
                                rs_vs_spy=rs_vs_spy(reviewed_candidate, market),
                                market_context_alignment=reviewed_candidate.get("market_context_alignment"))
            if reviewed_candidate and last_stage >= 3:
                evidence.update(trigger_price=reviewed_candidate.get("trigger_price"),
                                invalidation_price=reviewed_candidate.get("invalidation_price"))
            if reviewed_candidate and last_stage >= 4:
                evidence.update(quality_tier=reviewed_candidate.get("quality_tier"),
                                quality_version=reviewed_candidate.get("quality_version"),
                                quality_reasons=reviewed_candidate.get("quality_reasons"))
            repo.save_workflow_review({
                "snapshot_id": snapshot_id, "session_date": as_of,
                "sector": sector if last_stage >= 1 else None,
                "industry": industry if last_stage >= 1 else None,
                "symbol": reviewed_candidate.get("symbol") if reviewed_candidate else None,
                "group_type": reviewed_candidate.get("group_type") if reviewed_candidate else None,
                "setup_type": reviewed_candidate.get("setup_type") if last_stage >= 3 and reviewed_candidate else None,
                "outcome": outcome, "stop_stage": stop_stage, "reason": reason, "evidence": evidence,
            })
            st.success("Đã lưu lượt rà soát cho snapshot này.")

    history = repo.get_workflow_reviews(snapshot_id)
    with st.expander(f"Lịch sử rà soát snapshot này ({len(history)})"):
        if not history:
            st.caption("Chưa có lượt rà soát nào được lưu.")
        for row in history[:20]:
            st.write(f"**#{row['id']} · {row['outcome']}** · {row['created_at']} · {saved_review_path(row)}")
            st.caption(f"Dừng/chờ: {row.get('stop_stage') or 'Đi hết sáu bước'} · {row['reason']}")
            with st.popover(f"Bằng chứng đã lưu #{row['id']}"):
                st.json(row["evidence"])
    if st.button("Xem chất lượng tín hiệu →", key="wf_signal_quality"):
        _navigate("Chất lượng tín hiệu")
