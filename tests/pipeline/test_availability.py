"""Availability flags: the box-score slimmer, the flags, and the no-leak rules."""

import math

from cfp_rankings.availability import Availability, season_flags
from cfp_rankings.features import AVAILABILITY_FEATURES, FEATURES, History, build_rows
from cfp_rankings.poll_model import PollRanker
from cfp_rankings.pull_players import STATS, plan, slim, week_path
from cfp_rankings.snapshots import Season


def _row(**stats):
    return [float(stats.get(s, 0)) for s in STATS]


def _box(game_id, team, **players):
    return {"game_id": game_id, "team": team, "players": {pid[1:]: row for pid, row in players.items()}}


QB1, QB2 = _row(pass_att=30, pass_yds=250), _row(pass_att=28, pass_yds=200)
RB1, WR1, LB1, K1 = _row(carries=20, rush_yds=100), _row(catches=8, rec_yds=90), _row(tackles=10), _row(kicks=5)


def test_slim_drops_names_and_keeps_counts():
    raw = [{"id": 7, "teams": [{"team": "A", "categories": [
        {"name": "passing", "types": [
            {"name": "C/ATT", "athletes": [{"id": "11", "name": "Somebody Famous", "stat": "28/51"}]},
            {"name": "YDS", "athletes": [{"id": "11", "name": "Somebody Famous", "stat": "295"}]}]},
        {"name": "punting", "types": [{"name": "NO", "athletes": [{"id": "12", "name": "A Punter", "stat": "3"}]}]},
        {"name": "rushing", "types": [{"name": "CAR", "athletes": [{"id": "-7", "name": " Team", "stat": "2"}]}]},
    ]}]}]
    out = slim(raw)
    assert out == [{"game_id": 7, "team": "A", "players": {"11": _row(pass_att=51, pass_yds=295), "12": _row()}}]
    assert "Famous" not in str(out) and "Punter" not in str(out)


def test_cached_weeks_are_never_fetched_again(tmp_path):
    (tmp_path / "calendar").mkdir()
    (tmp_path / "calendar" / "2099.json").write_text(
        '[{"seasonType": "regular", "week": 1}, {"seasonType": "postseason", "week": 1}]')
    assert plan([2099], tmp_path) == [(2099, "regular", 1), (2099, "postseason", 1)]
    path = week_path(2099, "regular", 1, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("[]")
    assert plan([2099], tmp_path) == [(2099, "postseason", 1)]


def test_first_game_has_no_flags_and_a_full_lineup_raises_none():
    boxes = [_box(g, "A", p1=QB1, p2=RB1, p3=WR1, p4=LB1, p5=K1) for g in (1, 2)]
    flags = season_flags(boxes, {1: 0, 2: 1})
    assert all(math.isnan(getattr(flags[(1, "A")], f)) for f in AVAILABILITY_FEATURES[:7])
    assert flags[(2, "A")] == Availability(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def test_each_flag_fires_for_its_own_absence():
    full = dict(p1=QB1, p2=RB1, p3=WR1, p4=LB1, p5=K1)

    def week2(**lineup):
        return season_flags([_box(1, "A", **full), _box(2, "A", **lineup)], {1: 0, 2: 1})[(2, "A")]

    backup_qb = week2(p9=QB2, p2=RB1, p3=WR1, p4=LB1, p5=K1)
    assert backup_qb.qb_changed == 1 and backup_qb.top_rb_missing == 0
    # The passer's 250 of 440 offensive yards are gone; no tackles are. Average of 0.568 and 0.
    assert abs(backup_qb.production_missing_pct - (250 / 440) / 2) < 1e-9

    assert week2(p1=QB1, p8=_row(carries=5), p3=WR1, p4=LB1, p5=K1).top_rb_missing == 1
    assert week2(p1=QB1, p2=RB1, p8=_row(catches=2), p4=LB1, p5=K1).top_wr_missing == 1
    assert week2(p1=QB1, p2=RB1, p3=WR1, p8=_row(tackles=4), p5=K1).top_tackler_missing == 1
    assert week2(p1=QB1, p2=RB1, p3=WR1, p4=LB1, p8=_row(kicks=3)).kicker_changed == 1

    hurt_early = week2(p1=_row(pass_att=5), p9=QB2, p2=RB1, p3=WR1, p4=LB1, p5=K1)
    assert hurt_early.usage_drop == 1 and hurt_early.qb_changed == 1


def test_a_missing_part_of_the_box_score_is_blank_not_a_flag():
    # No defensive stats were recorded in game 2: we cannot say the tackler was out.
    flags = season_flags([_box(1, "A", p1=QB1, p2=RB1, p4=LB1), _box(2, "A", p1=QB1, p2=RB1)], {1: 0, 2: 1})[(2, "A")]
    assert math.isnan(flags.top_tackler_missing) and flags.qb_changed == 0


def test_flags_only_use_earlier_games():
    # Game 3 has a new passer. Game 2's flags must be the same with or without game 3.
    boxes = [_box(1, "A", p1=QB1, p2=RB1), _box(2, "A", p1=QB1, p2=RB1), _box(3, "A", p9=QB2, p2=RB1)]
    order = {1: 0, 2: 1, 3: 2}
    assert repr(season_flags(boxes, order)[(2, "A")]) == repr(season_flags(boxes[:2], order)[(2, "A")])
    assert season_flags(boxes, order)[(3, "A")].qb_changed == 1


def test_flags_ride_along_with_the_game_through_snapshots(season):
    # Rebuild the fixture season with box scores: Team 01 changes passer in its
    # week 2 game (id 3). Week 1 game (id 2) is its first, so it has no flags.
    raw = [{"id": g.id, "season": 2099, "week": g.slot if g.slot < 100 else 1,
            "seasonType": "regular" if g.slot < 100 else "postseason",
            "startDate": g.start.isoformat(), "completed": True, "neutralSite": g.neutral,
            "homeTeam": g.home, "awayTeam": g.away, "homePoints": g.home_points, "awayPoints": g.away_points,
            "homeClassification": "fbs", "awayClassification": "fbs"} for g in season.games]
    boxes = [_box(2, "Team 01", p1=QB1, p2=RB1), _box(3, "Team 01", p9=QB2, p2=RB1)]
    rankings = [{"season": 2099, "seasonType": "regular", "week": w,
                 "polls": [{"poll": "AP Top 25", "ranks": [{"rank": r.rank, "school": r.team} for r in p.ranks]}]}
                for w, p in ((1, season.release("ap", 1)), (2, season.release("ap", 2)), (3, season.release("ap", 2)))]
    calendar = [{"seasonType": "regular", "week": w, "startDate": f"2099-09-{d:02d}T07:00:00.000Z"}
                for w, d in ((1, 1), (2, 8), (3, 15))]
    s = Season.from_raw(2099, raw, [], rankings, calendar, boxes)

    week2 = s.snapshot("ap", 2)
    assert all(g.id != 3 for g in week2.games)  # the game with the change is not visible yet
    teams, X = build_rows(week2, History(), availability=True)
    assert X.shape[1] == len(FEATURES) + len(AVAILABILITY_FEATURES)
    row = dict(zip(FEATURES + AVAILABILITY_FEATURES, X[teams.index("Team 01")]))
    assert math.isnan(row["qb_changed"])  # first game: nothing to compare with

    teams, X = build_rows(s.snapshot("ap", 3), History(), availability=True)
    row = dict(zip(FEATURES + AVAILABILITY_FEATURES, X[teams.index("Team 01")]))
    assert row["qb_changed"] == 1
    opp = dict(zip(FEATURES + AVAILABILITY_FEATURES, X[teams.index("Team 05")]))
    assert opp["opp_qb_changed"] == 1 and math.isnan(opp["qb_changed"])  # Team 05 has no box score


def test_model_trains_with_and_without_the_flags(season):
    from cfp_rankings.backtest import examples

    for availability in (False, True):
        model = PollRanker(trees=5, availability=availability)
        model.fit(examples(season, "ap"))
        assert len(model.predict(season.snapshot("ap", 2))) == 25
        assert len(model.importance()) == len(FEATURES) + (len(AVAILABILITY_FEATURES) if availability else 0)
