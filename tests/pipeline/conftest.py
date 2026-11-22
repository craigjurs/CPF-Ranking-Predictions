"""A tiny made-up season, in CFBD's raw JSON shape. No network, no real data."""

import pytest

from cfp_rankings.snapshots import Season

TEAMS = [f"Team {i:02d}" for i in range(1, 31)]  # Team 01 is the best


def _game(gid, week, day, home, away, hp, ap_, season_type="regular"):
    return {
        "id": gid, "season": 2099, "week": week, "seasonType": season_type,
        "startDate": f"2099-09-{day:02d}T18:00:00.000Z", "completed": True, "neutralSite": False,
        "homeTeam": home, "awayTeam": away, "homePoints": hp, "awayPoints": ap_,
        "homeClassification": "fbs", "awayClassification": "fbs",
        "homePregameElo": 1500, "awayPregameElo": 1500, "homePostgameElo": 1510, "awayPostgameElo": 1490,
    }


def _poll(name, order):
    return {"poll": name, "ranks": [{"rank": i + 1, "school": t, "points": 100 - i, "firstPlaceVotes": 0}
                                    for i, t in enumerate(order)]}


@pytest.fixture
def season():
    top25 = TEAMS[:25]
    # Week 1: Team 03 (ranked 3) loses at home to unranked Team 26. Team 01 beats Team 02.
    games = [
        _game(1, 1, 6, "Team 03", "Team 26", 10, 20),
        _game(2, 1, 6, "Team 01", "Team 02", 30, 20),
        # Week 2 game: must be invisible to the week 2 poll.
        _game(3, 2, 13, "Team 01", "Team 05", 0, 50),
        # Labelled week 1 but actually played after week 2 began: must also be invisible.
        _game(4, 1, 9, "Team 04", "Team 27", 0, 50),
        _game(5, 1, 27, "Team 06", "Team 07", 7, 3, season_type="postseason"),
    ]
    lines = [{"id": 1, "lines": [{"provider": "a", "spread": -10, "spreadOpen": -9, "overUnder": 50},
                                 {"provider": "b", "spread": -12, "spreadOpen": None, "overUnder": 52}]}]
    week2 = [t for t in top25 if t != "Team 03"] + ["Team 26"]
    rankings = [
        {"season": 2099, "seasonType": "regular", "week": 1, "polls": [_poll("AP Top 25", top25), _poll("Coaches Poll", top25)]},
        {"season": 2099, "seasonType": "regular", "week": 2,
         "polls": [_poll("AP Top 25", week2), _poll("Coaches Poll", week2), _poll("Playoff Committee Rankings", week2),
                   _poll("FCS Coaches Poll", top25)]},
        {"season": 2099, "seasonType": "postseason", "week": 1,
         "polls": [_poll("AP Top 25", week2), _poll("Playoff Committee Rankings", week2)]},
    ]
    calendar = [
        {"seasonType": "regular", "week": 1, "startDate": "2099-09-01T07:00:00.000Z"},
        {"seasonType": "regular", "week": 2, "startDate": "2099-09-08T07:00:00.000Z"},
        {"seasonType": "postseason", "week": 1, "startDate": "2099-09-20T07:00:00.000Z"},
    ]
    return Season.from_raw(2099, games, lines, rankings, calendar)
