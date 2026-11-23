"""Stage 2: features, the pairwise training signal and the model contract."""

import numpy as np

from cfp_rankings.backtest import examples
from cfp_rankings.features import FEATURES, History, build_rows, labels, points_share
from cfp_rankings.poll_model import PollRanker, pairwise_objective


def test_feature_table_shape_and_candidates(season):
    snap = season.snapshot("ap", 2)
    teams, X = build_rows(snap, History())
    assert X.shape == (len(teams), len(FEATURES))
    assert "Team 26" in teams  # unranked, did not lose: a candidate
    assert "Team 03" in teams  # lost, but was ranked last week: still a candidate
    row = dict(zip(FEATURES, X[teams.index("Team 03")]))
    assert row["prev_rank"] == 3 and row["losses"] == 1 and row["loss_at_home"] == 1
    assert row["beat_spread_by"] == -21  # favoured by 11, lost by 10
    assert dict(zip(FEATURES, X[teams.index("Team 04")]))["teams_above_that_lost"] == 2  # Teams 02 and 03


def test_features_cannot_see_the_week_being_predicted(season):
    # Team 01 loses 0-50 in week 2. The week 2 poll's features must not know.
    teams, X = build_rows(season.snapshot("ap", 2), History())
    row = dict(zip(FEATURES, X[teams.index("Team 01")]))
    assert row["losses"] == 0 and row["season_losses"] == 0


def test_no_features_for_the_preseason_poll(season):
    assert build_rows(season.snapshot("ap", 1), History()) is None


def test_labels_and_points_share(season):
    actual = season.release("ap", 2)
    y = labels(["Team 01", "Team 03", "Team 26"], actual)
    assert list(y) == [25, 0, 1]  # first, dropped out, entered at 25
    share = points_share(actual)
    assert max(share.values()) == share["Team 01"] <= 1.0


def test_pairwise_signal_pushes_the_right_way():
    # One poll, three teams, real order A > B > (unranked C). All scores equal.
    objective = pairwise_objective(np.array([2.0, 1.0, 0.0]), [3])
    grad, hess = objective(np.zeros(3), None)
    # LightGBM moves scores *against* the gradient: negative means "raise it".
    assert grad[0] < 0 < grad[2] and abs(grad[1]) < 1e-12
    assert (hess > 0).all()


def test_two_unranked_teams_are_never_compared():
    objective = pairwise_objective(np.array([0.0, 0.0]), [2])
    grad, _ = objective(np.array([5.0, -5.0]), None)
    assert not grad.any()


def test_model_follows_the_fit_predict_contract(season):
    model = PollRanker(trees=5)
    assert model.predict(season.snapshot("ap", 2)) is None  # not fitted yet
    model.fit(examples(season, "ap"))
    assert model.predict(season.snapshot("ap", 1)) is None  # preseason
    predicted = model.predict(season.snapshot("ap", 2))
    assert len(predicted) == 25 and len(set(predicted)) == 25
    assert abs(sum(share for _, share in model.importance()) - 1.0) < 1e-9 or not any(s for _, s in model.importance())
