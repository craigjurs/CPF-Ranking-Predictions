"""Pull the core CFBD data once and keep it on disk.

    uv run python -m cfp_rankings.pull --start 2000 --end 2025

Up to five files per season land in ``data/raw/<dataset>/<year>.json`` (gitignored):

    rankings   every weekly AP / Coaches / CFP poll
    games      every game involving an FBS team, regular season and postseason
    lines      sportsbook spreads, totals and moneylines (2013 onward only)
    calendar   the start and end date of each week
    media      which TV network showed each game, and the kickoff time

One more file has no season: ``data/raw/venues.json``, the stadium list with
capacities.

Analogy: this is the weekly grocery run. We buy a whole season in five trips,
put it in the pantry (``data/raw``), and cook from the pantry afterwards.
A file that is already in the pantry is never bought again, so re-running this
costs zero API calls. That matters: the free CFBD tier is ~1,000 calls a month.

A manifest (``data/raw/manifest.json``) records when each file was pulled.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
from pathlib import Path

from cfp_rankings.cfbd_tools import REPO_ROOT, cfbd_session

RAW_DIR = REPO_ROOT / "data" / "raw"

# dataset -> (MCP tool, extra arguments)
DATASETS: dict[str, tuple[str, dict]] = {
    "rankings": ("get_rankings", {"season_type": "both"}),
    "games": ("get_games", {"season_type": "both", "classification": "fbs"}),
    "lines": ("get_betting_lines", {"season_type": "both"}),
    "calendar": ("get_calendar", {}),
    "media": ("get_game_media", {"season_type": "both", "classification": "fbs", "media_type": "tv"}),
}

# Datasets with one file for all seasons: name -> MCP tool.
ONE_OFF: dict[str, str] = {"venues": "get_venues"}

# CFBD has no sportsbook lines before 2013 (checked: 2005 and 2012 come back
# empty), so we don't spend quota asking.
LINES_FIRST_SEASON = 2013
# Likewise there are no TV listings before 2003 (checked: 2000 to 2002 come back empty).
MEDIA_FIRST_SEASON = 2003


def datasets_for(year: int) -> list[str]:
    first = {"lines": LINES_FIRST_SEASON, "media": MEDIA_FIRST_SEASON}
    return [d for d in DATASETS if year >= first.get(d, 0)]


def raw_path(dataset: str, year: int | None, raw_dir: Path = RAW_DIR) -> Path:
    """Where a pull is kept. ``year`` is None for the one-off datasets."""
    return raw_dir / f"{dataset}.json" if year is None else raw_dir / dataset / f"{year}.json"


def plan(years: list[int], raw_dir: Path = RAW_DIR, refresh: bool = False) -> list[tuple[str, int | None]]:
    """The (dataset, year) pairs that still need an API call. Year is None for one-off datasets."""
    todo: list[tuple[str, int | None]] = [
        (dataset, year)
        for year in years
        for dataset in datasets_for(year)
        if refresh or not raw_path(dataset, year, raw_dir).exists()
    ]
    todo += [(d, None) for d in ONE_OFF if refresh or not raw_path(d, None, raw_dir).exists()]
    return todo


async def pull(years: list[int], raw_dir: Path = RAW_DIR, refresh: bool = False, max_calls: int = 150) -> int:
    todo = plan(years, raw_dir, refresh)
    if not todo:
        print("Everything is already cached. 0 API calls.")
        return 0
    if len(todo) > max_calls:
        raise SystemExit(f"{len(todo)} calls needed, above --max-calls {max_calls}. Pull fewer seasons at a time.")
    wanted = sum(len(datasets_for(y)) for y in years) + len(ONE_OFF)
    print(f"{len(todo)} API calls needed ({wanted - len(todo)} files already cached).")

    manifest_path = raw_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    async with cfbd_session() as call:
        for i, (dataset, year) in enumerate(todo, 1):
            if year is None:
                tool = ONE_OFF[dataset]
                payload = await call(tool)
            else:
                tool, extra = DATASETS[dataset]
                payload = await call(tool, year=year, **extra)
            path = raw_path(dataset, year, raw_dir)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload["data"]))
            manifest[dataset if year is None else f"{dataset}/{year}"] = {
                "pulled_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "tool": tool,
                "params": payload.get("params"),
                "rows": payload.get("count"),
            }
            manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))
            print(f"  [{i}/{len(todo)}] {dataset} {year or ''}: {payload.get('count')} rows")
            await asyncio.sleep(2.5)  # stay under the server's 30 calls/minute
    return len(todo)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--start", type=int, default=2000, help="first season")
    ap.add_argument("--end", type=int, default=2025, help="last completed season")
    ap.add_argument("--refresh", action="store_true", help="re-pull even if cached (costs quota)")
    ap.add_argument("--max-calls", type=int, default=150)
    ap.add_argument("--dry-run", action="store_true", help="only print how many calls would be made")
    args = ap.parse_args()
    years = list(range(args.start, args.end + 1))
    if args.dry_run:
        print(f"{len(plan(years, refresh=args.refresh))} API calls would be made.")
        return
    asyncio.run(pull(years, refresh=args.refresh, max_calls=args.max_calls))


if __name__ == "__main__":
    main()
