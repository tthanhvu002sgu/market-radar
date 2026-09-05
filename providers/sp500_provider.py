import io
import logging
from typing import Any, Dict, List
import requests
import pandas as pd

from providers.base import BaseUniverseProvider

logger = logging.getLogger(__name__)

class WikipediaSP500Provider(BaseUniverseProvider):
    WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    @staticmethod
    def clean_symbol(symbol: str) -> str:
        """Standardize symbol for yfinance/Yahoo (e.g. BRK.B -> BRK-B)."""
        if not symbol or not isinstance(symbol, str):
            return ""
        return symbol.strip().upper().replace(".", "-")

    def fetch_constituents(self) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            logger.info("Fetching S&P 500 constituents from Wikipedia...")
            resp = requests.get(self.WIKIPEDIA_URL, headers=headers, timeout=self.timeout)
            resp.raise_for_status()

            tables = pd.read_html(io.StringIO(resp.text))
            if not tables:
                raise ValueError("No tables found on Wikipedia S&P 500 page.")

            df = tables[0]
            # Expected columns: Symbol, Security, GICS Sector, GICS Sub-Industry
            records = []
            for _, row in df.iterrows():
                raw_sym = str(row.get("Symbol", ""))
                sym = self.clean_symbol(raw_sym)
                if not sym:
                    continue

                records.append({
                    "symbol": sym,
                    "security": str(row.get("Security", "")),
                    "sector": str(row.get("GICS Sector", "Unknown")),
                    "sub_industry": str(row.get("GICS Sub-Industry", "Unknown")),
                    "date_added": str(row.get("Date added", "")),
                    "cik": str(row.get("CIK", "")),
                })

            logger.info(f"Successfully retrieved {len(records)} S&P 500 constituents.")
            return records

        except Exception as e:
            logger.error(f"Error fetching S&P 500 constituents: {e}")
            raise
