"""Turn a snapshot into a table: one row per team that could be ranked.

Analogy: a scouting card for every candidate. Before the voters fill in their
ballots, we write down, for each team, everything a voter could know that
morning: where the team sat last week, what it just did, who it did it to,
its record, and what the scoreboard-only ratings from Stage 1 say. Stage 2
then learns how voters turn those cards into an order.

Everything here is computed from a ``Snapshot`` (this season, up to this
morning) and a ``History`` (finished earlier seasons). Neither can see the
poll being predicted.
"""

from __future__ import annotations


import numpy as np

from cfp_rankings.power import POWER, RESUME, PowerSettings, Ratings, fit_ratings, next_season_prior
from cfp_rankings.snapshots import FINAL_SLOT, PollRelease, Snapshot

NOT_RANKED = 40.0  # stand-in "rank" for a team outside the top 25
NAN = float("nan")


def _era_index(season: int) -> int:
    return 0 if season <= 2013 else 1 if season <= 2023 else 2


class History:
    """What finished earlier seasons tell us about this one.

    Two things carry over from year to year:

    * **Stage 1 ratings.** Last season's final ratings are the starting guess
      for this season's (see ``power.py``).
    * **Brand.** How often a program has finished in the final poll over the
      previous five seasons. Voters give familiar names the benefit of the
      doubt, especially early in the season.

    ``learn`` only ever receives finished past seasons, and ``prior`` and
    ``brand`` only look at seasons *before* the one being asked about.
    """

    def __init__(self):
        self.final_ratings: dict[int, dict[str, Ratings]] = {}
        self.final_poll: dict[int, dict[str, int]] = {}

    def learn(self, examples) -> None:
        by_season: dict[int, list] = {}
        for snap, actual in examples:
            by_season.setdefault(snap.season, []).append((snap, actual))
        for season in sorted(by_season):
            snap, actual = max(by_season[season], key=lambda ex: ex[0].slot)
            if season not in self.final_ratings:
                # Latest snapshot plus the games it was about to learn of is
                # the whole season only when the last release is the final
                # poll, which is the normal case. Otherwise it is the season
                # up to the last release, which is still all in the past.
                self.final_ratings[season] = {
                    "power": fit_ratings(snap.games, self.prior(season, POWER, "power"), POWER.cap, POWER.shrink),
                    "resume": fit_ratings(snap.games, self.prior(season, RESUME, "resume"), RESUME.cap, RESUME.shrink),
                }
            if actual.slot == FINAL_SLOT:
                self.final_poll[season] = actual.rank_of()

    def prior(self, season: int, settings: PowerSettings, kind: str) -> dict[str, float]:
        earlier = [y for y in self.final_ratings if y < season]
        if not earlier:
            return {}
        last = max(earlier)
        return next_season_prior(self.final_ratings[last][kind], settings, seasons_ago=season - last)

    def brand(self, season: int) -> dict[str, float]:
        """0 to 1. A team that finished #1 in each of the last five seasons scores 1."""
        years = sorted(y for y in self.final_poll if y < season)[-5:]
        if not years:
            return {}
        out: dict[str, float] = {}
        for y in years:
            for team, rank in self.final_poll[y].items():
                out[team] = out.get(team, 0.0) + (26 - min(rank, 26)) / 25 / len(years)
        return out


def points_share(release: PollRelease) -> dict[str, float]:
    """Each team's vote points as a share of the maximum possible.

    #1 on every ballot is 1.0. Empty when the poll has no points (AP before
    2014, and the CFP always). The number of voters is not in the data, so it
    is estimated from the total points handed out: each ballot gives 325.
    """
    pts = {r.team: r.points for r in release.ranks if r.points}
    if len(pts) < 20:
        return {}
    voters = sum(pts.values()) / 325.0
    return {t: p / (25.0 * voters) for t, p in pts.items()}


FEATURES = [
    # where the team stood
    "prev_rank", "prev_ranked", "prev_share", "share_gap_above", "share_gap_below",
    "other_poll_rank", "preseason_rank", "brand",
    # added in the second round (docs/stage-2-round-2.md)
    "rank_two_polls_ago", "last_move", "power_conference", "resume_queue", "power_queue",
    # traffic: what happened to the teams around it
    "teams_above_that_lost", "rank_if_only_losers_drop",
    # what it just did (games since last week's poll)
    "games", "wins", "losses", "margin", "worst_margin", "best_win_opp_rank", "ranked_wins",
    "loss_opp_rank", "loss_at_home", "opp_power", "surprise", "beat_spread_by", "spread",
    # the season so far
    "season_wins", "season_losses", "win_pct", "season_ranked_wins", "schedule_strength",
    # Stage 1: scoreboard-only ratings
    "power", "power_rank", "power_change", "resume", "resume_rank", "resume_change",
    # when
    "week", "is_final", "era",
]


def _cap(margin: float, cap: float = 28.0) -> float:
    return max(-cap, min(cap, margin))


def build_rows(snap: Snapshot, history: History, cache: dict | None = None):
    """Return ``(teams, X)``: the candidates and their feature rows, or None.

    Candidates are last week's 25 plus every FBS team that has not lost since
    that poll. (Across 2005 to 2023, one team out of 709 newcomers entered the
    AP poll in a week it lost.)
    """
    prev = snap.latest(snap.poll, before_slot=snap.slot)
    if prev is None:
        return None
    other_name = {"ap": "coaches", "coaches": "ap"}.get(snap.poll)
    other = snap.latest(other_name, before_slot=snap.slot) if other_name else None
    pre = next((p for p in snap.polls if p.poll == snap.poll and p.slot == 1), None)

    prev_rank = prev.rank_of()
    other_rank = other.rank_of() if other else {}
    pre_rank = pre.rank_of() if pre else {}
    share = points_share(prev)
    brand = history.brand(snap.season)
    # Momentum: where the team sat two polls ago, and so how it moved last time.
    prev2 = snap.latest(snap.poll, before_slot=prev.slot)
    prev2_rank = prev2.rank_of() if prev2 else None

    since = [g for g in snap.games if g.slot >= prev.slot]
    before = [g for g in snap.games if g.slot < prev.slot]

    # Stage 1 ratings, now and as of last week's poll. The same games feed
    # the AP and Coaches models, so results are cached between them.
    cache = cache if cache is not None else {}
    key = (snap.season, snap.slot, prev.slot, len(snap.games))
    if key not in cache:
        cache[key] = {
            kind: (
                fit_ratings(snap.games, history.prior(snap.season, st, kind), st.cap, st.shrink),
                fit_ratings(before, history.prior(snap.season, st, kind), st.cap, st.shrink),
            )
            for kind, st in (("power", POWER), ("resume", RESUME))
        }
    power_now, power_before = cache[key]["power"]
    resume_now, resume_before = cache[key]["resume"]

    fbs = snap.fbs_teams() | set(prev_rank)
    power_rank = power_now.ranks(fbs)
    resume_rank = resume_now.ranks(fbs)

    # Per-team view of every game: (opponent, margin, at_home, game)
    def per_team(games):
        out: dict[str, list] = {}
        for g in games:
            m = g.home_points - g.away_points
            out.setdefault(g.home, []).append((g.away, g.away_fbs, m, not g.neutral, g, 1))
            out.setdefault(g.away, []).append((g.home, g.home_fbs, -m, False, g, -1))
        return out

    recent, season_games = per_team(since), per_team(snap.games)
    lost_recently = {t for t, gs in recent.items() if any(m < 0 for _, _, m, _, _, _ in gs)}
    losers_above = sorted(prev_rank[t] for t in lost_recently if t in prev_rank)

    teams = sorted(set(prev_rank) | {t for t in fbs if t not in lost_recently})
    # The queue: among the teams outside last week's 25, who is first in line?
    # A tree can read "résumé rank 31" but not "best résumé of anyone waiting".
    waiting = [t for t in teams if t not in prev_rank]
    resume_queue = {t: i + 1 for i, t in enumerate(sorted(waiting, key=lambda t: (resume_rank.get(t, len(fbs)), t)))}
    power_queue = {t: i + 1 for i, t in enumerate(sorted(waiting, key=lambda t: (power_rank.get(t, len(fbs)), t)))}
    week = 17 if snap.slot == FINAL_SLOT else snap.slot
    rows = []
    for t in teams:
        pr = prev_rank.get(t)
        gs = recent.get(t, [])
        wins = [x for x in gs if x[2] > 0]
        losses = [x for x in gs if x[2] < 0]
        covers = [x[2] + x[5] * x[4].spread_home for x in gs if x[4].spread_home is not None]
        spreads = [x[5] * x[4].spread_home for x in gs if x[4].spread_home is not None]
        sg = season_games.get(t, [])
        s_wins = sum(1 for x in sg if x[2] > 0)
        s_losses = sum(1 for x in sg if x[2] < 0)
        above_lost = sum(1 for r in losers_above if pr is not None and r < pr)
        rows.append([
            pr if pr is not None else NOT_RANKED,
            1.0 if pr is not None else 0.0,
            share.get(t, 0.0) if share else NAN,
            _gap(share, prev, pr, -1),
            _gap(share, prev, pr, +1),
            other_rank.get(t, NOT_RANKED) if other else NAN,
            pre_rank.get(t, NOT_RANKED) if pre else NAN,
            brand.get(t, 0.0),
            prev2_rank.get(t, NOT_RANKED) if prev2_rank is not None else NAN,
            prev2_rank.get(t, NOT_RANKED) - (pr if pr is not None else NOT_RANKED) if prev2_rank is not None else NAN,
            1.0 if snap.is_power_conference(t) else 0.0,
            resume_queue.get(t, 0),
            power_queue.get(t, 0),
            above_lost,
            (pr - above_lost) if pr is not None else NOT_RANKED,
            len(gs),
            len(wins),
            len(losses),
            sum(_cap(x[2]) for x in gs),
            min((_cap(x[2]) for x in gs), default=NAN),
            min((prev_rank.get(x[0], NOT_RANKED) for x in wins), default=NAN),
            sum(1 for x in wins if x[0] in prev_rank),
            min((prev_rank.get(x[0], NOT_RANKED) for x in losses), default=NAN),
            max((1.0 if x[3] else 0.0 for x in losses), default=NAN),
            _mean([power_before.of(x[0], x[1]) for x in gs]),
            sum(_cap(x[2]) - x[5] * power_before.expected_margin(x[4]) for x in gs) if gs else NAN,
            sum(covers) if covers else NAN,
            _mean(spreads),
            s_wins,
            s_losses,
            s_wins / (s_wins + s_losses) if s_wins + s_losses else NAN,
            sum(1 for x in sg if x[2] > 0 and x[0] in prev_rank),
            _mean([power_now.of(x[0], x[1]) for x in sg]),
            power_now.of(t),
            power_rank.get(t, len(fbs)),
            power_now.of(t) - power_before.of(t),
            resume_now.of(t),
            resume_rank.get(t, len(fbs)),
            resume_now.of(t) - resume_before.of(t),
            week,
            1.0 if snap.slot == FINAL_SLOT else 0.0,
            _era_index(snap.season),
        ])
    return teams, np.array(rows, dtype=float)


def _mean(values) -> float:
    return sum(values) / len(values) if values else NAN


def _gap(share: dict[str, float], prev: PollRelease, rank: int | None, step: int) -> float:
    """How far (in share of points) to the team one spot above or below.

    A team that barely trails the one above it gets passed more easily than
    one that trails by a mile, even though both are "one spot back".
    """
    if not share or rank is None:
        return NAN
    mine = next((r.team for r in prev.ranks if r.rank == rank), None)
    neighbour = next((r.team for r in prev.ranks if r.rank == rank + step), None)
    if mine is None or mine not in share:
        return NAN
    if neighbour is None:
        return (1.0 - share[mine]) if step < 0 else share[mine]
    return abs(share.get(neighbour, 0.0) - share[mine])


def labels(teams: list[str], actual: PollRelease) -> np.ndarray:
    """26 minus the real rank, so #1 is 25 and #25 is 1. 0 means not ranked."""
    rank = actual.rank_of()
    return np.array([max(0, 26 - rank[t]) if t in rank else 0 for t in teams], dtype=float)


