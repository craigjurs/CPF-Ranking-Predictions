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

Two follow-ups build on that:

* **The acid test.** A gap alone is not bias, because the judges may see
  real quality the scores miss. So we watch what teams did *after* each
  ranking, and add a fourth measuring stick: a rating built from sportsbook
  point spreads, which is the best outside opinion of how strong a team is.
* **Conference championships.** Title games are played the week before the
  final ranking. We measure how much winning one moves a team, beyond the
  win itself, and use it as a control.

Only team-level numbers are used. The sealed 2024 and 2025 seasons are never
loaded.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from cfp_rankings.finance import money_scores
from cfp_rankings.tv import fan_base, tv_scores
from cfp_rankings.power import POWER, RESUME, Ratings, fit_ratings, next_season_prior
from cfp_rankings.snapshots import FINAL_SLOT, RAW_DIR, Game, Season

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
    market: int = CAP  # rank by a rating built from sportsbook spreads, capped at 26
    is_final: bool = False  # the last ranking, made after the conference title games
    champion: bool = False  # won a conference title game (final ranking only)
    runner_up: bool = False  # lost a conference title game (final ranking only)
    money: float = float("nan")  # athletic revenue in doublings above the average team; nan if unknown
    # The next three are yearly averages over the three seasons before this one; nan if unknown.
    tv: float = float("nan")  # games on free broadcast TV (ABC, CBS, FOX, NBC)
    tv_national: float = float("nan")  # games on broadcast or main cable (adds ESPN, ESPN2, FS1)
    crowd: float = float("nan")  # average home crowd, in units of 10,000 fans
    tie: bool = False  # a committee member is recused from this school this season
    league_ties: int = 0  # committee members recused from OTHER schools in this team's conference


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


TIES_FILE = Path(__file__).with_name("committee_ties.json")


def committee_ties(season: int, path: Path = TIES_FILE) -> dict[str, int]:
    """Schools with a recused committee member that season -> how many members.

    A member is recused from a school that pays them or employs close family.
    They may not vote on that team and must leave the room when it is
    discussed, so this measures a friend on the committee, not a vote.
    """
    return json.loads(path.read_text()).get(str(season), {})


def league_tie_counts(ties: dict[str, int], conf: dict[str, str]) -> dict[str, int]:
    """For each team, members recused from other schools in its conference.

    Those members *can* vote on this team, and what is good for the league
    is good for their own school. Independents have no league, so they get 0.
    """
    seats: dict[str, int] = {}
    for school, n in ties.items():
        league = conf.get(school)
        if league and league != "FBS Independents":
            seats[league] = seats.get(league, 0) + n
    return {team: seats[league] - ties.get(team, 0) for team, league in conf.items() if league in seats}


def title_games(year: int, title_slot: int, raw_dir: Path = RAW_DIR) -> dict[str, bool]:
    """Teams that played a conference title game: True for the winner.

    CFBD labels these games in a notes field only in recent seasons, so the
    rule is: in the week before the final ranking, a conference's title game
    is its only game between two of its own members. If a made-up regular
    game shares the week, the title game is the one on a neutral field.
    Conferences with no title game that year (the Big 12 before 2017, for
    example) correctly produce nothing.
    """
    by_conf: dict[str, list[dict]] = {}
    for g in json.loads((raw_dir / "games" / f"{year}.json").read_text()):
        same = g.get("homeConference") and g.get("homeConference") == g.get("awayConference")
        if (g["seasonType"] == "regular" and g["week"] == title_slot and same and g.get("completed")
                and g.get("homeClassification") == "fbs" and g.get("homePoints") is not None):
            by_conf.setdefault(g["homeConference"], []).append(g)
    out: dict[str, bool] = {}
    for games in by_conf.values():
        labelled = [g for g in games if "championship" in (g.get("notes") or "").lower()]
        neutral = [g for g in games if g.get("neutralSite")]
        pick = labelled if len(labelled) == 1 else games if len(games) == 1 else neutral if len(neutral) == 1 else []
        for g in pick:
            home_won = g["homePoints"] > g["awayPoints"]
            out[g["homeTeam"]], out[g["awayTeam"]] = home_won, not home_won
    return out


def market_ratings(games) -> Ratings:
    """A rating built from point spreads instead of scores.

    Each spread is the sportsbook's forecast of the margin, so fitting the
    Stage 1 maths to spreads gives the betting market's opinion of every
    team's strength. Only spreads of games already played are used.
    """
    as_scores = [replace(g, home_points=-g.spread_home, away_points=0) for g in games if g.spread_home is not None]
    return fit_ratings(as_scores, {}, POWER.cap, POWER.shrink)


def _capped(rank_of: dict[str, int], team: str) -> int:
    return min(rank_of.get(team, CAP), CAP)


def is_power(conf: dict[str, str], team: str) -> bool:
    return conf.get(team) in POWER_CONFERENCES or team == "Notre Dame"


def week_rows(season: Season, slot: int, priors: dict[str, dict[str, float]], brand: dict[str, float],
              conf: dict[str, str], titles: dict[str, bool] | None = None,
              money: dict[str, float] | None = None,
              extra: dict[str, dict[str, float]] | None = None) -> list[Row]:
    # ``titles`` is passed only for the final ranking, the one made after the title games.
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
    market = market_ratings(games).ranks(fbs)
    is_final, titles, money = titles is not None, titles or {}, money or {}
    nan = float("nan")
    tv, tv_national, crowd, ties, league_ties = (
        (extra or {}).get(k, {}) for k in ("tv", "tv_national", "crowd", "tie", "league_ties"))
    losses: dict[str, int] = {}
    for g in games:
        if g.loser:
            losses[g.loser] = losses.get(g.loser, 0) + 1
    cfp_rank, ap_rank = cfp.rank_of(), ap.rank_of()
    teams = set(cfp_rank) | set(ap_rank) | {t for t in fbs if min(resume[t], power[t], blend[t]) <= 25}
    return [
        Row(season.year, slot, t, _capped(cfp_rank, t), _capped(ap_rank, t), _capped(resume, t), _capped(power, t),
            _capped(blend, t), losses.get(t, 0), brand.get(t, 0.0), is_power(conf, t), _capped(market, t),
            is_final, titles.get(t) is True, titles.get(t) is False, money.get(t, nan),
            tv.get(t, nan), tv_national.get(t, nan), crowd.get(t, nan),
            ties.get(t, 0) > 0, int(league_ties.get(t, 0)))
        for t in sorted(teams)
    ]


@dataclass(frozen=True)
class Later:
    """One game played after a ranking came out, seen from one team's side."""

    season: int
    team: Row  # the team's row in the latest ranking before the game
    opponent: Row | None  # None when the opponent was outside every top 25
    opp_power_conf: bool
    won: bool
    beat_spread_by: float | None  # final margin minus the sportsbook's forecast
    bowl: bool


@dataclass(frozen=True)
class Study:
    rows: list[Row]
    later: list[Later]


def later_games(season: Season, rows: list[Row], conf: dict[str, str]) -> list[Later]:
    """Every game played after a ranking, tied to the latest ranking before it."""
    slots = sorted({r.slot for r in rows})
    lookup = {(r.slot, r.team): r for r in rows}
    out: list[Later] = []
    for g in season.games:
        known = [s for s in slots if s <= g.slot]
        if not known or g.winner is None or not (g.home_fbs and g.away_fbs):
            continue
        slot = known[-1]
        margin = g.home_points - g.away_points
        for team, opp, sign in ((g.home, g.away, 1), (g.away, g.home, -1)):
            row = lookup.get((slot, team))
            if row is None:
                continue
            beat = None if g.spread_home is None else sign * (margin + g.spread_home)
            out.append(Later(season.year, row, lookup.get((slot, opp)), is_power(conf, opp), sign * margin > 0, beat,
                             g.slot == FINAL_SLOT))
    return out


def build(first_season: int = 2005, raw_dir: Path = RAW_DIR) -> Study:
    """Walk the seasons in order so ratings and brand only ever look backwards."""
    rows: list[Row] = []
    later: list[Later] = []
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
            slots = [rel.slot for rel in season.releases("cfp")]
            money = money_scores(year, raw_dir) if (raw_dir / "eada").exists() else {}
            extra = {
                "tv": tv_scores(year, raw_dir, field="broadcast"),
                "tv_national": tv_scores(year, raw_dir, field="national"),
                "crowd": {t: f["attendance"] / 10_000 for t, f in fan_base(year, raw_dir).items() if "attendance" in f},
            }
            ties = committee_ties(year)
            extra["tie"] = ties
            extra["league_ties"] = league_tie_counts(ties, conf)
            season_rows: list[Row] = []
            for slot in slots:
                titles = title_games(year, slot - 1, raw_dir) if slot == max(slots) else None
                season_rows += week_rows(season, slot, priors, brand, conf, titles, money, extra)
            rows += season_rows
            later += later_games(season, season_rows, conf)
        final = {
            "power": fit_ratings(season.games, priors["power"], POWER.cap, POWER.shrink),
            "resume": fit_ratings(season.games, priors["resume"], RESUME.cap, RESUME.shrink),
        }
        last_poll = season.release("ap", FINAL_SLOT)
        if last_poll:
            final_polls[year] = last_poll.rank_of()
        last_year = year
    return Study(rows, later)


def build_rows(first_season: int = 2005, raw_dir: Path = RAW_DIR) -> list[Row]:
    return build(first_season, raw_dir).rows


# ---------- the statistics ----------
def _slopes(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(y)), X])
    return np.linalg.lstsq(design, y, rcond=None)[0][1:]


def _team_season_groups(keys) -> list[np.ndarray]:
    groups: dict[tuple[int, str], list[int]] = {}
    for i, key in enumerate(keys):
        groups.setdefault(key, []).append(i)
    return [np.array(v) for v in groups.values()]


def effect(rows: list[Row], y, controls=(), factors=("brand", "power_conf"), draws: int = 2000,
           seed: int = 0) -> dict[str, tuple[float, float, float]]:
    """Slope of ``y`` on each factor, holding the controls fixed, with a 95% range.

    The same team appears week after week with nearly the same rank, so the
    rows are not independent. The range comes from a bootstrap that resamples
    whole team-seasons: draw team-seasons with replacement, refit, repeat.
    """
    names = [*factors, *controls]
    target = np.array([y(r) for r in rows], dtype=float)
    X = np.array([[float(getattr(r, n)) for n in names] for r in rows])
    point = _slopes(target, X)
    members = _team_season_groups((r.season, r.team) for r in rows)
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(draws):
        pick = np.concatenate([members[i] for i in rng.integers(0, len(members), len(members))])
        samples.append(_slopes(target[pick], X[pick]))
    lo, hi = np.percentile(np.array(samples), [2.5, 97.5], axis=0)
    return {n: (float(point[i]), float(lo[i]), float(hi[i])) for i, n in enumerate(names)}


def average(values, keys, draws: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """A plain average with a 95% range, resampling whole team-seasons."""
    v = np.array(list(values), dtype=float)
    members = _team_season_groups(keys)
    rng = np.random.default_rng(seed)
    means = [v[np.concatenate([members[i] for i in rng.integers(0, len(members), len(members))])].mean()
             for _ in range(draws)]
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(v.mean()), float(lo), float(hi)


def team_seasons(rows: list[Row]) -> int:
    return len({(r.season, r.team) for r in rows})


SAME_FIELD = ("resume", "power", "losses")
TESTS = {
    "Committee vs résumé rank (main test)": (lambda r: r.resume - r.cfp, ()),
    "Committee vs power rank": (lambda r: r.power - r.cfp, ()),
    "Committee vs blend of the two": (lambda r: r.blend - r.cfp, ()),
    "Committee vs betting-market rank": (lambda r: r.market - r.cfp, ()),
    "Committee, same résumé, power and losses": (lambda r: -r.cfp, SAME_FIELD),
    "  ... and same title-game result": (lambda r: -r.cfp, (*SAME_FIELD, "champion", "runner_up")),
    "AP voters vs résumé rank": (lambda r: r.resume - r.ap, ()),
    "AP voters vs betting-market rank": (lambda r: r.market - r.ap, ()),
    "AP voters, same résumé, power and losses": (lambda r: -r.ap, SAME_FIELD),
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


# ---------- the acid test: what happened next ----------
RANKINGS = {"Committee": "cfp", "AP voters": "ap", "Résumé rank": "resume", "Power rank": "power",
            "Betting-market rank": "market"}


def pick_record(later: list[Later], attr: str, only=lambda g: True) -> tuple[int, int]:
    """(right, total) when the better-ranked team is picked to win.

    Each game is counted once, from the side of the team ranked better. Games
    where the two teams are level (both outside the top 25) are skipped.
    """
    right = total = 0
    for g in later:
        mine = getattr(g.team, attr)
        theirs = getattr(g.opponent, attr) if g.opponent else CAP
        if mine < theirs and only(g):
            right, total = right + g.won, total + 1
    return right, total


def disagreements(later: list[Later], only=lambda g: True) -> tuple[int, int]:
    """Games where the committee and AP voters ordered the two teams differently.

    Returns (times the committee's pick won, games).
    """
    right = total = 0
    for g in later:
        if g.opponent is None or not only(g):
            continue
        if g.team.cfp < g.opponent.cfp and g.team.ap > g.opponent.ap:
            right, total = right + g.won, total + 1
    return right, total


def cross_league(g: Later) -> bool:
    return g.team.power_conf != g.opp_power_conf


def underdog_league(later: list[Later], ranked_only: bool = True) -> list[Later]:
    """Games where a non-power-conference team from the sample met a power-conference team."""
    return [g for g in later if not g.team.power_conf and g.opp_power_conf
            and (not ranked_only or g.team.cfp <= 25 or g.team.ap <= 25)]


# ---------- conference championships ----------
def title_week_moves(rows: list[Row]) -> dict[str, dict[str, tuple[float, int]]]:
    """Average spots gained from the second-to-last ranking to the final one."""
    by_season: dict[int, list[Row]] = {}
    for r in rows:
        by_season.setdefault(r.season, []).append(r)
    moves: dict[str, dict[str, list[int]]] = {"cfp": {}, "ap": {}}
    for season_rows in by_season.values():
        slots = sorted({r.slot for r in season_rows})
        before = {r.team: r for r in season_rows if r.slot == slots[-2]}
        for r in (r for r in season_rows if r.slot == slots[-1]):
            group = "Won a title game" if r.champion else "Lost a title game" if r.runner_up else "Did not play"
            for poll in moves:
                was = getattr(before[r.team], poll) if r.team in before else CAP
                if was <= 25:  # only teams that were ranked going in
                    moves[poll].setdefault(group, []).append(was - getattr(r, poll))
    return {poll: {k: (float(np.mean(v)), len(v)) for k, v in groups.items()} for poll, groups in moves.items()}


# ---------- money against league ----------
MONEY_TESTS = {
    "Committee vs AP, same team and week": (lambda r: r.ap - r.cfp, ()),
    "Committee vs résumé rank": (lambda r: r.resume - r.cfp, ()),
    "Committee, same résumé, power and losses": (lambda r: -r.cfp, SAME_FIELD),
}


def with_money(rows: list[Row]) -> list[Row]:
    return [r for r in rows if r.money == r.money]  # drops nan


def known(rows: list[Row], *fields: str) -> list[Row]:
    """Rows where every named field has a value."""
    return [r for r in rows if all(getattr(r, f) == getattr(r, f) for f in fields)]


TV_TESTS = {**MONEY_TESTS, "AP voters vs résumé rank": (lambda r: r.resume - r.ap, ())}
TV_MEASURES = {
    "tv": "per extra free-broadcast game a year",
    "tv_national": "per extra national TV game a year",
    "crowd": "per extra 10,000 fans at home games",
}


def tv_table(rows: list[Row], measure: str, y, controls=()) -> dict[str, tuple[float, float, float]]:
    """One clout measure on its own, then against league, then against league and money."""
    have = known(rows, measure)
    joint = effect(have, y, controls, factors=(measure, "power_conf", "brand"))
    funded = known(have, "money")
    out = {
        "alone": effect(have, y, controls, factors=(measure,))[measure],
        "league fixed": joint[measure],
        "league, measure fixed": joint["power_conf"],
        "inside power conferences": effect([r for r in have if r.power_conf], y, controls, factors=(measure, "brand"))[measure],
    }
    if funded:
        out["league and money fixed"] = effect(funded, y, controls, factors=(measure, "power_conf", "money", "brand"))[measure]
    return out


def tie_tables(rows: list[Row], y, controls=()) -> dict[str, tuple[float, float, float]]:
    """A friend on the committee, and league-mates on it, with league held fixed."""
    e = effect(rows, y, controls, factors=("tie", "league_ties", "power_conf", "brand"))
    power = [r for r in rows if r.power_conf]
    inside = effect(power, y, controls, factors=("tie", "league_ties", "brand"))
    return {
        "own school has a member": e["tie"],
        "per league-mate on the committee": e["league_ties"],
        "league, ties held fixed": e["power_conf"],
        "own school, power conferences only": inside["tie"],
        "per league-mate, power conferences only": inside["league_ties"],
    }


def same_school_change(rows: list[Row], y) -> tuple[float, float, float, int]:
    """Schools seen both with and without a member: their gap with, minus without.

    The cleanest comparison available, because the school stays the same and
    only the seat on the committee changes. Returns the average change with a
    95% range (resampling schools) and the number of schools.
    """
    by: dict[str, dict[bool, dict[int, list[float]]]] = {}
    for r in rows:
        by.setdefault(r.team, {True: {}, False: {}})[r.tie].setdefault(r.season, []).append(y(r))
    diffs = []
    for groups in by.values():
        if groups[True] and groups[False]:
            season_mean = {flag: np.mean([np.mean(v) for v in groups[flag].values()]) for flag in (True, False)}
            diffs.append(season_mean[True] - season_mean[False])
    d = np.array(diffs)
    rng = np.random.default_rng(0)
    means = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(d.mean()), float(lo), float(hi), len(d)


def border_zone(rows: list[Row]) -> tuple[float, float, list[Row]]:
    """The money range where both kinds of school exist.

    From the poorest power-conference team to the richest team outside the
    power conferences. Inside it, league differs while money is about equal.
    """
    known = with_money(rows)
    low = min(r.money for r in known if r.power_conf)
    high = max(r.money for r in known if not r.power_conf)
    return low, high, [r for r in known if low <= r.money <= high]


def _fmt(e: tuple[float, float, float]) -> str:
    return f"{e[0]:+5.2f} ({e[1]:+5.2f} to {e[2]:+5.2f})"


def main() -> None:
    study = build()
    rows, later = study.rows, study.later
    weeks = len({(r.season, r.slot) for r in rows})
    print(f"{weeks} committee rankings, {len(rows)} team-weeks, {team_seasons(rows)} team-seasons\n")
    print("Extra spots (positive = ranked higher than justified), with a 95% range")
    print(f"{'':44s} {'brand 0 to 1':>24s} {'power conference':>24s}")
    for name, (y, controls) in TESTS.items():
        e = effect(rows, y, controls)
        print(f"{name:44s} {_fmt(e['brand']):>24s} {_fmt(e['power_conf']):>24s}")
    over, under = biggest_gaps(rows)
    for title, group in (("Ranked furthest ABOVE their résumé", over), ("Ranked furthest BELOW their résumé", under)):
        print(f"\n{title} (season average, spots)")
        for gap, (year, team) in group:
            print(f"  {year} {team:20s} {gap:+5.1f}")

    print("\nACID TEST: games played after each ranking")
    print(f"{'Picking the better-ranked team to win':40s} {'all games':>16s} {'cross-league games':>20s}")
    for name, attr in RANKINGS.items():
        a, b = pick_record(later, attr), pick_record(later, attr, cross_league)
        print(f"  {name:38s} {a[0]:4d}/{a[1]:<4d} {a[0] / a[1]:5.1%} {b[0]:6d}/{b[1]:<4d} {b[0] / b[1]:5.1%}")
    d, dx = disagreements(later), disagreements(later, cross_league)
    print(f"  When committee and AP disagree, the committee's pick won {d[0]} of {d[1]} (cross-league: {dx[0]} of {dx[1]})")
    for label, games in (("Ranked small-league teams vs power-conference teams", underdog_league(later)),
                         ("  ... bowls only", [g for g in underdog_league(later) if g.bowl])):
        lined = [g for g in games if g.beat_spread_by is not None]
        ats = average((g.beat_spread_by for g in lined), ((g.season, g.team.team) for g in lined))
        covered = sum(g.beat_spread_by > 0 for g in lined)
        print(f"  {label}: won {sum(g.won for g in games)} of {len(games)}, beat the spread in {covered} of "
              f"{len(lined)}, by {_fmt(ats)} points on average")

    games = underdog_league(later)
    upsets = [g for g in games if g.opponent is not None and g.opponent.cfp < g.team.cfp]
    print(f"  ... when the committee ranked the power-conference team higher: small-league team won "
          f"{sum(g.won for g in upsets)} of {len(upsets)}")

    print("\nCONFERENCE CHAMPIONSHIPS (final rankings only)")
    final = [r for r in rows if r.is_final]
    print(f"  {len(final)} team rows, {sum(r.champion for r in final)} title-game winners, "
          f"{sum(r.runner_up for r in final)} losers in the sample")
    for poll, groups in title_week_moves(rows).items():
        text = ", ".join(f"{k} {v[0]:+.1f} (n={v[1]})" for k, v in sorted(groups.items()))
        print(f"  Spots gained in the final {poll.upper()} ranking: {text}")
    for name, y in (("Committee", lambda r: -r.cfp), ("AP voters", lambda r: -r.ap)):
        e = effect(final, y, SAME_FIELD, factors=("champion", "runner_up", "power_conf", "brand"))
        print(f"  {name}, same résumé, power and losses: champion {_fmt(e['champion'])}, "
              f"runner-up {_fmt(e['runner_up'])}, power conference {_fmt(e['power_conf'])}")
    e = effect(final, lambda r: r.ap - r.cfp, factors=("champion", "runner_up", "power_conf", "brand"))
    print(f"  Committee vs AP: champion {_fmt(e['champion'])}, power conference {_fmt(e['power_conf'])}")

    print("\nTV AND CROWDS AGAINST LEAGUE (scores from the three seasons before each one)")
    by = {(r.season, r.team): r for r in known(rows, "tv", "crowd")}
    for label, flag in (("power conference", True), ("others", False)):
        group = [r for r in by.values() if r.power_conf == flag]
        print(f"  Typical {label} team: {np.median([r.tv for r in group]):.1f} broadcast games, "
              f"{np.median([r.tv_national for r in group]):.1f} national games, "
              f"{np.median([r.crowd for r in group]) * 10_000:,.0f} fans (n={len(group)})")
    for measure, unit in TV_MEASURES.items():
        print(f"  Extra spots {unit}, with a 95% range ({team_seasons(known(rows, measure))} team-seasons)")
        for name, (y, controls) in TV_TESTS.items():
            print(f"    {name}")
            for label, e in tv_table(rows, measure, y, controls).items():
                print(f"      {label:26s} {_fmt(e)}")

    print("\nCOMMITTEE TIES")
    tied = {(r.season, r.team) for r in rows if r.tie}
    print(f"  {len(tied)} of {team_seasons(rows)} team-seasons had a recused member. League-mates on the committee: "
          f"power conference median {np.median([r.league_ties for r in rows if r.power_conf]):.0f}, "
          f"others {np.median([r.league_ties for r in rows if not r.power_conf]):.0f}")
    for name, (y, controls) in TV_TESTS.items():
        print(f"    {name}")
        for label, e in tie_tables(rows, y, controls).items():
            print(f"      {label:40s} {_fmt(e)}")
    for name, y in (("Committee vs AP", lambda r: r.ap - r.cfp), ("Committee vs résumé rank", lambda r: r.resume - r.cfp),
                    ("AP voters vs résumé rank", lambda r: r.resume - r.ap)):
        m, lo, hi, n = same_school_change(rows, y)
        print(f"  Same school, with a member minus without ({n} schools), {name}: {_fmt((m, lo, hi))}")

    known_money = with_money(rows)
    if not known_money:
        print("\nMONEY: no EADA files found. Run: uv run --extra finance python -m cfp_rankings.finance")
        return
    by_team = {(r.season, r.team): r for r in known_money}
    rich = [r.money for r in by_team.values() if r.power_conf]
    poor = [r.money for r in by_team.values() if not r.power_conf]
    print(f"\nMONEY AGAINST LEAGUE ({team_seasons(known_money)} team-seasons with finance data)")
    print(f"  Typical athletic revenue against the average team: power conference x{2 ** np.median(rich):.2f}, "
          f"others x{2 ** np.median(poor):.2f}")
    print("  Extra spots per doubling of revenue, and for league, with a 95% range")
    for name, (y, controls) in MONEY_TESTS.items():
        alone = effect(known_money, y, controls, factors=("money",))["money"]
        joint = effect(known_money, y, controls, factors=("money", "power_conf", "brand"))
        inside = {label: effect([r for r in known_money if r.power_conf == flag], y, controls, factors=("money", "brand"))["money"]
                  for label, flag in (("power", True), ("other", False))}
        print(f"  {name}")
        print(f"    money on its own               {_fmt(alone)}")
        print(f"    money, league held fixed       {_fmt(joint['money'])}")
        print(f"    league, money held fixed       {_fmt(joint['power_conf'])}")
        print(f"    money inside power conferences {_fmt(inside['power'])}")
        print(f"    money inside other leagues     {_fmt(inside['other'])}")
    low, high, zone = border_zone(rows)
    # With so few teams in the zone there is nothing to test, so only the count is reported.
    print(f"  Border zone (revenue x{2 ** low:.2f} to x{2 ** high:.2f} of average): "
          f"{team_seasons([r for r in zone if r.power_conf])} power-conference and "
          f"{team_seasons([r for r in zone if not r.power_conf])} other team-seasons")


if __name__ == "__main__":
    main()
