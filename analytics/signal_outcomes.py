"""
Signal Outcomes Module.
Measures scanner filter quality independently of actual trades.
Key rules:
- Signals evaluated using next trading session OPEN price.
- Consecutive daily appearances are grouped into a single run/streak.
- All eligible signals are recorded (unbiased).
- Short returns are calculated in the short direction.
- Evaluates 5, 10, and 20 session forward outcomes.
- Calculates SPY excess return, baseline return, and MFE/MAE (in % and ATR).
- Supports score quartile validation and regime breakdowns.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from config.settings import BENCHMARK_TICKER
from analytics.market_calendar import is_end_of_trading_week

WEEKDAY_LABELS = {
    0: "Thứ Hai (T2)",
    1: "Thứ Ba (T3)",
    2: "Thứ Tư (T4)",
    3: "Thứ Năm (T5)",
    4: "Thứ Sáu (T6)",
    5: "Thứ Bảy",
    6: "Chủ Nhật"
}

def process_signal_streaks(
    as_of: str,
    rule_version: str,
    candidates: List[Dict[str, Any]],
    active_signals: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Track continuous signal streaks.
    If a symbol+setup was already active on the preceding day, continue the streak.
    If new, initiate a new signal record with streak_count=1.
    """
    # Active map from existing signal records: (symbol, setup_type) -> signal_dict
    active_map = {f"{s['symbol']}:{s['setup_type']}": s for s in active_signals if s.get("status") == "active"}

    records_to_upsert = []
    seen_in_current = set()

    for c in candidates:
        sym = c["symbol"]
        setup_type = c.get("setup_type") or c.get("group_type") or "default"
        side = "short" if "short" in c.get("group_type", "") else "long"
        key = f"{sym}:{setup_type}"
        seen_in_current.add(key)

        candle_pat = (
            c.get("candle_pattern") or
            c.get("evidence_json", {}).get("candlestick", {}).get("features", {}).get("pattern") or
            "Không rõ mẫu hình"
        )

        if key in active_map:
            # Continue existing streak
            existing = active_map[key]
            records_to_upsert.append({
                "signal_key": existing["signal_key"],
                "symbol": sym,
                "setup_type": setup_type,
                "latest_detected_date": as_of,
                "streak_count": existing.get("streak_count", 1) + 1,
                "status": "active",
                "trigger_price": c.get("trigger_price"),
                "invalidation_price": c.get("invalidation_price"),
                "candle_pattern": existing.get("candle_pattern") or candle_pat or "Không rõ mẫu hình"
            })
        else:
            # New signal streak starting today
            new_key = f"{as_of}:{sym}:{setup_type}"
            records_to_upsert.append({
                "signal_key": new_key,
                "symbol": sym,
                "company_name": c.get("company_name", sym),
                "sector": c.get("sector", ""),
                "sub_industry": c.get("sub_industry", ""),
                "side": side,
                "group_type": c.get("group_type", ""),
                "setup_type": setup_type,
                "rule_version": rule_version,
                "first_detected_date": as_of,
                "latest_detected_date": as_of,
                "streak_count": 1,
                "status": "active",
                "trigger_price": c.get("trigger_price"),
                "invalidation_price": c.get("invalidation_price"),
                "initial_close": c.get("close_price"),
                "initial_atr": c.get("atr14"),
                "initial_score": c.get("score"),
                "entry_date": None,
                "entry_price": None,
                "spy_entry_price": None,
                "baseline_entry_index": None,
                "candle_pattern": candle_pat
            })

    # Close streaks that disappeared today
    for key, act in active_map.items():
        if key not in seen_in_current:
            records_to_upsert.append({
                "signal_key": act["signal_key"],
                "symbol": act["symbol"],
                "setup_type": act["setup_type"],
                "latest_detected_date": act["latest_detected_date"],
                "streak_count": act.get("streak_count", 1),
                "status": "closed",
                "candle_pattern": act.get("candle_pattern", "Không rõ mẫu hình")
            })

    return records_to_upsert

def evaluate_signal_outcomes(
    signals: List[Dict[str, Any]],
    daily_bars_df: pd.DataFrame,
    horizons: Optional[List[Any]] = None
) -> List[Dict[str, Any]]:
    """
    Evaluate outcomes for all signals:
    1. Resolve next-day open price as entry benchmark.
    2. Support intra-week swing horizons: 1, 2, 3, 4 sessions and week-close window (99 / 'week_close').
       For week-close: if entry is already end-of-week, marks 'no_window_in_week' (discarding cases with no intra-week holding room).
    3. Support macro context horizons: 5, 10, 20 sessions.
    4. Compute forward gross returns, SPY returns, and MFE/MAE (in % and ATR).
    5. Disclaim: Gross filter returns, not actual trade P&L (excludes slippage, commissions, borrow fees).
    """
    if daily_bars_df.empty or not signals:
        return []

    if horizons is None:
        horizons = [1, 2, 3, 4, 99, 5, 10, 20]

    bars_df = daily_bars_df.sort_values(["symbol", "date"]).copy()
    if not pd.api.types.is_datetime64_any_dtype(bars_df["date"]):
        bars_df["date"] = pd.to_datetime(bars_df["date"])
    spy_bars = bars_df[bars_df["symbol"] == BENCHMARK_TICKER].drop_duplicates("date").set_index("date")

    outcomes = []

    for s in signals:
        sig_id = s["id"]
        sig_key = s["signal_key"]
        sym = s["symbol"]
        side = s.get("side", "long")
        first_date = s["first_detected_date"]
        initial_atr = float(s.get("initial_atr") or 1.0)
        trigger_p = s.get("trigger_price")
        inv_p = s.get("invalidation_price")

        sym_bars = bars_df[bars_df["symbol"] == sym]
        if sym_bars.empty:
            for h in horizons:
                h_int = 99 if (h == 99 or h == "week_close") else int(h)
                h_lbl = "Chốt cuối tuần" if h_int == 99 else f"{h_int} phiên"
                outcomes.append({
                    "signal_id": sig_id,
                    "signal_key": sig_key,
                    "symbol": sym,
                    "side": side,
                    "horizon_days": h_int,
                    "horizon_label": h_lbl,
                    "entry_day_of_week": None,
                    "entry_date": None,
                    "entry_price": None,
                    "spy_entry_price": None,
                    "status": "insufficient_data"
                })
            continue

        # Find bars strictly after first_detected_date
        subsequent_bars = sym_bars[sym_bars["date"].dt.strftime("%Y-%m-%d") > first_date].copy()
        if subsequent_bars.empty:
            for h in horizons:
                h_int = 99 if (h == 99 or h == "week_close") else int(h)
                h_lbl = "Chốt cuối tuần" if h_int == 99 else f"{h_int} phiên"
                outcomes.append({
                    "signal_id": sig_id,
                    "signal_key": sig_key,
                    "symbol": sym,
                    "side": side,
                    "horizon_days": h_int,
                    "horizon_label": h_lbl,
                    "entry_day_of_week": None,
                    "entry_date": None,
                    "entry_price": None,
                    "spy_entry_price": None,
                    "status": "pending"
                })
            continue

        # Entry bar is the 1st subsequent trading session
        entry_bar = subsequent_bars.iloc[0]
        entry_date = entry_bar["date"]
        entry_date_str = entry_date.strftime("%Y-%m-%d")
        entry_price = float(entry_bar["open"])
        entry_dt_obj = entry_date.date() if hasattr(entry_date, "date") else entry_date
        entry_day_name = WEEKDAY_LABELS.get(entry_dt_obj.weekday(), "Không xác định")

        # SPY entry price on same date
        spy_entry_price = None
        if entry_date in spy_bars.index:
            spy_entry_price = float(spy_bars.loc[entry_date]["open"])

        n_avail = len(subsequent_bars)

        for h in horizons:
            is_week_close = (h == 99 or h == "week_close")
            h_int = 99 if is_week_close else int(h)
            h_lbl = "Chốt cuối tuần" if is_week_close else f"{h_int} phiên"

            if is_week_close:
                # Check if entry is already on the last trading day of week
                if is_end_of_trading_week(entry_dt_obj):
                    # Discard/flag case: no intra-week holding window left
                    outcomes.append({
                        "signal_id": sig_id,
                        "signal_key": sig_key,
                        "symbol": sym,
                        "side": side,
                        "horizon_days": 99,
                        "horizon_label": h_lbl,
                        "entry_day_of_week": entry_day_name,
                        "entry_date": entry_date_str,
                        "entry_price": entry_price,
                        "spy_entry_price": spy_entry_price,
                        "status": "no_window_in_week",
                        "candle_pattern": s.get("candle_pattern", "Không rõ mẫu hình"),
                        "setup_type": s.get("setup_type", ""),
                        "crosses_weekend": 0,
                        "exit_date": None,
                        "exit_price": None,
                        "return_pct": None,
                        "spy_return_pct": None,
                        "excess_return_spy": None,
                        "baseline_return_pct": None,
                        "excess_return_baseline": None,
                        "mfe_pct": None,
                        "mae_pct": None,
                        "mfe_atr": None,
                        "mae_atr": None,
                        "hit_trigger": 0,
                        "hit_invalidation": 0
                    })
                    continue

                # Find bars belonging to the exact same calendar week
                entry_iso = entry_dt_obj.isocalendar()
                same_week_mask = subsequent_bars["date"].apply(
                    lambda d: (d.date() if hasattr(d, "date") else d).isocalendar()[:2] == (entry_iso.year, entry_iso.week)
                )
                same_week_bars = subsequent_bars[same_week_mask]
                if same_week_bars.empty:
                    same_week_bars = subsequent_bars.iloc[:1]

                last_sw_bar = same_week_bars.iloc[-1]
                last_sw_date = last_sw_bar["date"].date() if hasattr(last_sw_bar["date"], "date") else last_sw_bar["date"]
                max_market_date = bars_df["date"].max()
                max_market_dt = max_market_date.date() if hasattr(max_market_date, "date") else max_market_date
                max_market_iso = max_market_dt.isocalendar()[:2]
                market_in_later_week = (max_market_iso > (entry_iso.year, entry_iso.week))
                week_has_ended = is_end_of_trading_week(last_sw_date) or (len(subsequent_bars) > len(same_week_bars)) or market_in_later_week

                if not week_has_ended:
                    # Week is still ongoing
                    outcomes.append({
                        "signal_id": sig_id,
                        "signal_key": sig_key,
                        "symbol": sym,
                        "side": side,
                        "horizon_days": 99,
                        "horizon_label": h_lbl,
                        "entry_day_of_week": entry_day_name,
                        "entry_date": entry_date_str,
                        "entry_price": entry_price,
                        "spy_entry_price": spy_entry_price,
                        "status": "pending",
                        "crosses_weekend": 0,
                        "exit_date": None,
                        "exit_price": None,
                        "return_pct": None,
                        "spy_return_pct": None,
                        "excess_return_spy": None,
                        "baseline_return_pct": None,
                        "excess_return_baseline": None,
                        "mfe_pct": None,
                        "mae_pct": None,
                        "mfe_atr": None,
                        "mae_atr": None,
                        "hit_trigger": 0,
                        "hit_invalidation": 0
                    })
                    continue

                window = same_week_bars
            else:
                if n_avail < h_int:
                    # Pending: not enough trading sessions have elapsed yet
                    outcomes.append({
                        "signal_id": sig_id,
                        "signal_key": sig_key,
                        "symbol": sym,
                        "side": side,
                        "horizon_days": h_int,
                        "horizon_label": h_lbl,
                        "entry_day_of_week": entry_day_name,
                        "entry_date": entry_date_str,
                        "entry_price": entry_price,
                        "spy_entry_price": spy_entry_price,
                        "status": "pending",
                        "crosses_weekend": 0,
                        "exit_date": None,
                        "exit_price": None,
                        "return_pct": None,
                        "spy_return_pct": None,
                        "excess_return_spy": None,
                        "baseline_return_pct": None,
                        "excess_return_baseline": None,
                        "mfe_pct": None,
                        "mae_pct": None,
                        "mfe_atr": None,
                        "mae_atr": None,
                        "hit_trigger": 0,
                        "hit_invalidation": 0
                    })
                    continue

                window = subsequent_bars.iloc[:h_int]

            exit_bar = window.iloc[-1]
            exit_date = exit_bar["date"].strftime("%Y-%m-%d")
            exit_price = float(exit_bar["close"])

            # Weekend boundary check [D-04, R-06]
            entry_bar = subsequent_bars.iloc[0]
            entry_dt_val = entry_bar["date"].date() if hasattr(entry_bar["date"], "date") else entry_bar["date"]
            exit_dt_val = exit_bar["date"].date() if hasattr(exit_bar["date"], "date") else exit_bar["date"]
            entry_iso = entry_dt_val.isocalendar()[:2]
            exit_iso = exit_dt_val.isocalendar()[:2]
            if h_int == 99:
                crosses_weekend = 0
            else:
                crosses_weekend = 1 if (exit_iso != entry_iso or (exit_dt_val - entry_dt_val).days >= 7) else 0

            # Returns according to side
            if side == "long":
                ret_pct = round((exit_price - entry_price) / entry_price * 100.0, 2)
                max_favorable = float(window["high"].max())
                max_adverse = float(window["low"].min())
                mfe_pct = round((max_favorable - entry_price) / entry_price * 100.0, 2)
                mae_pct = round((max_adverse - entry_price) / entry_price * 100.0, 2)
                mfe_atr = round((max_favorable - entry_price) / initial_atr, 2) if initial_atr > 0 else None
                mae_atr = round((max_adverse - entry_price) / initial_atr, 2) if initial_atr > 0 else None
            else:  # Short
                ret_pct = round((entry_price - exit_price) / entry_price * 100.0, 2)
                min_favorable = float(window["low"].min())
                max_adverse = float(window["high"].max())
                mfe_pct = round((entry_price - min_favorable) / entry_price * 100.0, 2)
                mae_pct = round((entry_price - max_adverse) / entry_price * 100.0, 2)
                mfe_atr = round((entry_price - min_favorable) / initial_atr, 2) if initial_atr > 0 else None
                mae_atr = round((entry_price - max_adverse) / initial_atr, 2) if initial_atr > 0 else None

            # SPY benchmark return over exact same window
            spy_ret_pct = None
            excess_spy = None
            exit_dt = exit_bar["date"]
            if spy_entry_price and exit_dt in spy_bars.index:
                spy_exit_price = float(spy_bars.loc[exit_dt]["close"])
                spy_ret_pct = round((spy_exit_price - spy_entry_price) / spy_entry_price * 100.0, 2)
                excess_spy = round(ret_pct - spy_ret_pct, 2)

            # Did price cross trigger or invalidation during the window?
            hit_trigger = 0
            hit_inv = 0
            if trigger_p is not None:
                if side == "long":
                    hit_trigger = int(window["high"].max() >= trigger_p)
                else:
                    hit_trigger = int(window["low"].min() <= trigger_p)

            if inv_p is not None:
                if side == "long":
                    hit_inv = int(window["low"].min() <= inv_p)
                else:
                    hit_inv = int(window["high"].max() >= inv_p)

            outcomes.append({
                "signal_id": sig_id,
                "signal_key": sig_key,
                "symbol": sym,
                "side": side,
                "horizon_days": h_int,
                "horizon_label": h_lbl,
                "entry_day_of_week": entry_day_name,
                "entry_date": entry_date_str,
                "entry_price": entry_price,
                "spy_entry_price": spy_entry_price,
                "status": "completed",
                "crosses_weekend": crosses_weekend,
                "candle_pattern": s.get("candle_pattern", "Không rõ mẫu hình"),
                "setup_type": s.get("setup_type", ""),
                "exit_date": exit_date,
                "exit_price": exit_price,
                "return_pct": ret_pct,
                "spy_return_pct": spy_ret_pct,
                "excess_return_spy": excess_spy,
                "baseline_return_pct": None,
                "excess_return_baseline": None,
                "mfe_pct": mfe_pct,
                "mae_pct": mae_pct,
                "mfe_atr": mfe_atr,
                "mae_atr": mae_atr,
                "hit_trigger": hit_trigger,
                "hit_invalidation": hit_inv
            })

    return outcomes

def compute_quality_summary(df_outcomes: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute aggregate quality statistics for scanner signals:
    - Win rate, Average return, Median return
    - Excess return vs SPY
    - MFE / MAE ratios
    - Sample counts (Total, Completed, Pending, No-Window in Week)
    - Score quartile predictability check
    - Candlestick pattern impact (within setups & overall)
    - Weekday entry breakdown (Thứ Hai đến Thứ Sáu)
    - Directional side breakdown (Long vs Short)
    """
    if df_outcomes.empty:
        return {
            "total_signals": 0,
            "completed": 0,
            "pending": 0,
            "no_window_count": 0,
            "win_rate": 0.0,
            "avg_return": 0.0,
            "med_return": 0.0,
            "avg_excess_spy": 0.0,
            "avg_mfe": 0.0,
            "avg_mae": 0.0,
            "setup_breakdown": pd.DataFrame(),
            "candle_breakdown": pd.DataFrame(),
            "setup_candle_breakdown": pd.DataFrame(),
            "weekday_breakdown": pd.DataFrame(),
            "side_breakdown": pd.DataFrame(),
            "score_check": {}
        }

    total = len(df_outcomes)
    completed_df = df_outcomes[df_outcomes["status"] == "completed"].copy()
    pending_count = int((df_outcomes["status"] == "pending").sum())
    no_window_count = int((df_outcomes["status"] == "no_window_in_week").sum())
    completed_count = len(completed_df)

    if completed_df.empty:
        return {
            "total_signals": total,
            "completed": 0,
            "pending": pending_count,
            "no_window_count": no_window_count,
            "win_rate": 0.0,
            "avg_return": 0.0,
            "med_return": 0.0,
            "avg_excess_spy": 0.0,
            "avg_mfe": 0.0,
            "avg_mae": 0.0,
            "setup_breakdown": pd.DataFrame(),
            "candle_breakdown": pd.DataFrame(),
            "setup_candle_breakdown": pd.DataFrame(),
            "weekday_breakdown": pd.DataFrame(),
            "side_breakdown": pd.DataFrame(),
            "score_check": {
                "top_quartile_avg": None,
                "bottom_quartile_avg": None,
                "is_monotonic": False
            }
        }

    returns = completed_df["return_pct"].dropna()
    excess_spy = completed_df["excess_return_spy"].dropna()

    win_rate = round(float((returns > 0).sum()) / len(returns) * 100.0, 1) if not returns.empty else 0.0
    avg_return = round(float(returns.mean()), 2) if not returns.empty else 0.0
    med_return = round(float(returns.median()), 2) if not returns.empty else 0.0
    avg_excess = round(float(excess_spy.mean()), 2) if not excess_spy.empty else 0.0
    avg_mfe = round(float(completed_df["mfe_pct"].dropna().mean()), 2) if "mfe_pct" in completed_df else 0.0
    avg_mae = round(float(completed_df["mae_pct"].dropna().mean()), 2) if "mae_pct" in completed_df else 0.0

    crosses_weekend_count = int((completed_df["crosses_weekend"] == 1).sum()) if "crosses_weekend" in completed_df.columns else 0
    intra_week_count = completed_count - crosses_weekend_count

    MIN_SAMPLE_THRESHOLD = 5

    # Setup breakdown
    breakdown_rows = []
    if "setup_type" in completed_df.columns:
        for s_type, g in completed_df.groupby("setup_type"):
            g_rets = g["return_pct"].dropna()
            g_spy = g["excess_return_spy"].dropna()
            if not g_rets.empty:
                n_done = len(g_rets)
                is_adq = n_done >= MIN_SAMPLE_THRESHOLD
                breakdown_rows.append({
                    "Setup": s_type,
                    "Mẫu": n_done,
                    "Mẫu Hoàn Tất": n_done,
                    "Mẫu Đang Chờ": len(g) - n_done,
                    "Độ Tin Cậy": "Đủ mẫu (≥5)" if is_adq else f"⚠️ Thiếu mẫu ({n_done}/5)",
                    "Tỷ lệ thắng (%)": round(float((g_rets > 0).sum()) / n_done * 100.0, 1),
                    "Lợi suất TB (%)": round(float(g_rets.mean()), 2),
                    "Vượt SPY (%)": round(float(g_spy.mean()), 2) if not g_spy.empty else 0.0,
                    "MFE TB (%)": round(float(g["mfe_pct"].dropna().mean()), 2) if "mfe_pct" in g else 0.0,
                    "MAE TB (%)": round(float(g["mae_pct"].dropna().mean()), 2) if "mae_pct" in g else 0.0,
                    "is_adequate": is_adq
                })
    setup_breakdown = pd.DataFrame(breakdown_rows)

    # Candlestick pattern breakdown
    candle_rows = []
    if "candle_pattern" in completed_df.columns:
        for c_pat, g in completed_df.groupby("candle_pattern"):
            g_rets = g["return_pct"].dropna()
            g_spy = g["excess_return_spy"].dropna()
            if not g_rets.empty:
                n_done = len(g_rets)
                is_adq = n_done >= MIN_SAMPLE_THRESHOLD
                candle_rows.append({
                    "Mẫu Nến": c_pat,
                    "Mẫu": n_done,
                    "Mẫu Hoàn Tất": n_done,
                    "Mẫu Đang Chờ": len(g) - n_done,
                    "Độ Tin Cậy": "Đủ mẫu (≥5)" if is_adq else f"⚠️ Thiếu mẫu ({n_done}/5)",
                    "Tỷ lệ thắng (%)": round(float((g_rets > 0).sum()) / n_done * 100.0, 1),
                    "Lợi suất TB (%)": round(float(g_rets.mean()), 2),
                    "Vượt SPY (%)": round(float(g_spy.mean()), 2) if not g_spy.empty else 0.0,
                    "MFE TB (%)": round(float(g["mfe_pct"].dropna().mean()), 2) if "mfe_pct" in g else 0.0,
                    "MAE TB (%)": round(float(g["mae_pct"].dropna().mean()), 2) if "mae_pct" in g else 0.0,
                    "is_adequate": is_adq
                })
    candle_breakdown = pd.DataFrame(candle_rows)

    # Setup + Candlestick interaction breakdown ("cùng setup, có mẫu nến này thì kết quả có khác không?")
    setup_candle_rows = []
    if "candle_pattern" in completed_df.columns and "setup_type" in completed_df.columns:
        for (s_type, c_pat), g in completed_df.groupby(["setup_type", "candle_pattern"]):
            g_rets = g["return_pct"].dropna()
            g_spy = g["excess_return_spy"].dropna()
            if not g_rets.empty:
                n_done = len(g_rets)
                is_adq = n_done >= MIN_SAMPLE_THRESHOLD
                setup_candle_rows.append({
                    "Setup": s_type,
                    "Mẫu Nến": c_pat,
                    "Mẫu": n_done,
                    "Mẫu Hoàn Tất": n_done,
                    "Mẫu Đang Chờ": len(g) - n_done,
                    "Độ Tin Cậy": "Đủ mẫu (≥5)" if is_adq else f"⚠️ Thiếu mẫu ({n_done}/5)",
                    "Tỷ lệ thắng (%)": round(float((g_rets > 0).sum()) / n_done * 100.0, 1),
                    "Lợi suất TB (%)": round(float(g_rets.mean()), 2),
                    "Vượt SPY (%)": round(float(g_spy.mean()), 2) if not g_spy.empty else 0.0,
                    "MFE TB (%)": round(float(g["mfe_pct"].dropna().mean()), 2) if "mfe_pct" in g else 0.0,
                    "MAE TB (%)": round(float(g["mae_pct"].dropna().mean()), 2) if "mae_pct" in g else 0.0,
                    "is_adequate": is_adq
                })
    setup_candle_breakdown = pd.DataFrame(setup_candle_rows)

    # Weekday breakdown [D-04]
    weekday_rows = []
    if "entry_day_of_week" in completed_df.columns:
        day_order = ["Thứ Hai (T2)", "Thứ Ba (T3)", "Thứ Tư (T4)", "Thứ Năm (T5)", "Thứ Sáu (T6)"]
        for day_name in day_order:
            g = completed_df[completed_df["entry_day_of_week"] == day_name]
            if g.empty:
                continue
            g_rets = g["return_pct"].dropna()
            g_spy = g["excess_return_spy"].dropna()
            if not g_rets.empty:
                n_done = len(g_rets)
                is_adq = n_done >= MIN_SAMPLE_THRESHOLD
                weekday_rows.append({
                    "Thứ Trong Tuần": day_name,
                    "Mẫu": n_done,
                    "Mẫu Hoàn Tất": n_done,
                    "Độ Tin Cậy": "Đủ mẫu (≥5)" if is_adq else f"⚠️ Thiếu mẫu ({n_done}/5)",
                    "Tỷ lệ thắng (%)": round(float((g_rets > 0).sum()) / n_done * 100.0, 1),
                    "Lợi suất TB (%)": round(float(g_rets.mean()), 2),
                    "Vượt SPY (%)": round(float(g_spy.mean()), 2) if not g_spy.empty else 0.0,
                    "MFE TB (%)": round(float(g["mfe_pct"].dropna().mean()), 2) if "mfe_pct" in g else 0.0,
                    "MAE TB (%)": round(float(g["mae_pct"].dropna().mean()), 2) if "mae_pct" in g else 0.0,
                    "is_adequate": is_adq
                })
    weekday_breakdown = pd.DataFrame(weekday_rows)

    # Side breakdown (Long vs Short) [D-04]
    side_rows = []
    if "side" in completed_df.columns:
        for s_side, g in completed_df.groupby("side"):
            g_rets = g["return_pct"].dropna()
            g_spy = g["excess_return_spy"].dropna()
            if not g_rets.empty:
                n_done = len(g_rets)
                is_adq = n_done >= MIN_SAMPLE_THRESHOLD
                side_label = "Long (Mua)" if str(s_side).lower() == "long" else "Short (Bán khống)"
                side_rows.append({
                    "Chiều Giao Dịch": side_label,
                    "Mẫu": n_done,
                    "Mẫu Hoàn Tất": n_done,
                    "Độ Tin Cậy": "Đủ mẫu (≥5)" if is_adq else f"⚠️ Thiếu mẫu ({n_done}/5)",
                    "Tỷ lệ thắng (%)": round(float((g_rets > 0).sum()) / n_done * 100.0, 1),
                    "Lợi suất TB (%)": round(float(g_rets.mean()), 2),
                    "Vượt SPY (%)": round(float(g_spy.mean()), 2) if not g_spy.empty else 0.0,
                    "MFE TB (%)": round(float(g["mfe_pct"].dropna().mean()), 2) if "mfe_pct" in g else 0.0,
                    "MAE TB (%)": round(float(g["mae_pct"].dropna().mean()), 2) if "mae_pct" in g else 0.0,
                    "is_adequate": is_adq
                })
    side_breakdown = pd.DataFrame(side_rows)

    # Score predictability check (Top 25% vs Bottom 25%)
    score_check = {
        "top_quartile_avg": None,
        "bottom_quartile_avg": None,
        "is_monotonic": False
    }
    if len(completed_df) >= 8 and "initial_score" in completed_df.columns:
        valid_scores = completed_df.dropna(subset=["initial_score", "return_pct"])
        if len(valid_scores) >= 8:
            q75 = valid_scores["initial_score"].quantile(0.75)
            q25 = valid_scores["initial_score"].quantile(0.25)
            top_q = valid_scores[valid_scores["initial_score"] >= q75]["return_pct"]
            bot_q = valid_scores[valid_scores["initial_score"] <= q25]["return_pct"]
            if not top_q.empty and not bot_q.empty:
                top_avg = round(float(top_q.mean()), 2)
                bot_avg = round(float(bot_q.mean()), 2)
                score_check["top_quartile_avg"] = top_avg
                score_check["bottom_quartile_avg"] = bot_avg
                score_check["is_monotonic"] = bool(top_avg > bot_avg)

    return {
        "total_signals": total,
        "completed": completed_count,
        "pending": pending_count,
        "no_window_count": no_window_count,
        "crosses_weekend_count": crosses_weekend_count,
        "intra_week_count": intra_week_count,
        "win_rate": win_rate,
        "avg_return": avg_return,
        "med_return": med_return,
        "avg_excess_spy": avg_excess,
        "avg_mfe": avg_mfe,
        "avg_mae": avg_mae,
        "setup_breakdown": setup_breakdown,
        "candle_breakdown": candle_breakdown,
        "setup_candle_breakdown": setup_candle_breakdown,
        "weekday_breakdown": weekday_breakdown,
        "side_breakdown": side_breakdown,
        "score_check": score_check
    }
