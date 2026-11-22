"""Stage 1: the scoreboard-only power rating."""

import datetime as dt

from cfp_rankings.power import fit_ratings
from cfp_rankings.snapshots import Game


def game(gid, home, away, hp, ap, neutral=True, fbs=(True, True)):
    return Game(gid, 2099, 1, dt.datetime(2099, 9, gid, tzinfo=dt.timezone.utc), home, away, hp, ap,
                neutral, fbs[0], fbs[1])


def test_winners_rate_above_losers_and_chains_carry():
    # A beat B, B beat C. A never played C, but should still rate above it.
    r = fit_ratings([game(1, "A", "B", 30, 20), game(2, "B", "C", 30, 20)])
    assert r.of("A") > r.of("B") > r.of("C")


def test_blowouts_are_capped():
    close = fit_ratings([game(1, "A", "B", 48, 20)])  # won by exactly the cap
    rout = fit_ratings([game(1, "A", "B", 80, 0)])
    assert abs(close.of("A") - rout.of("A")) < 1e-9


def test_few_games_stay_near_the_starting_guess():
    one = fit_ratings([game(1, "A", "B", 34, 20)], shrink=2.0)
    many = fit_ratings([game(i, "A", "B", 34, 20) for i in range(1, 9)], shrink=2.0)
    assert 0 < one.of("A") < many.of("A") < 7.01  # full belief would be +7 / -7


def test_prior_is_the_rating_when_there_are_no_games():
    r = fit_ratings([], prior={"A": 12.0, "B": -3.0})
    assert abs(r.of("A") - 12.0) < 1e-9 and abs(r.of("B") + 3.0) < 1e-9


def test_resume_rating_ignores_margin():
    narrow = fit_ratings([game(1, "A", "B", 21, 20)], cap=1.0)
    wide = fit_ratings([game(1, "A", "B", 60, 0)], cap=1.0)
    assert abs(narrow.of("A") - wide.of("A")) < 1e-9


def test_lower_division_teams_share_one_rating():
    r = fit_ratings([game(1, "A", "Small U", 50, 0, fbs=(True, False)), game(2, "B", "Tiny State", 50, 0, fbs=(True, False))])
    assert r.of("Small U", is_fbs=False) == r.of("Tiny State", is_fbs=False) < r.of("A")
