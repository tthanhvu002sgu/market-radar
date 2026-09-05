from abc import ABC, abstractmethod
from typing import Any, Dict, List
import pandas as pd

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
