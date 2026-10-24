from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from providers.alpaca_provider import (
    AlpacaAuthError,
    AlpacaQuoteError,
    AlpacaQuoteProvider,
    get_us_session_window,
)


def mock_response(status_code=200, payload=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload or {}
    resp.raise_for_status.side_effect = (
        None if status_code < 400 else requests.HTTPError(f"HTTP {status_code}")
    )
    return resp


def make_provider():
    return AlpacaQuoteProvider(key_id="test-key", secret_key="test-secret")


def test_missing_keys_not_configured_returns_empty():
    provider = AlpacaQuoteProvider(key_id="", secret_key="")
    assert provider.is_configured() is False
    df = provider.fetch_quotes("AAPL", datetime(2026, 1, 5, 14, 30), datetime(2026, 1, 5, 15, 0))
    assert df.empty


def test_fetch_quotes_pagination_and_columns():
    provider = make_provider()
    page1 = {
        "quotes": [
            {"t": "2026-01-05T14:30:05Z", "bp": 100.00, "bs": 500, "ap": 100.02, "as": 400},
            {"t": "2026-01-05T14:30:09Z", "bp": 100.00, "bs": 600, "ap": 100.02, "as": 300},
        ],
        "next_page_token": "token-1",
    }
    page2 = {
        "quotes": [
            {"t": "2026-01-05T14:31:02Z", "bp": 100.01, "bs": 200, "ap": 100.03, "as": 350},
        ],
    }

    with patch("providers.alpaca_provider.requests.get") as mock_get, \
         patch("providers.alpaca_provider.time.sleep"):
        mock_get.side_effect = [mock_response(payload=page1), mock_response(payload=page2)]
        df = provider.fetch_quotes("AAPL", datetime(2026, 1, 5, 14, 30), datetime(2026, 1, 5, 15, 0))

    assert mock_get.call_count == 2
    assert list(df.columns) == ["symbol", "timestamp", "bid_price", "bid_size", "ask_price", "ask_size"]
    assert len(df) == 3
    assert df["symbol"].eq("AAPL").all()
    assert df["timestamp"].is_monotonic_increasing
    # Trang 2 phải mang page_token từ trang 1
    _, kwargs_page2 = mock_get.call_args_list[1]
    assert kwargs_page2["params"]["page_token"] == "token-1"
    assert kwargs_page2["params"]["feed"] == "iex"


def test_fetch_quotes_retries_on_429_then_succeeds():
    provider = make_provider()
    ok_page = {"quotes": [
        {"t": "2026-01-05T14:30:05Z", "bp": 100.00, "bs": 500, "ap": 100.02, "as": 400},
    ]}

    with patch("providers.alpaca_provider.requests.get") as mock_get, \
         patch("providers.alpaca_provider.time.sleep") as mock_sleep:
        mock_get.side_effect = [mock_response(status_code=429), mock_response(payload=ok_page)]
        df = provider.fetch_quotes("AAPL", datetime(2026, 1, 5, 14, 30), datetime(2026, 1, 5, 15, 0))

    assert mock_get.call_count == 2
    assert mock_sleep.call_count >= 1
    assert len(df) == 1


def test_fetch_quotes_network_error_retried_then_swallowed():
    provider = make_provider()
    with patch("providers.alpaca_provider.requests.get") as mock_get, \
         patch("providers.alpaca_provider.time.sleep"):
        mock_get.side_effect = requests.ConnectionError("boom")
        df = provider.fetch_quotes("BAD", datetime(2026, 1, 5, 14, 30), datetime(2026, 1, 5, 15, 0))
    assert df.empty
    assert mock_get.call_count == provider.max_retries  # lỗi mạng được retry


def test_fetch_quotes_auth_error_propagates_without_retry():
    """401/403 phải ném AlpacaAuthError ngay (không retry) để job/UI cảnh báo riêng."""
    provider = make_provider()
    with patch("providers.alpaca_provider.requests.get") as mock_get, \
         patch("providers.alpaca_provider.time.sleep") as mock_sleep:
        mock_get.return_value = mock_response(status_code=401)
        with pytest.raises(AlpacaAuthError):
            provider.fetch_quotes("AAPL", datetime(2026, 1, 5, 14, 30), datetime(2026, 1, 5, 15, 0))
    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


def test_fetch_quotes_client_error_no_retry_swallowed():
    """4xx khác (vd 404 symbol lạ) không retry, nuốt lỗi trả rỗng (fault tolerance từng symbol)."""
    provider = make_provider()
    with patch("providers.alpaca_provider.requests.get") as mock_get, \
         patch("providers.alpaca_provider.time.sleep"):
        mock_get.return_value = mock_response(status_code=404)
        df = provider.fetch_quotes("NOPE", datetime(2026, 1, 5, 14, 30), datetime(2026, 1, 5, 15, 0))
    assert df.empty
    assert mock_get.call_count == 1
    assert isinstance(AlpacaQuoteError("x"), Exception)  # sanity: hierarchy tồn tại


def test_fetch_quotes_dedupes_and_sorts_timestamps():
    provider = make_provider()
    payload = {"quotes": [
        {"t": "2026-01-05T14:31:02Z", "bp": 100.01, "bs": 200, "ap": 100.03, "as": 350},
        {"t": "2026-01-05T14:30:05Z", "bp": 100.00, "bs": 500, "ap": 100.02, "as": 400},
        {"t": "2026-01-05T14:30:05Z", "bp": 100.00, "bs": 700, "ap": 100.02, "as": 400},
    ]}
    with patch("providers.alpaca_provider.requests.get") as mock_get, \
         patch("providers.alpaca_provider.time.sleep"):
        mock_get.return_value = mock_response(payload=payload)
        df = provider.fetch_quotes("AAPL", datetime(2026, 1, 5, 14, 30), datetime(2026, 1, 5, 15, 0))

    assert len(df) == 2  # timestamp trùng giữ bản cuối
    assert df["timestamp"].is_monotonic_increasing


def test_get_us_session_window_dst_and_winter():
    # EDT (UTC-4): 9:30 ET = 13:30 UTC
    start, end = get_us_session_window(pd.Timestamp("2026-07-15").date())
    assert start.strftime("%H:%M") == "13:30" and end.strftime("%H:%M") == "20:00"
    # EST (UTC-5): 9:30 ET = 14:30 UTC
    start, end = get_us_session_window(pd.Timestamp("2026-01-15").date())
    assert start.strftime("%H:%M") == "14:30" and end.strftime("%H:%M") == "21:00"


def test_fetch_session_quotes_before_open_returns_empty():
    provider = make_provider()
    # Session ở tương lai xa: now < start phiên -> phải trả rỗng mà không gọi API
    future_date = pd.Timestamp("2030-07-15").date()
    with patch("providers.alpaca_provider.requests.get") as mock_get:
        df = provider.fetch_session_quotes("AAPL", future_date)
    assert df.empty
    mock_get.assert_not_called()
