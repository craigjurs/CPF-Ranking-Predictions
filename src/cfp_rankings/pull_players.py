"""Pull per-game player box scores, one week at a time, and keep a slim copy.

    uv run python -m cfp_rankings.pull_players --start 2013 --end 2023

One API call per week of a season, about 16 a season. Files land in
``data/raw/player_stats/<year>/<season type>-<week>.json`` (gitignored). A week
that is already on disk is never asked for again.

Analogy: the box score is the **attendance sheet** for a game. We only need to
know *which seat was filled and how much work that seat did*, not who sat in
it. So before anything touches the disk, this module throws away every player
name and keeps only CFBD's numeric athlete id and a handful of counting stats.
The id is needed to tell "the same passer as last week" from "a different
passer", and for nothing else.

What is kept, per team and game, for each athlete id::

    [pass attempts, pass yards, carries, rush yards, catches, receiving yards,
     tackles, kicks attempted (field goals + extra points)]

An athlete who appears in any box score category at all (punting, returns,
fumbles and so on) gets a row, even if it is all zeros. That is what "he
played" means here.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
from pathlib import Path

from cfp_rankings.cfbd_tools import cfbd_session
from cfp_rankings.pull import RAW_DIR

DATASET = "player_stats"
STATS = ("pass_att", "pass_yds", "carries", "rush_yds", "catches", "rec_yds", "tackles", "kicks")

# (box score category, stat type) -> what to add it to. "a/b" stats use b.
_SOURCES = {
    ("passing", "C/ATT"): ("pass_att", "attempts"),
    ("passing", "YDS"): ("pass_yds", "number"),
    ("rushing", "CAR"): ("carries", "number"),
    ("rushing", "YDS"): ("rush_yds", "number"),
    ("receiving", "REC"): ("catches", "number"),
    ("receiving", "YDS"): ("rec_yds", "number"),
    ("defensive", "TOT"): ("tackles", "number"),
    ("kicking", "FG"): ("kicks", "attempts"),
    ("kicking", "XP"): ("kicks", "attempts"),
}


def _number(text, kind: str) -> float:
    try:
        if kind == "attempts":  # "28/51" -> 51
            return float(str(text).split("/")[1])
        return float(text)
    except (IndexError, TypeError, ValueError):
        return 0.0


def slim(raw_games: list[dict]) -> list[dict]:
    """Reduce CFBD's response to ids and counting stats. Names never survive this."""
    out = []
    for game in raw_games:
        for team in game.get("teams") or []:
            players: dict[str, list[float]] = {}
            for category in team.get("categories") or []:
                for stat_type in category.get("types") or []:
                    target = _SOURCES.get((category.get("name"), stat_type.get("name")))
                    for athlete in stat_type.get("athletes") or []:
                        pid = str(athlete.get("id") or "")
                        # CFBD files whole-unit lines ("Team") under negative ids.
                        if not pid or pid.startswith("-"):
                            continue
                        row = players.setdefault(pid, [0.0] * len(STATS))
                        if target:
                            row[STATS.index(target[0])] += _number(athlete.get("stat"), target[1])
            out.append({"game_id": game.get("id"), "team": team.get("team"), "players": players})
    return out


def weeks_of(year: int, raw_dir: Path = RAW_DIR) -> list[tuple[str, int]]:
    """(season type, week) pairs of a season, from the cached calendar."""
    calendar = json.loads((raw_dir / "calendar" / f"{year}.json").read_text())
    return [(c["seasonType"], c["week"]) for c in calendar if c["seasonType"] in ("regular", "postseason")]


def week_path(year: int, season_type: str, week: int, raw_dir: Path = RAW_DIR) -> Path:
    return raw_dir / DATASET / str(year) / f"{season_type}-{week}.json"


def plan(years: list[int], raw_dir: Path = RAW_DIR) -> list[tuple[int, str, int]]:
    """The (year, season type, week) triples that still need an API call."""
    return [
        (year, season_type, week)
        for year in years
        for season_type, week in weeks_of(year, raw_dir)
        if not week_path(year, season_type, week, raw_dir).exists()
    ]


async def pull(years: list[int], raw_dir: Path = RAW_DIR, max_calls: int = 190) -> int:
    todo = plan(years, raw_dir)
    if not todo:
        print("Everything is already cached. 0 API calls.")
        return 0
    if len(todo) > max_calls:
        raise SystemExit(f"{len(todo)} calls needed, above --max-calls {max_calls}. The server allows 200 a day; "
                         "pull fewer seasons at a time.")
    print(f"{len(todo)} API calls needed.")
    manifest_path = raw_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    async with cfbd_session() as call:
        for i, (year, season_type, week) in enumerate(todo, 1):
            payload = await call("get_game_player_stats", year=year, week=week, season_type=season_type)
            rows = slim(payload["data"])
            path = week_path(year, season_type, week, raw_dir)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(rows, separators=(",", ":")))
            manifest[f"{DATASET}/{year}/{season_type}-{week}"] = {
                "pulled_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "tool": "get_game_player_stats",
                "params": payload.get("params"),
                "rows": payload.get("count"),
            }
            manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))
            print(f"  [{i}/{len(todo)}] {year} {season_type} week {week}: {payload.get('count')} games", flush=True)
            await asyncio.sleep(2.5)  # stay under the server's 30 calls/minute
    return len(todo)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--start", type=int, default=2013, help="first season")
    ap.add_argument("--end", type=int, default=2023, help="last season")
    ap.add_argument("--skip", type=int, nargs="*", default=[2020], help="seasons to leave out")
    ap.add_argument("--max-calls", type=int, default=190)
    ap.add_argument("--dry-run", action="store_true", help="only print how many calls would be made")
    args = ap.parse_args()
    years = [y for y in range(args.start, args.end + 1) if y not in args.skip]
    if args.dry_run:
        print(f"{len(plan(years))} API calls would be made.")
        return
    asyncio.run(pull(years, max_calls=args.max_calls))


if __name__ == "__main__":
    main()
