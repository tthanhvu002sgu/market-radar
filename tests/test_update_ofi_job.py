import re
from datetime import timedelta
from unittest.mock import MagicMock

import pandas as pd

from jobs.update_ofi import run_update_ofi
from providers.alpaca_provider import AlpacaAuthError, AlpacaQuoteProvider, get_us_session_window
from storage.ofi_store import OfiHistoryRepository

OPEN_STATUS = {"status_phase": "regular"}
CLOSED_STATUS = {"status_phase": "weekend"}
QUOTES_COLUMNS = ["symbol", "timestamp", "bid_price", "bid_size", "ask_price", "ask_size"]


class FakeQuoteProvider:
    """Provider giả trả quote stream cố định, lọc theo [start, end] như Alpaca."""

    def __init__(self, quotes_df):
        self.quotes_df = quotes_df
        self.calls = []

    def is_configured(self):
        return True

    def fetch_quotes(self, symbol, start, end):
        self.calls.append((symbol, start, end))
        mask = (self.quotes_df["timestamp"] >= pd.Timestamp(start)) & (
            self.quotes_df["timestamp"] <= pd.Timestamp(end)
        )
        return self.quotes_df[mask].reset_index(drop=True)


def make_session_quote_stream():
    """Quote stream đặt trong phiên hôm nay (CKS values: +200, +300, -300, +400)."""
    start_utc, _ = get_us_session_window()
    offsets = [(1, 100.00, 500, 100.02, 500),   # base
               (2, 100.00, 600, 100.02, 400),
               (3, 100.01, 300, 100.02, 400),
               (4, 100.01, 0, 100.02, 400),
               (61, 99.99, 200, 100.05, 700)]
    rows = []
    for off, bp, bs, ap, as_ in offsets:
        rows.append({
            "symbol": "TEST",
            "timestamp": pd.Timestamp(start_utc + timedelta(seconds=off)),
            "bid_price": bp, "bid_size": bs, "ask_price": ap, "ask_size": as_,
        })
    return pd.DataFrame(rows), start_utc


def make_fake_repo(symbols=("TEST",)):
    repo = MagicMock()
    repo.get_latest_snapshot.return_value = {"id": 1}
    repo.get_candidates_by_snapshot.return_value = [{"symbol": s} for s in symbols]
    return repo


def test_update_ofi_skips_when_missing_keys(tmp_path):
    provider = AlpacaQuoteProvider(key_id="", secret_key="")
    result = run_update_ofi(
        ofi_db_path=tmp_path / "ofi.db", provider=provider,
        main_repo=make_fake_repo(), market_status=OPEN_STATUS,
    )
    assert result["skipped"] == "missing_alpaca_keys"
    assert result["minutes_saved"] == 0


def test_update_ofi_skips_when_market_closed(tmp_path):
    quotes_df, _ = make_session_quote_stream()
    result = run_update_ofi(
        ofi_db_path=tmp_path / "ofi.db", provider=FakeQuoteProvider(quotes_df),
        main_repo=make_fake_repo(), market_status=CLOSED_STATUS,
    )
    assert result["skipped"] == "market_weekend"


def test_update_ofi_happy_path_and_seam_idempotency(tmp_path):
    quotes_df, start_utc = make_session_quote_stream()
    provider = FakeQuoteProvider(quotes_df)
    now = start_utc + timedelta(seconds=90)
    store = OfiHistoryRepository(db_path=tmp_path / "ofi.db")

    result = run_update_ofi(
        ofi_db_path=tmp_path / "ofi.db", provider=provider,
        main_repo=make_fake_repo(), market_status=OPEN_STATUS, now_utc=now,
    )
    assert result["success"] is True
    assert result["symbols_collected"] == 1
    assert result["minutes_saved"] == 2  # 2 phút: +200 và +400

    history = store.get_ofi_history(symbols=["TEST"])
    assert len(history) == 2
    assert history["ofi"].sum() == 600.0
    assert history["cum_ofi"].iloc[-1] == 600.0

    # Chạy lại: cursor = phút cuối, chỉ tính lại phút đang dở (seam), không nhân đôi
    result2 = run_update_ofi(
        ofi_db_path=tmp_path / "ofi.db", provider=provider,
        main_repo=make_fake_repo(), market_status=OPEN_STATUS, now_utc=now,
    )
    assert result2["success"] is True
    assert result2["minutes_saved"] == 1  # chỉ bucket cuối được tính lại
    history2 = store.get_ofi_history(symbols=["TEST"])
    assert len(history2) == 2  # không trùng lặp
    assert history2["ofi"].sum() == 600.0

    # Lần fetch thứ 2 phải lùi buffer 3 phút trước cursor
    second_call_start = provider.calls[1][1]
    assert second_call_start <= pd.Timestamp(get_us_session_window()[0])


def test_update_ofi_no_candidates(tmp_path):
    quotes_df, _ = make_session_quote_stream()
    empty_repo = MagicMock()
    empty_repo.get_latest_snapshot.return_value = None
    result = run_update_ofi(
        ofi_db_path=tmp_path / "ofi.db", provider=FakeQuoteProvider(quotes_df),
        main_repo=empty_repo, market_status=OPEN_STATUS,
    )
    assert result["skipped"] == "no_candidates"


class AuthFailProvider:
    def is_configured(self):
        return True

    def fetch_quotes(self, symbol, start, end):
        raise AlpacaAuthError("401")


def test_update_ofi_aborts_on_auth_error(tmp_path):
    """Lỗi xác thực Alpaca phải làm job thất bại rõ ràng (workflow báo đỏ), không nuốt."""
    result = run_update_ofi(
        ofi_db_path=tmp_path / "ofi.db", provider=AuthFailProvider(),
        main_repo=make_fake_repo(), market_status=OPEN_STATUS,
    )
    assert result["success"] is False
    assert result["error"] == "alpaca_auth"
    assert result["minutes_saved"] == 0


def test_update_ofi_degraded_when_nothing_collected_mid_session(tmp_path):
    """Sau 15 phút đầu phiên mà 0 symbol có quote -> success False (degraded)."""
    empty_df = pd.DataFrame(columns=QUOTES_COLUMNS)
    _, start_utc = make_session_quote_stream()
    result = run_update_ofi(
        ofi_db_path=tmp_path / "ofi.db", provider=FakeQuoteProvider(empty_df),
        main_repo=make_fake_repo(), market_status=OPEN_STATUS,
        now_utc=start_utc + timedelta(minutes=30),
    )
    assert result["success"] is False
    assert result["degraded"] is True

    # Đầu phiên (< 15 phút) thì chỉ ghi nhận no_data, chưa coi là thất bại
    result_early = run_update_ofi(
        ofi_db_path=tmp_path / "ofi.db", provider=FakeQuoteProvider(empty_df),
        main_repo=make_fake_repo(), market_status=OPEN_STATUS,
        now_utc=start_utc + timedelta(minutes=2),
    )
    assert result_early["success"] is True
    assert "degraded" not in result_early


def test_update_ofi_cursor_and_ts_use_iso_z_format(tmp_path):
    quotes_df, start_utc = make_session_quote_stream()
    store = OfiHistoryRepository(db_path=tmp_path / "ofi.db")
    run_update_ofi(
        ofi_db_path=tmp_path / "ofi.db", provider=FakeQuoteProvider(quotes_df),
        main_repo=make_fake_repo(), market_status=OPEN_STATUS,
        now_utc=pd.Timestamp(start_utc).to_pydatetime() + timedelta(seconds=90),
    )
    cursor = store.get_cursor("TEST")
    assert cursor and re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", cursor)
    history = store.get_ofi_history(symbols=["TEST"])
    assert history["ts"].str.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$").all()


def test_update_ofi_clamps_cursor_to_session_start(tmp_path):
    """Cursor từ phiên cũ (hôm qua) phải bị kẹp về đầu phiên hôm nay —
    không fetch lại dữ liệu cũ, không ghép event qua ranh giới phiên."""
    quotes_df, start_utc = make_session_quote_stream()
    store = OfiHistoryRepository(db_path=tmp_path / "ofi.db")
    # Giả lập cursor tồn dư từ phiên trước: trốn trước giờ mở cửa hôm nay
    stale = (pd.Timestamp(start_utc) - pd.Timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    store.save_cursor("TEST", stale)

    result = run_update_ofi(
        ofi_db_path=tmp_path / "ofi.db", provider=FakeQuoteProvider(quotes_df),
        main_repo=make_fake_repo(), market_status=OPEN_STATUS,
        now_utc=pd.Timestamp(start_utc).to_pydatetime() + timedelta(seconds=90),
    )
    assert result["success"] is True
    assert result["minutes_saved"] == 2
    # Cursor phải tiến tới bucket của phiên hôm nay, không còn là giá trị cũ
    assert store.get_cursor("TEST") > stale
    # Fetch window không được lùi về trước đầu phiên
    history = store.get_ofi_history(symbols=["TEST"])
    assert history["ts"].min() >= stale  # toàn bộ dữ liệu thuộc phiên hiện tại
