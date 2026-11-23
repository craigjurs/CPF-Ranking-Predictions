"""Stage 2: learn how voters turn a week of football into a new top 25.

The baseline rule says "a ranked team that loses drops 7.5 spots". That is one
number for every loss. Real voters are subtler: a close road loss to #2 costs
less than a home blowout by a nobody, and a team can climb without playing
because three teams above it lost.

What the model learns
---------------------
Not "what rank will Team A get?" but "**will Team A be ranked above Team B?**",
for every pair of teams in a poll.

Analogy: judging a chess tournament. You never ask "is this player a 7 out of
10?". You only ever see who beat whom, and from thousands of those head to
head results you work out a strength number for each player. Here a "result"
is one team finishing above another in a real poll. The model learns a
scoring function so that, as often as possible, the team with the higher
score is the one the voters put higher. To predict a new poll we score every
candidate and sort.

Why pairs rather than rank numbers or vote points?

* It works for every season and every poll. Vote points only exist from 2014
  for AP, and never for the CFP. An order always exists.
* It handles the teams outside the top 25 honestly. All we know about them is
  "below the 25 who made it". As a pair that is exactly what gets said:
  ranked beats unranked, and two unranked teams are never compared.
* Rank is a zero-sum game. One team moving up pushes others down. Sorting
  scores respects that automatically; predicting 25 separate rank numbers
  does not.

Vote points still help, as *inputs*: last week's points show whether #6 was
breathing down #5's neck or a mile behind.

The scoring function is a gradient-boosted tree model (LightGBM): a few
hundred small decision trees, each one correcting the mistakes of the ones
before it. Trees suit this job because voter logic is full of "it depends":
a loss matters differently in week 3 than in week 13.
"""

from __future__ import annotations

import lightgbm as lgb
import numpy as np

from cfp_rankings.features import FEATURES, History, build_rows, labels
from cfp_rankings.snapshots import PollRelease, Snapshot

Example = tuple[Snapshot, PollRelease]

SETTINGS = dict(
    learning_rate=0.05,  # how big a correction each new tree may make
    num_leaves=15,  # how many "it depends" branches one tree may have
    min_data_in_leaf=20,
    feature_fraction=0.8,
    bagging_fraction=0.8,
    bagging_freq=1,
    lambda_l2=1.0,
    verbose=-1,
    num_threads=4,
    seed=0,
    deterministic=True,
    force_row_wise=True,
)


def pairwise_objective(labels_by_row: np.ndarray, group_sizes: list[int]):
    """Build the "who should be above whom" training signal.

    For each poll (a *group*), take every pair where team i really finished
    above team j. If the model currently scores i only a little higher than j,
    or lower, nudge i up and j down. Confident, correct pairs get almost no
    nudge. This is the RankNet loss: logistic regression on score differences.

    Pairs of two unranked teams are skipped: we do not know their true order.
    """
    longest, n_groups = max(group_sizes), len(group_sizes)
    index = np.zeros((n_groups, longest), dtype=int)
    real = np.zeros((n_groups, longest), dtype=bool)
    start = 0
    for i, size in enumerate(group_sizes):
        index[i, :size] = np.arange(start, start + size)
        real[i, :size] = True
        start += size
    y = np.where(real, labels_by_row[index], -1.0)
    # above[g, i, j] is True when, in poll g, team i really finished above team j.
    above = (y[:, :, None] > y[:, None, :]) & real[:, :, None] & real[:, None, :]

    def objective(scores: np.ndarray, _dataset):
        s = scores[index]
        diff = s[:, :, None] - s[:, None, :]
        wrongness = np.where(above, 1.0 / (1.0 + np.exp(np.clip(diff, -50, 50))), 0.0)
        curve = wrongness * (1.0 - wrongness)
        g = wrongness.sum(axis=1) - wrongness.sum(axis=2)  # pushed down as j, pulled up as i
        h = curve.sum(axis=1) + curve.sum(axis=2)
        grad, hess = np.zeros_like(scores), np.zeros_like(scores)
        grad[index[real]] = g[real]
        hess[index[real]] = np.maximum(h[real], 1e-6)
        return grad, hess

    return objective


class PollRanker:
    """Predict this week's poll from last week's poll plus what just happened.

    Same two methods as the baselines, so the backtester treats it identically:

        fit(examples)      study past (snapshot, actual poll) pairs
        predict(snapshot)  return teams, best first
    """

    def __init__(self, trees: int = 600):
        self.trees = trees
        self.name = "Stage 2: learned ranker"
        self.history = History()
        self.model: lgb.Booster | None = None
        self._ratings_cache: dict = {}

    def fit(self, examples: list[Example]) -> None:
        self.history = History()
        self.history.learn(examples)
        tables, answers, sizes = [], [], []
        for snap, actual in examples:
            built = build_rows(snap, self.history, self._ratings_cache)
            if built is None:
                continue  # the preseason poll: nothing to start from
            teams, X = built
            tables.append(X)
            answers.append(labels(teams, actual))
            sizes.append(len(teams))
        if not tables:
            return
        X, y = np.vstack(tables), np.concatenate(answers)
        params = dict(SETTINGS, objective=pairwise_objective(y, sizes))
        self.model = lgb.train(params, lgb.Dataset(X, y, feature_name=FEATURES), self.trees)

    def scores(self, snap: Snapshot) -> dict[str, float] | None:
        """The model's strength number for every candidate. Higher is better."""
        if self.model is None:
            return None
        built = build_rows(snap, self.history, self._ratings_cache)
        if built is None:
            return None
        teams, X = built
        return dict(zip(teams, self.model.predict(X)))

    def predict(self, snap: Snapshot) -> list[str] | None:
        scores = self.scores(snap)
        if scores is None:
            return None
        return sorted(scores, key=lambda t: (-scores[t], t))[:25]

    def importance(self) -> list[tuple[str, float]]:
        """Which inputs the trees leaned on most, as shares that sum to 1."""
        if self.model is None:
            return []
        gain = self.model.feature_importance(importance_type="gain")
        total = float(gain.sum()) or 1.0
        return sorted(zip(FEATURES, (float(g) / total for g in gain)), key=lambda kv: -kv[1])
