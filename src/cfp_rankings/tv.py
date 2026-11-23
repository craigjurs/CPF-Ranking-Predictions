"""TV exposure and fan-base size, measured from earlier seasons.

Two ingredients for the "clout" study (docs/research/money-and-politics-in-rankings.md):

* **TV exposure.** CFBD lists which network showed each game. We count, per
  team and season, how many regular-season games were on a channel the whole
  country gets, and how many of those were in primetime.
* **Fan base.** Average home attendance from the games data, and the capacity
  of the home stadium from the CFBD venue list.

Analogy: a restaurant's window table. Sitting there gets you noticed, but the
owner also seats the best-dressed guests there. Networks pick the games they
expect to be good, so a highly ranked team is on in primetime *because* it is
highly ranked. To keep cause and effect apart, every score here is built only
from seasons **before** the one being studied.

    uv run python -m cfp_rankings.tv --season 2023

Caveats, measured on the data:

* CFBD lists a network for roughly two games in three from 2012 on. The rest
  were streaming-only or regional. Before 2012 the listings are thin and
  uneven (176 of 792 games in 2007), and there are none before 2003. Counts
  are fair between teams in the same season, not between distant seasons.
* The venue list gives today's capacity, not the capacity in each past season.
* This is a count of TV slots, not of viewers.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from cfp_rankings.snapshots import RAW_DIR

FIRST_SEASON = 2003  # CFBD has no TV listings before this
EASTERN = ZoneInfo("America/New_York")
PRIMETIME_HOUR = 19  # 7 PM Eastern or later

# Free over-the-air networks. "ABCR" is CFBD's label for a regional ABC game.
BROADCAST = {"ABC", "ABCR", "CBS", "FOX", "NBC"}
# Cable channels nearly every cable home gets. Conference channels (BTN, SECN,
# ACCN, PAC12), ESPNU, CBSSN and the like are deliberately left out.
CABLE = {"ESPN", "ESPN2", "FS1"}
NATIONAL = BROADCAST | CABLE


@dataclass
class Exposure:
    """One team's regular-season TV slots in one season."""

    listed: int = 0     # games with any TV network listed
    national: int = 0   # games on a broadcast network or main cable channel
    broadcast: int = 0  # games on a free over-the-air network
    primetime: int = 0  # national games kicking off at 7 PM Eastern or later


def _load(kind: str, year: int, raw_dir: Path) -> list[dict]:
    path = raw_dir / kind / f"{year}.json"
    return json.loads(path.read_text()) if path.exists() else []


def fbs_teams(year: int, raw_dir: Path = RAW_DIR) -> set[str]:
    teams = set()
    for g in _load("games", year, raw_dir):
        for side in ("home", "away"):
            if g.get(f"{side}Classification") == "fbs":
                teams.add(g[f"{side}Team"])
    return teams


def _is_primetime(start: str) -> bool:
    when = dt.datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(EASTERN)
    return when.hour >= PRIMETIME_HOUR


def season_exposure(year: int, raw_dir: Path = RAW_DIR) -> dict[str, Exposure]:
    """TV slots for every FBS team in one season. Empty if there are no listings.

    A game listed on two channels counts once, on its widest-reaching channel.
    Bowls and playoff games are left out: getting into one is a reward for the
    ranking, which is the thing we are trying to explain.
    """
    games: dict[int, dict] = {}
    for row in _load("media", year, raw_dir):
        if row.get("seasonType") != "regular" or row.get("mediaType") != "tv":
            continue
        outlet = (row.get("outlet") or "").strip().upper()
        game = games.setdefault(row["id"], {"row": row, "outlets": set()})
        game["outlets"].add(outlet)
    if not games:
        return {}
    out = {team: Exposure() for team in fbs_teams(year, raw_dir)}
    for game in games.values():
        row, outlets = game["row"], game["outlets"]
        national = bool(outlets & NATIONAL)
        prime = national and not row.get("isStartTimeTBD") and _is_primetime(row["startTime"])
        for team in (row["homeTeam"], row["awayTeam"]):
            if team not in out:
                continue  # not an FBS team
            e = out[team]
            e.listed += 1
            e.national += national
            e.broadcast += bool(outlets & BROADCAST)
            e.primetime += prime
    return out


def tv_scores(season: int, raw_dir: Path = RAW_DIR, years: int = 3, field: str = "national") -> dict[str, float]:
    """Average TV slots per season over the ``years`` seasons before ``season``.

    In plain units: 6.0 means the team averaged six games a year on national
    TV. A team that was in FBS but never on national TV scores 0. Seasons
    with no listings at all are skipped rather than counted as zero.
    """
    seasons = [e for y in range(season - years, season) if (e := season_exposure(y, raw_dir))]
    if not seasons:
        return {}
    teams = fbs_teams(season, raw_dir) or set().union(*seasons)
    out = {}
    for team in teams:
        seen = [getattr(e[team], field) for e in seasons if team in e]
        if seen:  # a team new to FBS has no history, so it gets no score
            out[team] = sum(seen) / len(seen)
    return out


def capacities(raw_dir: Path = RAW_DIR) -> dict[int, int]:
    path = raw_dir / "venues.json"
    if not path.exists():
        return {}
    return {v["id"]: v["capacity"] for v in json.loads(path.read_text()) if v.get("capacity")}


def fan_base(season: int, raw_dir: Path = RAW_DIR, years: int = 3) -> dict[str, dict[str, float]]:
    """Home crowd size from the ``years`` seasons before ``season``.

    ``attendance`` is the average announced crowd at true home games.
    ``capacity`` is the size of the stadium the team used most. 2020 is
    skipped because crowds were restricted.
    """
    cap = capacities(raw_dir)
    crowds: dict[str, list[int]] = {}
    venues: dict[str, Counter] = {}
    for year in range(season - years, season):
        if year == 2020:
            continue
        for g in _load("games", year, raw_dir):
            if g.get("neutralSite") or g.get("homeClassification") != "fbs" or g.get("seasonType") != "regular":
                continue
            team = g["homeTeam"]
            if g.get("attendance"):
                crowds.setdefault(team, []).append(g["attendance"])
            if g.get("venueId"):
                venues.setdefault(team, Counter())[g["venueId"]] += 1
    out: dict[str, dict[str, float]] = {}
    for team in set(crowds) | set(venues):
        row: dict[str, float] = {}
        if crowds.get(team):
            row["attendance"] = sum(crowds[team]) / len(crowds[team])
        home = venues[team].most_common(1)[0][0] if team in venues else None
        if home in cap:
            row["capacity"] = cap[home]
        if row:
            out[team] = row
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Show the TV and fan-base scores going into one season.")
    ap.add_argument("--season", type=int, default=2023)
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()
    national = tv_scores(args.season)
    prime = tv_scores(args.season, field="primetime")
    broadcast = tv_scores(args.season, field="broadcast")
    fans = fan_base(args.season)
    print(f"Going into {args.season}: yearly average over the three seasons before it ({len(national)} teams)\n")
    print("| team | national TV games | on free broadcast | national primetime | home crowd | stadium |")
    print("|---|---|---|---|---|---|")
    ranked = sorted(national, key=lambda t: (-national[t], -prime.get(t, 0), t))
    for team in ranked[: args.top] + ranked[-5:]:
        f = fans.get(team, {})
        print(f"| {team} | {national[team]:.1f} | {broadcast.get(team, 0):.1f} | {prime.get(team, 0):.1f} "
              f"| {f.get('attendance', float('nan')):,.0f} | {f.get('capacity', float('nan')):,.0f} |")


if __name__ == "__main__":
    main()
