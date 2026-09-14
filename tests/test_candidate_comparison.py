"""
Unit tests for candidate cards comparison component and safe HTML rendering.
Ensures side-by-side comparison avoids markdown code block escaping bug.
"""
from unittest.mock import MagicMock, patch
import pytest
from app.components.candidate_cards import (
    render_html_safe,
    render_candidates_comparison,
)

def test_render_html_safe_uses_st_html_when_available():
    """Verify render_html_safe delegates to st.html and strips indentation."""
    with patch("streamlit.html") as mock_html, patch("streamlit.markdown") as mock_md:
        test_str = """
            <div style="color: red;">
                <span>Test</span>
            </div>
        """
        render_html_safe(test_str)
        assert mock_html.called
        assert not mock_md.called
        called_arg = mock_html.call_args[0][0]
        # Should be dedented and trimmed
        assert called_arg.startswith('<div style="color: red;">')
        assert called_arg.endswith('</div>')

def test_render_html_safe_fallback_to_markdown():
    """Verify fallback to st.markdown with unsafe_allow_html when st.html is absent."""
    with patch("streamlit.html", create=False) as _, patch("streamlit.markdown") as mock_md:
        # Simulate environment without st.html
        with patch("builtins.hasattr", side_effect=lambda obj, name: False if name == "html" else hasattr(obj, name)):
            test_str = """
                <div>Hello</div>
            """
            render_html_safe(test_str)
            assert mock_md.called
            called_arg, kwargs = mock_md.call_args
            assert kwargs.get("unsafe_allow_html") is True
            assert called_arg[0].startswith("<div>Hello</div>")

def test_render_candidates_comparison_rendering():
    """Verify render_candidates_comparison runs smoothly for mock candidates and calls safe rendering."""
    mock_candidates = [
        {
            "symbol": "SWKS",
            "company_name": "Skyworks Solutions",
            "sector": "Information Technology",
            "sub_industry": "Semiconductors",
            "group_type": "long_cont",
            "setup_type": "Pullback MA20",
            "status": "confirmed",
            "close_price": 95.50,
            "trigger_price": 96.00,
            "invalidation_price": 92.00,
            "perf_1d": 1.25,
            "perf_5d": -0.50,
            "perf_20d": 5.40,
            "score": 12.5,
            "is_oneil_leader": False,
            "atr14": 2.10,
            "atr_pct": 2.20,
            "fa_flags": {
                "has_data": False
            }
        },
        {
            "symbol": "DELL",
            "company_name": "Dell Technologies",
            "sector": "Information Technology",
            "sub_industry": "Technology Hardware",
            "group_type": "long_cont",
            "setup_type": "Breakout",
            "status": "confirmed",
            "close_price": 120.00,
            "trigger_price": 121.00,
            "invalidation_price": 115.00,
            "perf_1d": 3.10,
            "perf_5d": 7.80,
            "perf_20d": 15.20,
            "score": 18.0,
            "is_oneil_leader": True,
            "atr14": 3.40,
            "atr_pct": 2.83,
            "fa_flags": {
                "has_data": True,
                "metrics": {
                    "rev_growth_str": "+15%",
                    "eps_growth_str": "+22%",
                    "profit_margin_str": "8.5%"
                },
                "days_to_earnings": 10,
                "next_earnings_date": "2026-09-24",
                "period_end": "2026-06-30"
            }
        }
    ]

    captured_html = []
    def mock_safe_render(html):
        captured_html.append(html)

    with patch("streamlit.multiselect", return_value=["SWKS", "DELL"]), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.link_button") as _, \
         patch("app.components.candidate_cards.render_html_safe", side_effect=mock_safe_render):
        
        render_candidates_comparison(mock_candidates)
        
        # 2 cards should have been rendered
        assert len(captured_html) == 2
        # Verify card 1 (SWKS - non-leader, no FA)
        assert "SWKS" in captured_html[0]
        assert "Skyworks Solutions" in captured_html[0]
        assert "Chưa có dữ liệu FA" in captured_html[0]
        assert "LEADER" not in captured_html[0]
        assert "&lt;div" not in captured_html[0]

        # Verify card 2 (DELL - leader, with FA)
        assert "DELL" in captured_html[1]
        assert "Dell Technologies" in captured_html[1]
        assert "LEADER" in captured_html[1]
        assert "Doanh thu YoY:</b> +15%" in captured_html[1]
        assert "⚠️ Còn 10 ngày" in captured_html[1]
        assert "&lt;div" not in captured_html[1]
