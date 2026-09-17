from copy import deepcopy
import math

import pytest

from analytics.candidate_quality import evaluate_quality, rank_for_review, select_shortlist


def candidate(symbol="AAA", short=False):
    c = {
        "symbol": symbol, "group_type": "long_cont", "setup_type": "pullback_ma20",
        "status": "confirmed", "close_price": 101, "trigger_price": 100,
        "invalidation_price": 98, "atr14": 2, "dist_ma20_atr": .5,
        "resistance_level": 108, "support_level": 92, "perf_1d": 1,
        "avg_dollar_vol20": 20_000_000, "rel_volume": 1.5,
        "fa_flags": {"days_to_earnings": 30}, "score": 20, "sub_industry": "Tech",
        "evidence_json": {"candlestick": {"features": {
            "open": 99, "low": 99, "high": 101.5, "close": 101}}},
    }
    if short:
        c.update(group_type="short_cont", setup_type="pullback_ma20_res",
                 close_price=99, invalidation_price=102, dist_ma20_atr=-.5, perf_1d=-1)
        c["evidence_json"]["candlestick"]["features"] = {
            "open": 101, "high": 101, "low": 98.5, "close": 99}
    return c


@pytest.mark.parametrize("short", [False, True])
def test_reference_entry_risk_and_room_are_directional(short):
    q = evaluate_quality(candidate(short=short))
    assert q["tier"] == "ready"
    assert q["entry_reference"] == (99 if short else 101)
    assert q["risk_atr"] == 1.5
    assert q["room_risk"] == pytest.approx(7 / 3)


@pytest.mark.parametrize("field,value,tier", [
    ("atr14", None, "wait"), ("atr14", math.nan, "wait"),
    ("atr14", math.inf, "wait"), ("atr14", 0, "wait"),
    ("invalidation_price", 102, "reject"),
    ("invalidation_price", 90, "reject"),
    ("resistance_level", 102, "reject"),
    ("resistance_level", 100, "wait"),
    ("resistance_level", math.inf, "wait"),
    ("dist_ma20_atr", 4.36, "reject"),
    ("dist_ma20_atr", None, "wait"),
    ("avg_dollar_vol20", 1_000_000, "reject"),
    ("avg_dollar_vol20", None, "wait"),
])
def test_bad_or_missing_inputs_never_pass(field, value, tier):
    c = candidate()
    c[field] = value
    assert evaluate_quality(c)["tier"] == tier


@pytest.mark.parametrize("days,tier", [(None, "wait"), (-1, "wait"), (0, "reject"), (7, "reject"), (8, "ready")])
def test_earnings_gate(days, tier):
    c = candidate()
    c["fa_flags"]["days_to_earnings"] = days
    assert evaluate_quality(c)["tier"] == tier


def test_confirmed_label_does_not_replace_price_reaction():
    c = candidate()
    # Green day vs yesterday can still close below today's open.
    c["evidence_json"]["candlestick"]["features"]["open"] = 101.2
    assert evaluate_quality(c)["tier"] == "wait"
    c = candidate()
    c["evidence_json"]["candlestick"]["features"].update(open=100.8, low=100.7)
    assert evaluate_quality(c)["tier"] == "wait"  # never touched MA


def test_missing_candle_and_inconsistent_candle_wait():
    c = candidate()
    c["evidence_json"] = {}
    assert evaluate_quality(c)["tier"] == "wait"
    c = candidate()
    c["evidence_json"]["candlestick"]["features"]["close"] = 105
    assert evaluate_quality(c)["tier"] == "wait"


@pytest.mark.parametrize("short", [False, True])
def test_breakout_requires_volume_and_actual_forward_barrier(short):
    c = candidate(short=short)
    c["setup_type"] = "breakdown" if short else "breakout"
    c["rel_volume"] = 1.0
    assert evaluate_quality(c)["tier"] == "wait"
    c["rel_volume"] = 1.5
    c["support_level" if short else "resistance_level"] = c["trigger_price"]
    q = evaluate_quality(c)
    assert q["tier"] == "wait" and q["room_risk"] is None


def test_raw_score_cannot_rescue_rejected_setup_and_inputs_unchanged():
    good, bad = candidate("GOOD"), candidate("BAD")
    bad.update(score=99999, dist_ma20_atr=4.36)
    original = deepcopy([good, bad])
    ranked = rank_for_review([bad, good])
    assert [c["symbol"] for c in ranked] == ["GOOD", "BAD"]
    assert [c["symbol"] for c in select_shortlist(ranked)] == ["GOOD"]
    assert [good, bad] == original


def test_shortlist_is_deterministic_unique_and_capped_without_filling():
    cs = [candidate(str(i)) for i in range(12)]
    ranked = rank_for_review(cs + [candidate("0")])
    assert rank_for_review(list(reversed(cs))) == rank_for_review(cs)
    assert len(select_shortlist(ranked)) == 2
    assert len(select_shortlist(ranked, industry_limit=None)) == 10
    assert len({c["symbol"] for c in select_shortlist(ranked, industry_limit=None)}) == 10
    assert select_shortlist(ranked, limit=0) == []
    assert select_shortlist(rank_for_review([{**candidate(), "dist_ma20_atr": 5}])) == []


def test_pretrigger_entry_uses_trigger_not_favorable_close():
    c = candidate()
    c["close_price"] = 99.5
    c["evidence_json"]["candlestick"]["features"]["close"] = 99.5
    q = evaluate_quality(c)
    assert q["entry_reference"] == 100
    assert q["risk_atr"] == 1
    assert q["tier"] == "wait"


def test_ui_default_shortlist_and_switch_to_rejections():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_string('''
from app.components.candidate_cards import render_candidates_section
from tests.test_candidate_quality import candidate
good, bad = candidate("GOOD"), candidate("BAD")
bad["dist_ma20_atr"] = 4.36
render_candidates_section([good, bad], as_of="2026-09-09")
''').run(timeout=30)
    assert not app.exception
    assert app.dataframe[0].value["Mã"].tolist() == ["GOOD"]
    app.selectbox(key="cand_quality_view").select("Không ưu tiên").run()
    assert not app.exception
    assert app.dataframe[0].value["Mã"].tolist() == ["BAD"]
    assert "MA20" in app.dataframe[0].value.iloc[0]["Lý do xét lọc"]
