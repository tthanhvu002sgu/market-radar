import os
from pathlib import Path
from config.sector_mappings import BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "market_radar.db")))
LOCK_FILE = DATA_DIR / "update.lock"

# Technical parameters
MA_PERIODS = [20, 50, 200]
VOLUME_MA_PERIOD = 20
BREAKOUT_LOOKBACK = 20
RS_WINDOWS = {
    "1W": 5,
    "1M": 20,
    "3M": 60,
}

# Screening thresholds
MIN_AVG_VOLUME = 100_000        # Minimum 20d average volume
MIN_PRICE = 5.0                 # Minimum share price
VOLUME_SURGE_RATIO = 1.2        # Volume surge threshold vs 20d SMA
PULLBACK_TOLERANCE_PCT = 0.025  # Within 2.5% of MA20 or MA50
MIN_COVERAGE_PCT = 0.95         # Minimum universe coverage threshold
DEFAULT_FETCH_PERIOD = "2y"     # Fetch 2y of daily bars to ensure >= 253 closes for 1Y returns
BARS_FETCH_PERIOD = "2y"

# Observation counts required for returns (N returns require N+1 closes)
MIN_OBS_252D = 253
MIN_OBS_126D = 127
MIN_OBS_60D = 61
MIN_OBS_20D = 21
MIN_OBS_5D = 6
MIN_OBS_1D = 2

# App settings
APP_TITLE = "Market Radar | S&P 500 Swing Trading Radar"
RULE_VERSION = "v1.2"

# Base Building Detector Settings ("Đang xây nền")
BASE_RULE_VERSION = "v1.0"
BASE_WINDOW_BARS = 20           # Cửa sổ nền 20 phiên
BASE_MIN_BARS = 40              # Cần ít nhất 40 phiên hợp lệ (41 phiên để có TR đầy đủ)
BASE_MAX_WIDTH_PCT = 12.0       # (upper - lower) / lower <= 12%
BASE_MAX_EFFICIENCY_RATIO = 0.35 # ER <= 0.35: ròng Close chia tổng biến động
BASE_MAX_CENTER_SHIFT = 0.30    # Độ lệch tâm giá 2 nửa nền <= 0.30
BASE_MAX_TR_CONTRACTION = 0.80  # True Range 10 phiên cuối / 10 phiên đầu <= 0.80
BASE_MAX_VOL_CONTRACTION = 0.80 # Volume 10 phiên cuối / 10 phiên đầu <= 0.80
BASE_BREAKOUT_VOL_RATIO = 1.20  # Volume phiên phá vỡ >= 1.2x SMA20 vol
BASE_VOLUME_BALANCE_THRESHOLD = 0.10 # > 0.10: thuận, < -0.10: mâu thuẫn


# US Trading Session & Market Hours (NYSE / NASDAQ)
US_MARKET_TZ = "America/New_York"
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0

# O'Neil Industry Ranking (CANSLIM) Parameters
INDUSTRY_LOOKBACK_PERIODS = {
    "DAY": 1,
    "WK": 5,
    "MTH": 20,
    "QTR": 60,
    "6M": 126,
    "1Y": 252,
}
COMPOSITE_RS_WEIGHTS = {
    "QTR": 0.30,
    "6M": 0.25,
    "1Y": 0.20,
    "MTH": 0.15,
    "WK": 0.10,
}
BLEND_RS_WEIGHTS = {
    "COMP": 0.50,
    "MTH": 0.25,
    "WK": 0.25,
}
LEADING_GROUP_THRESHOLD = 80  # Top 20% industry groups (COMP >= 80)
