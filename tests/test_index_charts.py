import pytest
import pandas as pd
from datetime import datetime
from app.components.index_charts import create_unified_index_figure, INDEX_SPECS

def test_index_specs_validity():
    assert len(INDEX_SPECS) == 3
    names = [s["name"] for s in INDEX_SPECS]
    assert "S&P 500" in names
    assert "NASDAQ" in names
    assert "DOW" in names

def test_create_unified_index_figure():
    # Mock intraday candle data
    dates = pd.date_range("2026-09-11 09:30", "2026-09-11 16:00", freq="15min")
    df = pd.DataFrame({
        "Datetime": dates,
        "Open": [5000.0 + i for i in range(len(dates))],
        "High": [5005.0 + i for i in range(len(dates))],
        "Low": [4995.0 + i for i in range(len(dates))],
        "Close": [5002.0 + i for i in range(len(dates))],
        "Volume": [10000 + i * 100 for i in range(len(dates))]
    })
    
    fig = create_unified_index_figure(df, prev_close=4990.0, rel_vol=1.2, is_intraday=True)
    assert fig is not None
    # Subplots: 1 bar for RVOL + 1 candlestick
    assert len(fig.data) >= 2
    # Check layout
    assert fig.layout.paper_bgcolor == "#FFFFFF"
    assert fig.layout.plot_bgcolor == "#FFFFFF"
