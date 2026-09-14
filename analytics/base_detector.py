"""
Base Building Detector Module (Đang Xây Nền).
Identifies tight consolidation bases and accumulation evidence prior to breakout.
Maintains state machine across trading sessions with frozen upper/lower bounds.
"""
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
import json
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from config.settings import (
    BASE_RULE_VERSION,
    BASE_WINDOW_BARS,
    BASE_MIN_BARS,
    BASE_MAX_WIDTH_PCT,
    BASE_MAX_EFFICIENCY_RATIO,
    BASE_MAX_CENTER_SHIFT,
    BASE_MAX_TR_CONTRACTION,
    BASE_MAX_VOL_CONTRACTION,
    BASE_BREAKOUT_VOL_RATIO,
    BASE_VOLUME_BALANCE_THRESHOLD,
    MIN_PRICE,
    MIN_AVG_VOLUME,
)


@dataclass
class BaseConfig:
    rule_version: str = BASE_RULE_VERSION
    window_bars: int = BASE_WINDOW_BARS
    min_bars: int = BASE_MIN_BARS
    max_width_pct: float = BASE_MAX_WIDTH_PCT
    max_efficiency_ratio: float = BASE_MAX_EFFICIENCY_RATIO
    max_center_shift: float = BASE_MAX_CENTER_SHIFT
    max_tr_contraction: float = BASE_MAX_TR_CONTRACTION
    max_vol_contraction: float = BASE_MAX_VOL_CONTRACTION
    breakout_vol_ratio: float = BASE_BREAKOUT_VOL_RATIO
    vol_balance_threshold: float = BASE_VOLUME_BALANCE_THRESHOLD
    min_price: float = MIN_PRICE
    min_avg_volume: float = MIN_AVG_VOLUME


@dataclass
class BaseResult:
    symbol: str
    as_of: str
    rule_version: str
    data_status: str  # "valid", "insufficient_data", "invalid_data", "stale_data"
    base_id: Optional[str] = None
    detected_at: Optional[str] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    state: str = "none"  # "forming", "tight", "breakout_unconfirmed", "breakout_confirmed", "fresh_breakout", "climbing", "played_out", "broken_down", "weakening", "lost_structure", "none"
    lifecycle_phase: str = "forming"  # "forming", "fresh_breakout", "climbing", "played_out", "failed_before_breakout", "none"
    is_active: bool = False
    upper: Optional[float] = None
    lower: Optional[float] = None
    close_price: Optional[float] = None
    perf_1d: Optional[float] = None  # Daily percentage return on session as_of
    width_pct: Optional[float] = None
    efficiency_ratio: Optional[float] = None
    center_shift: Optional[float] = None
    tr_contraction: Optional[float] = None
    vol_contraction: Optional[float] = None
    position: Optional[float] = None  # (close_T - lower) / (upper - lower)
    distance_to_upper_pct: Optional[float] = None
    now_vs_pivot_pct: Optional[float] = None  # 100 * (close / upper - 1)
    signed_volume_balance: Optional[float] = None  # Up/down volume, net (-1 to +1)
    volume_balance_label: str = "Cân bằng"  # "Volume thuận", "Volume cân bằng", "Volume mâu thuẫn"
    trend_context: str = "Chưa đủ dữ liệu"  # "Nền trong xu hướng tăng", "Nền trong xu hướng giảm", "Trung tính", "Chưa đủ dữ liệu"
    rs_vs_spy: Optional[float] = None
    rs_rating: Optional[int] = None  # Percentile rank 1-99
    high_52w: Optional[float] = None  # Highest High over last 252 sessions
    from_52w_high_pct: Optional[float] = None  # 100 * (High252 - Close) / High252
    breakout_date: Optional[str] = None
    breakout_price: Optional[float] = None
    breakout_bar_count: int = 0
    consecutive_below_ma50: int = 0
    ended_at: Optional[str] = None
    end_reason: Optional[str] = None
    formula_version: str = "v2.0"
    ma50: Optional[float] = None
    ma200: Optional[float] = None
    price_vs_ma50_pct: Optional[float] = None
    price_vs_ma200_pct: Optional[float] = None
    pressure_bias: str = "Chưa tính"
    consecutive_weakening: int = 0
    checks: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["checks_json"] = json.dumps(self.checks, ensure_ascii=False)
        d["warnings_json"] = json.dumps(self.warnings, ensure_ascii=False)
        d["notes_json"] = json.dumps(self.notes, ensure_ascii=False)
        return d


def _compute_frozen_pre_breakout_quality(
    df: pd.DataFrame,
    breakout_idx: int,
    window_bars: int,
    frozen_upper: float,
    frozen_lower: float,
    cfg: BaseConfig
) -> Dict[str, Any]:
    """Compute base quality metrics on the 20-bar window ending at T-1 of breakout (decoupled from breakout bar)."""
    bp_slice = df.iloc[breakout_idx - window_bars : breakout_idx]
    bp_win_end = df["date_dt"].iloc[breakout_idx - 1].strftime("%Y-%m-%d")
    bp_win_start = df["date_dt"].iloc[breakout_idx - window_bars].strftime("%Y-%m-%d")
    bp_vols = bp_slice["volume"].to_numpy()
    bp_vf = float(np.mean(bp_vols[:10]))
    bp_vl = float(np.mean(bp_vols[10:]))
    vol_contraction = bp_vl / bp_vf if bp_vf > 0 else 1.0

    bp_closes = bp_slice["close"].to_numpy()
    bp_diffs = np.diff(bp_closes)
    bp_p = float(np.sum(np.abs(bp_diffs)))
    bp_n = abs(float(bp_closes[-1] - bp_closes[0]))
    er = (bp_n / bp_p) if bp_p > 0 else 0.0

    bp_cf = float(np.mean(bp_closes[:10]))
    bp_cl = float(np.mean(bp_closes[10:]))
    center = (abs(bp_cl - bp_cf) / (frozen_upper - frozen_lower)) if (frozen_upper > frozen_lower) else 0.0

    tr_contraction = None
    if breakout_idx >= window_bars + 1:
        tr_slice_prev = df.iloc[breakout_idx - window_bars - 1 : breakout_idx].copy()
        pc = tr_slice_prev["close"].shift(1)
        tr_p = np.maximum(
            tr_slice_prev["high"] - tr_slice_prev["low"],
            np.maximum((tr_slice_prev["high"] - pc).abs(), (tr_slice_prev["low"] - pc).abs())
        ).iloc[1:].to_numpy()
        if float(np.mean(tr_p[:10])) > 0:
            tr_contraction = float(np.mean(tr_p[10:])) / float(np.mean(tr_p[:10]))

    bp_step_vols = bp_vols[1:]
    bp_sum_vols = float(np.sum(bp_step_vols))
    signed_vol = 0.0
    if bp_sum_vols > 0:
        signed_vol = float(np.sum(np.sign(bp_diffs) * bp_step_vols) / bp_sum_vols)
    if signed_vol > cfg.vol_balance_threshold:
        vol_label = "Volume thuận"
    elif signed_vol < -cfg.vol_balance_threshold:
        vol_label = "Volume mâu thuẫn"
    else:
        vol_label = "Cân bằng"

    frozen_w_pct = round(100.0 * (frozen_upper - frozen_lower) / frozen_lower, 2) if frozen_lower > 0 else 0.0
    pass_w = bool(frozen_w_pct <= cfg.max_width_pct)
    pass_e = bool(er <= cfg.max_efficiency_ratio)
    pass_c = bool(center <= cfg.max_center_shift)
    pass_t = bool(tr_contraction is not None and tr_contraction <= cfg.max_tr_contraction)
    pass_v = bool(vol_contraction is not None and vol_contraction <= cfg.max_vol_contraction)
    is_liq = float(bp_closes[-1]) >= cfg.min_price and float(np.mean(bp_vols)) >= cfg.min_avg_volume
    checks = [
        {
            "name": "Thanh khoản",
            "pass": is_liq,
            "value": f"${bp_closes[-1]:.2f} | {float(np.mean(bp_vols)):,.0f}/phiên",
            "threshold": f">=${cfg.min_price}, >={cfg.min_avg_volume:,.0f}"
        },
        {
            "name": "Độ rộng nền",
            "pass": pass_w,
            "value": f"{frozen_w_pct:.1f}%",
            "threshold": f"<={cfg.max_width_pct:.1f}%"
        },
        {
            "name": "Hiệu suất dịch chuyển (ER)",
            "pass": pass_e,
            "value": f"{er:.3f}",
            "threshold": f"<={cfg.max_efficiency_ratio:.2f}"
        },
        {
            "name": "Độ lệch tâm giá (Center Shift)",
            "pass": pass_c,
            "value": f"{center:.3f}",
            "threshold": f"<={cfg.max_center_shift:.2f}"
        },
        {
            "name": "Co hẹp True Range (10 phiên cuối / đầu)",
            "pass": pass_t,
            "value": f"{tr_contraction:.2f}" if tr_contraction is not None else "N/A",
            "threshold": f"<={cfg.max_tr_contraction:.2f}"
        },
        {
            "name": "Volume cạn dần (10 phiên cuối / đầu)",
            "pass": pass_v,
            "value": f"{vol_contraction:.2f}" if vol_contraction is not None else "N/A",
            "threshold": f"<={cfg.max_vol_contraction:.2f}"
        },
    ]

    return {
        "window_start": bp_win_start,
        "window_end": bp_win_end,
        "vol_contraction": vol_contraction,
        "tr_contraction": tr_contraction,
        "efficiency_ratio": er,
        "center_shift": center,
        "signed_volume_balance": signed_vol,
        "volume_balance_label": vol_label,
        "checks": checks
    }


def detect_base(
    bars: pd.DataFrame,
    as_of: Union[date, str, datetime],
    previous_base: Optional[Dict[str, Any]] = None,
    config: Optional[BaseConfig] = None,
    spy_perf_20d: Optional[float] = None,
    rs_rating: Optional[int] = None
) -> BaseResult:
    """
    Evaluate closed daily bars up to session as_of for consolidation base structure.

    Args:
        bars: DataFrame with OHLCV data.
        as_of: Target closed trading session.
        previous_base: Base state dictionary from previous session if exists.
        config: Custom BaseConfig thresholds if provided.
        spy_perf_20d: Benchmark SPY 20d return for RS calculation.
        rs_rating: Relative Strength percentile rating (1-99) in S&P 500 universe.

    Returns:
        BaseResult containing state, frozen boundaries, metrics, and accumulation evidence.
    """
    cfg = config or BaseConfig()

    # If previous_base has already broken out and is in post-breakout lifecycle, delegate to track_post_breakout_base
    if previous_base and (
        previous_base.get("lifecycle_phase") in ("fresh_breakout", "climbing")
        or (previous_base.get("breakout_date") and previous_base.get("state") in ("breakout_confirmed", "fresh_breakout", "climbing"))
    ):
        return track_post_breakout_base(
            previous_base=previous_base,
            bars=bars,
            as_of=as_of,
            config=config,
            rs_rating=rs_rating,
            spy_perf_20d=spy_perf_20d
        )

    if isinstance(as_of, (date, datetime)):
        as_of_str = as_of.strftime("%Y-%m-%d")
    else:
        as_of_str = str(as_of).split("T")[0].split(" ")[0]

    sym = "UNKNOWN"
    if not bars.empty and "symbol" in bars.columns:
        sym = str(bars["symbol"].iloc[-1])
    elif previous_base and previous_base.get("symbol"):
        sym = str(previous_base["symbol"])

    # 1. Basic validation
    if bars.empty:
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Dữ liệu nến trống", data_status="insufficient_data")

    # Standardize column names to lowercase
    df = bars.copy()
    col_map = {c: c.lower() for c in df.columns}
    df.rename(columns=col_map, inplace=True)

    required_cols = {"date", "open", "high", "low", "close", "volume"}
    if not required_cols.issubset(df.columns):
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Thiếu cột OHLCV bắt buộc", data_status="invalid_data")

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["date_dt"] = pd.to_datetime(df["date"])
    as_of_dt = pd.to_datetime(as_of_str)
    df = df[df["date_dt"] <= as_of_dt].sort_values("date_dt").reset_index(drop=True)

    if df.empty:
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Dữ liệu trống sau khi lọc as_of", data_status="insufficient_data")

    latest_bar_date_str = df["date_dt"].iloc[-1].strftime("%Y-%m-%d")

    # Handle stale data
    if latest_bar_date_str != as_of_str:
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Dữ liệu cũ / chưa đồng phiên", data_status="stale_data")

    # 2. Check sufficient bar count (requires at least min_bars, e.g. 40)
    if len(df) < cfg.min_bars:
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, f"Thiếu phiên giao dịch (có {len(df)}/{cfg.min_bars} phiên)", data_status="insufficient_data")

    # Check finite numbers and logical OHLC
    check_slice = df.iloc[-cfg.min_bars:]
    for col in ["open", "high", "low", "close", "volume"]:
        vals = check_slice[col].to_numpy()
        if not np.all(np.isfinite(vals)):
            return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Giá trị không hữu hạn (NaN hoặc Inf)", data_status="invalid_data")

    # Strict OHLC validation: Low <= Open, Close <= High, positive prices, non-negative volume
    # Use small epsilon (1e-4) to prevent rejection due to IEEE 754 float precision artifacts
    if (
        np.any(check_slice["close"] <= 0)
        or np.any(check_slice["open"] <= 0)
        or np.any(check_slice["low"] <= 0)
        or np.any(check_slice["high"] <= 0)
        or np.any(check_slice["volume"] < 0)
        or np.any(check_slice["high"] < check_slice["low"] - 1e-4)
        or np.any(check_slice["open"] < check_slice["low"] - 1e-4)
        or np.any(check_slice["open"] > check_slice["high"] + 1e-4)
        or np.any(check_slice["close"] < check_slice["low"] - 1e-4)
        or np.any(check_slice["close"] > check_slice["high"] + 1e-4)
    ):
        return _handle_invalid_or_error(
            sym, as_of_str, cfg, previous_base,
            "Giá trị OHLC không hợp lệ (Vi phạm Low <= Open, Close <= High hoặc giá <= 0)",
            data_status="invalid_data"
        )

    # Check trading dates: duplicate dates and chronological ordering
    dates_list = check_slice["date_dt"].dt.date.tolist()
    if df["date_dt"].duplicated().any() or check_slice["date_dt"].duplicated().any() or any(d1 >= d2 for d1, d2 in zip(dates_list[:-1], dates_list[1:])):
        return _handle_invalid_or_error(
            sym, as_of_str, cfg, previous_base,
            "Dữ liệu có ngày trùng lặp hoặc không theo thứ tự thời gian",
            data_status="invalid_data"
        )

    # Check trading calendar continuity: ensure no official market sessions were skipped
    from analytics.market_calendar import get_trading_days
    for d_prev, d_curr in zip(dates_list[:-1], dates_list[1:]):
        skipped = get_trading_days(d_prev + timedelta(days=1), d_curr - timedelta(days=1))
        if skipped or (d_curr - d_prev).days > 7:
            skip_desc = ", ".join(d.strftime("%Y-%m-%d") for d in skipped[:3]) if skipped else f"khoảng trống {(d_curr - d_prev).days} ngày"
            return _handle_invalid_or_error(
                sym, as_of_str, cfg, previous_base,
                f"Thiếu phiên giao dịch theo lịch thị trường ({skip_desc})",
                data_status="insufficient_data"
            )

    # 3. Base 20-bar slice
    window_bars = cfg.window_bars
    base = df.iloc[-window_bars:].copy()
    window_start = base["date_dt"].iloc[0].strftime("%Y-%m-%d")
    window_end = as_of_str

    close_T = float(base["close"].iloc[-1])
    high_T = float(base["high"].iloc[-1])
    low_T = float(base["low"].iloc[-1])
    volume_T = float(base["volume"].iloc[-1])

    perf_1d = None
    if len(df) >= 2:
        c_prev = float(df["close"].iloc[-2])
        if c_prev > 0:
            perf_1d = round(100.0 * (close_T - c_prev) / c_prev, 2)

    upper = float(base["high"].max())
    lower = float(base["low"].min())

    if lower <= 0 or upper <= lower:
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Biên nền không hợp lệ (Lower <= 0 hoặc Upper <= Lower)")

    width_pct = 100.0 * (upper - lower) / lower

    # 4. Efficiency Ratio (ER)
    # 20 closes have 19 step differences
    close_vals = base["close"].to_numpy()
    diffs = np.diff(close_vals)
    path = float(np.sum(np.abs(diffs)))
    net_change = abs(float(close_vals[-1] - close_vals[0]))

    if path <= 0:
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Biến động đường đi bằng 0 (giá đứng yên)")

    efficiency_ratio = net_change / path

    # 5. Center Shift (Độ lệch tâm giữa 2 nửa nền)
    first_half_close = base["close"].iloc[:10].to_numpy()
    last_half_close = base["close"].iloc[10:].to_numpy()
    center_shift = abs(float(np.mean(last_half_close) - np.mean(first_half_close))) / (upper - lower)

    # 6. True Range Contraction
    # Needs prior close for the first bar of base (index -21 in df)
    tr_slice = df.iloc[-window_bars - 1:].copy()
    prev_close = tr_slice["close"].shift(1)
    tr_vals = np.maximum(
        tr_slice["high"] - tr_slice["low"],
        np.maximum(
            (tr_slice["high"] - prev_close).abs(),
            (tr_slice["low"] - prev_close).abs()
        )
    ).iloc[1:].to_numpy()

    tr_first = float(np.mean(tr_vals[:10]))
    tr_last = float(np.mean(tr_vals[10:]))
    if tr_first <= 0 or not np.isfinite(tr_first) or not np.isfinite(tr_last):
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Mẫu số True Range bằng 0 (biến động bằng 0)", data_status="invalid_data")
    tr_contraction = tr_last / tr_first

    # 7. Volume Contraction
    vol_vals = base["volume"].to_numpy()
    vol_first = float(np.mean(vol_vals[:10]))
    vol_last = float(np.mean(vol_vals[10:]))
    if vol_first <= 0 or not np.isfinite(vol_first) or not np.isfinite(vol_last):
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Mẫu số Volume bằng 0 (khối lượng bằng 0)", data_status="invalid_data")
    vol_contraction = vol_last / vol_first

    # 8. Liquidity
    avg_volume20 = float(np.mean(vol_vals))
    is_liquid = bool((close_T >= cfg.min_price) and (avg_volume20 >= cfg.min_avg_volume))

    # 9. Accumulation Evidence: Signed Volume Balance
    step_vols = vol_vals[1:]
    sum_step_vols = float(np.sum(step_vols))
    if sum_step_vols <= 0:
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Tổng khối lượng bằng 0", data_status="invalid_data")
    signed_volume_balance = float(np.sum(np.sign(diffs) * step_vols) / sum_step_vols)

    if signed_volume_balance > cfg.vol_balance_threshold:
        volume_balance_label = "Volume thuận"
    elif signed_volume_balance < -cfg.vol_balance_threshold:
        volume_balance_label = "Volume mâu thuẫn"
    else:
        volume_balance_label = "Cân bằng"

    # 10. Trend Context & Moving Averages (MA50, MA200)
    ma50 = None
    ma200 = None
    price_vs_ma50_pct = None
    price_vs_ma200_pct = None

    if len(df) >= 50:
        ma50 = round(float(df["close"].rolling(50).mean().iloc[-1]), 2)
        if ma50 > 0:
            price_vs_ma50_pct = round((close_T - ma50) / ma50 * 100.0, 2)

    if len(df) >= 55 and ma50 is not None:
        ma50_series = df["close"].rolling(50).mean()
        ma50_T = float(ma50_series.iloc[-1])
        ma50_T_minus_5 = float(ma50_series.iloc[-6])
        if close_T > ma50_T and ma50_T >= ma50_T_minus_5:
            trend_context = "Nền trong xu hướng tăng"
        elif close_T < ma50_T and ma50_T < ma50_T_minus_5:
            trend_context = "Nền trong xu hướng giảm"
        else:
            trend_context = "Trung tính"
    else:
        trend_context = "Chưa đủ dữ liệu"

    if len(df) >= 200:
        ma200 = round(float(df["close"].rolling(200).mean().iloc[-1]), 2)
        if ma200 > 0:
            price_vs_ma200_pct = round((close_T - ma200) / ma200 * 100.0, 2)

    # 10b. Multi-session Buying/Selling Pressure Profile
    pressure_bias = "Chưa tính"
    try:
        from analytics.setup_analyzer import analyze_multi_session_pressure
        pressure_profile = analyze_multi_session_pressure(sym, bars=df, as_of=as_of_str)
        if isinstance(pressure_profile, dict):
            pressure_bias = pressure_profile.get("pressure_bias", "Chưa tính")
    except Exception:
        pass

    # 11. Relative Strength vs SPY
    rs_vs_spy = None
    if spy_perf_20d is not None and len(df) >= 21:
        c_prev20 = float(df["close"].iloc[-21])
        if c_prev20 > 0:
            stock_perf_20d = float((close_T - c_prev20) / c_prev20 * 100.0)
            rs_vs_spy = round(stock_perf_20d - spy_perf_20d, 2)

    # 11b. 52-Week High (252 bars) & Distance below high
    high_52w = None
    from_52w_high_pct = None
    if len(df) >= 252:
        high_52w = round(float(df["high"].iloc[-252:].max()), 2)
        if high_52w > 0:
            from_52w_high_pct = round(100.0 * (high_52w - close_T) / high_52w, 2)

    # 12. Condition Checks
    pass_width = bool(width_pct <= cfg.max_width_pct)
    pass_er = bool(efficiency_ratio <= cfg.max_efficiency_ratio)
    pass_center = bool(center_shift <= cfg.max_center_shift)
    rolling_base_pass = bool(is_liquid and pass_width and pass_er and pass_center)

    pass_tr = bool(tr_contraction is not None and tr_contraction <= cfg.max_tr_contraction)
    pass_vol = bool(vol_contraction is not None and vol_contraction <= cfg.max_vol_contraction)
    tight_pass = bool(rolling_base_pass and pass_tr and pass_vol)

    checks = [
        {
            "name": "Thanh khoản",
            "pass": is_liquid,
            "value": f"${close_T:.2f} | {avg_volume20:,.0f}/phiên",
            "threshold": f">=${cfg.min_price}, >={cfg.min_avg_volume:,.0f}"
        },
        {
            "name": "Độ rộng nền",
            "pass": pass_width,
            "value": f"{width_pct:.1f}%",
            "threshold": f"<={cfg.max_width_pct:.1f}%"
        },
        {
            "name": "Hiệu suất dịch chuyển (ER)",
            "pass": pass_er,
            "value": f"{efficiency_ratio:.3f}",
            "threshold": f"<={cfg.max_efficiency_ratio:.2f}"
        },
        {
            "name": "Độ lệch tâm giá (Center Shift)",
            "pass": pass_center,
            "value": f"{center_shift:.3f}",
            "threshold": f"<={cfg.max_center_shift:.2f}"
        },
        {
            "name": "Co hẹp True Range (10 phiên cuối / đầu)",
            "pass": pass_tr,
            "value": f"{tr_contraction:.2f}" if tr_contraction is not None else "N/A",
            "threshold": f"<={cfg.max_tr_contraction:.2f}"
        },
        {
            "name": "Volume cạn dần (10 phiên cuối / đầu)",
            "pass": pass_vol,
            "value": f"{vol_contraction:.2f}" if vol_contraction is not None else "N/A",
            "threshold": f"<={cfg.max_vol_contraction:.2f}"
        },
    ]

    warnings: List[str] = []
    notes: List[str] = []

    # 13. State Machine & Frozen Bounds Evaluation
    prev_is_active = bool(previous_base and previous_base.get("is_active"))

    if prev_is_active:
        # Continuing an ongoing base: bounds are FROZEN from initial base detection
        frozen_upper = float(previous_base["upper"])
        frozen_lower = float(previous_base["lower"])
        base_id = str(previous_base["base_id"])
        detected_at = str(previous_base["detected_at"])
        prev_weakening = int(previous_base.get("consecutive_weakening", 0))
        prev_state = str(previous_base.get("state", "forming"))
        win_start = str(previous_base.get("window_start", window_start))

        # Position within frozen base (can be <0 or >1 after breakout/breakdown)
        position = (close_T - frozen_lower) / (frozen_upper - frozen_lower) if frozen_upper > frozen_lower else 0.5
        distance_to_upper_pct = round((frozen_upper - close_T) / close_T * 100.0, 2) if close_T > 0 else 0.0
        now_vs_pivot_pct = round(100.0 * (close_T / frozen_upper - 1.0), 2) if frozen_upper > 0 else 0.0

        lifecycle_phase = "forming"
        breakout_date = previous_base.get("breakout_date")
        breakout_price = previous_base.get("breakout_price")
        breakout_bar_count = int(previous_base.get("breakout_bar_count", 0))
        consecutive_below_ma50 = int(previous_base.get("consecutive_below_ma50", 0))
        ended_at = previous_base.get("ended_at")
        end_reason = previous_base.get("end_reason")

        # Sequential evaluation of unassessed intermediate sessions from Forming state
        prev_as_of_str = str(previous_base.get("as_of", ""))
        intermediate_failure = False
        if prev_as_of_str:
            prev_as_of_dt = pd.to_datetime(prev_as_of_str)
            unassessed_bars = df[(df["date_dt"] > prev_as_of_dt) & (df["date_dt"] < as_of_dt)]
            for u_idx in unassessed_bars.index:
                u_row = df.loc[u_idx]
                u_close = float(u_row["close"])
                u_vol = float(u_row["volume"])
                u_date_str = u_row["date_dt"].strftime("%Y-%m-%d")
                u_loc = int(u_idx)

                # 1. Breakdown check
                if u_close < frozen_lower:
                    state = "broken_down"
                    lifecycle_phase = "failed_before_breakout"
                    is_active = False
                    consecutive_weakening = 0
                    ended_at = u_date_str
                    end_reason = f"Thủng biên dưới nền (${frozen_lower:.2f}) tại giá ${u_close:.2f}."
                    notes.append(end_reason)
                    intermediate_failure = True
                    break

                # 2. Breakout check
                elif u_close > frozen_upper:
                    u_prev_vols = df["volume"].iloc[max(0, u_loc - window_bars) : u_loc].to_numpy()
                    avg_u_vol = float(np.mean(u_prev_vols)) if len(u_prev_vols) > 0 else 0.0
                    vol_ratio = (u_vol / avg_u_vol) if avg_u_vol > 0 else 1.0

                    if vol_ratio >= cfg.breakout_vol_ratio:
                        # Confirmed breakout at intermediate session u!
                        post_bo_base = dict(previous_base)
                        u_ma50 = None
                        if u_loc >= 49:
                            u_ma50 = float(df["close"].iloc[:u_loc + 1].rolling(50).mean().iloc[-1])
                        bo_below_ma50 = 1 if (u_ma50 is not None and u_close < u_ma50) else 0

                        # Always compute base quality metrics at T-1 of breakout (20 bars ending at u_loc - 1)
                        if u_loc >= window_bars:
                            q_metrics = _compute_frozen_pre_breakout_quality(
                                df=df,
                                breakout_idx=u_loc,
                                window_bars=window_bars,
                                frozen_upper=frozen_upper,
                                frozen_lower=frozen_lower,
                                cfg=cfg
                            )
                            post_bo_base.update(q_metrics)

                        bo_notes = list(previous_base.get("notes", []))
                        bo_notes.append(f"Breakout vượt biên trên (${frozen_upper:.2f}) kèm volume xác nhận ({vol_ratio:.2f}x SMA20 vol).")

                        post_bo_base.update({
                            "as_of": u_date_str,
                            "state": "breakout_confirmed",
                            "lifecycle_phase": "fresh_breakout",
                            "breakout_date": u_date_str,
                            "breakout_price": u_close,
                            "breakout_bar_count": 1,
                            "consecutive_below_ma50": bo_below_ma50,
                            "is_active": True,
                            "notes": bo_notes
                        })

                        return track_post_breakout_base(
                            previous_base=post_bo_base,
                            bars=bars,
                            as_of=as_of,
                            config=cfg,
                            rs_rating=rs_rating,
                            spy_perf_20d=spy_perf_20d
                        )
                    else:
                        prev_state = "breakout_unconfirmed"
                        prev_weakening = 0

                # 3. Inside bounds [lower, upper]
                else:
                    if prev_state == "breakout_unconfirmed":
                        notes.append("Vượt nền rồi quay lại trong biên.")

                    if u_loc >= window_bars - 1:
                        b_u = df.iloc[u_loc - window_bars + 1 : u_loc + 1]
                        u_highs = b_u["high"].to_numpy()
                        u_lows = b_u["low"].to_numpy()
                        u_max = float(np.max(u_highs))
                        u_min = float(np.min(u_lows))
                        u_w = 100.0 * (u_max - u_min) / u_min if u_min > 0 else 999.0
                        u_cls = b_u["close"].to_numpy()
                        u_df = np.diff(u_cls)
                        u_pt = float(np.sum(np.abs(u_df)))
                        u_nt = abs(float(u_cls[-1] - u_cls[0]))
                        u_er = (u_nt / u_pt) if u_pt > 0 else 1.0
                        u_cs = (abs(float(np.mean(u_cls[10:]) - np.mean(u_cls[:10]))) / (u_max - u_min)) if u_max > u_min else 1.0
                        u_liq = float(u_cls[-1]) >= cfg.min_price and float(np.mean(b_u["volume"].iloc[-20:].to_numpy())) >= cfg.min_avg_volume

                        u_rolling_pass = bool(u_w <= cfg.max_width_pct and u_er <= cfg.max_efficiency_ratio and u_cs <= cfg.max_center_shift and u_liq)
                    else:
                        u_rolling_pass = True

                    if u_rolling_pass:
                        prev_weakening = 0
                        prev_state = "forming"
                    else:
                        prev_weakening += 1
                        if prev_weakening >= 2:
                            state = "lost_structure"
                            lifecycle_phase = "failed_before_breakout"
                            is_active = False
                            ended_at = u_date_str
                            end_reason = "Mất cấu trúc nền sau 2 phiên suy yếu liên tiếp."
                            notes.append(end_reason)
                            intermediate_failure = True
                            break
                        else:
                            prev_state = "weakening"

        # Sequential checks as specified
        if intermediate_failure:
            pass
        elif close_T < frozen_lower:
            state = "broken_down"
            lifecycle_phase = "failed_before_breakout"
            is_active = False
            consecutive_weakening = 0
            ended_at = as_of_str
            end_reason = f"Thủng biên dưới nền (${frozen_lower:.2f}) tại giá ${close_T:.2f}."
            notes.append(end_reason)
        elif close_T > frozen_upper:
            # Check breakout volume confirmation
            prev_20_vols = df["volume"].iloc[-window_bars - 1:-1].to_numpy()
            avg_prev_vol = float(np.mean(prev_20_vols)) if len(prev_20_vols) > 0 else 0.0
            vol_ratio = (volume_T / avg_prev_vol) if avg_prev_vol > 0 else 1.0

            if vol_ratio >= cfg.breakout_vol_ratio:
                state = "breakout_confirmed"
                lifecycle_phase = "fresh_breakout"
                breakout_date = as_of_str
                breakout_price = close_T
                breakout_bar_count = 1
                is_active = False  # Base forming phase completes; continued by post-breakout tracker
                consecutive_weakening = 0
                if ma50 is not None and close_T < ma50:
                    consecutive_below_ma50 = 1
                else:
                    consecutive_below_ma50 = 0
                notes.append(f"Breakout vượt biên trên (${frozen_upper:.2f}) kèm volume xác nhận ({vol_ratio:.2f}x SMA20 vol).")
            else:
                state = "breakout_unconfirmed"
                lifecycle_phase = "forming"
                is_active = True
                consecutive_weakening = 0
                notes.append(f"Vượt biên trên (${frozen_upper:.2f}) nhưng volume chưa đạt ({vol_ratio:.2f}x < {cfg.breakout_vol_ratio}x).")
        elif rolling_base_pass:
            consecutive_weakening = 0
            state = "tight" if tight_pass else "forming"
            lifecycle_phase = "forming"
            is_active = True
            if prev_state == "breakout_unconfirmed":
                notes.append("Vượt nền rồi quay lại trong biên.")
        else:
            # Inside bounds [lower, upper] but rolling 20-bar structure conditions weakened
            consecutive_weakening = prev_weakening + 1
            if consecutive_weakening >= 2:
                state = "lost_structure"
                lifecycle_phase = "failed_before_breakout"
                is_active = False
                ended_at = as_of_str
                end_reason = "Mất cấu trúc nền sau 2 phiên suy yếu liên tiếp."
                notes.append(end_reason)
            else:
                state = "weakening"
                lifecycle_phase = "forming"
                is_active = True
                notes.append("Cấu trúc nền suy yếu (không đạt độ hẹp/ER ở cửa sổ lăn 20 phiên).")
            if prev_state == "breakout_unconfirmed":
                notes.append("Vượt nền rồi quay lại trong biên.")

        # Probe / wick tests (râu nến vượt biên nhưng Close vẫn nằm trong nền)
        if is_active and state in ("forming", "tight", "weakening"):
            if high_T > frozen_upper and close_T <= frozen_upper:
                warnings.append(f"Kiểm định biên trên: Râu nến chạm ${high_T:.2f} vượt kháng cự ${frozen_upper:.2f}.")
            if low_T < frozen_lower and close_T >= frozen_lower:
                warnings.append(f"Kiểm định biên dưới: Râu nến nhúng ${low_T:.2f} dưới hỗ trợ ${frozen_lower:.2f}.")

        frozen_width_pct = round(100.0 * (frozen_upper - frozen_lower) / frozen_lower, 2) if frozen_lower > 0 else width_pct

        if state == "breakout_confirmed":
            # Always compute quality metrics at T-1 of breakout (20 bars ending at T-1), decoupled from breakout bar
            if len(df) >= window_bars + 1:
                q_metrics = _compute_frozen_pre_breakout_quality(
                    df=df,
                    breakout_idx=len(df) - 1,
                    window_bars=window_bars,
                    frozen_upper=frozen_upper,
                    frozen_lower=frozen_lower,
                    cfg=cfg
                )
                vol_contraction = q_metrics["vol_contraction"]
                tr_contraction = q_metrics["tr_contraction"]
                efficiency_ratio = q_metrics["efficiency_ratio"]
                center_shift = q_metrics["center_shift"]
                signed_volume_balance = q_metrics["signed_volume_balance"]
                volume_balance_label = q_metrics["volume_balance_label"]
                checks = q_metrics["checks"]
                window_end = q_metrics["window_end"]

        return BaseResult(
            symbol=sym,
            as_of=as_of_str,
            rule_version=cfg.rule_version,
            data_status="valid",
            base_id=base_id,
            detected_at=detected_at,
            window_start=win_start,
            window_end=window_end,
            state=state,
            lifecycle_phase=lifecycle_phase,
            is_active=is_active,
            upper=frozen_upper,
            lower=frozen_lower,
            close_price=close_T,
            perf_1d=perf_1d,
            width_pct=frozen_width_pct,
            efficiency_ratio=efficiency_ratio,
            center_shift=center_shift,
            tr_contraction=tr_contraction,
            vol_contraction=vol_contraction,
            position=position,
            distance_to_upper_pct=distance_to_upper_pct,
            now_vs_pivot_pct=now_vs_pivot_pct,
            signed_volume_balance=signed_volume_balance,
            volume_balance_label=volume_balance_label,
            trend_context=trend_context,
            rs_vs_spy=rs_vs_spy,
            rs_rating=rs_rating if rs_rating is not None else previous_base.get("rs_rating"),
            high_52w=high_52w,
            from_52w_high_pct=from_52w_high_pct,
            breakout_date=breakout_date,
            breakout_price=breakout_price,
            breakout_bar_count=breakout_bar_count,
            consecutive_below_ma50=consecutive_below_ma50,
            ended_at=ended_at,
            end_reason=end_reason,
            formula_version="v2.0",
            ma50=ma50,
            ma200=ma200,
            price_vs_ma50_pct=price_vs_ma50_pct,
            price_vs_ma200_pct=price_vs_ma200_pct,
            pressure_bias=pressure_bias,
            consecutive_weakening=consecutive_weakening,
            checks=checks,
            warnings=warnings,
            notes=notes
        )

    else:
        # No active base from previous session
        # Check if a previously closed base requires a fresh 20-bar window after its close date
        if previous_base and not previous_base.get("is_active"):
            closed_end_date = previous_base.get("as_of") or previous_base.get("window_end")
            if closed_end_date and window_start <= str(closed_end_date):
                dist_up = round((upper - close_T) / close_T * 100.0, 2) if close_T > 0 else 0.0
                now_pivot = round(100.0 * (close_T / upper - 1.0), 2) if upper > 0 else 0.0
                return BaseResult(
                    symbol=sym,
                    as_of=as_of_str,
                    rule_version=cfg.rule_version,
                    data_status="valid",
                    state="none",
                    lifecycle_phase="none",
                    is_active=False,
                    close_price=close_T,
                    perf_1d=perf_1d,
                    upper=upper,
                    lower=lower,
                    width_pct=width_pct,
                    efficiency_ratio=efficiency_ratio,
                    center_shift=center_shift,
                    tr_contraction=tr_contraction,
                    vol_contraction=vol_contraction,
                    distance_to_upper_pct=dist_up,
                    now_vs_pivot_pct=now_pivot,
                    signed_volume_balance=signed_volume_balance,
                    volume_balance_label=volume_balance_label,
                    trend_context=trend_context,
                    rs_vs_spy=rs_vs_spy,
                    rs_rating=rs_rating if rs_rating is not None else previous_base.get("rs_rating"),
                    high_52w=high_52w,
                    from_52w_high_pct=from_52w_high_pct,
                    formula_version="v2.0",
                    ma50=ma50,
                    ma200=ma200,
                    price_vs_ma50_pct=price_vs_ma50_pct,
                    price_vs_ma200_pct=price_vs_ma200_pct,
                    pressure_bias=pressure_bias,
                    checks=checks,
                    notes=["Cửa sổ 20 phiên chưa vượt qua ngày kết thúc của đợt nền cũ."]
                )

        dist_upper = round((upper - close_T) / close_T * 100.0, 2) if close_T > 0 else 0.0
        now_vs_pivot = round(100.0 * (close_T / upper - 1.0), 2) if upper > 0 else 0.0

        if rolling_base_pass:
            # A NEW BASE IS BORN! Freeze boundaries at this detection bar
            base_id = f"{sym}:{as_of_str}:{cfg.rule_version}"
            detected_at = as_of_str
            frozen_upper = upper
            frozen_lower = lower
            state = "tight" if tight_pass else "forming"
            lifecycle_phase = "forming"
            is_active = True
            position = (close_T - frozen_lower) / (frozen_upper - frozen_lower) if frozen_upper > frozen_lower else 0.5
            notes.append(f"Phát hiện nền giá mới ({'Nền co chặt' if state == 'tight' else 'Đang xây nền'}).")

            return BaseResult(
                symbol=sym,
                as_of=as_of_str,
                rule_version=cfg.rule_version,
                data_status="valid",
                base_id=base_id,
                detected_at=detected_at,
                window_start=window_start,
                window_end=window_end,
                state=state,
                lifecycle_phase=lifecycle_phase,
                is_active=is_active,
                upper=frozen_upper,
                lower=frozen_lower,
                close_price=close_T,
                perf_1d=perf_1d,
                width_pct=width_pct,
                efficiency_ratio=efficiency_ratio,
                center_shift=center_shift,
                tr_contraction=tr_contraction,
                vol_contraction=vol_contraction,
                position=position,
                distance_to_upper_pct=dist_upper,
                now_vs_pivot_pct=now_vs_pivot,
                signed_volume_balance=signed_volume_balance,
                volume_balance_label=volume_balance_label,
                trend_context=trend_context,
                rs_vs_spy=rs_vs_spy,
                rs_rating=rs_rating,
                high_52w=high_52w,
                from_52w_high_pct=from_52w_high_pct,
                formula_version="v2.0",
                ma50=ma50,
                ma200=ma200,
                price_vs_ma50_pct=price_vs_ma50_pct,
                price_vs_ma200_pct=price_vs_ma200_pct,
                pressure_bias=pressure_bias,
                consecutive_weakening=0,
                checks=checks,
                warnings=warnings,
                notes=notes
            )
        else:
            # No base detected
            position = (close_T - lower) / (upper - lower) if upper > lower else 0.5
            return BaseResult(
                symbol=sym,
                as_of=as_of_str,
                rule_version=cfg.rule_version,
                data_status="valid",
                state="none",
                lifecycle_phase="none",
                is_active=False,
                upper=upper,
                lower=lower,
                close_price=close_T,
                perf_1d=perf_1d,
                width_pct=width_pct,
                efficiency_ratio=efficiency_ratio,
                center_shift=center_shift,
                tr_contraction=tr_contraction,
                vol_contraction=vol_contraction,
                position=position,
                distance_to_upper_pct=dist_upper,
                now_vs_pivot_pct=now_vs_pivot,
                signed_volume_balance=signed_volume_balance,
                volume_balance_label=volume_balance_label,
                trend_context=trend_context,
                rs_vs_spy=rs_vs_spy,
                rs_rating=rs_rating,
                high_52w=high_52w,
                from_52w_high_pct=from_52w_high_pct,
                formula_version="v2.0",
                ma50=ma50,
                ma200=ma200,
                price_vs_ma50_pct=price_vs_ma50_pct,
                price_vs_ma200_pct=price_vs_ma200_pct,
                pressure_bias=pressure_bias,
                checks=checks
            )


def track_post_breakout_base(
    previous_base: Dict[str, Any],
    bars: pd.DataFrame,
    as_of: Union[date, str, datetime],
    config: Optional[BaseConfig] = None,
    rs_rating: Optional[int] = None,
    spy_perf_20d: Optional[float] = None
) -> BaseResult:
    """
    Evaluate an already broken-out base for post-breakout lifecycle:
    - Fresh breakouts (sessions 1-5 post breakout, where breakout bar = 1)
    - Climbing (session 6+ post breakout, still valid)
    - Played out (Close < frozen lower OR 2 consecutive closes below MA50)
    """
    cfg = config or BaseConfig()

    if isinstance(as_of, (date, datetime)):
        as_of_str = as_of.strftime("%Y-%m-%d")
    else:
        as_of_str = str(as_of).split("T")[0].split(" ")[0]

    sym = str(previous_base.get("symbol", "UNKNOWN"))
    if previous_base.get("state") in ("played_out", "broken_down", "lost_structure") or previous_base.get("lifecycle_phase") in ("played_out", "failed_before_breakout"):
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Nền đã kết thúc vòng đời", data_status=previous_base.get("data_status", "valid"))

    if bars.empty:
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Dữ liệu nến trống", data_status="insufficient_data")

    df = bars.copy()
    col_map = {c: c.lower() for c in df.columns}
    df.rename(columns=col_map, inplace=True)

    required_cols = {"date", "open", "high", "low", "close", "volume"}
    if not required_cols.issubset(df.columns):
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Thiếu cột OHLCV bắt buộc", data_status="invalid_data")

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["date_dt"] = pd.to_datetime(df["date"])
    as_of_dt = pd.to_datetime(as_of_str)
    df = df[df["date_dt"] <= as_of_dt].sort_values("date_dt").reset_index(drop=True)

    if df.empty:
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Dữ liệu trống sau khi lọc as_of", data_status="insufficient_data")

    latest_bar_date_str = df["date_dt"].iloc[-1].strftime("%Y-%m-%d")
    if latest_bar_date_str != as_of_str:
        return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Dữ liệu cũ / chưa đồng phiên", data_status="stale_data")

    # Validate OHLCV data integrity (NaN, Inf, non-positive price, negative volume, bounds)
    prev_as_of_check = str(previous_base.get("as_of", ""))
    n_check = max(min(len(df), cfg.min_bars), 50 if len(df) >= 50 else len(df))
    if prev_as_of_check:
        try:
            unassessed_cnt = int((df["date_dt"] > pd.to_datetime(prev_as_of_check)).sum())
            n_check = max(n_check, unassessed_cnt + 1)
        except Exception:
            pass
    check_slice = df.iloc[-min(len(df), n_check):]

    for col in ["open", "high", "low", "close", "volume"]:
        vals = check_slice[col].to_numpy()
        if not np.all(np.isfinite(vals)):
            return _handle_invalid_or_error(sym, as_of_str, cfg, previous_base, "Giá trị không hữu hạn (NaN hoặc Inf)", data_status="invalid_data")

    # Strict OHLC validation: Low <= Open, Close <= High, positive prices, non-negative volume
    if (
        np.any(check_slice["close"] <= 0)
        or np.any(check_slice["open"] <= 0)
        or np.any(check_slice["low"] <= 0)
        or np.any(check_slice["high"] <= 0)
        or np.any(check_slice["volume"] < 0)
        or np.any(check_slice["high"] < check_slice["low"] - 1e-4)
        or np.any(check_slice["open"] < check_slice["low"] - 1e-4)
        or np.any(check_slice["open"] > check_slice["high"] + 1e-4)
        or np.any(check_slice["close"] < check_slice["low"] - 1e-4)
        or np.any(check_slice["close"] > check_slice["high"] + 1e-4)
    ):
        return _handle_invalid_or_error(
            sym, as_of_str, cfg, previous_base,
            "Giá trị OHLC không hợp lệ (Vi phạm Low <= Open, Close <= High hoặc giá <= 0)",
            data_status="invalid_data"
        )

    # Check trading dates: duplicate dates and chronological ordering
    dates_list = check_slice["date_dt"].dt.date.tolist()
    if df["date_dt"].duplicated().any() or check_slice["date_dt"].duplicated().any() or any(d1 >= d2 for d1, d2 in zip(dates_list[:-1], dates_list[1:])):
        return _handle_invalid_or_error(
            sym, as_of_str, cfg, previous_base,
            "Dữ liệu có ngày trùng lặp hoặc không theo thứ tự thời gian",
            data_status="invalid_data"
        )

    # Check trading calendar continuity: ensure no official market sessions were skipped
    from analytics.market_calendar import get_trading_days
    for d_prev, d_curr in zip(dates_list[:-1], dates_list[1:]):
        skipped = get_trading_days(d_prev + timedelta(days=1), d_curr - timedelta(days=1))
        if skipped or (d_curr - d_prev).days > 7:
            skip_desc = ", ".join(d.strftime("%Y-%m-%d") for d in skipped[:3]) if skipped else f"khoảng trống {(d_curr - d_prev).days} ngày"
            return _handle_invalid_or_error(
                sym, as_of_str, cfg, previous_base,
                f"Thiếu phiên giao dịch theo lịch thị trường ({skip_desc})",
                data_status="insufficient_data"
            )

    # Frozen boundaries & base characteristics
    frozen_upper = float(previous_base["upper"])
    frozen_lower = float(previous_base["lower"])
    base_id = str(previous_base["base_id"])
    detected_at = str(previous_base["detected_at"])
    win_start = str(previous_base.get("window_start", ""))
    win_end = str(previous_base.get("window_end", ""))
    breakout_date = str(previous_base.get("breakout_date") or detected_at)
    breakout_price = previous_base.get("breakout_price")
    prev_bar_count = int(previous_base.get("breakout_bar_count", 1))
    prev_below_ma50 = int(previous_base.get("consecutive_below_ma50", 0))

    # Current bar
    close_T = float(df["close"].iloc[-1])
    high_T = float(df["high"].iloc[-1])
    low_T = float(df["low"].iloc[-1])
    volume_T = float(df["volume"].iloc[-1])

    perf_1d = None
    if len(df) >= 2:
        c_prev = float(df["close"].iloc[-2])
        if c_prev > 0:
            perf_1d = round(100.0 * (close_T - c_prev) / c_prev, 2)

    position = (close_T - frozen_lower) / (frozen_upper - frozen_lower) if frozen_upper > frozen_lower else 1.0
    distance_to_upper_pct = round((frozen_upper - close_T) / close_T * 100.0, 2) if close_T > 0 else 0.0
    now_vs_pivot_pct = round(100.0 * (close_T / frozen_upper - 1.0), 2) if frozen_upper > 0 else 0.0

    # Moving averages
    ma50 = None
    ma200 = None
    price_vs_ma50_pct = None
    price_vs_ma200_pct = None
    trend_context = "Chưa đủ dữ liệu"

    if len(df) >= 50:
        ma50 = round(float(df["close"].rolling(50).mean().iloc[-1]), 2)
        if ma50 > 0:
            price_vs_ma50_pct = round((close_T - ma50) / ma50 * 100.0, 2)

    if len(df) >= 55 and ma50 is not None:
        ma50_series = df["close"].rolling(50).mean()
        ma50_T = float(ma50_series.iloc[-1])
        ma50_T_minus_5 = float(ma50_series.iloc[-6])
        if close_T > ma50_T and ma50_T >= ma50_T_minus_5:
            trend_context = "Nền trong xu hướng tăng"
        elif close_T < ma50_T and ma50_T < ma50_T_minus_5:
            trend_context = "Nền trong xu hướng giảm"
        else:
            trend_context = "Trung tính"

    if len(df) >= 200:
        ma200 = round(float(df["close"].rolling(200).mean().iloc[-1]), 2)
        if ma200 > 0:
            price_vs_ma200_pct = round((close_T - ma200) / ma200 * 100.0, 2)

    # 52-week high
    high_52w = None
    from_52w_high_pct = None
    if len(df) >= 252:
        high_52w = round(float(df["high"].iloc[-252:].max()), 2)
        if high_52w > 0:
            from_52w_high_pct = round(100.0 * (high_52w - close_T) / high_52w, 2)

    # Multi-session pressure
    pressure_bias = "Chưa tính"
    try:
        from analytics.setup_analyzer import analyze_multi_session_pressure
        pressure_profile = analyze_multi_session_pressure(sym, bars=df, as_of=as_of_str)
        if isinstance(pressure_profile, dict):
            pressure_bias = pressure_profile.get("pressure_bias", "Chưa tính")
    except Exception:
        pass

    # RS vs SPY 20d
    rs_vs_spy = previous_base.get("rs_vs_spy")
    if spy_perf_20d is not None and len(df) >= 21:
        c_prev20 = float(df["close"].iloc[-21])
        if c_prev20 > 0:
            stock_perf_20d = float((close_T - c_prev20) / c_prev20 * 100.0)
            rs_vs_spy = round(stock_perf_20d - spy_perf_20d, 2)

    # Sequential evaluation of unassessed sessions according to trading calendar
    prev_as_of = str(previous_base.get("as_of", ""))
    ma50_rolling = df["close"].rolling(50).mean() if len(df) >= 50 else pd.Series([None] * len(df), index=df.index)

    unassessed_indices = []
    prev_status = previous_base.get("data_status", "valid")
    bo_date_str = str(previous_base.get("breakout_date") or "")

    last_valid_note = None
    for n in previous_base.get("notes", []):
        if str(n).startswith("last_valid_as_of:"):
            last_valid_note = str(n).split(":", 1)[1].strip()
            break

    if prev_status == "valid" and prev_as_of:
        prev_as_of_dt = pd.to_datetime(prev_as_of)
        unassessed_mask = (df["date_dt"] > prev_as_of_dt) & (df["date_dt"] <= as_of_dt)
        unassessed_indices = df.index[unassessed_mask].tolist()
    elif last_valid_note:
        valid_dt = pd.to_datetime(last_valid_note)
        unassessed_mask = (df["date_dt"] > valid_dt) & (df["date_dt"] <= as_of_dt)
        unassessed_indices = df.index[unassessed_mask].tolist()
    elif bo_date_str:
        bo_dt = pd.to_datetime(bo_date_str)
        bo_matches = df.index[df["date_dt"] == bo_dt].tolist()
        if bo_matches:
            last_assessed_idx = bo_matches[0] + max(prev_bar_count - 1, 0)
            unassessed_mask = (df.index > last_assessed_idx) & (df["date_dt"] <= as_of_dt)
            unassessed_indices = df.index[unassessed_mask].tolist()
        else:
            unassessed_mask = (df["date_dt"] > bo_dt) & (df["date_dt"] <= as_of_dt)
            unassessed_indices = df.index[unassessed_mask].tolist()
    elif prev_as_of:
        prev_as_of_dt = pd.to_datetime(prev_as_of)
        unassessed_mask = (df["date_dt"] > prev_as_of_dt) & (df["date_dt"] <= as_of_dt)
        unassessed_indices = df.index[unassessed_mask].tolist()

    cur_bar_count = prev_bar_count
    cur_below_ma50 = prev_below_ma50
    is_played_out = False
    end_reason = None
    ended_at = None

    if unassessed_indices:
        for idx in unassessed_indices:
            cur_bar_count += 1
            b_close = float(df.loc[idx, "close"])
            b_date_str = df.loc[idx, "date_dt"].strftime("%Y-%m-%d")
            b_ma50 = ma50_rolling.loc[idx]

            if pd.notna(b_ma50) and b_ma50 > 0 and b_close < float(b_ma50):
                cur_below_ma50 += 1
            else:
                cur_below_ma50 = 0

            if b_close < frozen_lower:
                is_played_out = True
                end_reason = f"Thủng đáy nền (${frozen_lower:.2f}) tại giá ${b_close:.2f}."
                ended_at = b_date_str
                break
            elif cur_below_ma50 >= 2:
                is_played_out = True
                end_reason = "2 phiên liên tiếp đóng cửa dưới MA50 sau breakout."
                ended_at = b_date_str
                break
    else:
        # Same session (idempotent run) or fallback if dates could not match
        if prev_as_of != as_of_str:
            cur_bar_count = prev_bar_count + 1
            if len(df) >= 50:
                cur_ma50 = float(ma50_rolling.iloc[-1])
                if close_T < cur_ma50:
                    cur_below_ma50 = prev_below_ma50 + 1
                else:
                    cur_below_ma50 = 0
        if close_T < frozen_lower:
            is_played_out = True
            end_reason = f"Thủng đáy nền (${frozen_lower:.2f}) tại giá ${close_T:.2f}."
            ended_at = as_of_str
        elif cur_below_ma50 >= 2:
            is_played_out = True
            end_reason = "2 phiên liên tiếp đóng cửa dưới MA50 sau breakout."
            ended_at = as_of_str

    breakout_bar_count = cur_bar_count
    consecutive_below_ma50 = cur_below_ma50

    notes = list(previous_base.get("notes", []))
    warnings = list(previous_base.get("warnings", []))

    if is_played_out:
        state = "played_out"
        lifecycle_phase = "played_out"
        is_active = False
        notes.append(f"Kết thúc chu kỳ theo dõi sau breakout: {end_reason}")
    else:
        is_active = True
        if breakout_bar_count <= 5:
            state = "fresh_breakout"
            lifecycle_phase = "fresh_breakout"
        else:
            state = "climbing"
            lifecycle_phase = "climbing"

    return BaseResult(
        symbol=sym,
        as_of=as_of_str,
        rule_version=cfg.rule_version,
        data_status="valid",
        base_id=base_id,
        detected_at=detected_at,
        window_start=win_start,
        window_end=win_end,
        state=state,
        lifecycle_phase=lifecycle_phase,
        is_active=is_active,
        upper=frozen_upper,
        lower=frozen_lower,
        close_price=close_T,
        perf_1d=perf_1d,
        width_pct=previous_base.get("width_pct"),
        efficiency_ratio=previous_base.get("efficiency_ratio"),
        center_shift=previous_base.get("center_shift"),
        tr_contraction=previous_base.get("tr_contraction"),
        vol_contraction=previous_base.get("vol_contraction"),
        position=position,
        distance_to_upper_pct=distance_to_upper_pct,
        now_vs_pivot_pct=now_vs_pivot_pct,
        signed_volume_balance=previous_base.get("signed_volume_balance"),
        volume_balance_label=previous_base.get("volume_balance_label", "Cân bằng"),
        trend_context=trend_context,
        rs_vs_spy=rs_vs_spy,
        rs_rating=rs_rating if rs_rating is not None else previous_base.get("rs_rating"),
        high_52w=high_52w,
        from_52w_high_pct=from_52w_high_pct,
        breakout_date=breakout_date,
        breakout_price=breakout_price,
        breakout_bar_count=breakout_bar_count,
        consecutive_below_ma50=consecutive_below_ma50,
        ended_at=ended_at or previous_base.get("ended_at"),
        end_reason=end_reason or previous_base.get("end_reason"),
        formula_version=str(previous_base.get("formula_version", "v2.0")),
        ma50=ma50,
        ma200=ma200,
        price_vs_ma50_pct=price_vs_ma50_pct,
        price_vs_ma200_pct=price_vs_ma200_pct,
        pressure_bias=pressure_bias,
        consecutive_weakening=0,
        checks=previous_base.get("checks", []),
        warnings=warnings,
        notes=notes
    )


def _handle_invalid_or_error(
    sym: str,
    as_of_str: str,
    cfg: BaseConfig,
    previous_base: Optional[Dict[str, Any]],
    reason: str,
    data_status: str = "invalid_data"
) -> BaseResult:
    """Helper to return safe invalid_data/insufficient_data result without breaking ongoing active base."""
    actual_sym = previous_base.get("symbol") if (previous_base and previous_base.get("symbol") and sym == "UNKNOWN") else sym

    # Check if there is an ongoing base to preserve (forming, fresh_breakout, climbing, breakout_confirmed)
    is_ongoing_base = bool(
        previous_base and previous_base.get("base_id") and (
            previous_base.get("is_active")
            or previous_base.get("state") in ("breakout_confirmed", "fresh_breakout", "climbing")
            or previous_base.get("lifecycle_phase") in ("fresh_breakout", "climbing")
        )
        and previous_base.get("state") not in ("played_out", "broken_down", "lost_structure")
        and previous_base.get("lifecycle_phase") not in ("played_out", "failed_before_breakout")
    )

    if is_ongoing_base:
        prev_notes = list(previous_base.get("notes", [])) if previous_base else []
        last_valid = previous_base.get("last_valid_as_of")
        if not last_valid and previous_base.get("data_status") == "valid":
            last_valid = previous_base.get("as_of")
        if not last_valid:
            for n in prev_notes:
                if str(n).startswith("last_valid_as_of:"):
                    last_valid = str(n).split(":", 1)[1].strip()
                    break

        notes_out = [n for n in prev_notes if not str(n).startswith("last_valid_as_of:")]
        notes_out.append(f"Dữ liệu không đủ / không hợp lệ: {reason}")
        if last_valid:
            notes_out.append(f"last_valid_as_of:{last_valid}")

        base_state = previous_base.get("state", "forming")
        base_lifecycle = previous_base.get("lifecycle_phase", "forming")
        return BaseResult(
            symbol=actual_sym,
            as_of=as_of_str,
            rule_version=cfg.rule_version,
            data_status=data_status,
            base_id=previous_base.get("base_id"),
            detected_at=previous_base.get("detected_at"),
            window_start=previous_base.get("window_start"),
            window_end=previous_base.get("window_end"),
            state=base_state,
            lifecycle_phase=base_lifecycle,
            is_active=True,
            upper=previous_base.get("upper"),
            lower=previous_base.get("lower"),
            close_price=previous_base.get("close_price"),
            perf_1d=previous_base.get("perf_1d"),
            width_pct=previous_base.get("width_pct"),
            efficiency_ratio=previous_base.get("efficiency_ratio"),
            center_shift=previous_base.get("center_shift"),
            tr_contraction=previous_base.get("tr_contraction"),
            vol_contraction=previous_base.get("vol_contraction"),
            position=previous_base.get("position"),
            distance_to_upper_pct=previous_base.get("distance_to_upper_pct"),
            now_vs_pivot_pct=previous_base.get("now_vs_pivot_pct"),
            signed_volume_balance=previous_base.get("signed_volume_balance"),
            volume_balance_label=previous_base.get("volume_balance_label", "Cân bằng"),
            trend_context=previous_base.get("trend_context", "Chưa đủ dữ liệu"),
            rs_vs_spy=previous_base.get("rs_vs_spy"),
            rs_rating=previous_base.get("rs_rating"),
            high_52w=previous_base.get("high_52w"),
            from_52w_high_pct=previous_base.get("from_52w_high_pct"),
            breakout_date=previous_base.get("breakout_date"),
            breakout_price=previous_base.get("breakout_price"),
            breakout_bar_count=int(previous_base.get("breakout_bar_count", 0)),
            consecutive_below_ma50=int(previous_base.get("consecutive_below_ma50", 0)),
            ended_at=previous_base.get("ended_at"),
            end_reason=previous_base.get("end_reason"),
            formula_version=str(previous_base.get("formula_version", "v2.0")),
            consecutive_weakening=previous_base.get("consecutive_weakening", 0),
            ma50=previous_base.get("ma50"),
            ma200=previous_base.get("ma200"),
            price_vs_ma50_pct=previous_base.get("price_vs_ma50_pct"),
            price_vs_ma200_pct=previous_base.get("price_vs_ma200_pct"),
            pressure_bias=previous_base.get("pressure_bias", "Chưa tính"),
            checks=previous_base.get("checks", []),
            warnings=[f"Dữ liệu bất thường ({reason}); giữ nguyên đợt nền, không báo thủng."],
            notes=notes_out
        )

    if previous_base and previous_base.get("base_id"):
        return BaseResult(
            symbol=actual_sym,
            as_of=as_of_str,
            rule_version=cfg.rule_version,
            data_status=data_status,
            base_id=previous_base.get("base_id"),
            detected_at=previous_base.get("detected_at"),
            window_start=previous_base.get("window_start"),
            window_end=previous_base.get("window_end"),
            state=previous_base.get("state", "none"),
            lifecycle_phase=previous_base.get("lifecycle_phase", "none"),
            is_active=False,
            upper=previous_base.get("upper"),
            lower=previous_base.get("lower"),
            close_price=previous_base.get("close_price"),
            ended_at=previous_base.get("ended_at"),
            end_reason=previous_base.get("end_reason"),
            notes=[f"Dữ liệu không hợp lệ / không đủ: {reason}"]
        )

    return BaseResult(
        symbol=sym,
        as_of=as_of_str,
        rule_version=cfg.rule_version,
        data_status=data_status,
        lifecycle_phase=previous_base.get("lifecycle_phase", "none") if previous_base else "none",
        notes=[f"Dữ liệu không hợp lệ / không đủ: {reason}"]
    )
