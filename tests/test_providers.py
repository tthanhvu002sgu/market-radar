import pytest
from providers.sp500_provider import WikipediaSP500Provider
from config.sector_mappings import SECTOR_ETF_MAP, ETF_TO_SECTOR_MAP, BENCHMARK_TICKER, BENCHMARK_EQUAL_WEIGHT

def test_clean_symbol():
    assert WikipediaSP500Provider.clean_symbol("BRK.B") == "BRK-B"
    assert WikipediaSP500Provider.clean_symbol("BF.B") == "BF-B"
    assert WikipediaSP500Provider.clean_symbol("AAPL") == "AAPL"
    assert WikipediaSP500Provider.clean_symbol("  msft  ") == "MSFT"
    assert WikipediaSP500Provider.clean_symbol("") == ""

def test_sector_mappings():
    # S&P 500 has exactly 11 GICS sectors
    assert len(SECTOR_ETF_MAP) == 11
    assert "Information Technology" in SECTOR_ETF_MAP
    assert SECTOR_ETF_MAP["Information Technology"] == "XLK"
    assert SECTOR_ETF_MAP["Financials"] == "XLF"
    assert SECTOR_ETF_MAP["Energy"] == "XLE"
    assert BENCHMARK_TICKER == "SPY"
    assert BENCHMARK_EQUAL_WEIGHT == "RSP"
    assert len(ETF_TO_SECTOR_MAP) == 11
