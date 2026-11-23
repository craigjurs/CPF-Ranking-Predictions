"""Stage 3: the CFP committee model."""

import json

import numpy as np
import pytest

from cfp_rankings.cfp_model import DEFAULT, FEATURES, CarryForward, CfpRanker, build_rows, carried_order, fit_pairwise
from cfp_rankings.features import History
from cfp_rankings.snapshots import PollRelease, RankedTeam, Snapshot


def _release(poll, slot, order):
    return PollRelease(2099, poll, slot, tuple(RankedTeam(i + 1, t) for i, t in enumerate(order)))


@pytest.fixture
def raw_dir(tmp_path):
    (tmp_path / "games").mkdir()
    (tmp_path / "games" / "2099.json").write_text(json.dumps([]))
    return tmp_path


def test_first_week_starts_from_the_ap_poll():
    snap = Snapshot(2099, "cfp", 10, (), (_release("ap", 10, ["A", "B", "C"]),))
    assert carried_order(snap) == {"A": 1.0, "B": 2.0, "C": 3.0}
    assert CarryForward().predict(snap) == ["A", "B", "C"]


def test_later_weeks_move_last_weeks_committee_rank_the_way_ap_moved():
    polls = (
        _release("ap", 10, ["A", "B", "C"]),
        _release("cfp", 10, ["B", "A", "C"]),  # the committee preferred B
        _release("ap", 11, ["A", "C", "B"]),  # AP then dropped B one spot and raised C one
    )
    order = carried_order(Snapshot(2099, "cfp", 11, (), polls))
    assert order == {"A": 2.0, "B": 2.0, "C": 2.0}  # B: 1 + 1, A: 2 + 0, C: 3 - 1
    # Ties go to the team AP has higher this week.
    assert CarryForward().predict(Snapshot(2099, "cfp", 11, (), polls)) == ["A", "C", "B"]


def test_pairwise_fit_learns_which_input_matters():
    rng = np.random.default_rng(0)
    tables, ranks = [], []
    for _ in range(20):
        X = rng.normal(size=(30, 2))
        order = np.argsort(-X[:, 0])  # only the first input decides the order
        rank = np.empty(30)
        rank[order] = np.arange(1, 31)
        tables.append(X)
        ranks.append(np.minimum(rank, 26))
    w = fit_pairwise(tables, ranks, ridge=1.0)
    assert w[0] > 5 * abs(w[1])


def test_untrained_model_uses_the_simple_rule(season, raw_dir):
    snap = season.snapshot("cfp", 2)
    model = CfpRanker([], raw_dir=raw_dir)
    model.fit([])
    assert model.predict(snap) == CarryForward().predict(snap)


def test_model_follows_the_fit_predict_contract(season, raw_dir):
    snap, actual = season.snapshot("cfp", 2), season.release("cfp", 2)
    model = CfpRanker([], raw_dir=raw_dir)
    model.fit([(snap, actual)])
    predicted = model.predict(snap)
    assert len(predicted) == 25 and len(set(predicted)) == 25
    assert [name for name, _ in model.importance()] and set(n for n, _ in model.importance()) == set(DEFAULT)


def test_inputs_cannot_see_the_ranking_being_predicted(season, raw_dir):
    snap = season.snapshot("cfp", 2)
    assert not any(p.poll == "cfp" and p.slot >= 2 for p in snap.polls)
    assert all(g.slot < 2 for g in snap.games)
    teams, X = build_rows(snap, History(), raw_dir)
    assert X.shape == (len(teams), len(FEATURES))
    assert "Team 26" in teams  # ranked by AP this week, so a candidate
