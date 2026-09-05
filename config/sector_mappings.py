"""Mapping of GICS Sectors to SPDR Sector ETFs and market benchmarks."""

BENCHMARK_TICKER = "SPY"
BENCHMARK_EQUAL_WEIGHT = "RSP"

# 11 Select Sector SPDR ETFs mapping to GICS Sectors
SECTOR_ETF_MAP = {
    "Information Technology": "XLK",
    "Health Care": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Industrials": "XLI",
    "Communication Services": "XLC",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Materials": "XLB",
}

# Reverse mapping: ETF -> Sector Name
ETF_TO_SECTOR_MAP = {v: k for k, v in SECTOR_ETF_MAP.items()}

# Vietnamese translations / readable names for Sectors
SECTOR_NAMES_VI = {
    "Information Technology": "Công nghệ thông tin",
    "Health Care": "Y tế & Chăm sóc sức khỏe",
    "Financials": "Tài chính & Ngân hàng",
    "Consumer Discretionary": "Tiêu dùng không thiết yếu",
    "Industrials": "Công nghiệp",
    "Communication Services": "Dịch vụ truyền thông",
    "Consumer Staples": "Tiêu dùng thiết yếu",
    "Energy": "Năng lượng",
    "Utilities": "Tiện ích công cộng",
    "Real Estate": "Bất động sản",
    "Materials": "Nguyên vật liệu",
}
