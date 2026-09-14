"""
Signal Outcomes Update Job.
Evaluates forward outcomes (5, 10, 20 sessions) for all active and historical signals.
Can be executed as part of the daily EOD pipeline or as a standalone scheduled job.
"""
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config.settings import BENCHMARK_TICKER
from storage.database import init_db
from storage.repository import MarketRadarRepository
from analytics.signal_outcomes import evaluate_signal_outcomes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("update_signal_outcomes")

def run_update_signal_outcomes(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Evaluate and update forward outcomes for all stored signals."""
    init_db(db_path)
    repo = MarketRadarRepository(db_path)

    signals = repo.get_signal_records()
    if not signals:
        logger.info("Chưa có tín hiệu nào trong bảng signal_records để đánh giá.")
        return {"success": True, "total_signals": 0, "evaluated_outcomes": 0}

    # Fetch daily bars for symbols and SPY
    symbols = list(set(s["symbol"] for s in signals) | {BENCHMARK_TICKER})
    earliest_date = min(s["first_detected_date"] for s in signals)
    daily_bars = repo.get_daily_bars(symbols=symbols, start_date=earliest_date)

    if daily_bars.empty:
        logger.warning("Không tìm thấy dữ liệu giá ngày để đánh giá outcomes.")
        return {"success": False, "message": "Thiếu dữ liệu nến ngày."}

    logger.info(f"Bắt đầu đánh giá forward outcomes cho {len(signals)} tín hiệu...")
    outcomes = evaluate_signal_outcomes(signals, daily_bars, horizons=[1, 2, 3, 4, 99, 5, 10, 20])

    saved_count = repo.save_signal_outcomes(outcomes)

    # Persist resolved entry date & price back to signal_records
    entry_updates = {}
    for o in outcomes:
        sig_id = o.get("signal_id")
        if sig_id and o.get("entry_date") and o.get("entry_price") is not None and sig_id not in entry_updates:
            entry_updates[sig_id] = (o["entry_date"], o["entry_price"], o.get("spy_entry_price"))

    for sig_id, (e_date, e_price, spy_p) in entry_updates.items():
        repo.update_signal_entry_info(sig_id, e_date, e_price, spy_p)

    completed = sum(1 for o in outcomes if o.get("status") == "completed")
    pending = sum(1 for o in outcomes if o.get("status") == "pending")
    no_window = sum(1 for o in outcomes if o.get("status") == "no_window_in_week")

    msg = f"Đã cập nhật {saved_count} outcomes ({completed} hoàn tất, {pending} đang chờ, {no_window} không còn window trong tuần)."
    logger.info(msg)

    return {
        "success": True,
        "total_signals": len(signals),
        "evaluated_outcomes": saved_count,
        "completed": completed,
        "pending": pending,
        "message": msg
    }

if __name__ == "__main__":
    res = run_update_signal_outcomes()
    print(res)
