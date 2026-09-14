import logging
import sys
from datetime import datetime, time, timedelta, date
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo
import pandas as pd

from config.settings import (
    RULE_VERSION,
    MIN_COVERAGE_PCT,
    BENCHMARK_TICKER,
    BENCHMARK_EQUAL_WEIGHT,
    BARS_FETCH_PERIOD,
    US_MARKET_TZ,
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
)
from config.sector_mappings import SECTOR_ETF_MAP
from storage.database import init_db
from storage.lock import ProcessLock
from storage.repository import MarketRadarRepository
from providers.sp500_provider import WikipediaSP500Provider
from providers.yfinance_provider import YFinanceProvider
from analytics.market_breadth import compute_stock_indicators, compute_market_breadth
from analytics.sector_ranker import rank_sectors
from analytics.industry_ranker import rank_industry_groups
from analytics.screening_rules import screen_candidates
from analytics.market_participation import compute_market_breadth_history, compute_sector_health
from analytics.sector_rotation import compute_sector_rotation

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

from analytics.market_calendar import determine_trading_session

def determine_target_trading_session(ref_time: Optional[datetime] = None) -> Tuple[str, bool]:
    """
    Determine the target closed US equity trading session in America/New_York [D-03].
    Uses official NYSE calendar holidays and early closes (13:00 ET).
    """
    return determine_trading_session(ref_time)


def process_base_detection_for_session(
    repo: MarketRadarRepository,
    df_bars: pd.DataFrame,
    active_bars: pd.DataFrame,
    fresh_sp500: Set[str],
    sp500_symbols: List[str],
    target_session: str,
    spy_1m: Optional[float] = None,
    rs_ratings_map: Optional[Dict[str, int]] = None
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Detect consolidation bases, track post-breakout lifecycle, and maintain state machine across sessions.
    - Tracks active post-breakout bases (Fresh breakouts -> Climbing -> Played out).
    - Scopes new base detection strictly to S&P 500 stocks (excluding benchmark and ETFs).
    - Retains ongoing active bases for symbols with missing/stale data as observation records.
    - Excludes stale symbols from base_building_symbols to prevent corrupting candidate FA priority.
    """
    from analytics.base_detector import detect_base, track_post_breakout_base

    base_records = []
    base_building_symbols = []
    recorded_base_ids = set()

    prev_active_bases = repo.get_active_bases_by_symbol(before_date=target_session)
    active_post_breakouts = repo.get_active_post_breakout_bases(before_date=target_session)

    bars_by_sym = active_bars.groupby("symbol") if not active_bars.empty and "symbol" in active_bars.columns else None
    all_bars_by_sym = df_bars.groupby("symbol") if not df_bars.empty and "symbol" in df_bars.columns else None

    # 1. Track ongoing active post-breakout bases (Fresh breakouts & Climbing)
    for pb in active_post_breakouts:
        sym = pb["symbol"]
        bid = pb.get("base_id")
        if sp500_symbols and sym not in sp500_symbols:
            continue

        s_bars = pd.DataFrame()
        if bars_by_sym and sym in bars_by_sym.groups:
            s_bars = bars_by_sym.get_group(sym)
        elif all_bars_by_sym and sym in all_bars_by_sym.groups:
            s_bars = all_bars_by_sym.get_group(sym)

        rs_val = (rs_ratings_map or {}).get(sym)
        res_pb = track_post_breakout_base(
            previous_base=pb,
            bars=s_bars,
            as_of=target_session,
            rs_rating=rs_val,
            spy_perf_20d=spy_1m
        )
        base_dict = res_pb.to_dict()
        base_records.append(base_dict)
        if bid:
            recorded_base_ids.add(bid)

    processed_symbols = set()
    # 2. Process fresh S&P 500 member stocks (forming bases or new bases)
    for sym in fresh_sp500:
        processed_symbols.add(sym)
        if bars_by_sym is None or sym not in bars_by_sym.groups:
            continue
        s_bars = bars_by_sym.get_group(sym)
        prev_base = prev_active_bases.get(sym)
        if not prev_base:
            prev_base = repo.get_last_base_by_symbol(sym, before_date=target_session)

        # If prev_base was already handled in active_post_breakouts, don't re-track as forming
        if prev_base and prev_base.get("base_id") in recorded_base_ids:
            prev_base = None

        rs_val = (rs_ratings_map or {}).get(sym)
        res = detect_base(s_bars, as_of=target_session, previous_base=prev_base, spy_perf_20d=spy_1m, rs_rating=rs_val)
        if res.base_id or res.is_active or res.state in ("forming", "tight", "breakout_unconfirmed", "breakout_confirmed", "fresh_breakout", "climbing", "played_out", "broken_down", "weakening", "lost_structure"):
            if res.base_id and res.base_id in recorded_base_ids:
                continue
            base_dict = res.to_dict()
            base_records.append(base_dict)
            if res.base_id:
                recorded_base_ids.add(res.base_id)
            if res.is_active and res.lifecycle_phase == "forming" and res.data_status == "valid":
                base_building_symbols.append(sym)

    # 3. Retain ongoing active bases for symbols with missing or stale data
    for sym, prev_base in prev_active_bases.items():
        if sym in processed_symbols:
            continue
        bid = prev_base.get("base_id")
        if bid and bid in recorded_base_ids:
            continue
        # Strictly ignore benchmark and sector ETFs that might be in legacy active bases
        if sp500_symbols and sym not in sp500_symbols:
            continue
        # Retrieve any available bars for sym from df_bars (e.g. older bars) or fallback to empty df
        s_bars = pd.DataFrame()
        if not df_bars.empty and "symbol" in df_bars.columns:
            s_bars = df_bars[df_bars["symbol"] == sym]

        rs_val = (rs_ratings_map or {}).get(sym)
        res = detect_base(s_bars, as_of=target_session, previous_base=prev_base, spy_perf_20d=spy_1m, rs_rating=rs_val)
        base_dict = res.to_dict()
        if base_dict.get("data_status") == "valid":
            base_dict["data_status"] = "stale_data"
        base_records.append(base_dict)
        if bid:
            recorded_base_ids.add(bid)
        # Stale/missing symbols are NOT added to base_building_symbols to avoid corrupting FA priority screening

    return base_records, base_building_symbols


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

        # 2. Fetch Daily OHLCV Bars (fetch 2y for >= 253 closes required by 252d returns) [D-01]
        yf_provider = YFinanceProvider(batch_size=100)
        daily_records, failed_symbols = yf_provider.fetch_daily_ohlcv(all_symbols, period=BARS_FETCH_PERIOD)

        if not daily_records:
            raise ValueError("Không thể tải nến ngày từ nguồn dữ liệu.")

        repo.save_daily_bars(daily_records)
        logger.info(f"Đã lưu {len(daily_records)} bản ghi giá ngày vào database.")

        # Query daily bars from DB for indicators
        df_bars = repo.get_daily_bars(symbols=all_symbols)

        # 3. Session alignment & Data Quality Gates [D-03]
        cal_session, is_closed_today = determine_target_trading_session()
        logger.info(f"America/New_York session audit: cal_session={cal_session}, is_closed_today={is_closed_today}")

        # If market today is NOT closed yet, discard unclosed intraday bars to prevent lookahead / incomplete signals
        if not is_closed_today:
            tz = ZoneInfo(US_MARKET_TZ)
            today_ny_str = datetime.now(tz).strftime("%Y-%m-%d")
            unclosed_mask = df_bars["date"].dt.strftime("%Y-%m-%d") == today_ny_str
            if unclosed_mask.any():
                logger.info(f"Đã loại bỏ {unclosed_mask.sum()} bản ghi nến ngày chưa chốt phiên của hôm nay ({today_ny_str}).")
                df_bars = df_bars[~unclosed_mask].copy()

        # Identify target session from benchmark SPY
        spy_bars = df_bars[df_bars["symbol"] == BENCHMARK_TICKER]
        if not spy_bars.empty:
            target_session = spy_bars["date"].dt.strftime("%Y-%m-%d").max()
        else:
            target_session = cal_session
            logger.warning(f"Cảnh báo: Không tìm thấy nến SPY! Tạm dùng target_session={target_session}")

        # Check session freshness: stocks having a bar on target_session
        fresh_symbols = set()
        stale_symbols = []
        bars_by_symbol = df_bars.groupby("symbol")
        for sym, sym_bars in bars_by_symbol:
            latest_sym_date = sym_bars["date"].dt.strftime("%Y-%m-%d").max()
            if latest_sym_date == target_session:
                fresh_symbols.add(sym)
            else:
                if sym in sp500_symbols:
                    stale_symbols.append(sym)

        fresh_sp500 = set(s for s in fresh_symbols if s in sp500_symbols)
        total_sp500 = len(sp500_symbols)
        fresh_count = len(fresh_sp500)
        coverage_pct = round(fresh_count / total_sp500, 4) if total_sp500 > 0 else 0.0

        # Check 252d history coverage (>=250 trading days in 1 calendar year)
        symbols_with_252d = sum(1 for sym in fresh_sp500 if len(bars_by_symbol.get_group(sym)) >= 250)
        coverage_252d_pct = round(symbols_with_252d / total_sp500, 4) if total_sp500 > 0 else 0.0

        # Determine snapshot status
        is_spy_fresh = (BENCHMARK_TICKER in fresh_symbols)
        if coverage_pct >= MIN_COVERAGE_PCT and is_spy_fresh:
            snapshot_status = "complete"
        elif not is_spy_fresh:
            snapshot_status = "failed"
            logger.error("Dữ liệu Benchmark SPY không đồng phiên hoặc bị thiếu! Trạng thái: failed.")
        else:
            snapshot_status = "degraded"
            logger.warning(f"Độ bao phủ ({coverage_pct*100:.1f}%) dưới ngưỡng {MIN_COVERAGE_PCT*100}%! Trạng thái: degraded.")

        logger.info(f"Phiên mục tiêu (Target Session): {target_session}")
        logger.info(f"Độ bao phủ đồng phiên: {fresh_count}/{total_sp500} ({coverage_pct * 100.0:.1f}%), Đủ 1Y (>=253 nến): {symbols_with_252d}/{total_sp500} ({coverage_252d_pct*100:.1f}%)")
        if stale_symbols:
            logger.info(f"Số mã lệch phiên (stale): {len(stale_symbols)}")

        # 4. Analytics: Indicators & Breadth
        # Filter active bars to fresh symbols to ensure same-session integrity [D-03]
        active_symbols = list(fresh_symbols)
        active_bars = df_bars[df_bars["symbol"].isin(active_symbols)].copy()
        latest_stocks_df = compute_stock_indicators(active_bars)
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

        market_metrics = compute_market_breadth(latest_stocks_df, active_bars)
        sector_metrics = rank_sectors(latest_stocks_df, constituents_df)
        industry_metrics = rank_industry_groups(latest_stocks_df, constituents_df)

        # Market participation breadth history (past 60 sessions) [Step 2]
        market_history = compute_market_breadth_history(df_bars, constituents_df=constituents_df, max_sessions=60, as_of=target_session)

        # Sector internal health (turnover share, top 5 concentration, median returns, divergence) [Step 2]
        sector_health = compute_sector_health(latest_stocks_df, df_bars, constituents_df, as_of=target_session)

        # Sector relative strength rotation vs SPY (4 quadrants & historical trails) [Step 3]
        sector_rotation = compute_sector_rotation(df_bars, as_of=target_session, trail_length=10)

        if industry_metrics:
            top_leading = [f"{ind['industry']} (COMP #{ind['comp_score']})" for ind in industry_metrics[:3]]
            logger.info(f"Đã xếp hạng {len(industry_metrics)} nhóm ngành. Top dẫn đầu: {', '.join(top_leading)}")

        # Session date for point-in-time FA evaluation [D-07]
        session_dt = None
        try:
            session_dt = datetime.strptime(target_session, "%Y-%m-%d").date()
        except Exception:
            pass

        # 4b. Base Building Detection ("Đang xây nền") across all fresh symbols
        base_records = []
        base_building_symbols = []
        spy_1m = None
        try:
            spy_row = latest_stocks_df[latest_stocks_df["symbol"] == BENCHMARK_TICKER]
            if not spy_row.empty and "perf_20d" in spy_row.columns and pd.notna(spy_row["perf_20d"].iloc[0]):
                spy_1m = float(spy_row["perf_20d"].iloc[0])

            rs_ratings_map = {}
            if not latest_stocks_df.empty and "rs_rating" in latest_stocks_df.columns:
                rs_ratings_map = {
                    str(row["symbol"]): int(row["rs_rating"])
                    for _, row in latest_stocks_df.iterrows()
                    if pd.notna(row.get("rs_rating"))
                }

            base_records, base_building_symbols = process_base_detection_for_session(
                repo=repo,
                df_bars=df_bars,
                active_bars=active_bars,
                fresh_sp500=fresh_sp500,
                sp500_symbols=sp500_symbols,
                target_session=target_session,
                spy_1m=spy_1m,
                rs_ratings_map=rs_ratings_map
            )
            logger.info(f"Phát hiện {len(base_records)} bản ghi nền giá ({len(base_building_symbols)} mã đang xây nền).")
        except Exception as base_err:
            logger.warning(f"Lỗi khi quét nền giá (base building): {base_err}")

        # 5. Preliminary screening to find priority candidates for FA enrichment
        prelim_candidates = screen_candidates(latest_stocks_df, sector_metrics, None, industry_metrics, ref_date=session_dt, require_benchmark=True)
        # Bổ sung FA cho cả mã ứng viên và mã đang xây nền [D-01]
        candidate_symbols = list(dict.fromkeys([c["symbol"] for c in prelim_candidates] + base_building_symbols))

        # 6. Fetch fundamentals & earnings calendar for candidate symbols
        if candidate_symbols:
            logger.info(f"Cập nhật FA và lịch earnings cho {len(candidate_symbols)} mã ứng viên & xây nền...")
            fa_records = yf_provider.fetch_fundamentals(candidate_symbols)
            repo.save_fundamentals(fa_records)

        # Reload fundamentals and re-run final candidate screening
        fundamentals_df = repo.get_fundamentals(candidate_symbols) if candidate_symbols else pd.DataFrame()
        final_candidates = screen_candidates(latest_stocks_df, sector_metrics, fundamentals_df, industry_metrics, ref_date=session_dt, require_benchmark=True)

        # 7. Save Snapshot
        snapshot_id = repo.save_snapshot(
            as_of=target_session,
            rule_version=RULE_VERSION,
            total_universe=total_sp500,
            valid_universe=min(fresh_count, total_sp500),
            coverage_pct=coverage_pct,
            missing_symbols=failed_symbols + stale_symbols,
            market_metrics=market_metrics,
            sector_metrics=sector_metrics,
            candidates=final_candidates,
            industry_metrics=industry_metrics,
            coverage_252d=coverage_252d_pct,
            status=snapshot_status,
            market_history=market_history,
            sector_rotation=sector_rotation,
            sector_health=sector_health,
            methodology_version="v2.1"
        )

        # 7b. Save Base Snapshots
        if base_records:
            try:
                saved_base_count = repo.save_base_snapshots(base_records, snapshot_id=snapshot_id)
                logger.info(f"Đã lưu {saved_base_count} bản ghi nền giá cho snapshot #{snapshot_id}.")
            except Exception as base_save_err:
                logger.warning(f"Lỗi khi lưu base_snapshots: {base_save_err}")

        # 8. Generate and save Signal Events (Today Dashboard alerts)
        try:
            prev_snapshot = repo.get_previous_session_snapshot(target_session)
            prev_candidates = repo.get_candidates_by_snapshot(prev_snapshot["id"]) if prev_snapshot else []
            prev_bases_list = repo.get_base_snapshots(snapshot_id=prev_snapshot["id"]) if prev_snapshot else []
            current_snapshot_dict = repo.get_snapshot_by_id(snapshot_id) or {}

            # Correlate against the last known base snapshot so state transitions are not lost
            prev_bases_map = {b["base_id"]: b for b in prev_bases_list if b.get("base_id")}
            for b in base_records:
                bid = b.get("base_id")
                sym = b.get("symbol")
                if bid and bid not in prev_bases_map and sym:
                    last_b = repo.get_last_base_by_symbol(sym, before_date=target_session)
                    if last_b and last_b.get("base_id") == bid:
                        prev_bases_map[bid] = last_b
            prev_bases_list = list(prev_bases_map.values())

            from analytics.signal_events import generate_signal_events
            new_events = generate_signal_events(
                current_snapshot=current_snapshot_dict,
                current_candidates=final_candidates,
                prev_snapshot=prev_snapshot,
                prev_candidates=prev_candidates,
                missing_symbols=failed_symbols + stale_symbols,
                current_bases=base_records,
                prev_bases=prev_bases_list
            )
            saved_events_count = repo.save_signal_events(new_events)
            logger.info(f"Đã ghi nhận {saved_events_count} sự kiện biến động cho phiên {target_session}.")
        except Exception as ev_err:
            logger.warning(f"Lỗi khi phát sinh sự kiện tín hiệu: {ev_err}")

        # 9. Record/Update continuous Signal Streaks
        try:
            from analytics.signal_outcomes import process_signal_streaks
            active_signals = repo.get_signal_records(status="active")
            signals_to_upsert = process_signal_streaks(
                as_of=target_session,
                rule_version=RULE_VERSION,
                candidates=final_candidates,
                active_signals=active_signals
            )
            saved_signals_count = repo.upsert_signal_records(signals_to_upsert)
            logger.info(f"Đã theo dõi và cập nhật {saved_signals_count} chuỗi tín hiệu (signal streaks).")
        except Exception as sig_err:
            logger.warning(f"Lỗi khi cập nhật chuỗi tín hiệu: {sig_err}")

        # 10. Update Signal Forward Outcomes
        try:
            from jobs.update_signal_outcomes import run_update_signal_outcomes
            outcome_res = run_update_signal_outcomes(db_path)
            logger.info(f"Đánh giá hiệu quả tín hiệu hoàn tất: {outcome_res.get('message')}")
        except Exception as out_err:
            logger.warning(f"Chưa thể cập nhật forward outcomes: {out_err}")

        duration = (datetime.now() - start_time).total_seconds()
        msg = f"Cập nhật thành công snapshot #{snapshot_id} (As of: {target_session}) trong {duration:.1f}s. Độ bao phủ: {coverage_pct*100:.1f}%. Trạng thái: {snapshot_status}. Tổng ứng viên: {len(final_candidates)}."
        logger.info(msg)

        return {
            "success": True,
            "snapshot_id": snapshot_id,
            "as_of": target_session,
            "coverage_pct": coverage_pct,
            "coverage_252d": coverage_252d_pct,
            "status": snapshot_status,
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
