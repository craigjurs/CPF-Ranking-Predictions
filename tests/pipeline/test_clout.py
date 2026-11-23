import pytest
"""The clout study: the gap between a ranking and on-field results."""

import numpy as np

from cfp_rankings.clout import CAP, Row, _capped, biggest_gaps, brand_scores, effect, team_seasons


def _row(season, team, cfp, resume, brand, power_conf, slot=10):
    return Row(season, slot, team, cfp, cfp, resume, resume, resume, 0, brand, power_conf)


def test_unranked_teams_count_as_26th():
    assert _capped({"A": 3}, "A") == 3
    assert _capped({"A": 3}, "B") == CAP
    assert _capped({"A": 90}, "A") == CAP


def test_brand_only_uses_earlier_seasons():
    finals = {2010: {"A": 1}, 2011: {"A": 1, "B": 26}, 2012: {"C": 1}}
    brand = brand_scores(finals, 2012)
    assert brand["A"] == 1.0  # first in both earlier seasons
    assert "C" not in brand  # 2012's own final poll is in the future


def test_effect_recovers_a_planted_tilt():
    # The judges give power-conference teams 3 extra spots and ignore brand.
    rng = np.random.default_rng(1)
    rows = []
    for i in range(200):
        brand, power_conf = float(rng.random()), bool(i % 2)
        resume = int(rng.integers(8, 20))
        rows.append(_row(2020 + i % 3, f"T{i}", resume - (3 if power_conf else 0), resume, brand, power_conf))
    result = effect(rows, lambda r: r.resume - r.cfp, draws=200)
    assert abs(result["power_conf"][0] - 3.0) < 1e-9
    assert abs(result["brand"][0]) < 1e-9
    assert team_seasons(rows) == 200


def test_biggest_gaps_needs_three_weeks():
    rows = [_row(2021, "Often", 5, 15, 0.0, True, slot=s) for s in (10, 11, 12)]
    rows.append(_row(2021, "Once", 1, 25, 0.0, True))
    over, _ = biggest_gaps(rows)
    assert [team for _, (_, team) in over] == ["Often"]


# ---------- conference title games ----------
def _raw(home, away, hp, ap_, conf, week=15, neutral=False, notes=None, away_conf=None):
    return {"seasonType": "regular", "week": week, "completed": True, "homeTeam": home, "awayTeam": away,
            "homePoints": hp, "awayPoints": ap_, "homeConference": conf, "awayConference": away_conf or conf,
            "homeClassification": "fbs", "neutralSite": neutral, "notes": notes}


def test_title_games_are_found_without_labels(tmp_path):
    from cfp_rankings.clout import title_games

    games = [
        _raw("A", "B", 30, 20, "East"),  # the only East game that week: the title game
        _raw("C", "D", 10, 20, "West", neutral=True),  # West title game, on a neutral field
        _raw("E", "F", 10, 20, "West"),  # a made-up regular West game the same week
        _raw("G", "H", 10, 20, "North"),  # North has two ordinary games and no title game
        _raw("I", "J", 10, 20, "North"),
        _raw("K", "L", 10, 20, "South", away_conf="East"),  # not a conference game
        _raw("M", "N", 10, 20, "East", week=14),  # the wrong week
    ]
    (tmp_path / "games").mkdir()
    (tmp_path / "games" / "2099.json").write_text(__import__("json").dumps(games))
    assert title_games(2099, 15, tmp_path) == {"A": True, "B": False, "C": False, "D": True}


def test_a_labelled_title_game_wins_over_the_guess(tmp_path):
    from cfp_rankings.clout import title_games

    games = [_raw("A", "B", 30, 20, "East"), _raw("C", "D", 7, 3, "East", notes="East Championship")]
    (tmp_path / "games").mkdir()
    (tmp_path / "games" / "2099.json").write_text(__import__("json").dumps(games))
    assert title_games(2099, 15, tmp_path) == {"C": True, "D": False}


def test_title_week_moves_compares_the_last_two_rankings():
    from dataclasses import replace

    from cfp_rankings.clout import title_week_moves

    before = [_row(2021, "Champ", 5, 5, 0.0, True, slot=14), _row(2021, "Loser", 3, 3, 0.0, True, slot=14)]
    after = [replace(_row(2021, "Champ", 2, 2, 0.0, True, slot=15), is_final=True, champion=True),
             replace(_row(2021, "Loser", 7, 7, 0.0, True, slot=15), is_final=True, runner_up=True)]
    moves = title_week_moves(before + after)
    assert moves["cfp"] == {"Won a title game": (3.0, 1), "Lost a title game": (-4.0, 1)}


# ---------- the acid test ----------
def test_pick_record_counts_each_game_once_from_the_better_ranked_side():
    from cfp_rankings.clout import Later, disagreements, pick_record

    high, low = _row(2021, "High", 3, 3, 0.0, True), _row(2021, "Low", 9, 9, 0.0, False)
    games = [Later(2021, high, low, False, True, 4.0, False), Later(2021, low, high, True, False, -4.0, False)]
    assert pick_record(games, "cfp") == (1, 1)
    assert pick_record(games, "cfp", only=lambda g: False) == (0, 0)
    assert disagreements(games) == (0, 0)  # committee and AP agree here


def test_market_rating_follows_the_spread_not_the_score():
    import datetime as dt

    from cfp_rankings.clout import market_ratings
    from cfp_rankings.snapshots import Game

    when = dt.datetime(2099, 9, 6, tzinfo=dt.timezone.utc)
    # The underdog won by 30, but the sportsbook had the home team favored by 14.
    game = Game(1, 2099, 1, when, "Favorite", "Underdog", 0, 30, True, True, True, spread_home=-14.0)
    ratings = market_ratings([game])
    assert ratings.of("Favorite") > ratings.of("Underdog")


def test_tv_table_separates_tv_from_league():
    # League is worth 4 spots and TV nothing, but power teams are on TV more, so TV alone looks good.
    import random

    from cfp_rankings.clout import known, tv_table

    rng = random.Random(1)
    rows = []
    for i in range(120):
        power = i % 2 == 0
        tv = rng.uniform(2, 8) if power else rng.uniform(0, 3)
        resume = rng.randint(5, 22)
        cfp = resume - (4 if power else 0)
        rows.append(Row(2014 + i % 5, 10, f"T{i}", cfp, cfp, resume, resume, resume, 0, 0.0, power, tv=tv))
    rows.append(Row(2014, 10, "No history", 9, 9, 9, 9, 9, 0, 0.0, False))  # a team with no TV score
    assert len(known(rows, "tv")) == 120
    table = tv_table(rows, "tv", lambda r: r.resume - r.cfp)
    assert table["alone"][0] > 0.3
    assert abs(table["league fixed"][0]) < 0.05
    assert table["league, measure fixed"][0] == pytest.approx(4, abs=0.2)
    assert "league and money fixed" not in table  # no finance data in these rows
