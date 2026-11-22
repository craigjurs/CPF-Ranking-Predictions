"""Stage 1: a power rating learned from game results alone.

Analogy: a blind taste test. Cover the jerseys, hide the logos and the poll
numbers, and judge every team only by what happened on the field: who they
played, where, and what the score was. The output is one number per team,
in points. A team rated 10 would be expected to beat a team rated 3 by about
7 on a neutral field.

Why bother, when the polls already rank teams? Because Stage 2 needs a
measuring stick that is *not* the voters' opinion. "Voters have this team
12th, but the scoreboard says it plays like a top 5 team" is exactly the kind
of gap that predicts where a team moves next.

How it works, in one sentence: find the set of ratings that best explains
every final score, where each game says
``home rating - away rating + home edge = margin``.

Three details keep it honest:

* **Capped margins.** A 60-point rout counts the same as a 28-point one, so
  running up the score on a weak team does not buy a rating.
* **Shrinkage.** Early in the season there are few games, so every rating is
  pulled toward a starting guess. Like a batting average after ten at-bats:
  you believe it a little, not a lot. The pull fades as games pile up.
* **Starting guess.** Last season's final rating, shrunk toward average,
  because rosters turn over but programs do not change overnight.

Setting ``cap=1`` turns every game into "won by 1" or "lost by 1". The same
maths then gives a rating that only knows wins and losses, weighted by who
they came against. That is the *résumé* rating: not "how good are you?" but
"what have you accomplished?". Voters care about both.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cfp_rankings.snapshots import Game

FCS = "(non-FBS opponent)"  # every lower-division team is treated as one generic team


def _name(team: str, is_fbs: bool) -> str:
    return team if is_fbs else FCS


@dataclass(frozen=True)
class Ratings:
    """One rating per team, plus the home edge, all in the same units."""

    values: dict[str, float]
    home_edge: float
    default: float = 0.0  # an FBS team we have never seen is assumed average

    def of(self, team: str, is_fbs: bool = True) -> float:
        return self.values.get(_name(team, is_fbs), self.default if is_fbs else self.values.get(FCS, -15.0))

    def expected_margin(self, g: Game) -> float:
        """Points the home team is expected to win by."""
        edge = 0.0 if g.neutral else self.home_edge
        return self.of(g.home, g.home_fbs) - self.of(g.away, g.away_fbs) + edge

    def ranks(self, teams) -> dict[str, int]:
        """1 = best, among the given teams."""
        order = sorted(teams, key=lambda t: -self.of(t))
        return {t: i + 1 for i, t in enumerate(order)}


def fit_ratings(
    games,
    prior: dict[str, float] | None = None,
    cap: float = 28.0,
    shrink: float = 2.0,
    home_edge_guess: float | None = None,
) -> Ratings:
    """Solve for the ratings that best explain the scores.

    ``shrink`` is how many "imaginary games at the starting guess" each team
    carries. With shrink=2, a team that has played two real games is rated
    halfway between its starting guess and what those two games say.

    This is ridge regression, solved exactly. No iteration, no randomness.
    """
    prior = prior or {}
    if home_edge_guess is None:
        home_edge_guess = 2.5 * min(cap, 28.0) / 28.0
    names = sorted({_name(g.home, g.home_fbs) for g in games} | {_name(g.away, g.away_fbs) for g in games} | set(prior))
    index = {t: i for i, t in enumerate(names)}
    n = len(names)
    # Unknowns: one rating per team, then the home edge in the last slot.
    A = np.zeros((n + 1, n + 1))
    b = np.zeros(n + 1)
    for g in games:
        h, a = index[_name(g.home, g.home_fbs)], index[_name(g.away, g.away_fbs)]
        if h == a:
            continue  # two non-FBS teams: tells us nothing
        margin = float(np.clip(g.home_points - g.away_points, -cap, cap))
        # Each game adds x xT to A and x * margin to b, where x has +1 for the
        # home team, -1 for the away team and 1 for "played at home".
        cols, signs = [h, a], [1.0, -1.0]
        if not g.neutral:
            cols.append(n)
            signs.append(1.0)
        for ci, si in zip(cols, signs):
            b[ci] += si * margin
            for cj, sj in zip(cols, signs):
                A[ci, cj] += si * sj
    start = np.array([prior.get(t, -15.0 * cap / 28.0 if t == FCS else 0.0) for t in names] + [home_edge_guess])
    pull = np.full(n + 1, shrink)
    pull[n] = 50.0  # the home edge is well known; let it move only slowly
    solution = np.linalg.solve(A + np.diag(pull), b + pull * start)
    return Ratings({t: float(solution[i]) for t, i in index.items()}, float(solution[n]))


@dataclass(frozen=True)
class PowerSettings:
    cap: float = 28.0  # biggest margin a single game can count for
    shrink: float = 2.0  # imaginary games at the starting guess
    carry: float = 0.6  # share of last season's rating kept as this season's starting guess


POWER = PowerSettings(cap=28.0, shrink=2.0, carry=0.8)
RESUME = PowerSettings(cap=1.0, shrink=1.0, carry=0.3)


def next_season_prior(final: Ratings, settings: PowerSettings, seasons_ago: int = 1) -> dict[str, float]:
    """Starting guess for a new season: last season's rating, pulled toward average."""
    keep = settings.carry**seasons_ago
    return {t: keep * v for t, v in final.values.items() if t != FCS}


def check(seasons: dict, settings: PowerSettings = POWER) -> dict[str, float]:
    """How well does the rating call next week's winners?

    For every week: rate teams on earlier games only, then pick the winner of
    each FBS game that week. Compared on the same games with CFBD's own Elo
    and, from 2013, with the sportsbook's closing spread.
    """
    hits = {"power": [], "elo": [], "power_on_lined_games": [], "spread": []}
    final = None
    last_year = None
    for year in sorted(seasons):
        season = seasons[year]
        prior = next_season_prior(final, settings, year - last_year) if final else {}
        for slot in sorted({g.slot for g in season.games}):
            ratings = fit_ratings([g for g in season.games if g.slot < slot], prior, settings.cap, settings.shrink)
            for g in season.games:
                if g.slot != slot or g.winner is None or not (g.home_fbs and g.away_fbs):
                    continue
                home_won = g.home_points > g.away_points
                right = (ratings.expected_margin(g) > 0) == home_won
                if final is not None:  # the first season has no starting guess; don't grade it
                    hits["power"].append(right)
                    if g.home_elo_pre is not None and g.away_elo_pre is not None:
                        edge = 0 if g.neutral else 55
                        hits["elo"].append((g.home_elo_pre - g.away_elo_pre + edge > 0) == home_won)
                    if g.spread_home:
                        hits["power_on_lined_games"].append(right)
                        hits["spread"].append((g.spread_home < 0) == home_won)
        final = fit_ratings(season.games, prior, settings.cap, settings.shrink)
        last_year = year
    return {k: sum(v) / len(v) for k, v in hits.items() if v}


def main() -> None:
    from cfp_rankings.backtest import DEV_SEASONS
    from cfp_rankings.snapshots import load_seasons

    result = check(load_seasons(DEV_SEASONS))
    print("Share of FBS games where the favourite, according to each source, won:")
    for name, value in result.items():
        print(f"  {name:22s} {value:.1%}")


if __name__ == "__main__":
    main()
