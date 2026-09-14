import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import yfinance as yf

from config.settings import DEFAULT_FETCH_PERIOD
from providers.base import BaseMarketDataProvider

logger = logging.getLogger(__name__)
 
def _parse_date_or_ts(val: Any) -> Optional[datetime]:
    """Parse timestamps, date strings, or datetime objects into a python datetime."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val)
        except Exception:
            return None
    if isinstance(val, datetime):
        return val
    if hasattr(val, "to_pydatetime"):
        return val.to_pydatetime()
    if isinstance(val, str):
        clean = val.split()[0].strip()
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(clean, fmt)
            except ValueError:
                pass
        try:
            return pd.to_datetime(val).to_pydatetime()
        except Exception:
            return None
    return None

class YFinanceProvider(BaseMarketDataProvider):
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size

    def fetch_daily_ohlcv(self, symbols: List[str], period: str = DEFAULT_FETCH_PERIOD) -> Tuple[List[Tuple[str, str, float, float, float, float, float]], List[str]]:
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
                        try:
                            parsed_dt = datetime.fromtimestamp(ts)
                            # Only treat as next earnings if date is in the future [D-07]
                            if parsed_dt.date() >= datetime.now().date():
                                next_earnings = parsed_dt.strftime("%Y-%m-%d")
                        except Exception:
                            pass

                # Fiscal period & currency [R-02]
                mrq_val = info.get("mostRecentQuarter")
                period_end = None
                fiscal_period = None
                mrq_dt = _parse_date_or_ts(mrq_val)
                if mrq_dt:
                    period_end = mrq_dt.strftime("%Y-%m-%d")
                    fiscal_period = f"Kỳ kết thúc (MRQ): {period_end}"

                if not fiscal_period and "lastFiscalYearEnd" in info:
                    lfye_val = info.get("lastFiscalYearEnd")
                    lfye_dt = _parse_date_or_ts(lfye_val)
                    if lfye_dt:
                        period_end = lfye_dt.strftime("%Y-%m-%d")
                        fiscal_period = f"Niên độ kết thúc (FYE): {period_end}"

                retrieved_at = datetime.now().strftime("%Y-%m-%d")
                currency = info.get("financialCurrency") or info.get("currency") or "USD"
                rev_growth = info.get("revenueGrowth")
                eps_growth = info.get("earningsGrowth")
                data_status = "valid" if (rev_growth is not None or eps_growth is not None) else "partial"

                clean_sym = sym.strip().upper()
                sec_filing_url = f"https://www.sec.gov/edgar/browse/?CIK={clean_sym}"

                return {
                    "symbol": sym,
                    "sector": sector,
                    "industry": industry,
                    "revenue_growth": rev_growth,
                    "earnings_growth": eps_growth,
                    "profit_margins": info.get("profitMargins"),
                    "operating_margins": info.get("operatingMargins"),
                    "operating_cashflow": info.get("operatingCashflow"),
                    "total_debt": info.get("totalDebt"),
                    "next_earnings_date": next_earnings,
                    "is_financial": is_financial,
                    "period_end": period_end or "Chưa xác minh",
                    "fiscal_period": fiscal_period or "Chưa xác định kỳ",
                    "period_type": "Chỉ số tổng hợp Yahoo (YoY)",
                    "currency": currency,
                    "reported_date": None,
                    "retrieved_at": retrieved_at,
                    "source": "Yahoo Finance (Số liệu tổng hợp / Aggregate)",
                    "data_status": data_status,
                    "sec_filing_url": sec_filing_url,
                }
            except Exception as e:
                logger.warning(f"Error fetching fundamentals for {sym}: {e}")
                # Do not emit empty records that wipe out valid cached fundamentals [D-07]
                return None

        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sym = {executor.submit(_fetch_one, s): s for s in symbols}
            for future in as_completed(future_to_sym):
                res = future.result()
                if res is not None:
                    results.append(res)

        return results

    def fetch_earnings_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 150
    ) -> List[Dict[str, Any]]:
        """Fetch upcoming earnings calendar events from Yahoo Finance."""
        try:
            cal = yf.Calendars()
            df = cal.get_earnings_calendar(
                start=start_date,
                end=end_date,
                limit=limit,
                filter_most_active=False
            )
            if df is None or df.empty:
                return []

            df = df.reset_index()
            # Normalize column names
            records = []
            for _, row in df.iterrows():
                sym = str(row.get("Symbol") or row.get("index") or "").strip().upper()
                if not sym:
                    continue

                event_dt = row.get("Event Start Date")
                date_str = ""
                if hasattr(event_dt, "strftime"):
                    date_str = event_dt.strftime("%Y-%m-%d")
                elif event_dt:
                    date_str = str(event_dt)[:10]

                timing = str(row.get("Timing") or "TNS").strip().upper()
                if timing not in ("BMO", "AMC"):
                    timing = "TNS"

                eps_est = row.get("EPS Estimate")
                rep_eps = row.get("Reported EPS")
                surp = row.get("Surprise(%)")

                records.append({
                    "symbol": sym,
                    "company_name": str(row.get("Company") or sym),
                    "market_cap": float(row.get("Marketcap")) if pd.notna(row.get("Marketcap")) else None,
                    "event_name": str(row.get("Event Name") or "Earnings Announcement"),
                    "earnings_date": date_str,
                    "timing": timing,
                    "eps_estimate": float(eps_est) if pd.notna(eps_est) else None,
                    "reported_eps": float(rep_eps) if pd.notna(rep_eps) else None,
                    "surprise_pct": float(surp) if pd.notna(surp) else None,
                })
            return records
        except Exception as e:
            logger.warning(f"Error fetching earnings calendar from yfinance: {e}")
            return []
