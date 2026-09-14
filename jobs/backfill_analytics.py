"""
Backfill script for snapshots missing market_history, sector_rotation, or sector_health.
Computes analytics directly from daily_bars and constituents already stored in SQLite.
Does not require re-fetching data from Wikipedia or Yahoo Finance.
"""
import logging
import sys
from typing import Optional, List, Dict, Any
import pandas as pd

from storage.repository import MarketRadarRepository
from analytics.market_breadth import compute_stock_indicators
from analytics.market_participation import compute_market_breadth_history, compute_sector_health
from analytics.sector_rotation import compute_sector_rotation

logger = logging.getLogger(__name__)


def backfill_snapshot_analytics(
    snapshot_id: Optional[int] = None,
    repo: Optional[MarketRadarRepository] = None
) -> bool:
    """
    Backfill market_history, sector_rotation, and sector_health for snapshots.
    If snapshot_id is None, backfills all snapshots missing market_history.
    """
    if repo is None:
        repo = MarketRadarRepository()

    target_snapshots = []
    if snapshot_id is not None:
        snap = repo.get_snapshot_by_id(snapshot_id)
        if snap:
            target_snapshots.append(snap)
    else:
        all_snaps = repo.get_snapshots_list(limit=50)
        for s in all_snaps:
            full_snap = repo.get_snapshot_by_id(s["id"])
            if full_snap and not full_snap.get("market_history"):
                target_snapshots.append(full_snap)

    if not target_snapshots:
        logger.info("Không có snapshot nào cần backfill analytics.")
        return True

    df_bars = repo.get_daily_bars()
    if df_bars.empty:
        logger.error("Không tìm thấy dữ liệu daily_bars trong database để backfill.")
        return False

    constituents_df = repo.get_constituents()

    for snap in target_snapshots:
        sid = snap["id"]
        target_session = snap.get("as_of")
        if not target_session:
            continue

        logger.info(f"Đang tính toán analytics cho Snapshot #{sid} (phiên {target_session})...")

        # 1. Market participation breadth history (past 60 sessions)
        market_history = compute_market_breadth_history(
            df_bars,
            constituents_df=constituents_df,
            max_sessions=60,
            as_of=target_session
        )

        # 2. Sector relative strength rotation vs SPY (4 quadrants & historical trails)
        sector_rotation = compute_sector_rotation(
            df_bars,
            as_of=target_session,
            trail_length=10
        )

        # 3. Sector health
        # Filter bars up to target_session for point-in-time safety
        pit_bars = df_bars.copy()
        if not pd.api.types.is_string_dtype(pit_bars["date"]):
            pit_bars["date_str"] = pit_bars["date"].dt.strftime("%Y-%m-%d")
        else:
            pit_bars["date_str"] = pit_bars["date"].astype(str)
        pit_bars = pit_bars[pit_bars["date_str"] <= target_session]

        latest_stocks_df = compute_stock_indicators(pit_bars)
        if not latest_stocks_df.empty and not constituents_df.empty:
            latest_stocks_df = latest_stocks_df.merge(
                constituents_df[["symbol", "security", "sector", "sub_industry"]],
                on="symbol",
                how="left"
            )

        sector_health = compute_sector_health(
            latest_stocks_df,
            df_bars,
            constituents_df,
            as_of=target_session
        )

        # 4. Save to repository
        repo.update_snapshot_analytics(
            snapshot_id=sid,
            market_history=market_history,
            sector_rotation=sector_rotation,
            sector_health=sector_health,
            methodology_version="v2.1"
        )
        logger.info(f"Hoàn thành backfill analytics cho Snapshot #{sid}.")

    return True


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    target_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    backfill_snapshot_analytics(target_id)
