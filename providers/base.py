from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List
import pandas as pd

class BaseQuoteProvider(ABC):
    """Provider cho dữ liệu quote best bid/ask (Level 1) — nguồn OFI."""

    @abstractmethod
    def is_configured(self) -> bool:
        """True nếu đã có đủ credentials để gọi API."""
        pass

    @abstractmethod
    def fetch_quotes(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch quotes best bid/ask của 1 symbol trong khoảng [start, end] (UTC).

        Returns DataFrame với cột: symbol, timestamp (UTC, tăng dần),
        bid_price, bid_size, ask_price, ask_size. Lỗi symbol trả DataFrame rỗng.
        """
        pass

class BaseUniverseProvider(ABC):
    @abstractmethod
    def fetch_constituents(self) -> List[Dict[str, Any]]:
        """Fetch universe constituents with symbol, company name, sector, and industry."""
        pass

class BaseMarketDataProvider(ABC):
    @abstractmethod
    def fetch_daily_ohlcv(self, symbols: List[str], period: str = "1y") -> pd.DataFrame:
        """Fetch daily OHLCV bars for given symbols."""
        pass

    @abstractmethod
    def fetch_fundamentals(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Fetch fundamental data and next earnings date for symbols."""
        pass
