import asyncio
import json

import httpx
import respx

from cfbd_mcp import server
from cfbd_mcp.endpoints import BASE_URL

EXPECTED = {
    "get_games", "get_rankings", "get_betting_lines", "get_team_records", "get_fbs_teams",
    "get_calendar", "get_sp_ratings", "get_srs_ratings", "get_elo_ratings", "get_game_player_stats",
    "get_game_media", "get_venues",
}


def test_only_read_only_menu_tools_exposed():
    tools = asyncio.run(server.mcp.list_tools())
    assert {t.name for t in tools} == EXPECTED
    for t in tools:
        assert t.annotations.read_only_hint is True
        assert "key" not in json.dumps(t.input_schema).lower()


@respx.mock
def test_tool_call_returns_data_without_key(fake_key):
    server._client = None
    respx.get(f"{BASE_URL}/rankings").mock(return_value=httpx.Response(200, json=[{"season": 2024}]))
    result = asyncio.run(server.mcp.call_tool("get_rankings", {"year": 2024, "week": 3}))
    text = result.model_dump_json()
    assert "2024" in text
    assert fake_key not in text


def test_errors_are_friendly_and_clean(fake_key):
    server._client = None
    out = server._call("games", year=2024, team="bad;name")
    assert "error" in out and fake_key not in out["error"]


@respx.mock
def test_player_stats_needs_a_narrowing_filter(fake_key):
    server._client = None
    route = respx.get(f"{BASE_URL}/games/players").mock(return_value=httpx.Response(200, json=[{"id": 1}]))
    out = server.get_game_player_stats(year=2024)
    assert "error" in out and not route.called
    out = server.get_game_player_stats(year=2024, week=3, team="Texas A&M")
    assert "error" not in out and route.called
    assert dict(route.calls.last.request.url.params) == {"year": "2024", "week": "3", "team": "Texas A&M"}
