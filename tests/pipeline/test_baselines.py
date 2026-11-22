from cfp_rankings.backtest import walk_forward
from cfp_rankings.baselines import CopyPoll, Persistence, WinLossRule
from cfp_rankings.metrics import score


def test_score_perfect_and_one_swap():
    actual = {f"T{i}": i for i in range(1, 26)}
    order = [f"T{i}" for i in range(1, 26)]
    perfect = score(order, actual)
    assert perfect["teams_right"] == 25 and perfect["exact"] == 25 and perfect["avg_miss"] == 0
    order[0], order[1] = order[1], order[0]
    swapped = score(order, actual)
    assert swapped["exact"] == 23 and swapped["avg_miss"] == 2 / 25 and swapped["top4_right"] == 4


def test_score_counts_a_missing_team_as_rank_26():
    actual = {f"T{i}": i for i in range(1, 26)}
    order = [f"T{i}" for i in range(1, 25)] + ["Newcomer"]
    s = score(order, actual)
    assert s["teams_right"] == 24
    assert s["avg_miss"] == 2 / 26  # T25 is 1 spot off, Newcomer is 1 spot off, over 26 teams


def test_persistence_copies_last_week(season):
    pred = Persistence().predict(season.snapshot("ap", 2))
    assert pred == season.release("ap", 1).teams()


def test_preseason_poll_has_nothing_to_start_from(season):
    assert Persistence().predict(season.snapshot("ap", 1)) is None
    assert WinLossRule().predict(season.snapshot("ap", 1)) is None


def test_win_loss_rule_moves_the_right_teams(season):
    pred = WinLossRule().predict(season.snapshot("ap", 2))
    last = season.release("ap", 1).teams()
    assert pred[0] == "Team 01"  # won, stays on top
    assert pred.index("Team 02") > last.index("Team 02")  # lost to a ranked team, slips
    assert "Team 03" not in pred[:10]  # lost to an unranked team, falls hard
    assert "Team 26" in pred  # unranked team that beat a ranked team gets in
    assert len(pred) == 25 and len(set(pred)) == 25


def test_win_loss_rule_ignores_games_it_must_not_see(season):
    # Team 01 gets blown out in week 2. The week 2 poll prediction must not know.
    assert WinLossRule().predict(season.snapshot("ap", 2))[0] == "Team 01"


def test_cfp_copy_and_fallback_use_that_sundays_ap(season):
    snap = season.snapshot("cfp", 2)
    ap_week2 = season.release("ap", 2).teams()
    assert CopyPoll("ap").predict(snap) == ap_week2
    assert Persistence(fallback="ap").predict(snap) == ap_week2  # no earlier CFP exists
    assert WinLossRule(fallback="ap").predict(snap) == ap_week2  # and no games since Sunday


def test_walk_forward_trains_only_on_earlier_seasons(season):
    seen = []

    class Spy(Persistence):
        def fit(self, examples):
            seen.append(sorted({snap.season for snap, _ in examples}))

    from cfp_rankings.snapshots import Season

    seasons = {y: Season(y, season.games, season.polls, season.week_starts) for y in (2097, 2098, 2099)}
    rows = walk_forward(seasons, "ap", Spy, [2098, 2099])
    assert seen == [[2097], [2097, 2098]]  # never the test season, never a later one
    assert len(rows) == 4  # two releases with a predecessor, per test season


def test_tuning_does_not_crash_and_keeps_valid_output(season):
    from cfp_rankings.backtest import examples

    model = WinLossRule(tune=True)
    model.fit(examples(season, "ap"))
    assert len(model.predict(season.snapshot("ap", 2))) == 25
