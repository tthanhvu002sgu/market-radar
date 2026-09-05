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

# App settings
APP_TITLE = "Market Radar | S&P 500 Swing Trading Radar"
RULE_VERSION = "v1.0"
