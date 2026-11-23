"""MCP server exposing narrow, read-only CFBD tools.

The agent calls these tools and gets JSON data back. It never receives,
handles, or can request the API key. Every tool is a fixed menu item
(see endpoints.py); there is no generic "fetch any URL" tool on purpose.
"""

from __future__ import annotations

import logging
import sys
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from cfbd_mcp.client import CFBDClient, CFBDError
from cfbd_mcp.endpoints import ParamError
from cfbd_mcp.redact import RedactingFilter, scrub
from cfbd_mcp.secrets import SecretError

# stdio servers must keep stdout clean for the protocol: log to stderr only,
# and scrub every record.
_handler = logging.StreamHandler(sys.stderr)
_handler.addFilter(RedactingFilter())
_handler.setFormatter(logging.Formatter("%(asctime)s cfbd-mcp %(levelname)s %(message)s"))
logging.getLogger("cfbd_mcp").addHandler(_handler)
logging.getLogger("cfbd_mcp").setLevel(logging.INFO)
# httpx logs full URLs at INFO; keep it quiet.
logging.getLogger("httpx").setLevel(logging.WARNING)

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)
SeasonType = Literal["regular", "postseason", "both"]

mcp = MCPServer(
    name="cfbd",
    instructions=(
        "Read-only access to CollegeFootballData (games, polls, betting lines, ratings, TV listings, venues). "
        "Authentication is handled inside the server; never ask for or try to obtain an API key."
    ),
)
_client: CFBDClient | None = None


def _get_client() -> CFBDClient:
    global _client
    if _client is None:
        _client = CFBDClient()
    return _client


def _call(endpoint: str, **args) -> dict:
    try:
        return _get_client().fetch(endpoint, args)
    except (ParamError, CFBDError, SecretError) as exc:
        return {"error": scrub(str(exc))}
    except Exception as exc:  # never let a raw traceback (with locals) escape
        logging.getLogger("cfbd_mcp").exception("unexpected error")
        return {"error": scrub(f"Internal error: {type(exc).__name__}")}


@mcp.tool(annotations=READ_ONLY)
def get_games(
    year: int,
    week: int | None = None,
    season_type: SeasonType | None = None,
    team: str | None = None,
    conference: str | None = None,
    classification: Literal["fbs", "fcs", "ii", "iii"] | None = None,
) -> dict:
    """Game results and schedules for a season. Narrow with week, team, or conference."""
    return _call("games", year=year, week=week, season_type=season_type, team=team,
                 conference=conference, classification=classification)


@mcp.tool(annotations=READ_ONLY)
def get_rankings(year: int, week: int | None = None, season_type: SeasonType | None = None) -> dict:
    """Weekly poll rankings (AP Top 25, Coaches Poll, CFP rankings) for a season."""
    return _call("rankings", year=year, week=week, season_type=season_type)


@mcp.tool(annotations=READ_ONLY)
def get_betting_lines(
    year: int,
    week: int | None = None,
    season_type: SeasonType | None = None,
    team: str | None = None,
    conference: str | None = None,
) -> dict:
    """Sportsbook spreads, totals and moneylines for games."""
    return _call("lines", year=year, week=week, season_type=season_type, team=team, conference=conference)


@mcp.tool(annotations=READ_ONLY)
def get_team_records(year: int, team: str | None = None, conference: str | None = None) -> dict:
    """Win/loss records by team for a season."""
    return _call("records", year=year, team=team, conference=conference)


@mcp.tool(annotations=READ_ONLY)
def get_fbs_teams(year: int) -> dict:
    """List of FBS teams for a season."""
    return _call("fbs_teams", year=year)


@mcp.tool(annotations=READ_ONLY)
def get_calendar(year: int) -> dict:
    """Week start and end dates for a season."""
    return _call("calendar", year=year)


@mcp.tool(annotations=READ_ONLY)
def get_sp_ratings(year: int, team: str | None = None) -> dict:
    """SP+ efficiency ratings."""
    return _call("sp_ratings", year=year, team=team)


@mcp.tool(annotations=READ_ONLY)
def get_srs_ratings(year: int, team: str | None = None, conference: str | None = None) -> dict:
    """Simple Rating System (SRS) ratings."""
    return _call("srs_ratings", year=year, team=team, conference=conference)


@mcp.tool(annotations=READ_ONLY)
def get_elo_ratings(
    year: int,
    week: int | None = None,
    season_type: SeasonType | None = None,
    team: str | None = None,
    conference: str | None = None,
) -> dict:
    """Elo ratings, optionally as of a given week."""
    return _call("elo_ratings", year=year, week=week, season_type=season_type, team=team, conference=conference)


@mcp.tool(annotations=READ_ONLY)
def get_game_player_stats(
    year: int,
    week: int | None = None,
    season_type: SeasonType | None = None,
    team: str | None = None,
    conference: str | None = None,
) -> dict:
    """Per-game player box scores. Needs year plus at least one of week, team, or conference.

    Use it for team-level features only (for example "did the leading passer change").
    Keep raw pulls in data/raw/ and never commit player-level rows.
    """
    if week is None and team is None and conference is None:
        return {"error": "Give at least one of week, team, or conference to keep the pull small."}
    return _call("game_player_stats", year=year, week=week, season_type=season_type, team=team,
                 conference=conference)


@mcp.tool(annotations=READ_ONLY)
def get_game_media(
    year: int,
    week: int | None = None,
    season_type: SeasonType | None = None,
    team: str | None = None,
    conference: str | None = None,
    media_type: Literal["tv", "radio", "web", "ppv", "mobile"] | None = None,
    classification: Literal["fbs", "fcs", "ii", "iii"] | None = None,
) -> dict:
    """Which network or outlet carried each game, with the kickoff time."""
    return _call("game_media", year=year, week=week, season_type=season_type, team=team,
                 conference=conference, media_type=media_type, classification=classification)


@mcp.tool(annotations=READ_ONLY)
def get_venues() -> dict:
    """Stadiums with their capacity and location. Takes no options."""
    return _call("venues")


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
