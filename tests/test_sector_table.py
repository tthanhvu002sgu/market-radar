import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

from app.components.sector_table import render_gics_sectors, render_sector_section


@pytest.fixture
def mock_streamlit():
    with patch("app.components.sector_table.st") as mock_st:
        # Configure columns mock to return list of mocks based on requested count
        def fake_columns(spec, **kwargs):
            cnt = spec if isinstance(spec, int) else len(spec)
            return [MagicMock() for _ in range(cnt)]

        mock_st.columns.side_effect = fake_columns
        mock_st.tabs.side_effect = lambda tabs, **kwargs: [MagicMock() for _ in range(len(tabs))]
        mock_st.selectbox.side_effect = lambda label, options, **kwargs: options[0] if options else ""
        mock_st.multiselect.side_effect = lambda label, options, **kwargs: kwargs.get("default", [])
        mock_st.segmented_control.return_value = "macro"
        yield mock_st


def test_sector_table_missing_ma50_no_type_error_crash(mock_streamlit):
    """
    Acceptance Criteria (Issue 1):
    Trang ngành bị crash khi một ngành thiếu MA50:
    max() so sánh breadth kiểu None với số gây TypeError.
    Sửa: lọc giá trị hợp lệ trước khi chọn ngành có breadth cao nhất;
    tất cả thiếu thì hiển thị N/A.
    """
    # 3 sectors: Tech has 65.0%, Healthcare has None (missing MA50), Energy has 40.0%
    sector_metrics = [
        {"sector": "Information Technology", "sector_vi": "Công nghệ", "etf": "XLK", "status": "Dẫn đầu (Leading)", "status_desc": "OK", "breadth_ma50_pct": 65.0, "rank": 1},
        {"sector": "Health Care", "sector_vi": "Y tế", "etf": "XLV", "status": "Trung tính (Neutral)", "status_desc": "Thiếu MA50", "breadth_ma50_pct": None, "rank": 2},
        {"sector": "Energy", "sector_vi": "Năng lượng", "etf": "XLE", "status": "Suy yếu (Weakening)", "status_desc": "OK", "breadth_ma50_pct": 40.0, "rank": 3},
    ]

    sector_health = [
        {"sector": "Information Technology", "turnover_share_pct": 28.0, "is_divergent": False},
        {"sector": "Health Care", "turnover_share_pct": None, "is_divergent": False},  # also None turnover
        {"sector": "Energy", "turnover_share_pct": 12.0, "is_divergent": False},
    ]

    # This MUST NOT raise TypeError: '>' not supported between instances of 'NoneType' and 'float'
    render_gics_sectors(sector_metrics, sector_health=sector_health)

    # Check markdown calls for best breadth highlight
    md_calls = [str(call) for call in mock_streamlit.markdown.call_args_list]
    rendered_text = " ".join(md_calls)
    assert "Độ rộng tốt nhất: <b>Information Technology</b> (65.0% trên MA50)" in rendered_text
    assert "Thanh khoản lớn nhất: <b>Information Technology</b> (28.0% S&P 500)" in rendered_text


def test_sector_table_all_missing_ma50_displays_na(mock_streamlit):
    """When all sectors lack MA50, best breadth must display N/A without raising any error."""
    sector_metrics = [
        {"sector": "Information Technology", "sector_vi": "Công nghệ", "etf": "XLK", "status": "Trung tính (Neutral)", "status_desc": "OK", "breadth_ma50_pct": None, "rank": 1},
        {"sector": "Health Care", "sector_vi": "Y tế", "etf": "XLV", "status": "Trung tính (Neutral)", "status_desc": "OK", "breadth_ma50_pct": None, "rank": 2},
    ]

    render_gics_sectors(sector_metrics, sector_health=[])

    md_calls = [str(call) for call in mock_streamlit.markdown.call_args_list]
    rendered_text = " ".join(md_calls)
    assert "Độ rộng tốt nhất: <b>N/A</b>" in rendered_text


def test_sector_table_aux_matrix_1d_alignment_and_preserves_na(mock_streamlit):
    """
    Acceptance Criteria (Ngoài ra):
    Ma trận bổ trợ dùng cùng cửa sổ 1D (Net Breadth 1D vs Lợi suất ETF 1D),
    và giữ N/A thay vì điền 0.0.
    """
    sector_metrics = [
        {"sector": "Information Technology", "sector_vi": "Công nghệ", "etf": "XLK", "status": "Dẫn đầu (Leading)", "status_desc": "OK", "breadth_ma50_pct": 60.0, "etf_1d": 1.5, "rank": 1},
        {"sector": "Health Care", "sector_vi": "Y tế", "etf": "XLV", "status": "Suy yếu (Weakening)", "status_desc": "OK", "breadth_ma50_pct": 50.0, "etf_1d": None, "rank": 2},
    ]

    sector_health = [
        {"sector": "Information Technology", "turnover_share_pct": 25.0, "net_breadth": 0.45, "etf_1d": 1.5, "median_return_1d": 1.2},
        # XLV has missing net_breadth and missing etf_1d
        {"sector": "Health Care", "turnover_share_pct": 10.0, "net_breadth": None, "etf_1d": None, "median_return_1d": None},
    ]

    render_gics_sectors(sector_metrics, sector_health=sector_health)

    # Verify plotly_chart was called
    assert mock_streamlit.plotly_chart.called
    chart_calls = mock_streamlit.plotly_chart.call_args_list

    # Find the call for auxiliary matrix
    aux_call = next((c for c in chart_calls if c.kwargs.get("key") == "chart_aux_breadth_return_matrix"), None)
    assert aux_call is not None

    fig = aux_call.args[0]
    # Check that Y axis title or label is 1D return, not 1M return!
    assert "1D" in fig.layout.yaxis.title.text

    # XLV must NOT be plotted as a fake point at (0, 0)!
    # Only XLK should be plotted:
    plotted_etfs = []
    for trace in fig.data:
        if hasattr(trace, "text") and trace.text is not None:
            plotted_etfs.extend(list(trace.text))
    assert "XLK" in plotted_etfs
    assert "XLV" not in plotted_etfs


def test_sector_table_top5_none_metrics_no_type_error_crash(mock_streamlit):
    """
    Verify render_gics_sectors safely handles top5_concentration_pct = None
    and top5 stocks with None turnover_est, close, volume, and share_in_sector
    without raising any TypeError.
    """
    sector_metrics = [
        {"sector": "Information Technology", "sector_vi": "Công nghệ", "etf": "XLK", "status": "Dẫn đầu (Leading)", "status_desc": "OK", "breadth_ma50_pct": 65.0, "rank": 1}
    ]
    sector_health = [
        {
            "sector": "Information Technology",
            "turnover_share_pct": 28.0,
            "top5_concentration_pct": None,  # was line 306 crash
            "is_divergent": False,
            "top5_stocks": [{
                "symbol": "NVDA",
                "security": "Nvidia",
                "close": None,        # was line 412 crash
                "volume": None,       # was line 413 crash
                "turnover_est": None, # was line 405 crash
                "share_in_sector": None, # was line 415 crash
                "perf_1d": None,
                "perf_20d": None
            }]
        }
    ]

    # Must execute cleanly without any TypeError
    render_gics_sectors(sector_metrics, sector_health=sector_health)
    assert mock_streamlit.dataframe.called


def test_sector_rotation_chart_axis_title_and_quadrant_shapes(mock_streamlit):
    """
    Verify sector rotation chart uses proper HTML subscript for Y-axis (no raw {t-5})
    and includes pastel quadrant background shapes.
    """
    sector_metrics = [
        {"sector": "Information Technology", "sector_vi": "Công nghệ", "etf": "XLK", "status": "Dẫn đầu (Leading)", "status_desc": "OK", "breadth_ma50_pct": 65.0, "rank": 1}
    ]
    sector_rotation = {
        "sectors": [{
            "sector": "Information Technology",
            "sector_vi": "Công nghệ",
            "etf": "XLK",
            "rotation_state": "Dẫn đầu (Leading)",
            "current_x": 1.25,
            "current_y": 1.40,
            "etf_20d": 3.5,
            "spy_20d": 1.2,
            "regime": "Tăng trưởng dẫn dắt",
            "is_stale": False,
            "trail": [
                {"date": f"2026-09-{i:02d}", "x": 1.0 + i*0.05, "y": 1.0 + i*0.08}
                for i in range(1, 11)
            ]
        }]
    }

    render_gics_sectors(sector_metrics, sector_rotation=sector_rotation)

    chart_calls = mock_streamlit.plotly_chart.call_args_list
    rot_call = next((c for c in chart_calls if c.kwargs.get("key") == "chart_sector_rotation_quadrant"), None)
    assert rot_call is not None

    fig = rot_call.args[0]
    # Check Y axis title uses HTML subscript and no raw curly braces {t-5}
    assert "<sub>t</sub>" in fig.layout.yaxis.title.text
    assert "<sub>t-5</sub>" in fig.layout.yaxis.title.text
    assert "{t-5}" not in fig.layout.yaxis.title.text

    # Check quadrant background shapes exist (4 rectangles)
    assert len(fig.layout.shapes) >= 4


def test_sector_rotation_chart_trail_mode_off_hides_lines(mock_streamlit):
    """
    When trail_mode is 'Tắt đuôi (Chỉ hiện vị trí hiện tại)', no line or trail step traces should be added.
    """
    sector_metrics = [
        {"sector": "Information Technology", "sector_vi": "Công nghệ", "etf": "XLK", "status": "Dẫn đầu (Leading)", "status_desc": "OK", "breadth_ma50_pct": 65.0, "rank": 1}
    ]
    sector_rotation = {
        "sectors": [{
            "sector": "Information Technology",
            "sector_vi": "Công nghệ",
            "etf": "XLK",
            "rotation_state": "Dẫn đầu (Leading)",
            "current_x": 1.25,
            "current_y": 1.40,
            "etf_20d": 3.5,
            "spy_20d": 1.2,
            "regime": "Tăng trưởng dẫn dắt",
            "is_stale": False,
            "trail": [
                {"date": f"2026-09-{i:02d}", "x": 1.0 + i*0.05, "y": 1.0 + i*0.08}
                for i in range(1, 11)
            ]
        }]
    }

    # Mock selectbox to choose 'Tắt đuôi'
    mock_streamlit.selectbox.side_effect = lambda label, options, **kwargs: (
        "Tắt đuôi (Chỉ hiện vị trí hiện tại)" if "đuôi" in label.lower() else options[0]
    )

    render_gics_sectors(sector_metrics, sector_rotation=sector_rotation)

    chart_calls = mock_streamlit.plotly_chart.call_args_list
    rot_call = next((c for c in chart_calls if c.kwargs.get("key") == "chart_sector_rotation_quadrant"), None)
    assert rot_call is not None

    fig = rot_call.args[0]
    # No line traces should exist, only the marker trace
    line_traces = [t for t in fig.data if getattr(t, "mode", "") == "lines"]
    assert len(line_traces) == 0


def test_sector_rotation_chart_sector_filter_filters_data(mock_streamlit):
    """
    When selected_etfs is specified (e.g. only XLK), only XLK should appear in the rotation chart.
    """
    sector_metrics = [
        {"sector": "Information Technology", "sector_vi": "Công nghệ", "etf": "XLK", "status": "Dẫn đầu (Leading)", "status_desc": "OK", "breadth_ma50_pct": 65.0, "rank": 1},
        {"sector": "Energy", "sector_vi": "Năng lượng", "etf": "XLE", "status": "Dẫn đầu (Leading)", "status_desc": "OK", "breadth_ma50_pct": 60.0, "rank": 2}
    ]
    sector_rotation = {
        "sectors": [
            {
                "sector": "Information Technology",
                "sector_vi": "Công nghệ",
                "etf": "XLK",
                "rotation_state": "Dẫn đầu (Leading)",
                "current_x": 1.25,
                "current_y": 1.40,
                "etf_20d": 3.5,
                "spy_20d": 1.2,
                "regime": "Tăng trưởng dẫn dắt",
                "is_stale": False,
                "trail": [{"date": "2026-09-10", "x": 1.1, "y": 1.2}, {"date": "2026-09-11", "x": 1.25, "y": 1.40}]
            },
            {
                "sector": "Energy",
                "sector_vi": "Năng lượng",
                "etf": "XLE",
                "rotation_state": "Dẫn đầu (Leading)",
                "current_x": 2.75,
                "current_y": 0.38,
                "etf_20d": 5.0,
                "spy_20d": 1.2,
                "regime": "Tăng trưởng dẫn dắt",
                "is_stale": False,
                "trail": [{"date": "2026-09-10", "x": 2.5, "y": 0.3}, {"date": "2026-09-11", "x": 2.75, "y": 0.38}]
            }
        ]
    }

    # Filter to only XLK
    mock_streamlit.multiselect.side_effect = lambda label, options, **kwargs: (
        ["XLK"] if "lọc ngành" in label.lower() else []
    )

    render_gics_sectors(sector_metrics, sector_rotation=sector_rotation)

    chart_calls = mock_streamlit.plotly_chart.call_args_list
    rot_call = next((c for c in chart_calls if c.kwargs.get("key") == "chart_sector_rotation_quadrant"), None)
    assert rot_call is not None

    fig = rot_call.args[0]
    marker_traces = [t for t in fig.data if "markers+text" in getattr(t, "mode", "")]
    plotted_symbols = [t.text[0] for t in marker_traces if hasattr(t, "text") and t.text]
    assert "XLK" in plotted_symbols
    assert "XLE" not in plotted_symbols

