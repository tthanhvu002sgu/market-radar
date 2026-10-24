"""
Trang "Dòng tiền OFI" — Order Flow Imbalance Level-1 (Cont-Kukanov-Stoikov 2014).

Hai chế độ:
- Live (phiên đang mở): fetch quote Alpaca (IEX) trực tiếp, cache 2 phút.
- Lịch sử: đọc ofi_history.db do workflow OFI collector thu thập mỗi 15 phút.

OFI từ feed IEX là xấp xỉ của dòng tiền toàn thị trường (~2-3% khối lượng),
horizon dự báo ngắn (giây-phút) — dùng làm bối cảnh dòng tiền phiên,
không phải tín hiệu mua/bán cho swing trading.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.market_calendar import get_market_status_now
from analytics.order_flow_imbalance import (
    OFI_ZSCORE_MIN_MINUTES,
    OFI_ZSCORE_WINDOW,
    compute_ofi_from_quotes,
)
from config.settings import OFI_DB_PATH, OFI_MAX_SYMBOLS
from providers.alpaca_provider import AlpacaAuthError, AlpacaQuoteProvider
from storage.ofi_store import OfiHistoryRepository

logger = logging.getLogger(__name__)

CHART_TOP_N = 8
LIVE_FETCH_WORKERS = 8


def _candidate_symbols(candidates: List[Dict[str, Any]], cap: bool = True) -> List[str]:
    """Trích symbol, sắp theo rank (None cuối) để khớp thứ tự với job collector."""
    seen = set()
    entries = []
    for idx, c in enumerate(candidates or []):
        sym = (c.get("symbol") or "").strip().upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        rank = c.get("rank")
        rank_val = rank if isinstance(rank, (int, float)) else 0.0
        entries.append((((rank is None), rank_val), idx, sym))
    entries.sort(key=lambda t: (t[0], t[1]))
    symbols = [sym for _, _, sym in entries]
    return symbols[:OFI_MAX_SYMBOLS] if cap else symbols


def _fetch_one_symbol(provider: AlpacaQuoteProvider, sym: str):
    try:
        quotes = provider.fetch_session_quotes(sym)
        if quotes.empty:
            return sym, None
        metrics = compute_ofi_from_quotes(quotes, symbol=sym)
        return sym, (metrics if metrics["status"] == "ok" else None)
    except AlpacaAuthError:
        raise
    except Exception as exc:
        logger.warning(f"Lỗi tính OFI live cho {sym}: {exc}")
        return sym, None


@st.cache_data(ttl=120, show_spinner=False)
def fetch_live_ofi_metrics(symbols: tuple) -> Dict[str, Any]:
    """Fetch quotes phiên hiện tại cho các symbols (song song) và tính metrics OFI.

    Returns {"configured": bool, "auth_error": bool, "metrics": {sym: metrics}}.
    auth_error=True khi Alpaca từ chối key (401/403) — tách khỏi 'không có dữ liệu'.
    """
    provider = AlpacaQuoteProvider()
    if not provider.is_configured():
        return {"configured": False, "auth_error": False, "metrics": {}}

    metrics: Dict[str, Any] = {}
    try:
        with ThreadPoolExecutor(max_workers=LIVE_FETCH_WORKERS) as executor:
            futures = [executor.submit(_fetch_one_symbol, provider, sym) for sym in symbols]
            for future in as_completed(futures):
                sym, result = future.result()
                if result is not None:
                    metrics[sym] = result
    except AlpacaAuthError:
        return {"configured": True, "auth_error": True, "metrics": {}}
    return {"configured": True, "auth_error": False, "metrics": metrics}


def _plot_cum_ofi(records_by_symbol: Dict[str, List[Dict[str, Any]]], title: str) -> go.Figure:
    fig = go.Figure()
    for sym, records in records_by_symbol.items():
        ts = pd.to_datetime([r["ts"] for r in records])
        cum = [r["cum_ofi"] for r in records]
        fig.add_trace(go.Scatter(x=ts, y=cum, mode="lines", name=sym, line={"width": 2}))
    fig.update_layout(
        title=title,
        xaxis_title="Thời gian (UTC)",
        yaxis_title="OFI tích luỹ",
        height=380,
        margin={"l": 10, "r": 10, "t": 45, "b": 10},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        hovermode="x unified",
    )
    fig.add_hline(y=0, line_dash="dot", line_color="#9F2F2D", opacity=0.5)
    return fig


def _metrics_table(metrics: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    for sym, m in metrics.items():
        rows.append({
            "Symbol": sym,
            "OFI tích luỹ": round(m["integrated_ofi"], 0),
            "Z-score": round(m["ofi_zscore"], 2) if m["ofi_zscore"] is not None else None,
            "Imbalance": round(m["imbalance_ratio"], 3),
            "Số phút": m["n_minutes"],
            "Corr(OFI, Δmid)": round(m["ofi_price_corr"], 2) if m["ofi_price_corr"] is not None else None,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("OFI tích luỹ", key=lambda s: s.abs(), ascending=False)


def _render_live_section(symbols: List[str]):
    st.markdown("#### Phiên hiện tại (live)")
    with st.spinner("Đang tải quote từ Alpaca (IEX)..."):
        payload = fetch_live_ofi_metrics(tuple(symbols))

    if not payload["configured"]:
        st.info(
            "Chưa cấu hình Alpaca API key. Tạo tài khoản (paper) miễn phí tại "
            "[alpaca.markets](https://alpaca.markets), rồi set biến môi trường "
            "`APCA_API_KEY_ID` và `APCA_API_SECRET_KEY` trên Render (Dashboard → Environment) "
            "và GitHub Actions secrets (cho workflow thu thập lịch sử).",
            icon="🔑",
        )
        return

    if payload.get("auth_error"):
        st.error(
            "Alpaca từ chối API key (HTTP 401/403) — kiểm tra lại `APCA_API_KEY_ID` / "
            "`APCA_API_SECRET_KEY` trên Render. Đây là lỗi xác thực, không phải thiếu dữ liệu.",
            icon="⛔",
        )
        return

    metrics = payload["metrics"]
    if not metrics:
        st.caption("Chưa có dữ liệu quote — có thể thị trường chưa mở hoặc IEX chưa có update cho các symbol này.")
        return

    top = dict(sorted(metrics.items(), key=lambda kv: abs(kv[1]["integrated_ofi"]), reverse=True)[:CHART_TOP_N])
    st.plotly_chart(_plot_cum_ofi(top, "OFI tích luỹ — top candidates"), use_container_width=True)

    table = _metrics_table(metrics)
    st.dataframe(table.set_index("Symbol"), use_container_width=True)
    st.caption(
        f"Z-score: block OFI {OFI_ZSCORE_WINDOW} phút cuối so với phân phối cả phiên "
        f"(chỉ hiện khi có tối thiểu {OFI_ZSCORE_MIN_MINUTES} phút dữ liệu). "
        "Corr(OFI, Δmid): tương quan OFI phút với biến động mid-price (chẩn đoán kiểu CKS)."
    )


def _render_history_section(symbols: List[str]):
    st.markdown("#### Lịch sử theo phiên (thu thập mỗi 15 phút bởi workflow OFI)")
    try:
        store = OfiHistoryRepository(OFI_DB_PATH)
    except Exception as exc:
        st.warning(f"Không mở được ofi_history.db: {exc}")
        return

    session_dates = store.get_session_dates()
    if not session_dates:
        st.caption("Chưa có lịch sử OFI. Dữ liệu sẽ xuất hiện sau khi workflow `ofi_collector` chạy với Alpaca keys đã cấu hình.")
        return

    chosen = st.selectbox("Phiên", session_dates, index=0, key="ofi_history_session")
    summaries = store.get_session_summaries(chosen)
    if summaries.empty:
        st.caption(f"Không có dữ liệu cho phiên {chosen}.")
        return

    history = store.get_ofi_history(start_date=chosen, end_date=chosen)
    records_by_symbol: Dict[str, List[Dict[str, Any]]] = {}
    for sym, grp in history.groupby("symbol"):
        grp = grp.sort_values("ts")
        cum = grp["cum_ofi"].tolist()
        records_by_symbol[sym] = [
            {"ts": ts, "cum_ofi": c} for ts, c in zip(grp["ts"], cum)
        ]

    top_syms = (
        summaries.assign(abs_ofi=summaries["integrated_ofi"].abs())
        .sort_values("abs_ofi", ascending=False)["symbol"]
        .head(CHART_TOP_N)
        .tolist()
    )
    top_records = {s: records_by_symbol[s] for s in top_syms if s in records_by_symbol}
    if top_records:
        st.plotly_chart(_plot_cum_ofi(top_records, f"OFI tích luỹ — phiên {chosen}"), use_container_width=True)

    display = summaries.copy()
    display["integrated_ofi"] = display["integrated_ofi"].round(0)
    display["imbalance_ratio"] = pd.to_numeric(display["imbalance_ratio"], errors="coerce").round(3)
    display = display.rename(columns={
        "symbol": "Symbol", "session_date": "Phiên", "integrated_ofi": "OFI tích luỹ",
        "imbalance_ratio": "Imbalance", "n_minutes": "Số phút", "first_ts": "Từ", "last_ts": "Đến",
    })
    st.dataframe(display.set_index("Symbol"), use_container_width=True)


def render_ofi_section(candidates: List[Dict[str, Any]], as_of: str) -> None:
    st.markdown(
        "Dòng tiền vi cấu trúc (Order Flow Imbalance) của các ứng viên — áp lực mua/bán ròng "
        "sinh ra từ thay đổi khối lượng tại best bid/ask, theo Cont-Kukanov & Stoikov (2014)."
    )

    all_symbols = _candidate_symbols(candidates, cap=False)
    symbols = all_symbols[:OFI_MAX_SYMBOLS]
    if not symbols:
        st.warning("Không có ứng viên nào trong snapshot hiện tại.")
        return

    status = get_market_status_now()
    phase_labels = {
        "regular": "🟢 Phiên đang mở",
        "pre_market": "🕐 Trước phiên",
        "after_hours": "🌆 Sau giờ",
        "closed_night": "🔴 Đóng cửa (đêm)",
        "weekend": "🔴 Cuối tuần",
        "holiday": "🔴 Nghỉ lễ",
    }
    cap_note = (
        f" · hiển thị top {len(symbols)} theo rank (tổng {len(all_symbols)} ứng viên)"
        if len(all_symbols) > len(symbols) else ""
    )
    st.caption(
        f"{phase_labels.get(status.get('status_phase'), '—')} · "
        f"Theo dõi {len(symbols)} ứng viên từ snapshot {as_of}{cap_note}"
    )

    tab_live, tab_history = st.tabs(["Phiên hiện tại", "Lịch sử"])
    with tab_live:
        _render_live_section(symbols)
    with tab_history:
        _render_history_section(symbols)

    with st.expander("Phương pháp & giới hạn"):
        st.markdown(
            """
**OFI Level-1 (CKS 2014).** Với mỗi quote update, áp lực ròng:

`eₙ = 1{Pᵇₙ ≥ Pᵇₙ₋₁}·qᵇₙ − 1{Pᵇₙ ≤ Pᵇₙ₋₁}·qᵇₙ₋₁ − 1{Pᵃₙ ≤ Pᵃₙ₋₁}·qᵃₙ + 1{Pᵃₙ ≥ Pᵃₙ₋₁}·qᵃₙ₋₁`

Tổng hợp theo phút; **OFI tích luỹ** là tổng từ đầu phiên.

**Xử lý quote:** một bên sổ rỗng (giá 0) được giữ như size 0 — bắt được event
rút sạch một bên; quote locked (bid = ask) được giữ; quote cross (bid > ask)
và giá âm bị loại.

**Giới hạn quan trọng:**
- Nguồn quote là feed **IEX** (Alpaca free tier) — chỉ ~2–3% khối lượng thị trường Mỹ,
  nên OFI này là **xấp xỉ** của dòng tiền toàn thị trường, không phải sổ lệnh hợp nhất.
- Horizon dự báo của OFI ở mức **giây–phút**, khác với phong cách swing nhiều ngày:
  dùng như bối cảnh dòng tiền trong phiên (xác nhận/hợp lệ hoá setup), không phải tín hiệu mua/bán.
- Không thấy dark pool, hidden order; lệnh sửa trên sàn hiện thành hủy + đặt mới.
"""
        )
