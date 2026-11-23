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
