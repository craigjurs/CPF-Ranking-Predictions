"""TV exposure and fan-base scores."""

import json

from cfp_rankings.tv import fan_base, season_exposure, tv_scores


def _game(gid, home, away, **extra):
    row = {"id": gid, "seasonType": "regular", "homeTeam": home, "awayTeam": away,
           "homeClassification": "fbs", "awayClassification": "fbs", "neutralSite": False}
    row.update(extra)
    return row


def _listing(gid, home, away, outlet, start="2021-09-04T16:00:00.000Z", **extra):
    row = {"id": gid, "seasonType": "regular", "mediaType": "tv", "homeTeam": home, "awayTeam": away,
           "outlet": outlet, "startTime": start, "isStartTimeTBD": False}
    row.update(extra)
    return row


def _write(raw_dir, kind, year, rows):
    (raw_dir / kind).mkdir(exist_ok=True)
    (raw_dir / kind / f"{year}.json").write_text(json.dumps(rows))


def test_counts_national_broadcast_and_primetime_slots(tmp_path):
    _write(tmp_path, "games", 2021, [_game(1, "Big", "Small"), _game(2, "Big", "Other"), _game(3, "Small", "Other")])
    _write(tmp_path, "media", 2021, [
        _listing(1, "Big", "Small", "ABC", start="2021-09-04T23:30:00.000Z"),  # 7:30 PM Eastern
        _listing(2, "Big", "Other", "ESPN", start="2021-09-11T16:00:00.000Z"),  # noon Eastern
        _listing(3, "Small", "Other", "SECN", start="2021-09-18T23:30:00.000Z"),  # conference channel
    ])
    e = season_exposure(2021, tmp_path)
    assert (e["Big"].listed, e["Big"].national, e["Big"].broadcast, e["Big"].primetime) == (2, 2, 1, 1)
    assert (e["Small"].listed, e["Small"].national, e["Small"].primetime) == (2, 1, 1)
    assert (e["Other"].national, e["Other"].broadcast, e["Other"].primetime) == (1, 0, 0)


def test_a_game_on_two_channels_counts_once_and_bowls_are_left_out(tmp_path):
    _write(tmp_path, "games", 2021, [_game(1, "Big", "Small")])
    _write(tmp_path, "media", 2021, [
        _listing(1, "Big", "Small", "ESPNU"),
        _listing(1, "Big", "Small", "abc "),
        _listing(9, "Big", "Small", "ESPN", seasonType="postseason"),
    ])
    e = season_exposure(2021, tmp_path)["Big"]
    assert (e.listed, e.national, e.broadcast) == (1, 1, 1)


def test_primetime_follows_eastern_clock_after_daylight_saving_ends(tmp_path):
    _write(tmp_path, "games", 2021, [_game(1, "Big", "Small"), _game(2, "Big", "Other")])
    _write(tmp_path, "media", 2021, [
        _listing(1, "Big", "Small", "FOX", start="2021-11-20T23:30:00.000Z"),  # 6:30 PM Eastern in November
        _listing(2, "Big", "Other", "FOX", start="2021-11-28T00:00:00.000Z"),  # 7 PM Eastern
    ])
    assert season_exposure(2021, tmp_path)["Big"].primetime == 1


def test_scores_use_only_earlier_seasons(tmp_path):
    for year, outlet in ((2020, "ABC"), (2021, "ABC"), (2022, "SECN"), (2023, "ABC")):
        _write(tmp_path, "games", year, [_game(year, "Big", "Small")])
        _write(tmp_path, "media", year, [_listing(year, "Big", "Small", outlet)])
    scores = tv_scores(2023, tmp_path)  # looks at 2020, 2021 and 2022, never 2023
    assert scores == {"Big": 2 / 3, "Small": 2 / 3}
    changed = [_listing(2023, "Big", "Small", "SECN")]
    _write(tmp_path, "media", 2023, changed)
    assert tv_scores(2023, tmp_path) == scores


def test_seasons_without_listings_are_skipped_and_new_teams_get_no_score(tmp_path):
    _write(tmp_path, "games", 2021, [_game(1, "Big", "Small")])
    _write(tmp_path, "games", 2022, [_game(2, "Big", "Small")])
    _write(tmp_path, "media", 2022, [_listing(2, "Big", "Small", "CBS")])
    _write(tmp_path, "games", 2023, [_game(3, "Big", "Newcomer")])
    assert tv_scores(2023, tmp_path) == {"Big": 1.0}
    assert tv_scores(2021, tmp_path) == {}


def test_fan_base_uses_true_home_games_and_the_usual_stadium(tmp_path):
    (tmp_path / "venues.json").write_text(json.dumps([{"id": 7, "capacity": 80000}, {"id": 8, "capacity": 20000}]))
    _write(tmp_path, "games", 2022, [
        _game(1, "Big", "Small", attendance=70000, venueId=7),
        _game(2, "Big", "Other", attendance=60000, venueId=7),
        _game(3, "Big", "Other", attendance=90000, venueId=8, neutralSite=True),
        _game(4, "Small", "Big", attendance=None, venueId=8),
    ])
    fans = fan_base(2023, tmp_path)
    assert fans["Big"] == {"attendance": 65000, "capacity": 80000}
    assert fans["Small"] == {"capacity": 20000}
