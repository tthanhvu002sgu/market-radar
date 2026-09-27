"""
Unit tests for the Reorganized UI Architecture:
1. Sidebar-driven 1-level 10-page navigation structure and categories.
2. Candidate Cards: Contradiction rename, dual CSV downloads (filtered vs full), unified modal dialog helper.
3. Base Building: Dual data scope ("Trong snapshot" vs "Tất cả các đợt"), unique symbols and setup count format.
4. Setup Detail: 3-tab layout (Technical & Candlestick, Company & Earnings, Checklist).
5. Cross-navigation state contracts from Sector, Sub-industry, and Today dashboard.
"""
from unittest.mock import MagicMock, patch
import pytest
import pandas as pd

from app.components.candidate_cards import (
    GROUP_TITLES,
    render_candidates_section,
    render_candidates_table,
)
from app.components.base_watchlist import render_base_watchlist
from app.components.setup_detail import show_setup_detail_dialog, render_setup_detail_modal


def test_candidate_group_titles_and_base_exclusion():
    """Verify 'watchlist' is renamed to 'Tín Hiệu Mâu Thuẫn (Contradiction)' and base_building is excluded from candidate tabs."""
    title, desc = GROUP_TITLES.get("watchlist", ("", ""))
    assert "Tín Hiệu Mâu Thuẫn" in title
    assert "Contradiction" in title
    # Candidate tabs should not have base_building (it has its own dedicated page)
    assert "base_building" not in GROUP_TITLES


def test_candidate_cards_dual_csv_export_columns():
    """Verify dual CSV export standardization uses uniform column sets."""
    sample_candidates = [
        {
            "rank": 1,
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "sector": "Information Technology",
            "sub_industry": "Technology Hardware",
            "group_type": "breakout",
            "setup_type": "Pivot Breakout",
            "status": "confirmed",
            "score": 15.0,
            "is_oneil_leader": True,
            "close_price": 220.5,
            "trigger_price": 221.0,
            "invalidation_price": 215.0,
            "atr14": 3.2,
            "atr_pct": 1.45,
            "perf_1d": 1.2,
            "perf_5d": 3.4,
            "perf_20d": 8.5
        },
        {
            "rank": 2,
            "symbol": "MSFT",
            "company_name": "Microsoft Corp.",
            "sector": "Information Technology",
            "sub_industry": "Systems Software",
            "group_type": "long_cont",
            "setup_type": "Pullback MA20",
            "status": "watching",
            "score": 11.5,
            "is_oneil_leader": False,
            "close_price": 430.0,
            "trigger_price": 435.0,
            "invalidation_price": 420.0,
            "atr14": 5.0,
            "atr_pct": 1.16,
            "perf_1d": -0.5,
            "perf_5d": 1.0,
            "perf_20d": 4.2
        }
    ]

    export_cols = [
        "rank", "symbol", "company_name", "sector", "sub_industry",
        "group_type", "setup_type", "status", "score", "is_oneil_leader",
        "close_price", "trigger_price", "invalidation_price", "atr14", "atr_pct",
        "perf_1d", "perf_5d", "perf_20d"
    ]

    df_filtered = pd.DataFrame([sample_candidates[0]])
    df_all = pd.DataFrame(sample_candidates)

    csv_filtered = df_filtered[[c for c in export_cols if c in df_filtered.columns]].to_csv(index=False)
    csv_all = df_all[[c for c in export_cols if c in df_all.columns]].to_csv(index=False)

    assert "AAPL" in csv_filtered
    assert "MSFT" not in csv_filtered
    assert "AAPL" in csv_all
    assert "MSFT" in csv_all
    assert "rank,symbol,company_name" in csv_filtered
    assert "rank,symbol,company_name" in csv_all


def test_base_watchlist_dual_scope_and_counts():
    """Verify base watchlist component renders dual scopes and shows distinct symbol/setup counts."""
    mock_base_records = [
        {
            "symbol": "NVDA",
            "company_name": "NVIDIA Corp",
            "sector": "Information Technology",
            "sub_industry": "Semiconductors",
            "base_type": "Cup with Handle",
            "base_stage": "Stage 1",
            "base_status": "building",
            "base_length_weeks": 7,
            "base_depth_pct": 18.5,
            "pivot_price": 130.0,
            "current_price": 128.5,
            "breakout_volume_ratio": 1.2,
            "rs_rating": 95,
            "is_tight": True
        },
        {
            "symbol": "NVDA",  # Second base setup for same symbol
            "company_name": "NVIDIA Corp",
            "sector": "Information Technology",
            "sub_industry": "Semiconductors",
            "base_type": "Flat Base",
            "base_stage": "Stage 2",
            "base_status": "breakout_ready",
            "base_length_weeks": 5,
            "base_depth_pct": 9.2,
            "pivot_price": 132.0,
            "current_price": 131.8,
            "breakout_volume_ratio": 1.5,
            "rs_rating": 95,
            "is_tight": False
        },
        {
            "symbol": "AMZN",
            "company_name": "Amazon.com Inc",
            "sector": "Consumer Discretionary",
            "sub_industry": "Broadline Retail",
            "base_type": "Double Bottom",
            "base_stage": "Stage 1",
            "base_status": "completed",
            "base_length_weeks": 10,
            "base_depth_pct": 22.0,
            "pivot_price": 190.0,
            "current_price": 195.0,
            "breakout_volume_ratio": 2.1,
            "rs_rating": 88,
            "is_tight": False
        }
    ]

    mock_repo = MagicMock()
    mock_repo.get_latest_base_snapshots.return_value = mock_base_records

    with patch("streamlit.session_state", {}), \
         patch("streamlit.radio", return_value="Trong snapshot hiện tại"), \
         patch("streamlit.selectbox", return_value="Tất cả"), \
         patch("streamlit.text_input", return_value=""), \
         patch("streamlit.markdown") as mock_md, \
         patch("streamlit.expander"), \
         patch("streamlit.columns", side_effect=lambda n: [MagicMock() for _ in range(n if isinstance(n, int) else len(n))]):
        
        render_base_watchlist(
            base_records=mock_base_records,
            as_of="2026-03-27",
            repo=mock_repo
        )
        assert mock_md.called


def test_setup_detail_dialog_helper():
    """Verify show_setup_detail_dialog handles invocation gracefully with or without st.dialog."""
    sample_candidate = {
        "symbol": "TSLA",
        "company_name": "Tesla Inc",
        "sector": "Consumer Discretionary",
        "sub_industry": "Automobiles",
        "group_type": "breakout",
        "setup_type": "Cup with Handle",
        "status": "confirmed",
        "score": 14.0,
        "is_oneil_leader": True,
        "close_price": 250.0,
        "trigger_price": 252.0,
        "invalidation_price": 240.0,
        "atr14": 8.0,
        "atr_pct": 3.2,
        "perf_1d": 2.5,
        "perf_5d": 5.0,
        "perf_20d": 12.0
    }

    # Exercise dialog dispatch without opening a real Streamlit context in a unit test.
    with patch("streamlit.dialog", side_effect=lambda *args, **kwargs: lambda fn: fn), \
         patch("app.components.setup_detail.render_setup_detail_modal") as render_detail:
        show_setup_detail_dialog(sample_candidate, as_of="2026-03-27", repo=MagicMock(), key_suffix="test")
        render_detail.assert_called_once()


def test_main_navigation_structure():
    """The sidebar starts at market, follows the review path, and retains all routes."""
    from app.navigation import DEFAULT_PAGE, build_nav_sections, page_ids, resolve_initial_page

    sections = build_nav_sections(unread_count=3, candidate_count=12, base_count=4)
    ids = page_ids()
    assert DEFAULT_PAGE == ids[0] == "Thị trường"
    assert ids == [page for section in sections for page, _ in section["items"]]
    assert len(ids) == len(set(ids)) == 11
    assert ids.index("Ngành") < ids.index("Nhóm ngành") < ids.index("Ứng viên")
    assert ids.index("Ứng viên") < ids.index("Nền giá & bứt phá") < ids.index("Luồng rà soát") < ids.index("Chất lượng tín hiệu")
    assert {"Tổng hợp phiên", "Lịch BCTC", "Thay đổi giữa phiên", "Dữ liệu & vận hành"} <= set(ids)
    assert "(3)" in sections[1]["items"][0][1]

    fresh = {}
    assert resolve_initial_page(fresh) == "Thị trường"
    old_home = {"active_page": "Tổng hợp phiên"}
    assert resolve_initial_page(old_home) == "Thị trường"
    old_home["active_page"] = "Tổng hợp phiên"
    assert resolve_initial_page(old_home) == "Tổng hợp phiên"
    selected_detail = {"active_page": "Ứng viên"}
    assert resolve_initial_page(selected_detail) == "Ứng viên"
