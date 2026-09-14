import pytest
from app.components.metrics_cards import render_contrast_bar_card
from providers.yfinance_provider import YFinanceProvider

def test_render_contrast_bar_card():
    # Normal case: Advancing vs Declining
    html = render_contrast_bar_card(
        title_left="Advancing",
        title_right="Declining",
        val_left_pct=67.8,
        val_left_count=341,
        val_right_pct=32.2,
        val_right_count=162
    )
    assert "Advancing" in html
    assert "Declining" in html
    assert "67.8%" in html
    assert "32.2%" in html
    assert "(341)" in html
    assert "(162)" in html

def test_render_contrast_bar_card_zero():
    # Zero case: ensure no division by zero
    html = render_contrast_bar_card(
        title_left="Above",
        title_right="Below",
        val_left_pct=0.0,
        val_left_count=0,
        val_right_pct=0.0,
        val_right_count=0,
        center_label="SMA50"
    )
    assert "SMA50" in html
    assert "50.0%" in html  # Balanced default 50-50 width

def test_yfinance_fetch_earnings_calendar():
    provider = YFinanceProvider()
    # Test method exists and handles bad or mock dates cleanly
    res = provider.fetch_earnings_calendar(start_date="2099-01-01", end_date="2099-01-02", limit=5)
    assert isinstance(res, list)
