"""Pull the core CFBD data once and keep it on disk.

    uv run python -m cfp_rankings.pull --start 2014 --end 2025

Four files per season land in ``data/raw/<dataset>/<year>.json`` (gitignored):

    rankings   every weekly AP / Coaches / CFP poll
    games      every game involving an FBS team, regular season and postseason
    lines      sportsbook spreads, totals and moneylines for those games
    calendar   the start and end date of each week

Analogy: this is the weekly grocery run. We buy a whole season in four trips,
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
}


def raw_path(dataset: str, year: int, raw_dir: Path = RAW_DIR) -> Path:
    return raw_dir / dataset / f"{year}.json"


def plan(years: list[int], raw_dir: Path = RAW_DIR, refresh: bool = False) -> list[tuple[str, int]]:
    """The (dataset, year) pairs that still need an API call."""
    return [
        (dataset, year)
        for year in years
        for dataset in DATASETS
        if refresh or not raw_path(dataset, year, raw_dir).exists()
    ]


async def pull(years: list[int], raw_dir: Path = RAW_DIR, refresh: bool = False, max_calls: int = 150) -> int:
    todo = plan(years, raw_dir, refresh)
    if not todo:
        print("Everything is already cached. 0 API calls.")
        return 0
    if len(todo) > max_calls:
        raise SystemExit(f"{len(todo)} calls needed, above --max-calls {max_calls}. Pull fewer seasons at a time.")
    print(f"{len(todo)} API calls needed ({len(years) * len(DATASETS) - len(todo)} files already cached).")

    manifest_path = raw_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    async with cfbd_session() as call:
        for i, (dataset, year) in enumerate(todo, 1):
            tool, extra = DATASETS[dataset]
            payload = await call(tool, year=year, **extra)
            path = raw_path(dataset, year, raw_dir)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload["data"]))
            manifest[f"{dataset}/{year}"] = {
                "pulled_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "tool": tool,
                "params": payload.get("params"),
                "rows": payload.get("count"),
            }
            manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))
            print(f"  [{i}/{len(todo)}] {dataset} {year}: {payload.get('count')} rows")
            await asyncio.sleep(2.5)  # stay under the server's 30 calls/minute
    return len(todo)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--start", type=int, default=2014, help="first season (2014 = first CFP season)")
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
