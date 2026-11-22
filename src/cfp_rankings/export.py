"""Write the tidy, time-stamped tables to ``data/processed/`` (gitignored).

    uv run python -m cfp_rankings.export

Two CSVs you can open in a spreadsheet. Every row carries a ``known_from_slot``
column: the first poll release that was allowed to see it. A snapshot is then
just a filter, ``known_from_slot <= the poll I am predicting``.

Analogy: every newspaper in the archive gets a "printed on" stamp. Building a
snapshot never changes the papers; it only decides which ones you may read.

Costs zero API calls. It only reads ``data/raw``.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from cfp_rankings.snapshots import FINAL_SLOT, RAW_DIR, Season, load_seasons

OUT_DIR = RAW_DIR.parent / "processed"


def known_from_slot(season: Season, game) -> int:
    """First release slot whose snapshot contains this game."""
    slots = sorted({p.slot for p in season.polls} | {FINAL_SLOT})
    for slot in slots:
        if slot == FINAL_SLOT:
            return slot
        cutoff = season.week_starts.get(slot)
        if game.slot < slot and (cutoff is None or game.start < cutoff):
            return slot
    return FINAL_SLOT


def export(seasons: dict[int, Season], out_dir: Path = OUT_DIR) -> tuple[int, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    n_games = n_ranks = 0
    with open(out_dir / "games.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["season", "week_slot", "known_from_slot", "kickoff_utc", "home", "away", "home_points",
                    "away_points", "neutral", "home_fbs", "away_fbs", "spread_home", "spread_open_home",
                    "over_under", "home_elo_pre", "away_elo_pre"])
        for s in seasons.values():
            for g in s.games:
                w.writerow([g.season, g.slot, known_from_slot(s, g), g.start.isoformat(), g.home, g.away,
                            g.home_points, g.away_points, int(g.neutral), int(g.home_fbs), int(g.away_fbs),
                            g.spread_home, g.spread_open_home, g.over_under, g.home_elo_pre, g.away_elo_pre])
                n_games += 1
    with open(out_dir / "polls.csv", "w", newline="") as f:
        w = csv.writer(f)
        # A poll release is visible to later slots. AP and Coaches are also
        # visible to the same-week CFP ranking (Sunday comes before Tuesday).
        w.writerow(["season", "poll", "slot", "rank", "team", "points", "first_place_votes"])
        for s in seasons.values():
            for p in s.polls:
                for r in p.ranks:
                    w.writerow([p.season, p.poll, p.slot, r.rank, r.team, r.points, r.first_place_votes])
                    n_ranks += 1
    return n_games, n_ranks


def main() -> None:
    ap = argparse.ArgumentParser(description="Export tidy point-in-time tables.")
    ap.add_argument("--start", type=int, default=2014)
    ap.add_argument("--end", type=int, default=2025)
    args = ap.parse_args()
    n_games, n_ranks = export(load_seasons(range(args.start, args.end + 1)))
    print(f"Wrote {n_games} games and {n_ranks} poll rows to {OUT_DIR}")


if __name__ == "__main__":
    main()
