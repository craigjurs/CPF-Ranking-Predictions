"""Naive baselines: the bar every later model has to clear.

Analogy: tomorrow's weather forecast of "same as today" is right surprisingly
often. A fancy forecast only earns its keep if it beats that. Polls are the
same: voters start from last week's ballot and edit it. So the baselines are:

``Persistence``   Copy last week's poll unchanged. ("Same as today.")
``WinLossRule``   Copy last week's poll, then push losers down, nudge up
                  teams that beat a ranked opponent, and let unbeaten-this-week
                  outsiders fill the holes. A handful of knobs, no ML.
``CopyPoll``      Predict one poll by copying another, e.g. CFP = that
                  Sunday's AP.

Every model has the same two methods, which is the contract the backtester
relies on (the ML models will plug into the same socket later):

    fit(examples)      learn from past (snapshot, actual poll) pairs
    predict(snapshot)  return teams, best first
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from cfp_rankings.metrics import score
from cfp_rankings.snapshots import PollRelease, Snapshot

Example = tuple[Snapshot, PollRelease]


def _starting_poll(snap: Snapshot, fallback: str | None) -> PollRelease | None:
    """Last week's release of the poll being predicted, else the fallback poll.

    The fallback matters for the first CFP ranking of a season: there is no
    "last week's CFP", so we start from that Sunday's AP poll instead.
    """
    prev = snap.latest(snap.poll, before_slot=snap.slot)
    if prev is None and fallback:
        prev = snap.latest(fallback)
    return prev


class Persistence:
    """This week's poll = last week's poll, unchanged."""

    def __init__(self, fallback: str | None = None):
        self.fallback = fallback
        self.name = "Same as last week"

    def fit(self, examples: list[Example]) -> None:
        pass

    def predict(self, snap: Snapshot) -> list[str] | None:
        prev = _starting_poll(snap, self.fallback)
        return prev.teams()[:25] if prev else None


class CopyPoll:
    """Predict a poll by copying the latest release of a different poll."""

    def __init__(self, source: str = "ap"):
        self.source = source
        self.name = f"Copy this week's {source.upper()}"

    def fit(self, examples: list[Example]) -> None:
        pass

    def predict(self, snap: Snapshot) -> list[str] | None:
        src = snap.latest(self.source)
        return src.teams()[:25] if src else None


@dataclass(frozen=True)
class Knobs:
    """The win/loss rule's dials. Units are poll spots."""

    loss_to_ranked: float = 5.5  # spots a ranked team falls after losing to a ranked team
    loss_to_unranked: float = 9.5  # ... after losing to an unranked team (an upset hurts more)
    beat_ranked: float = 1.5  # spots a ranked team climbs for beating a ranked team
    entry: float = 1.0  # how far outside the top 25 an outsider starts (26 + entry)
    entry_per_loss: float = 2.0  # extra spots back for each loss on an outsider's record
    entry_beat_ranked: float = 4.0  # spots an outsider gains for beating a ranked team


@dataclass(frozen=True)
class _TeamWeek:
    """What one team did since the last poll. Computed once, reused while tuning."""

    team: str
    prev_rank: int | None
    losses_to_ranked: int
    losses_to_unranked: int
    wins_over_ranked: int
    season_losses: int
    elo: float


def _team_weeks(snap: Snapshot, prev: PollRelease) -> list[_TeamWeek]:
    prev_rank = prev.rank_of()
    since = snap.games_since(prev.slot)
    tally: dict[str, list[int]] = {}
    for g in since:
        if g.winner is None:
            continue
        w, l = g.winner, g.loser
        tally.setdefault(w, [0, 0, 0])
        tally.setdefault(l, [0, 0, 0])
        if w in prev_rank:
            tally[l][0] += 1
        else:
            tally[l][1] += 1
        if l in prev_rank:
            tally[w][2] += 1
    records, elo, fbs = snap.records(), snap.elo(), snap.fbs_teams()
    out = []
    for team in set(prev_rank) | (fbs & set(tally)):
        lr, lu, wr = tally.get(team, [0, 0, 0])
        if team not in prev_rank and (lr or lu):
            continue  # an unranked team that just lost is not getting in
        out.append(_TeamWeek(team, prev_rank.get(team), lr, lu, wr, records.get(team, (0, 0))[1], elo.get(team, 1500.0)))
    return out


def _rank(rows: list[_TeamWeek], k: Knobs) -> list[str]:
    scored = []
    for r in rows:
        if r.prev_rank is not None:
            s = r.prev_rank + k.loss_to_ranked * r.losses_to_ranked + k.loss_to_unranked * r.losses_to_unranked
            s -= k.beat_ranked * r.wins_over_ranked
        else:
            s = 26 + k.entry + k.entry_per_loss * r.season_losses - k.entry_beat_ranked * r.wins_over_ranked
        # ties: the team ranked higher last week goes first, then the better Elo
        scored.append((s, r.prev_rank if r.prev_rank is not None else 99, -r.elo, r.team))
    return [t[3] for t in sorted(scored)[:25]]


# The values each knob is allowed to take while tuning.
GRID = {
    "loss_to_ranked": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5],
    "loss_to_unranked": [3.5, 5.5, 7.5, 9.5, 11.5, 13.5, 15.5],
    "beat_ranked": [0.0, 0.5, 1.5, 2.5, 3.5],
    "entry": [0.0, 1.0, 2.0, 4.0],
    "entry_per_loss": [0.5, 1.0, 2.0, 3.0, 4.0],
    "entry_beat_ranked": [0.0, 2.0, 4.0, 6.0, 8.0],
}


class WinLossRule:
    """Last week's poll, adjusted for wins and losses.

    Every ranked team keeps last week's rank as its starting score, losers get
    spots added (worse), and winners over ranked teams get a few taken off.
    Unranked teams that did not lose queue up just outside the top 25, ordered
    by fewest losses. Sort everyone by score, keep the best 25.

    With ``tune=True`` the knobs are chosen on past seasons to minimise the
    average miss. That is the only "learning" here: six numbers.
    """

    def __init__(self, tune: bool = False, fallback: str | None = None, knobs: Knobs | None = None):
        self.tune = tune
        self.fallback = fallback
        self.knobs = knobs or Knobs()
        self.name = "Win/loss rule, tuned" if tune else "Win/loss rule, fixed"

    def predict(self, snap: Snapshot) -> list[str] | None:
        prev = _starting_poll(snap, self.fallback)
        return _rank(_team_weeks(snap, prev), self.knobs) if prev else None

    def fit(self, examples: list[Example]) -> None:
        if not self.tune:
            return
        prepared = []
        for snap, actual in examples:
            prev = _starting_poll(snap, self.fallback)
            if prev:
                prepared.append((_team_weeks(snap, prev), actual.rank_of()))
        if not prepared:
            return

        def loss(k: Knobs) -> float:
            return sum(score(_rank(rows, k), actual)["avg_miss"] for rows, actual in prepared) / len(prepared)

        # Coordinate descent: turn one dial at a time to its best setting,
        # go around the dials twice. Like tuning a radio with several knobs.
        best, best_loss = Knobs(), loss(Knobs())
        for _ in range(2):
            for knob, values in GRID.items():
                for v in values:
                    trial = replace(best, **{knob: v})
                    trial_loss = loss(trial)
                    if trial_loss < best_loss - 1e-12:
                        best, best_loss = trial, trial_loss
        self.knobs = best
