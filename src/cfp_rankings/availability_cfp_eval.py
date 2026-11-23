"""Do the availability flags help the Stage 3 CFP committee model?

    uv run python -m cfp_rankings.availability_cfp_eval

The committee says out loud that it considers whether key players were
available, so this is where the flags had the best chance of mattering. Two
ways of handing them over are tried:

* **directly**: extra inputs to the small Stage 3 model, next to "last week's
  ranking" and the rest;
* **through the editor**: the Stage 2 AP model that Stage 3 borrows (see
  cfp_model.py) is given the flag columns.

Analogy: the same taste test as availability_eval.py, in a different kitchen.
One extra check is needed here. Stage 3 itself has no dice in it, but its
editor does (random seeds). So the same plain model is also run with a second
set of editor seeds, to see how much the score moves when nothing real has
changed. A gain only counts if it is clearly bigger than that.

Walk-forward as everywhere else. The sealed 2024 and 2025 seasons are not
touched.
"""

from __future__ import annotations

import argparse
import statistics

import numpy as np

from cfp_rankings import cfp_model
from cfp_rankings.availability import FLAGS
from cfp_rankings.backtest import DEV_SEASONS, examples, walk_forward
from cfp_rankings.cfp_model import DEFAULT, FEATURES, CarryForward, CfpRanker
from cfp_rankings.features import AVAILABILITY_FEATURES, _availability_row
from cfp_rankings.poll_model import SETTINGS, PollRanker
from cfp_rankings.snapshots import Snapshot, load_seasons

TWO = ["qb_changed", "production_missing_pct"]


def flag_rows(snap: Snapshot, teams: list[str], names: list[str]) -> np.ndarray:
    """The chosen flags for each team, from its games since the last committee ranking.

    Blank becomes 0 ("nothing unusual seen"), because this small model cannot
    read blanks the way the tree model can.
    """
    prev = snap.latest("cfp", before_slot=snap.slot)
    since_slot = prev.slot if prev else snap.slot - 1
    recent: dict[str, list] = {}
    for g in snap.games:
        if g.slot >= since_slot:
            recent.setdefault(g.home, []).append((None, None, None, None, g, 1))
            recent.setdefault(g.away, []).append((None, None, None, None, g, -1))
    cols = [AVAILABILITY_FEATURES.index(n) for n in names]
    rows = [[_availability_row(recent.get(t, []))[c] for c in cols] for t in teams]
    return np.nan_to_num(np.array(rows, dtype=float).reshape(len(teams), len(cols)), nan=0.0)


class FlaggedCfpRanker(CfpRanker):
    """Stage 3 with optional flag inputs, an optional flag-reading editor, and a choice of editor seeds."""

    def __init__(self, background, flags=(), editor_flags: bool = False, editor_seeds=(0, 1, 2), cache=None):
        super().__init__(background, cache=cache)
        self.flags, self.editor_flags, self.editor_seeds = list(flags), editor_flags, tuple(editor_seeds)

    def _editor(self, season: int):
        key = ("editor", season, self.editor_trees, self.editor_flags, self.editor_seeds)
        if key not in self.cache:
            earlier = [ex for ex in self.background if ex[0].season < season]
            editor = None
            if earlier:
                editor = PollRanker(self.editor_trees, self.editor_seeds, self.cache, availability=self.editor_flags)
                editor.fit(earlier)
            self.cache[key] = editor if editor is not None and editor.models else None
        return self.cache[key]

    def _table(self, snap: Snapshot):
        built = cfp_model.build_rows(snap, self.history, self.raw_dir, self._edited(snap))
        if built is None:
            return None
        teams, X = built
        return teams, np.hstack([X[:, self.columns], flag_rows(snap, teams, self.flags)])

    def fit(self, examples_) -> None:
        tables, ranks = [], []
        for snap, actual in examples_:
            built = self._table(snap)
            if built is None:
                continue
            teams, X = built
            real = actual.rank_of()
            tables.append(X)
            ranks.append(np.array([real.get(t, 26) for t in teams], dtype=float))
        if not tables:
            return
        self.scale = np.maximum(np.vstack(tables).std(axis=0), 1e-9)
        self.weights = cfp_model.fit_pairwise([X / self.scale for X in tables], ranks, self.ridge)

    def predict(self, snap: Snapshot):
        if self.weights is None:
            return CarryForward().predict(snap)
        built = self._table(snap)
        if built is None:
            return None
        teams, X = built
        scores = (X / self.scale) @ self.weights
        return [teams[i] for i in sorted(range(len(teams)), key=lambda i: (-scores[i], teams[i]))][:25]

    def importance(self):
        names = [FEATURES[c] for c in self.columns] + self.flags
        return sorted(zip(names, (float(w) for w in self.weights)), key=lambda kv: -abs(kv[1]))


VARIANTS = {
    "Stage 3 as it is": {},
    "same model, other editor seeds": {"editor_seeds": (3, 4, 5)},
    "+ two flags, direct": {"flags": TWO},
    "+ all nine flags, direct": {"flags": list(AVAILABILITY_FEATURES)},
    "editor reads the flags": {"editor_flags": True},
    "editor reads flags + two direct": {"editor_flags": True, "flags": TWO},
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--threads", type=int)
    args = ap.parse_args()
    if args.threads:
        SETTINGS["num_threads"] = args.threads
    assert set(TWO) <= set(FLAGS)
    seasons = load_seasons(DEV_SEASONS)
    background = [ex for y in seasons for ex in examples(seasons[y], "ap")]
    test = [y for y in DEV_SEASONS if seasons[y].releases("cfp")]
    cache: dict = {}
    results = {}
    for name, kw in VARIANTS.items():
        results[name] = walk_forward(seasons, "cfp", lambda kw=kw: FlaggedCfpRanker(background, cache=cache, **kw), test)
        print(f"  {name} done", flush=True)

    base = results["Stage 3 as it is"]
    print(f"\n{len(base)} committee rankings, {test[0]} to {test[-1]}\n")
    print("| version | avg miss | change | teams right | rankings better / worse | seasons better / worse |")
    print("|---|---|---|---|---|---|")
    for name, rows in results.items():
        miss = statistics.fmean(r["avg_miss"] for r in rows)
        base_miss = statistics.fmean(r["avg_miss"] for r in base)
        right = statistics.fmean(r["teams_right"] for r in rows)
        better = sum(r["avg_miss"] < b["avg_miss"] - 1e-9 for r, b in zip(rows, base))
        worse = sum(r["avg_miss"] > b["avg_miss"] + 1e-9 for r, b in zip(rows, base))
        sb = sw = 0
        for y in test:
            m = statistics.fmean(r["avg_miss"] for r in rows if r["season"] == y)
            b = statistics.fmean(r["avg_miss"] for r in base if r["season"] == y)
            sb, sw = sb + (m < b - 1e-9), sw + (m > b + 1e-9)
        print(f"| {name} | {miss:.3f} | {miss - base_miss:+.3f} | {right:.2f} | {better} / {worse} | {sb} / {sw} |")

    final = FlaggedCfpRanker(background, flags=TWO, cache=cache)
    final.fit([ex for y in test for ex in examples(seasons[y], "cfp")])
    print("\nWeights with the two direct flags, studied on every season (negative: moves a team DOWN)")
    for name, w in final.importance():
        print(f"  {name:26s} {w:+.3f}")


if __name__ == "__main__":
    main()
