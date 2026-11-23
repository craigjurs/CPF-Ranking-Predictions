"""Does a famous name buy a better ranking?

Analogy: two gymnasts perform the same routine. If the famous one keeps
scoring a tenth higher, the judges are scoring the name. Here the routine is
what a team did on the field (the Stage 1 ratings, which see only scores and
schedules) and the judges' score is the CFP committee's ranking.

For every team in every committee ranking we compute a **gap**::

    gap = on-field rank - committee rank

A gap of +3 means the committee placed the team three spots higher than its
results justify. Then we ask whether *clout* explains the gap. This first
pass uses the two clout measures that need no new data:

* **brand**: how often the program finished in the final AP poll over the
  previous five seasons, from 0 to 1 (the same number Stage 2 uses).
* **power conference**: member of the ACC, Big 12, Big Ten, Pac-12 or SEC,
  or Notre Dame.

Three comparisons, decided before looking at any result:

1. Committee against the Stage 1 **résumé** rank (the main test), repeated
   with the **power** rank and a blend of the two as a cross-check.
2. The same test on the **AP poll** in the same weeks, to see whether the
   committee is more or less tilted than the voters.
3. Committee against AP directly, same team, same week. Both judged the same
   games, so on-field quality cancels out.

Only team-level numbers are used. The sealed 2024 and 2025 seasons are never
loaded.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cfp_rankings.power import POWER, RESUME, Ratings, fit_ratings, next_season_prior
from cfp_rankings.snapshots import FINAL_SLOT, RAW_DIR, Season

CAP = 26  # every team outside a top 25 is treated as "26th"
POWER_CONFERENCES = {"ACC", "Big 12", "Big Ten", "Pac-12", "SEC"}
CFP_SEASONS = tuple(y for y in range(2014, 2024) if y != 2020)


@dataclass(frozen=True)
class Row:
    """One team in one committee ranking week."""

    season: int
    slot: int
    team: str
    cfp: int  # committee rank, capped at 26
    ap: int  # AP rank the same week, capped at 26
    resume: int  # on-field ranks, capped at 26
    power: int
    blend: int
    losses: int
    brand: float
    power_conf: bool


def conferences(year: int, raw_dir: Path = RAW_DIR) -> dict[str, str]:
    """Each team's conference that season, read from the games file."""
    out: dict[str, str] = {}
    for g in json.loads((raw_dir / "games" / f"{year}.json").read_text()):
        for side in ("home", "away"):
            if g.get(f"{side}Conference"):
                out[g[f"{side}Team"]] = g[f"{side}Conference"]
    return out


def brand_scores(final_polls: dict[int, dict[str, int]], season: int) -> dict[str, float]:
    """0 to 1, from final AP polls of the five seasons before ``season``."""
    years = sorted(y for y in final_polls if y < season)[-5:]
    out: dict[str, float] = {}
    for y in years:
        for team, rank in final_polls[y].items():
            out[team] = out.get(team, 0.0) + (26 - min(rank, 26)) / 25 / len(years)
    return out


def _capped(rank_of: dict[str, int], team: str) -> int:
    return min(rank_of.get(team, CAP), CAP)


def week_rows(season: Season, slot: int, priors: dict[str, dict[str, float]], brand: dict[str, float],
              conf: dict[str, str]) -> list[Row]:
    """Rows for one committee ranking: every team in any of the top 25s."""
    cfp, ap = season.release("cfp", slot), season.release("ap", slot)
    if cfp is None or ap is None:
        return []
    games = season.games_known_at(slot)
    fbs = {g.home for g in games if g.home_fbs} | {g.away for g in games if g.away_fbs}
    resume = fit_ratings(games, priors["resume"], RESUME.cap, RESUME.shrink).ranks(fbs)
    power = fit_ratings(games, priors["power"], POWER.cap, POWER.shrink).ranks(fbs)
    blend_order = sorted(fbs, key=lambda t: (resume[t] + power[t], resume[t]))
    blend = {t: i + 1 for i, t in enumerate(blend_order)}
    losses: dict[str, int] = {}
    for g in games:
        if g.loser:
            losses[g.loser] = losses.get(g.loser, 0) + 1
    cfp_rank, ap_rank = cfp.rank_of(), ap.rank_of()
    teams = set(cfp_rank) | set(ap_rank) | {t for t in fbs if min(resume[t], power[t], blend[t]) <= 25}
    return [
        Row(season.year, slot, t, _capped(cfp_rank, t), _capped(ap_rank, t), _capped(resume, t), _capped(power, t),
            _capped(blend, t), losses.get(t, 0), brand.get(t, 0.0),
            conf.get(t) in POWER_CONFERENCES or t == "Notre Dame")
        for t in sorted(teams)
    ]


def build_rows(first_season: int = 2005, raw_dir: Path = RAW_DIR) -> list[Row]:
    """Walk the seasons in order so ratings and brand only ever look backwards."""
    rows: list[Row] = []
    final: dict[str, Ratings] = {}
    last_year = None
    final_polls: dict[int, dict[str, int]] = {}
    for year in [y for y in range(first_season, CFP_SEASONS[-1] + 1) if y != 2020]:
        season = Season.load(year, raw_dir)
        ago = year - last_year if last_year else 1
        priors = {
            "power": next_season_prior(final["power"], POWER, ago) if final else {},
            "resume": next_season_prior(final["resume"], RESUME, ago) if final else {},
        }
        if year in CFP_SEASONS:
            brand, conf = brand_scores(final_polls, year), conferences(year, raw_dir)
            for rel in season.releases("cfp"):
                rows += week_rows(season, rel.slot, priors, brand, conf)
        final = {
            "power": fit_ratings(season.games, priors["power"], POWER.cap, POWER.shrink),
            "resume": fit_ratings(season.games, priors["resume"], RESUME.cap, RESUME.shrink),
        }
        last_poll = season.release("ap", FINAL_SLOT)
        if last_poll:
            final_polls[year] = last_poll.rank_of()
        last_year = year
    return rows


# ---------- the statistics ----------
def _slopes(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(y)), X])
    return np.linalg.lstsq(design, y, rcond=None)[0][1:]


def effect(rows: list[Row], y, controls=(), draws: int = 2000, seed: int = 0) -> dict[str, tuple[float, float, float]]:
    """Slope of ``y`` on brand and power conference, with a 95% range.

    The same team appears week after week with nearly the same rank, so the
    rows are not independent. The range comes from a bootstrap that resamples
    whole team-seasons: draw team-seasons with replacement, refit, repeat.
    """
    names = ["brand", "power_conf", *controls]
    target = np.array([y(r) for r in rows], dtype=float)
    X = np.array([[float(getattr(r, n)) for n in names] for r in rows])
    point = _slopes(target, X)
    groups: dict[tuple[int, str], list[int]] = {}
    for i, r in enumerate(rows):
        groups.setdefault((r.season, r.team), []).append(i)
    members = [np.array(v) for v in groups.values()]
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(draws):
        pick = np.concatenate([members[i] for i in rng.integers(0, len(members), len(members))])
        samples.append(_slopes(target[pick], X[pick]))
    lo, hi = np.percentile(np.array(samples), [2.5, 97.5], axis=0)
    return {n: (float(point[i]), float(lo[i]), float(hi[i])) for i, n in enumerate(names)}


def team_seasons(rows: list[Row]) -> int:
    return len({(r.season, r.team) for r in rows})


TESTS = {
    "Committee vs résumé rank (main test)": (lambda r: r.resume - r.cfp, ()),
    "Committee vs power rank": (lambda r: r.power - r.cfp, ()),
    "Committee vs blend of the two": (lambda r: r.blend - r.cfp, ()),
    "Committee, same résumé, power and losses": (lambda r: -r.cfp, ("resume", "power", "losses")),
    "AP voters vs résumé rank": (lambda r: r.resume - r.ap, ()),
    "AP voters, same résumé, power and losses": (lambda r: -r.ap, ("resume", "power", "losses")),
    "Committee vs AP, same team and week": (lambda r: r.ap - r.cfp, ()),
}


def biggest_gaps(rows: list[Row], n: int = 8):
    """Team-seasons the committee ranked furthest above and below the résumé rank."""
    acc: dict[tuple[int, str], list[int]] = {}
    for r in rows:
        if r.cfp <= 25 or r.resume <= 25:
            acc.setdefault((r.season, r.team), []).append(r.resume - r.cfp)
    avg = sorted(((float(np.mean(v)), k) for k, v in acc.items() if len(v) >= 3), reverse=True)
    return avg[:n], avg[-n:][::-1]


def main() -> None:
    rows = build_rows()
    weeks = len({(r.season, r.slot) for r in rows})
    print(f"{weeks} committee rankings, {len(rows)} team-weeks, {team_seasons(rows)} team-seasons\n")
    print("Extra spots (positive = ranked higher than justified), with a 95% range")
    print(f"{'':44s} {'brand 0 to 1':>24s} {'power conference':>24s}")
    for name, (y, controls) in TESTS.items():
        e = effect(rows, y, controls)
        cells = [f"{e[k][0]:+5.2f} ({e[k][1]:+5.2f} to {e[k][2]:+5.2f})" for k in ("brand", "power_conf")]
        print(f"{name:44s} {cells[0]:>24s} {cells[1]:>24s}")
    over, under = biggest_gaps(rows)
    for title, group in (("Ranked furthest ABOVE their résumé", over), ("Ranked furthest BELOW their résumé", under)):
        print(f"\n{title} (season average, spots)")
        for gap, (year, team) in group:
            print(f"  {year} {team:20s} {gap:+5.1f}")


if __name__ == "__main__":
    main()
