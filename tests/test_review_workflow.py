"""The six-step path keeps context and records explicit no-action reviews."""
from streamlit.testing.v1 import AppTest

from app.components.review_workflow import candidate_key, candidates_in_group, rs_vs_spy, saved_review_path, sync_review_context
from storage.repository import MarketRadarRepository


def test_review_context_resets_only_when_snapshot_changes():
    state = {"wf_snapshot_id": 11, "wf_sector": "Technology", "wf_candidate": ("AAA", "long_cont", "breakout")}
    sync_review_context(state, 11)
    assert state["wf_candidate"][0] == "AAA"
    sync_review_context(state, 12)
    assert state["wf_snapshot_id"] == 12
    assert "wf_sector" not in state and "wf_candidate" not in state


def test_group_selection_does_not_mix_industries_or_setups():
    rows = [
        {"symbol": "AAA", "sector": "Technology", "sub_industry": "Software", "group_type": "long_cont", "setup_type": "breakout"},
        {"symbol": "AAA", "sector": "Technology", "sub_industry": "Software", "group_type": "long_rev", "setup_type": "reversal"},
        {"symbol": "BBB", "sector": "Technology", "sub_industry": "Hardware"},
    ]
    selected = candidates_in_group(rows, "Technology", "Software")
    assert len(selected) == 2
    assert candidate_key(selected[0]) != candidate_key(selected[1])
    assert rs_vs_spy({"perf_20d": 8.5}, {"spy_20d": 5.0}) == 3.5
    assert rs_vs_spy({"perf_20d": 8.5}, {}) is None
    assert saved_review_path({"sector": "Technology", "stop_stage": "Ngành/nhóm"}) == "Thị trường → Ngành/nhóm: Technology"


def test_workflow_records_no_action_against_exact_snapshot(tmp_path):
    repo = MarketRadarRepository(db_path=str(tmp_path / "review.db"))
    snapshot_id = repo.save_snapshot(
        as_of="2026-09-27", rule_version="v1", total_universe=100, valid_universe=95,
        coverage_pct=0.95, missing_symbols=[], market_metrics={}, sector_metrics=[], candidates=[],
    )
    other_snapshot = repo.save_snapshot(
        as_of="2026-09-27", rule_version="v1", total_universe=100, valid_universe=95,
        coverage_pct=0.95, missing_symbols=[], market_metrics={}, sector_metrics=[], candidates=[],
    )
    source = f'''
from storage.repository import MarketRadarRepository
from app.components.review_workflow import render_review_workflow
repo = MarketRadarRepository(db_path={str(tmp_path / "review.db")!r})
snapshot = {{"id": {snapshot_id}, "as_of": "2026-09-27", "rule_version": "v1", "status": "complete",
            "coverage_pct": 0.95, "valid_universe": 95,
            "market_metrics": {{"market_summary": "Độ rộng yếu", "pct_above_ma50": 38.0}},
            "sector_metrics": [{{"sector": "Technology", "rank": 3, "status": "Neutral"}}],
            "industry_metrics": []}}
render_review_workflow(snapshot, [], repo)
'''
    app = AppTest.from_string(source).run(timeout=30)
    assert not app.exception
    app.selectbox(key="wf_sector").set_value("Technology").run(timeout=30)
    assert not app.exception
    app.selectbox(key="wf_outcome").set_value("no_action").run(timeout=30)
    app.selectbox(key="wf_stop_stage").set_value("Ngành/nhóm").run(timeout=30)
    app.text_area(key="wf_reason").set_value("Không có ứng viên phù hợp trong nhóm này").run(timeout=30)
    app.button(key="wf_save_review").click().run(timeout=30)
    assert not app.exception
    rows = repo.get_workflow_reviews(snapshot_id)
    assert len(rows) == 1
    assert rows[0]["sector"] == "Technology"
    assert rows[0]["symbol"] is None
    assert rows[0]["stop_stage"] == "Ngành/nhóm"
    assert rows[0]["evidence"]["market_ma50_pct"] == 38.0
    assert repo.get_workflow_reviews(other_snapshot) == []


def test_repository_appends_review_revisions(tmp_path):
    repo = MarketRadarRepository(db_path=str(tmp_path / "review.db"))
    snapshot_id = repo.save_snapshot(
        as_of="2026-09-27", rule_version="v1", total_universe=100, valid_universe=100,
        coverage_pct=1.0, missing_symbols=[], market_metrics={}, sector_metrics=[], candidates=[],
    )
    review = {"snapshot_id": snapshot_id, "session_date": "2026-09-27", "outcome": "wait",
              "stop_stage": "Risk", "reason": "Thiếu mốc cản", "evidence": {"quality_version": "review-v1"}}
    repo.save_workflow_review(review)
    repo.save_workflow_review({**review, "outcome": "no_action", "reason": "Bỏ qua sau khi xem lại"})
    rows = repo.get_workflow_reviews(snapshot_id)
    assert [row["outcome"] for row in rows] == ["no_action", "wait"]
    assert rows[1]["evidence"]["quality_version"] == "review-v1"


def test_new_snapshot_keeps_leadership_evidence(tmp_path):
    repo = MarketRadarRepository(db_path=str(tmp_path / "rs.db"))
    snapshot_id = repo.save_snapshot(
        as_of="2026-09-27", rule_version="v1", total_universe=100, valid_universe=100,
        coverage_pct=1.0, missing_symbols=[], market_metrics={"spy_20d": 5.0}, sector_metrics=[],
        candidates=[{"symbol": "AAA", "group_type": "long_cont", "setup_type": "breakout",
                     "status": "confirmed", "close_price": 100, "perf_20d": 8.5,
                     "rs_rating": 88, "rs_vs_spy": 3.5}],
    )
    saved = repo.get_candidates_by_snapshot(snapshot_id)[0]
    assert saved["rs_rating"] == 88
    assert saved["rs_vs_spy"] == 3.5


def test_workflow_follows_group_to_candidate_and_risk(tmp_path):
    repo = MarketRadarRepository(db_path=str(tmp_path / "candidate_review.db"))
    snapshot_id = repo.save_snapshot(
        as_of="2026-09-27", rule_version="v1", total_universe=100, valid_universe=100,
        coverage_pct=1.0, missing_symbols=[], market_metrics={}, sector_metrics=[], candidates=[],
    )
    source = f'''
from tests.test_candidate_quality import candidate
from storage.repository import MarketRadarRepository
from app.components.review_workflow import render_review_workflow
repo = MarketRadarRepository(db_path={str(tmp_path / "candidate_review.db")!r})
row = candidate("AAA")
row.update(sector="Technology", perf_20d=8.5, rs_rating=88, is_oneil_leader=True)
snapshot = {{"id": {snapshot_id}, "as_of": "2026-09-27", "rule_version": "v1", "status": "complete",
            "coverage_pct": 1.0, "valid_universe": 100,
            "market_metrics": {{"spy_20d": 5.0}},
            "sector_metrics": [{{"sector": "Technology", "rank": 2}}],
            "industry_metrics": [{{"parent_sector": "Technology", "industry": "Tech", "rank": 1, "stk_count": 12}}]}}
render_review_workflow(snapshot, [row], repo)
'''
    app = AppTest.from_string(source).run(timeout=30)
    app.selectbox(key="wf_sector").set_value("Technology").run(timeout=30)
    app.selectbox(key="wf_industry").set_value("Tech").run(timeout=30)
    app.selectbox(key="wf_candidate").set_value(("AAA", "long_cont", "pullback_ma20")).run(timeout=30)
    assert not app.exception
    assert any("RS 20 phiên so SPY: 3.50 điểm %" in item.value for item in app.caption)
    assert any("Rủi ro giá tham chiếu" == item.label for item in app.metric)
    app.text_area(key="wf_reason").set_value("Theo dõi pullback sau khi kiểm tra plan").run(timeout=30)
    app.button(key="wf_save_review").click().run(timeout=30)
    assert not app.exception
    saved = repo.get_workflow_reviews(snapshot_id)
    assert saved[0]["symbol"] == "AAA"
    assert saved[0]["evidence"]["quality_tier"] == "ready"
    assert saved[0]["evidence"]["rs_vs_spy"] == 3.5
    app.selectbox(key="wf_outcome").set_value("no_action").run(timeout=30)
    app.selectbox(key="wf_stop_stage").set_value("Thị trường").run(timeout=30)
    app.button(key="wf_save_review").click().run(timeout=30)
    stopped_early = repo.get_workflow_reviews(snapshot_id)[0]
    assert stopped_early["symbol"] is None
    assert stopped_early["sector"] is None
    assert "quality_tier" not in stopped_early["evidence"]
    app.button(key="wf_candidates_detail").click().run(timeout=30)
    assert not app.exception
    assert app.session_state["active_page"] == "Ứng viên"
    assert app.session_state["cand_sector_filter"] == "Technology"
    assert app.session_state["cand_sub_industry_filter"] == "Tech"
    assert app.session_state["cand_nav_from"]["page"] == "Luồng rà soát"
