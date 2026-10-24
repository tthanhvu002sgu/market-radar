"""
Alpaca Market Data API quote provider — nguồn dữ liệu OFI (best bid/ask).

Free tier chỉ phục vụ feed IEX: OFI tính từ feed này là xấp xỉ của toàn thị trường
(IEX chiếm ~2-3% khối lượng), đủ cho mục đích hiển thị bối cảnh dòng tiền phiên.

Chỉ dùng `requests` (đã có trong requirements), không thêm dependency.
Lỗi từng symbol bị nuốt và trả DataFrame rỗng (theo convention YFinanceProvider).
"""
import logging
import time
from datetime import date, datetime
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from config.settings import (
    ALPACA_API_KEY_ID,
    ALPACA_API_SECRET_KEY,
    ALPACA_DATA_BASE_URL,
    US_MARKET_TZ,
)
from providers.base import BaseQuoteProvider

logger = logging.getLogger(__name__)

QUOTE_COLUMNS = ["symbol", "timestamp", "bid_price", "bid_size", "ask_price", "ask_size"]

SESSION_OPEN_ET = (9, 30)   # 9:30 ET
SESSION_CLOSE_ET = (16, 0)  # 16:00 ET


class AlpacaQuoteError(Exception):
    """Lỗi request Alpaca không retry được (4xx khác) hoặc hết lượt retry."""


class AlpacaAuthError(AlpacaQuoteError):
    """Alpaca từ chối xác thực (401/403) — key sai/thiếu quyền, không retry.

    Lỗi hệ thống (mọi symbol đều fail như nhau) nên được truyền lên caller
    thay vì nuốt: job OFI phải trả thất bại, UI phải hiện cảnh báo riêng.
    """


def get_us_session_window(session_date: Optional[date] = None) -> Tuple[datetime, datetime]:
    """Trả (start_utc, end_utc) của phiên regular session Mỹ (9:30–16:00 ET) của session_date."""
    tz_et = ZoneInfo(US_MARKET_TZ)
    if session_date is None:
        session_date = datetime.now(tz_et).date()
    start_et = datetime(
        session_date.year, session_date.month, session_date.day,
        SESSION_OPEN_ET[0], SESSION_OPEN_ET[1], tzinfo=tz_et,
    )
    end_et = datetime(
        session_date.year, session_date.month, session_date.day,
        SESSION_CLOSE_ET[0], SESSION_CLOSE_ET[1], tzinfo=tz_et,
    )
    tz_utc = ZoneInfo("UTC")
    return start_et.astimezone(tz_utc), end_et.astimezone(tz_utc)


def _rfc3339(dt: datetime) -> str:
    return dt.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


class AlpacaQuoteProvider(BaseQuoteProvider):
    def __init__(
        self,
        key_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: Optional[str] = None,
        feed: str = "iex",
        timeout: int = 15,
        max_retries: int = 3,
        retry_sleep: float = 2.0,
        per_symbol_pause: float = 0.2,
    ):
        self.key_id = key_id or ALPACA_API_KEY_ID
        self.secret_key = secret_key or ALPACA_API_SECRET_KEY
        self.base_url = (base_url or ALPACA_DATA_BASE_URL).rstrip("/")
        self.feed = feed
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_sleep = retry_sleep
        self.per_symbol_pause = per_symbol_pause

    def is_configured(self) -> bool:
        return bool(self.key_id and self.secret_key)

    def _headers(self) -> dict:
        return {
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret_key,
        }

    def _get_page(self, url: str, params: dict) -> dict:
        """GET một trang. 401/403 -> AlpacaAuthError, 4xx khác -> AlpacaQuoteError
        (đều không retry). 429/5xx và lỗi mạng -> retry tối đa max_retries lần."""
        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.get(url, headers=self._headers(), params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_err = str(exc)
                time.sleep(self.retry_sleep * attempt)
                continue
            if resp.status_code in (401, 403):
                raise AlpacaAuthError(
                    f"Alpaca từ chối xác thực (HTTP {resp.status_code}) — kiểm tra "
                    "APCA_API_KEY_ID / APCA_API_SECRET_KEY."
                )
            if resp.status_code == 429 or resp.status_code >= 500:
                last_err = f"HTTP {resp.status_code}"
                time.sleep(self.retry_sleep * attempt)
                continue
            if resp.status_code >= 400:
                raise AlpacaQuoteError(f"Alpaca API trả HTTP {resp.status_code}: {url}")
            return resp.json()
        raise AlpacaQuoteError(f"Alpaca API lỗi sau {self.max_retries} lần thử: {last_err}")

    def fetch_quotes(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch toàn bộ quote updates của symbol trong [start, end] (UTC), gồm phân trang."""
        if not self.is_configured():
            logger.warning("AlpacaQuoteProvider chưa cấu hình API key — bỏ qua fetch quotes.")
            return pd.DataFrame(columns=QUOTE_COLUMNS)

        sym = symbol.strip().upper()
        url = f"{self.base_url}/v2/stocks/{sym}/quotes"
        params = {
            "start": _rfc3339(start),
            "end": _rfc3339(end),
            "limit": 10000,
            "feed": self.feed,
        }

        rows: List[dict] = []
        try:
            while True:
                payload = self._get_page(url, params)
                for q in payload.get("quotes", []):
                    rows.append({
                        "symbol": sym,
                        "timestamp": q.get("t"),
                        "bid_price": q.get("bp"),
                        "bid_size": q.get("bs"),
                        "ask_price": q.get("ap"),
                        "ask_size": q.get("as"),
                    })
                next_token = payload.get("next_page_token")
                if not next_token:
                    break
                params["page_token"] = next_token
        except AlpacaAuthError:
            # Lỗi hệ thống — truyền lên để job/UI phân biệt với "không có dữ liệu".
            raise
        except Exception as exc:
            logger.warning(f"Lỗi fetch quotes Alpaca cho {sym}: {exc}")
            return pd.DataFrame(columns=QUOTE_COLUMNS)

        if self.per_symbol_pause > 0:
            time.sleep(self.per_symbol_pause)

        if not rows:
            return pd.DataFrame(columns=QUOTE_COLUMNS)

        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        for col in ("bid_price", "bid_size", "ask_price", "ask_size"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = (
            df.dropna(subset=["timestamp", "bid_price", "ask_price"])
            .sort_values("timestamp")
            .drop_duplicates(subset=["timestamp"], keep="last")
            .reset_index(drop=True)
        )
        return df[QUOTE_COLUMNS]

    def fetch_session_quotes(self, symbol: str, session_date: Optional[date] = None) -> pd.DataFrame:
        """Fetch quotes của phiên Mỹ hiện tại (hoặc session_date) đến hiện tại."""
        start_utc, end_utc = get_us_session_window(session_date)
        now_utc = datetime.now(ZoneInfo("UTC"))
        effective_end = min(now_utc, end_utc)
        if effective_end <= start_utc:
            return pd.DataFrame(columns=QUOTE_COLUMNS)
        return self.fetch_quotes(symbol, start_utc, effective_end)
