"""
OFI Collection Job — thu thập quote Alpaca (feed IEX) trong phiên Mỹ cho các
candidate từ snapshot mới nhất, tính OFI Level-1 theo phút và lưu vào
ofi_history.db (DB riêng, xem storage/ofi_store.py).

Được chạy bởi workflow .github/workflows/ofi_collector.yml mỗi 15 phút trong phiên.
Idempotent: cursor theo symbol + PK (symbol, ts). Mỗi lần chạy fetch lại buffer
3 phút trước cursor để tính lại trọn phút đang dở, nhưng chỉ lưu bucket từ
cursor trở đi (tránh ghi đè phút đã hoàn chỉnh bằng bản thiếu event).
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from analytics.market_calendar import get_market_status_now
from analytics.order_flow_imbalance import (
    OFI_BUCKET_SECONDS,
    aggregate_ofi_buckets,
    compute_ofi_events,
)
from config.settings import OFI_MAX_SYMBOLS, US_MARKET_TZ
from providers.alpaca_provider import AlpacaAuthError, AlpacaQuoteProvider, get_us_session_window
from storage.ofi_store import OfiHistoryRepository
from storage.repository import MarketRadarRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("update_ofi")

# Chỉ thu thập trong phiên regular + shortly sau đóng (after_hours) để chốt nốt
# phút cuối. Cron 21:45 UTC (16:45 EST / 17:45 EDT) nằm trong after_hours.
COLLECT_PHASES = {"regular", "after_hours"}
FETCH_BUFFER_BUCKETS = 3


def _rank_sort_key(candidate: Dict[str, Any], index: int):
    """Sắp xếp candidate theo rank (None cuối), giữ thứ tự gốc cho rank bằng nhau."""
    rank = candidate.get("rank")
    rank_val = rank if isinstance(rank, (int, float)) else 0.0
    return ((rank is None, rank_val), index)


def _resolve_candidate_symbols(repo: MarketRadarRepository) -> List[str]:
    """Lấy danh sách symbol candidate từ snapshot mới nhất (đọc-only), theo rank."""
    snapshot = repo.get_latest_snapshot()
    if not snapshot:
        return []
    candidates = repo.get_candidates_by_snapshot(snapshot.get("id"))
    entries = []
    for idx, c in enumerate(candidates):
        sym = (c.get("symbol") or "").strip().upper()
        if sym:
            entries.append((_rank_sort_key(c, idx), sym))
    entries.sort(key=lambda pair: pair[0])
    symbols: List[str] = []
    for _, sym in entries:
        if sym not in symbols:
            symbols.append(sym)
    return symbols


def _iso_z(ts: pd.Timestamp) -> str:
    """Format timestamp chuẩn ISO-Z (không phụ thuộc str(Timestamp) của pandas)."""
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def _buckets_to_records(buckets: pd.DataFrame, symbol: str, session_date: str) -> List[Dict[str, Any]]:
    records = []
    for _, row in buckets.iterrows():
        records.append({
            "symbol": symbol,
            "ts": _iso_z(row["ts"]),
            "session_date": session_date,
            "ofi": float(row["ofi"]),
            "n_updates": int(row["n_updates"]),
            "spread_avg": float(row["spread_avg"]) if pd.notna(row["spread_avg"]) else None,
            "bid_size_last": float(row["bid_size_last"]) if pd.notna(row["bid_size_last"]) else None,
            "ask_size_last": float(row["ask_size_last"]) if pd.notna(row["ask_size_last"]) else None,
            "mid_first": float(row["mid_first"]) if pd.notna(row["mid_first"]) else None,
            "mid_last": float(row["mid_last"]) if pd.notna(row["mid_last"]) else None,
            "source": "iex",
        })
    return records


def run_update_ofi(
    db_path: Optional[str] = None,
    ofi_db_path: Optional[str] = None,
    provider: Optional[AlpacaQuoteProvider] = None,
    main_repo: Optional[MarketRadarRepository] = None,
    market_status: Optional[Dict[str, Any]] = None,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Thu thập và lưu OFI phút cho candidates của phiên hiện tại."""
    provider = provider or AlpacaQuoteProvider()
    if not provider.is_configured():
        logger.info("Chưa cấu hình Alpaca API key (APCA_API_KEY_ID/SECRET) — bỏ qua job OFI.")
        return {"success": True, "skipped": "missing_alpaca_keys",
                "symbols_collected": 0, "minutes_saved": 0}

    status = market_status or get_market_status_now()
    phase = status.get("status_phase")
    if phase not in COLLECT_PHASES:
        logger.info(f"Thị trường đang ở trạng thái '{phase}' — không thu thập OFI.")
        return {"success": True, "skipped": f"market_{phase}",
                "symbols_collected": 0, "minutes_saved": 0}

    session_date = datetime.now(ZoneInfo(US_MARKET_TZ)).date()
    session_date_str = session_date.strftime("%Y-%m-%d")
    start_utc, end_utc = get_us_session_window(session_date)
    now = now_utc or datetime.now(ZoneInfo("UTC"))
    effective_end = min(now, end_utc)

    repo = main_repo or MarketRadarRepository(db_path)
    symbols = _resolve_candidate_symbols(repo)[:OFI_MAX_SYMBOLS]
    if not symbols:
        logger.info("Không có candidate nào trong snapshot mới nhất — bỏ qua job OFI.")
        return {"success": True, "skipped": "no_candidates", "session_date": session_date_str,
                "symbols_collected": 0, "minutes_saved": 0}

    ofi_store = OfiHistoryRepository(ofi_db_path)
    buffer = pd.Timedelta(seconds=OFI_BUCKET_SECONDS * FETCH_BUFFER_BUCKETS)

    collected: List[str] = []
    no_data: List[str] = []
    minutes_saved = 0

    for sym in symbols:
        cursor = ofi_store.get_cursor(sym)
        session_start_ts = pd.Timestamp(start_utc)
        cursor_ts = pd.Timestamp(cursor) if cursor else None
        # Kẹp cursor theo đầu phiên hiện tại: không ghép event OFI qua ranh giới
        # phiên (gap qua đêm sẽ phồng OFI phút đầu phiên) và không fetch lại
        # dữ liệu các phiên cũ. Buffer chỉ có tác dụng trong phiên.
        floor = max(cursor_ts, session_start_ts) if cursor_ts else session_start_ts
        fetch_start = max((floor - buffer).to_pydatetime(), start_utc)

        try:
            quotes = provider.fetch_quotes(sym, fetch_start, effective_end)
        except AlpacaAuthError:
            logger.error(
                "Alpaca xác thực thất bại (401/403) — dừng job OFI. Kiểm tra "
                "APCA_API_KEY_ID / APCA_API_SECRET_KEY."
            )
            return {"success": False, "error": "alpaca_auth",
                    "session_date": session_date_str,
                    "symbols_collected": 0, "minutes_saved": 0}
        if quotes.empty:
            no_data.append(sym)
            continue

        events = compute_ofi_events(quotes)
        buckets = aggregate_ofi_buckets(events, bucket_seconds=OFI_BUCKET_SECONDS)
        if buckets.empty:
            no_data.append(sym)
            continue

        # Chỉ lưu bucket từ cursor trở đi; buffer chỉ dùng để có ngữ cảnh tính
        # lại trọn phút đang dở.
        buckets = buckets[pd.to_datetime(buckets["ts"]) >= floor]
        if buckets.empty:
            no_data.append(sym)
            continue

        records = _buckets_to_records(buckets, sym, session_date_str)
        minutes_saved += ofi_store.save_ofi_minutes(records)
        ofi_store.save_cursor(sym, _iso_z(buckets["ts"].iloc[-1]))
        collected.append(sym)
        logger.info(f"OFI {sym}: lưu {len(records)} phút (từ {records[0]['ts']}).")

    result = {
        "success": True,
        "session_date": session_date_str,
        "phase": phase,
        "symbols_requested": len(symbols),
        "symbols_collected": len(collected),
        "symbols_no_data": no_data,
        "minutes_saved": minutes_saved,
    }
    # Chống mù vận hành: giữa phiên (sau 15 phút đầu) mà không có symbol nào
    # có dữ liệu quote thì gần như chắc chắn có vấn đề (key/feed/symbols) —
    # báo thất bại để workflow GitHub Actions hiện đỏ thay vì xanh vô nghĩa.
    elapsed_seconds = (effective_end - start_utc).total_seconds()
    if not collected and no_data and phase == "regular" and elapsed_seconds >= 900:
        result["success"] = False
        result["degraded"] = True
        result["message"] = (
            "Đã quá 15 phút đầu phiên nhưng không thu thập được quote của bất kỳ "
            "symbol nào — kiểm tra API key / feed Alpaca."
        )
    logger.info(f"Job OFI hoàn tất: {json.dumps(result, ensure_ascii=False)}")
    return result


if __name__ == "__main__":
    outcome = run_update_ofi()
    logger.info(json.dumps(outcome, ensure_ascii=False))
    sys.exit(0 if outcome.get("success") else 1)
