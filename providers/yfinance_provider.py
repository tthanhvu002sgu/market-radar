import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import yfinance as yf

from providers.base import BaseMarketDataProvider

logger = logging.getLogger(__name__)

class YFinanceProvider(BaseMarketDataProvider):
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size

    def fetch_daily_ohlcv(self, symbols: List[str], period: str = "1y") -> Tuple[List[Tuple[str, str, float, float, float, float, float]], List[str]]:
        """
        Fetch daily OHLCV bars for symbols in batches.
        Returns:
            records: list of (symbol, date_str, open, high, low, close, volume)
            failed_symbols: list of symbols that failed or had no data
        """
        all_records = []
        failed_symbols = []

        # Remove duplicates while preserving order
        unique_symbols = list(dict.fromkeys(symbols))
        total = len(unique_symbols)
        logger.info(f"Downloading daily bars for {total} symbols in batches of {self.batch_size}...")

        for i in range(0, total, self.batch_size):
            batch = unique_symbols[i : i + self.batch_size]
            logger.info(f"Downloading batch {i // self.batch_size + 1}/{(total + self.batch_size - 1) // self.batch_size} ({len(batch)} symbols)...")
            try:
                # yf.download with auto_adjust=True accounts for splits and dividends
                df = yf.download(
                    batch,
                    period=period,
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=True,
                    threads=True,
                    progress=False
                )
                if df.empty:
                    failed_symbols.extend(batch)
                    continue

                for sym in batch:
                    try:
                        if len(batch) == 1:
                            sym_df = df.copy()
                        elif sym in df.columns.levels[0]:
                            sym_df = df[sym].dropna(how="all")
                        else:
                            failed_symbols.append(sym)
                            continue

                        if sym_df.empty or len(sym_df) < 20:
                            failed_symbols.append(sym)
                            continue

                        # Extract columns
                        for idx, row in sym_df.iterrows():
                            # idx is Timestamp
                            date_str = idx.strftime("%Y-%m-%d")
                            c_open = float(row.get("Open", 0.0))
                            c_high = float(row.get("High", 0.0))
                            c_low = float(row.get("Low", 0.0))
                            c_close = float(row.get("Close", 0.0))
                            c_vol = float(row.get("Volume", 0.0))

                            if pd.isna(c_close) or c_close <= 0:
                                continue

                            all_records.append((
                                sym,
                                date_str,
                                round(c_open, 4),
                                round(c_high, 4),
                                round(c_low, 4),
                                round(c_close, 4),
                                round(c_vol, 0)
                            ))
                    except Exception as sym_err:
                        logger.warning(f"Error parsing data for {sym}: {sym_err}")
                        failed_symbols.append(sym)

            except Exception as batch_err:
                logger.error(f"Error downloading batch: {batch_err}")
                failed_symbols.extend(batch)

        logger.info(f"Downloaded {len(all_records)} daily bars. {len(failed_symbols)} symbols failed.")
        return all_records, failed_symbols

    def fetch_fundamentals(self, symbols: List[str], max_workers: int = 10) -> List[Dict[str, Any]]:
        """Fetch fundamental metrics and earnings date for candidate or priority symbols in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _fetch_one(sym: str) -> Dict[str, Any]:
            try:
                t = yf.Ticker(sym)
                info = t.info or {}

                # Sector & Industry
                sector = info.get("sector", "")
                industry = info.get("industry", "")
                is_financial = (
                    "Financial" in sector
                    or "Bank" in industry
                    or "Insurance" in industry
                )

                # Next earnings date
                next_earnings = "Chưa xác minh"
                try:
                    cal = t.calendar
                    if isinstance(cal, dict) and "Earnings Date" in cal:
                        ed = cal["Earnings Date"]
                        if isinstance(ed, list) and len(ed) > 0:
                            next_earnings = str(ed[0])
                        elif ed:
                            next_earnings = str(ed)
                    elif hasattr(cal, "empty") and not cal.empty:
                        if "Earnings Date" in cal.index:
                            val = cal.loc["Earnings Date"].values[0]
                            next_earnings = str(val)
                except Exception:
                    pass

                if next_earnings == "Chưa xác minh" and "earningsTimestamp" in info:
                    ts = info.get("earningsTimestamp")
                    if ts:
                        next_earnings = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

                return {
                    "symbol": sym,
                    "sector": sector,
                    "industry": industry,
                    "revenue_growth": info.get("revenueGrowth"),
                    "earnings_growth": info.get("earningsGrowth"),
                    "profit_margins": info.get("profitMargins"),
                    "operating_margins": info.get("operatingMargins"),
                    "operating_cashflow": info.get("operatingCashflow"),
                    "total_debt": info.get("totalDebt"),
                    "next_earnings_date": next_earnings,
                    "is_financial": is_financial,
                }
            except Exception as e:
                logger.warning(f"Error fetching fundamentals for {sym}: {e}")
                return {
                    "symbol": sym,
                    "sector": "",
                    "industry": "",
                    "revenue_growth": None,
                    "earnings_growth": None,
                    "profit_margins": None,
                    "operating_margins": None,
                    "operating_cashflow": None,
                    "total_debt": None,
                    "next_earnings_date": "Chưa xác minh",
                    "is_financial": False,
                }

        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sym = {executor.submit(_fetch_one, s): s for s in symbols}
            for future in as_completed(future_to_sym):
                results.append(future.result())

        return results
