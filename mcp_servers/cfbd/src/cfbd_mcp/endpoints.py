"""The allowlist: the only CFBD requests this server will ever make.

Analogy: a restaurant with a fixed menu. The agent can order any dish on the
menu, with the listed options, but cannot walk into the kitchen and ask the
chef to cook something else, or send the delivery driver to a new address.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from typing import Callable

BASE_URL = "https://api.collegefootballdata.com"
ALLOWED_HOST = "api.collegefootballdata.com"

SEASON_TYPES = {"regular", "postseason", "both"}
CLASSIFICATIONS = {"fbs", "fcs", "ii", "iii"}
MEDIA_TYPES = {"tv", "radio", "web", "ppv", "mobile"}
_NAME = re.compile(r"^[A-Za-z0-9 &.'()\-]{1,60}$")


class ParamError(ValueError):
    pass


def _year(v) -> int:
    v = int(v)
    if not 1869 <= v <= _dt.date.today().year + 1:
        raise ParamError("year is out of range")
    return v


def _week(v) -> int:
    v = int(v)
    if not 1 <= v <= 20:
        raise ParamError("week must be between 1 and 20")
    return v


def _season_type(v) -> str:
    v = str(v).lower()
    if v not in SEASON_TYPES:
        raise ParamError(f"season_type must be one of {sorted(SEASON_TYPES)}")
    return v


def _classification(v) -> str:
    v = str(v).lower()
    if v not in CLASSIFICATIONS:
        raise ParamError(f"classification must be one of {sorted(CLASSIFICATIONS)}")
    return v


def _media_type(v) -> str:
    v = str(v).lower()
    if v not in MEDIA_TYPES:
        raise ParamError(f"media_type must be one of {sorted(MEDIA_TYPES)}")
    return v


def _name(v) -> str:
    v = str(v).strip()
    if not _NAME.match(v):
        raise ParamError("team/conference names may only use letters, digits, spaces and & . ' ( ) -")
    return v


@dataclass(frozen=True)
class Endpoint:
    path: str
    # tool argument name -> (CFBD query parameter name, validator)
    params: dict[str, tuple[str, Callable]]
    required: tuple[str, ...] = ("year",)


ENDPOINTS: dict[str, Endpoint] = {
    "games": Endpoint(
        "/games",
        {
            "year": ("year", _year),
            "week": ("week", _week),
            "season_type": ("seasonType", _season_type),
            "team": ("team", _name),
            "conference": ("conference", _name),
            "classification": ("classification", _classification),
        },
    ),
    "rankings": Endpoint(
        "/rankings",
        {"year": ("year", _year), "week": ("week", _week), "season_type": ("seasonType", _season_type)},
    ),
    "lines": Endpoint(
        "/lines",
        {
            "year": ("year", _year),
            "week": ("week", _week),
            "season_type": ("seasonType", _season_type),
            "team": ("team", _name),
            "conference": ("conference", _name),
        },
    ),
    "records": Endpoint(
        "/records",
        {"year": ("year", _year), "team": ("team", _name), "conference": ("conference", _name)},
    ),
    "fbs_teams": Endpoint("/teams/fbs", {"year": ("year", _year)}),
    "calendar": Endpoint("/calendar", {"year": ("year", _year)}),
    "sp_ratings": Endpoint("/ratings/sp", {"year": ("year", _year), "team": ("team", _name)}),
    "srs_ratings": Endpoint(
        "/ratings/srs",
        {"year": ("year", _year), "team": ("team", _name), "conference": ("conference", _name)},
    ),
    "elo_ratings": Endpoint(
        "/ratings/elo",
        {
            "year": ("year", _year),
            "week": ("week", _week),
            "season_type": ("seasonType", _season_type),
            "team": ("team", _name),
            "conference": ("conference", _name),
        },
    ),
    # Which network showed each game, and when it kicked off. Team-level only.
    "game_media": Endpoint(
        "/games/media",
        {
            "year": ("year", _year),
            "week": ("week", _week),
            "season_type": ("seasonType", _season_type),
            "team": ("team", _name),
            "conference": ("conference", _name),
            "media_type": ("mediaType", _media_type),
            "classification": ("classification", _classification),
        },
    ),
    # Stadiums and their capacity. CFBD takes no options for this one.
    "venues": Endpoint("/venues", {}, required=()),
    "game_player_stats": Endpoint(
        "/games/players",
        {
            "year": ("year", _year),
            "week": ("week", _week),
            "season_type": ("seasonType", _season_type),
            "team": ("team", _name),
            "conference": ("conference", _name),
        },
    ),
}


def build_query(name: str, args: dict) -> tuple[str, dict]:
    """Validate tool arguments against the allowlist and return (path, query)."""
    if name not in ENDPOINTS:
        raise ParamError(f"'{name}' is not an allowed endpoint")
    ep = ENDPOINTS[name]
    unknown = set(k for k, v in args.items() if v is not None) - set(ep.params)
    if unknown:
        raise ParamError(f"unsupported parameters for {name}: {sorted(unknown)}")
    for req in ep.required:
        if args.get(req) is None:
            raise ParamError(f"'{req}' is required for {name}")
    query = {}
    for arg, value in args.items():
        if value is None:
            continue
        api_name, validate = ep.params[arg]
        try:
            query[api_name] = validate(value)
        except (TypeError, ValueError) as exc:
            raise ParamError(f"invalid {arg}: {exc}") from None
    return ep.path, query
