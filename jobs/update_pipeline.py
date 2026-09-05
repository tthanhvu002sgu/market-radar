import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd

from config.settings import (
    RULE_VERSION,
    MIN_COVERAGE_PCT,
    BENCHMARK_TICKER,
    BENCHMARK_EQUAL_WEIGHT,
)
from config.sector_mappings import SECTOR_ETF_MAP
from storage.database import init_db
from storage.lock import ProcessLock
from storage.repository import MarketRadarRepository
from providers.sp500_provider import WikipediaSP500Provider
from providers.yfinance_provider import YFinanceProvider
from analytics.market_breadth import compute_stock_indicators, compute_market_breadth
from analytics.sector_ranker import rank_sectors
from analytics.screening_rules import screen_candidates

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("update_pipeline")

def run_update_pipeline(db_path=None, force: bool = False) -> Dict[str, Any]:
    """
    Execute full update pipeline:
    1. Lock process
    2. Update S&P 500 universe
    3. Update daily OHLCV for universe & benchmark ETFs
    4. Calculate market breadth and sector ranks
    5. Screen candidates and enrich fundamentals
    6. Persist snapshot
    """
    repo = MarketRadarRepository(db_path)
    init_db(db_path)

    lock = ProcessLock()
    if not lock.acquire():
        msg = "Cập nhật đang được tiến trình khác thực thi. Vui lòng thử lại sau."
        logger.warning(msg)
        return {"success": False, "message": msg}

    try:
        start_time = datetime.now()
        logger.info("=== Bắt đầu chu kỳ cập nhật Market Radar ===")

        # 1. Fetch S&P 500 Constituents
        sp500_provider = WikipediaSP500Provider()
        constituents = sp500_provider.fetch_constituents()
        if not constituents:
            raise ValueError("Không thể lấy danh sách cổ phiếu S&P 500.")
        repo.save_constituents(constituents)
        logger.info(f"Đã lưu {len(constituents)} mã S&P 500 vào cơ sở dữ liệu.")

        # Universe symbols
        sp500_symbols = [c["symbol"] for c in constituents]
        etf_symbols = [BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT] + list(SECTOR_ETF_MAP.values())
        all_symbols = sp500_symbols + etf_symbols

        # 2. Fetch Daily OHLCV Bars
        yf_provider = YFinanceProvider(batch_size=100)
        daily_records, failed_symbols = yf_provider.fetch_daily_ohlcv(all_symbols, period="1y")

        if not daily_records:
            raise ValueError("Không thể tải nến ngày từ nguồn dữ liệu.")

        repo.save_daily_bars(daily_records)
        logger.info(f"Đã lưu {len(daily_records)} bản ghi giá ngày vào database.")

        # Calculate coverage
        valid_sp500_symbols = set(r[0] for r in daily_records if r[0] in sp500_symbols)
        total_sp500 = len(sp500_symbols)
        valid_count = len(valid_sp500_symbols)
        coverage_pct = round(valid_count / total_sp500, 4) if total_sp500 > 0 else 0.0

        logger.info(f"Độ bao phủ S&P 500: {valid_count}/{total_sp500} ({coverage_pct * 100.0:.1f}%)")
        if coverage_pct < MIN_COVERAGE_PCT:
            logger.warning(f"Cảnh báo: Độ bao phủ ({coverage_pct*100:.1f}%) thấp hơn ngưỡng {MIN_COVERAGE_PCT*100}%!")

        # 3. Analytics: Indicators & Breadth
        # Query last 260 days of daily bars from DB for indicators
        df_bars = repo.get_daily_bars(symbols=all_symbols)
        latest_stocks_df = compute_stock_indicators(df_bars)
        if latest_stocks_df.empty:
            raise ValueError("Không thể tính toán các chỉ báo kỹ thuật từ dữ liệu giá.")

        constituents_df = repo.get_constituents()
        # Merge sector info into latest_stocks_df
        latest_stocks_df = pd.merge(
            latest_stocks_df,
            constituents_df[["symbol", "security", "sector", "sub_industry"]],
            on="symbol",
            how="left"
        )

        market_metrics = compute_market_breadth(latest_stocks_df, df_bars)
        sector_metrics = rank_sectors(latest_stocks_df, constituents_df)

        # 4. Preliminary screening to find priority candidates for FA enrichment
        prelim_candidates = screen_candidates(latest_stocks_df, sector_metrics, None)
        candidate_symbols = list(dict.fromkeys(c["symbol"] for c in prelim_candidates))

        # 5. Fetch fundamentals & earnings calendar for candidate symbols
        if candidate_symbols:
            logger.info(f"Cập nhật FA và lịch earnings cho {len(candidate_symbols)} mã ứng viên...")
            fa_records = yf_provider.fetch_fundamentals(candidate_symbols)
            repo.save_fundamentals(fa_records)

        # Reload fundamentals and re-run final candidate screening
        fundamentals_df = repo.get_fundamentals(candidate_symbols) if candidate_symbols else pd.DataFrame()
        final_candidates = screen_candidates(latest_stocks_df, sector_metrics, fundamentals_df)

        # 6. Save Snapshot
        latest_date = repo.get_latest_bar_date() or datetime.now().strftime("%Y-%m-%d")
        snapshot_id = repo.save_snapshot(
            as_of=latest_date,
            rule_version=RULE_VERSION,
            total_universe=total_sp500,
            valid_universe=valid_count,
            coverage_pct=coverage_pct,
            missing_symbols=failed_symbols,
            market_metrics=market_metrics,
            sector_metrics=sector_metrics,
            candidates=final_candidates
        )

        duration = (datetime.now() - start_time).total_seconds()
        msg = f"Cập nhật thành công snapshot #{snapshot_id} (As of: {latest_date}) trong {duration:.1f}s. Độ bao phủ: {coverage_pct*100:.1f}%. Tổng ứng viên: {len(final_candidates)}."
        logger.info(msg)

        return {
            "success": True,
            "snapshot_id": snapshot_id,
            "as_of": latest_date,
            "coverage_pct": coverage_pct,
            "total_candidates": len(final_candidates),
            "message": msg
        }

    except Exception as e:
        logger.error(f"Lỗi trong quá trình cập nhật: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Lỗi cập nhật: {str(e)}"
        }
    finally:
        lock.release()

if __name__ == "__main__":
    res = run_update_pipeline()
    print(res)
