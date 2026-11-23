"""Stage 3: predict the CFP committee's ranking.

The committee publishes on Tuesday, two days after the AP and Coaches polls.
So the best starting point is already on the table: this week's AP poll, and
(after the first week) the committee's own ranking from last week. The job is
to learn how the committee *differs* from those.

Analogy: forecasting a food critic you have read for years. You do not start
from a blank page. You start from what the crowd of other reviewers said
about the same restaurant this week, plus what this critic wrote last time,
and then apply what you know about the critic's tastes. The clout study
(docs/clout-step-1-results.md) measured those tastes:

* the committee is about two spots kinder to power-conference teams than AP
  voters are;
* it leans on accomplishment (the résumé rating) and on losses;
* a conference title is worth about one extra spot, and a title-game loss
  is partly forgiven.

There are only 54 committee rankings to learn from, far too few for the big
tree model used for AP and Coaches. So this model is deliberately small: one
weight per input, ten weights in all by default. It still learns from pairs
("the committee put A above B"), exactly like Stage 2.

Before it has any past committee season to study (2014), it falls back to a
simple rule: last week's committee ranking, moved the way AP voters moved.
"""

from __future__ import annotations

import numpy as np

from cfp_rankings.clout import conferences, is_power, title_games
from cfp_rankings.features import History
from cfp_rankings.power import POWER, RESUME, fit_ratings
from cfp_rankings.snapshots import RAW_DIR, PollRelease, Snapshot

Example = tuple[Snapshot, PollRelease]

OUT = 30.0  # stand-in rank for a team outside a top 25
DEEP = 40.0  # Stage 1 ranks are capped here; beyond it the order no longer matters

BASE = ["carried", "ap", "coaches", "prev_cfp", "prev_offset"]
TASTES = ["power_conf", "brand", "losses", "resume_rank", "power_rank"]
TITLES = ["champion", "runner_up"]
FIRST_WEEK = [f"first_week_{name}" for name in TASTES]
FEATURES = BASE + TASTES + TITLES + FIRST_WEEK
# What the model uses by default. The committee's tastes are applied in the
# first week only: after that, last week's committee ranking already contains
# them, and adding them again did not help in testing (see docs/cfp-model-results.md).
DEFAULT = BASE + FIRST_WEEK


def _rank(rank_of: dict[str, int], team: str) -> float:
    return float(min(rank_of.get(team, OUT), OUT))


def carried_order(snap: Snapshot) -> dict[str, float]:
    """Last week's committee rank, moved by as many spots as AP voters moved the team.

    In the first week there is no committee ranking yet, so it is just the AP rank.
    """
    ap = snap.latest("ap").rank_of()
    prev_cfp = snap.latest("cfp", before_slot=snap.slot)
    if prev_cfp is None:
        return {t: _rank(ap, t) for t in ap}
    prev_ap_release = snap.latest("ap", before_slot=snap.slot)
    prev_ap = prev_ap_release.rank_of() if prev_ap_release else {}
    cfp = prev_cfp.rank_of()
    return {t: _rank(cfp, t) + _rank(ap, t) - _rank(prev_ap, t) for t in set(ap) | set(cfp)}


class CarryForward:
    """The rule on its own, as a bar to beat."""

    name = "Last week's CFP, moved like AP"

    def fit(self, examples: list[Example]) -> None:
        pass

    def predict(self, snap: Snapshot) -> list[str] | None:
        if snap.latest("ap") is None:
            return None
        ap = snap.latest("ap").rank_of()
        order = carried_order(snap)
        return sorted(order, key=lambda t: (order[t], _rank(ap, t), t))[:25]


def build_rows(snap: Snapshot, history: History, raw_dir=RAW_DIR):
    """``(teams, X)``: the candidates and one row of inputs each, or None."""
    ap_release, coaches_release = snap.latest("ap"), snap.latest("coaches")
    if ap_release is None:
        return None
    ap = ap_release.rank_of()
    coaches = coaches_release.rank_of() if coaches_release else ap
    prev_release = snap.latest("cfp", before_slot=snap.slot)
    first_week = prev_release is None
    prev_cfp = prev_release.rank_of() if prev_release else {}
    prev_ap_release = snap.latest("ap", before_slot=snap.slot)
    prev_ap = prev_ap_release.rank_of() if prev_ap_release else {}
    carried = carried_order(snap)

    fbs = snap.fbs_teams()
    resume = fit_ratings(snap.games, history.prior(snap.season, RESUME, "resume"), RESUME.cap, RESUME.shrink).ranks(fbs)
    power = fit_ratings(snap.games, history.prior(snap.season, POWER, "power"), POWER.cap, POWER.shrink).ranks(fbs)
    brand = history.brand(snap.season)
    conf = conferences(snap.season, raw_dir)
    losses: dict[str, int] = {}
    for g in snap.games:
        if g.loser:
            losses[g.loser] = losses.get(g.loser, 0) + 1
    # Title games are played the week before the final ranking. Five or more
    # found in last week's games means this is that ranking.
    titles = title_games(snap.season, snap.slot - 1, raw_dir)
    if len(titles) < 10:
        titles = {}

    # Candidates: anyone in this week's polls or last week's committee ranking,
    # plus teams the scoreboard rates highly that the voters left out.
    teams = sorted(set(ap) | set(coaches) | set(prev_cfp) | {t for t in fbs if resume[t] + power[t] <= 50})
    rows = []
    for t in teams:
        tastes = [
            1.0 if is_power(conf, t) else 0.0,
            brand.get(t, 0.0),
            float(losses.get(t, 0)),
            float(min(resume.get(t, DEEP), DEEP)),
            float(min(power.get(t, DEEP), DEEP)),
        ]
        rows.append([
            carried.get(t, OUT),
            _rank(ap, t),
            _rank(coaches, t),
            _rank(ap, t) if first_week else _rank(prev_cfp, t),
            0.0 if first_week else _rank(prev_ap, t) - _rank(prev_cfp, t),
            *tastes,
            1.0 if titles.get(t) is True else 0.0,
            1.0 if titles.get(t) is False else 0.0,
            *(x if first_week else 0.0 for x in tastes),
        ])
    return teams, np.array(rows, dtype=float)


def fit_pairwise(tables: list[np.ndarray], ranks: list[np.ndarray], ridge: float = 1.0, steps: int = 25) -> np.ndarray:
    """One weight per input, so that the higher-scored team is the one ranked higher.

    For every pair of teams in a ranking where one really finished above the
    other, the difference of their inputs should score positive. That is a
    logistic regression on differences, solved by Newton's method. ``ridge``
    pulls every weight toward zero, which stops a small sample from producing
    wild weights. Two unranked teams are never compared.
    """
    diffs = []
    for X, rank in zip(tables, ranks):
        i, j = np.where((rank[:, None] < rank[None, :]) & (rank[:, None] <= 25))
        diffs.append(X[i] - X[j])
    D = np.vstack(diffs)
    w = np.zeros(D.shape[1])
    for _ in range(steps):
        p = 1.0 / (1.0 + np.exp(-np.clip(D @ w, -30, 30)))  # chance the model gets each pair right
        gradient = D.T @ (p - 1.0) / len(D) + ridge * w / len(D)
        hessian = (D * (p * (1 - p))[:, None]).T @ D / len(D) + ridge * np.eye(len(w)) / len(D)
        w -= np.linalg.solve(hessian, gradient)
    return w


class CfpRanker:
    """Predict the committee's top 25. Same two methods as every other model.

    ``background`` is AP poll history for all seasons. It is used only for the
    things that carry over between years (Stage 1 starting guesses and brand),
    and ``History`` only ever looks at seasons before the one being predicted.
    """

    name = "Stage 3: CFP model"

    def __init__(self, background: list[Example], ridge: float = 10.0, use: list[str] | None = None, raw_dir=RAW_DIR):
        self.history = History()
        self.history.learn(background)
        self.ridge = ridge
        self.columns = [FEATURES.index(f) for f in (use or DEFAULT)]
        self.raw_dir = raw_dir
        self.scale: np.ndarray | None = None
        self.weights: np.ndarray | None = None

    def fit(self, examples: list[Example]) -> None:
        tables, ranks = [], []
        for snap, actual in examples:
            built = build_rows(snap, self.history, self.raw_dir)
            if built is None:
                continue
            teams, X = built
            real = actual.rank_of()
            tables.append(X[:, self.columns])
            ranks.append(np.array([real.get(t, 26) for t in teams], dtype=float))
        if not tables:
            return  # no committee season to study yet: predict() uses the simple rule
        self.scale = np.maximum(np.vstack(tables).std(axis=0), 1e-9)
        self.weights = fit_pairwise([X / self.scale for X in tables], ranks, self.ridge)

    def predict(self, snap: Snapshot) -> list[str] | None:
        if self.weights is None:
            return CarryForward().predict(snap)
        built = build_rows(snap, self.history, self.raw_dir)
        if built is None:
            return None
        teams, X = built
        scores = (X[:, self.columns] / self.scale) @ self.weights
        return [teams[i] for i in sorted(range(len(teams)), key=lambda i: (-scores[i], teams[i]))][:25]

    def importance(self) -> list[tuple[str, float]]:
        """Each input's weight, per one standard deviation of that input."""
        if self.weights is None:
            return []
        names = [FEATURES[c] for c in self.columns]
        return sorted(zip(names, (float(w) for w in self.weights)), key=lambda kv: -abs(kv[1]))


# ---------- report ----------
VARIANTS = {
    "Stage 3: CFP model": DEFAULT,
    "  without the first-week tastes": BASE,
    "  tastes in every week": BASE + TASTES + FIRST_WEEK,
    "  plus title-game results": DEFAULT + TITLES,
    "  everything": FEATURES,
}


def main() -> None:
    from cfp_rankings.backtest import DEV_SEASONS, examples, walk_forward
    from cfp_rankings.baselines import CopyPoll, WinLossRule
    from cfp_rankings.metrics import METRICS, average
    from cfp_rankings.snapshots import load_seasons

    seasons = load_seasons(DEV_SEASONS)
    background = [ex for y in seasons for ex in examples(seasons[y], "ap")]
    test = [y for y in DEV_SEASONS if seasons[y].releases("cfp")]
    menu = {"Copy this week's AP": lambda: CopyPoll("ap"), "Win/loss rule (the bar)": lambda: WinLossRule(fallback="ap"),
            CarryForward.name: CarryForward}
    for name, use in VARIANTS.items():
        menu[name] = lambda use=use: CfpRanker(background, use=use)
    results = {}
    for name, make in menu.items():
        rows = walk_forward(seasons, "cfp", make, test)
        for r in rows:
            slots = [x["slot"] for x in rows if x["season"] == r["season"]]
            r["when"] = "first" if r["slot"] == min(slots) else "final" if r["slot"] == max(slots) else "middle"
        results[name] = rows

    print(f"{len(results[CarryForward.name])} committee rankings, {test[0]} to {test[-1]}\n")
    print(f"{'':34s} " + " ".join(f"{m:>12s}" for m in METRICS) + "   first  middle   final")
    for name, rows in results.items():
        a = average(rows)
        parts = [average([r for r in rows if r["when"] == w])["avg_miss"] for w in ("first", "middle", "final")]
        print(f"{name:34s} " + " ".join(f"{a[m]:12.2f}" for m in METRICS) + "  " + " ".join(f"{p:7.2f}" for p in parts))

    bar, model = results["Win/loss rule (the bar)"], results["Stage 3: CFP model"]
    print("\nAverage miss by season (bar, model)")
    for y in test:
        b = average([r for r in bar if r["season"] == y])["avg_miss"]
        m = average([r for r in model if r["season"] == y])["avg_miss"]
        print(f"  {y}  {b:.2f}  {m:.2f}  {'better' if m < b else 'worse'}")
    better = sum(m["avg_miss"] < b["avg_miss"] for b, m in zip(bar, model))
    worse = sum(m["avg_miss"] > b["avg_miss"] for b, m in zip(bar, model))
    print(f"  rankings where the model beat the bar: {better} of {len(bar)}, worse in {worse}")

    final = CfpRanker(background)
    final.fit([ex for y in test for ex in examples(seasons[y], "cfp")])
    print("\nWeights, studied on every season. Positive: a higher value of the input moves a team UP.")
    print("(Rank inputs are negative because a bigger rank number is a worse rank.)")
    for name, w in final.importance():
        print(f"  {name:26s} {w:+.2f}")


if __name__ == "__main__":
    main()
