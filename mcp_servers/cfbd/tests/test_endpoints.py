import pytest

from cfbd_mcp.endpoints import ParamError, build_query


def test_maps_args_to_api_names():
    path, q = build_query("rankings", {"year": 2024, "week": 5, "season_type": "regular"})
    assert path == "/rankings"
    assert q == {"year": 2024, "week": 5, "seasonType": "regular"}


@pytest.mark.parametrize(
    "name,args",
    [
        ("admin", {"year": 2024}),                       # not on the menu
        ("games", {"year": 2024, "url": "http://evil"}),  # unknown param
        ("games", {"week": 3}),                           # missing year
        ("games", {"year": 1500}),                        # out of range
        ("games", {"year": 2024, "week": 99}),
        ("games", {"year": 2024, "team": "../../etc/passwd"}),
        ("games", {"year": 2024, "team": "Ohio State\nAuthorization: x"}),
        ("games", {"year": 2024, "season_type": "spring"}),
    ],
)
def test_rejects_off_menu_requests(name, args):
    with pytest.raises(ParamError):
        build_query(name, args)


def test_allows_real_team_names():
    _, q = build_query("games", {"year": 2024, "team": "Texas A&M"})
    assert q["team"] == "Texas A&M"


def test_player_stats_is_on_the_menu_with_fixed_options():
    path, q = build_query("game_player_stats", {"year": 2024, "week": 7, "conference": "SEC"})
    assert path == "/games/players"
    assert q == {"year": 2024, "week": 7, "conference": "SEC"}
    with pytest.raises(ParamError):
        build_query("game_player_stats", {"year": 2024, "player": "someone"})


def test_game_media_is_on_the_menu_with_fixed_options():
    path, q = build_query("game_media", {"year": 2023, "season_type": "both", "media_type": "TV", "classification": "fbs"})
    assert path == "/games/media"
    assert q == {"year": 2023, "seasonType": "both", "mediaType": "tv", "classification": "fbs"}
    with pytest.raises(ParamError):
        build_query("game_media", {"year": 2023, "media_type": "carrier pigeon"})
    with pytest.raises(ParamError):
        build_query("game_media", {"week": 3})  # year is still required


def test_venues_takes_no_options():
    assert build_query("venues", {}) == ("/venues", {})
    with pytest.raises(ParamError):
        build_query("venues", {"url": "http://evil"})
