"""Do the availability flags make the Stage 2 poll model better?

    uv run python -m cfp_rankings.availability_eval --seeds 0 1 2 3   (each "seed" is a batch of three models)

Analogy: a taste test with two cooks using the same recipe, where one of them
also gets an extra spice (the flags). To be fair, both cook the same dishes
(the same polls), and each cooks several times (several random seeds), because
two batches from the *same* cook never taste exactly alike either. The spice
only counts as helping if the gap between the cooks is clearly bigger than the
gap between one cook's own batches.

Same walk-forward rules as ``backtest.py``: to grade a season, both models
study earlier seasons only. Box scores were pulled from 2013, so the first
graded season is 2014. The sealed 2024 and 2025 seasons are not touched.

It also prints a second, model-free check: when a ranked team's quarterback
changed, did voters place it lower than the plain model expected?
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from cfp_rankings.backtest import DEV_SEASONS, examples
from cfp_rankings.features import AVAILABILITY_FEATURES, FEATURES, build_rows
from cfp_rankings.metrics import score
from cfp_rankings.poll_model import SETTINGS, PollRanker
from cfp_rankings.snapshots import load_seasons

FIRST_FLAG_SEASON = 2013


def run(seeds: list[int], polls=("ap", "coaches"), trees: int = 600, committee: int = 3) -> dict:
    """``committee`` is how many models are averaged inside each cook, as in
    the real Stage 2 model. Batch ``s`` uses model seeds ``s*committee`` up to
    ``s*committee + committee - 1``, so batch 0 is exactly the model the
    backtest runs."""
    seasons = load_seasons(DEV_SEASONS)
    cache: dict = {}  # scouting cards, shared so each is written once
    with_flags = [y for y in DEV_SEASONS if any(g.home_avail for g in seasons[y].games)]
    test_seasons = [y for y in with_flags if y > min(with_flags)]
    rows, teams_seen = [], []
    for seed in seeds:
        for poll in polls:
            for test_year in test_seasons:
                train = [ex for y in sorted(seasons) if y < test_year for ex in examples(seasons[y], poll)]
                judges = tuple(range(seed * committee, (seed + 1) * committee))
                plain = PollRanker(trees, seeds=judges, cache=cache)
                flagged = PollRanker(trees, seeds=judges, cache=cache, availability=True)
                plain.fit(train)
                flagged.fit(train)
                for snap, actual in examples(seasons[test_year], poll):
                    answer = actual.rank_of()
                    a, b = plain.predict(snap), flagged.predict(snap)
                    if a is None or b is None:
                        continue
                    rows.append({"seed": seed, "poll": poll, "season": test_year, "slot": snap.slot,
                                 "plain": score(a, answer)["avg_miss"],
                                 "flagged": score(b, answer)["avg_miss"],
                                 "plain_in": score(a, answer)["teams_right"],
                                 "flagged_in": score(b, answer)["teams_right"]})
                    if seed == seeds[0]:
                        teams_seen += _team_rows(plain, flagged, snap, answer, poll)
                print(f"  seed {seed} {poll} {test_year} done", flush=True)
    return {"rows": rows, "teams": teams_seen, "test_seasons": test_seasons,
            "importance": dict(flagged.importance())}


def _team_rows(plain: PollRanker, flagged: PollRanker, snap, answer: dict[str, int], poll: str) -> list[dict]:
    """For teams ranked last week: where the plain model put them, where voters did, and their flags."""
    teams, X = build_rows(snap, flagged.history, flagged._ratings_cache, availability=True)
    order = sorted(plain.scores(snap).items(), key=lambda kv: (-kv[1], kv[0]))
    position = {t: i + 1 for i, (t, _) in enumerate(order)}
    col = {name: i for i, name in enumerate(FEATURES + AVAILABILITY_FEATURES)}
    out = []
    for t, x in zip(teams, X):
        if not x[col["prev_ranked"]] or not x[col["games"]]:
            continue
        out.append({"poll": poll, "season": snap.season, "slot": snap.slot,
                    "predicted": min(position[t], 26), "actual": answer.get(t, 26), "lost": bool(x[col["losses"]]),
                    **{f: x[col[f]] for f in AVAILABILITY_FEATURES}})
    return out


def _mean_se(values: list[float]) -> tuple[float, float]:
    if len(values) < 2:
        return (values[0] if values else float("nan")), float("nan")
    return statistics.fmean(values), statistics.stdev(values) / len(values) ** 0.5


def report(result: dict) -> str:
    rows, lines = result["rows"], []
    seeds = sorted({r["seed"] for r in rows})
    lines.append(f"Test seasons: {result['test_seasons']}. Seeds: {seeds}.\n")
    lines.append("| poll | polls | plain model | with flags | change | seed-to-seed spread, plain | polls better / worse |")
    lines.append("|---|---|---|---|---|---|---|")
    for poll in sorted({r["poll"] for r in rows}):
        mine = [r for r in rows if r["poll"] == poll]
        per_seed = {s: (statistics.fmean(r["plain"] for r in mine if r["seed"] == s),
                        statistics.fmean(r["flagged"] for r in mine if r["seed"] == s)) for s in seeds}
        plain = statistics.fmean(p for p, _ in per_seed.values())
        flagged = statistics.fmean(f for _, f in per_seed.values())
        spread = max(p for p, _ in per_seed.values()) - min(p for p, _ in per_seed.values())
        # Average each poll over seeds, then count which model was closer.
        by_poll: dict[tuple, list[float]] = {}
        for r in mine:
            by_poll.setdefault((r["season"], r["slot"]), []).append(r["flagged"] - r["plain"])
        diffs = [statistics.fmean(v) for v in by_poll.values()]
        better, worse = sum(d < -1e-9 for d in diffs), sum(d > 1e-9 for d in diffs)
        lines.append(f"| {poll} | {len(diffs)} | {plain:.3f} | {flagged:.3f} | {flagged - plain:+.3f} | "
                     f"{spread:.3f} | {better} / {worse} |")
        lines.append(f"|   per seed | | " + ", ".join(f"{p:.3f}" for p, _ in per_seed.values()) + " | "
                     + ", ".join(f"{f:.3f}" for _, f in per_seed.values()) + " | | | |")

    lines.append("\nRanked teams that played: voters' rank minus the plain model's rank "
                 "(positive = voters put the team lower than the model expected)\n")
    lines.append("| poll | flag | result | teams with flag | avg gap with flag | teams without | avg gap without |")
    lines.append("|---|---|---|---|---|---|---|")
    for poll in sorted({t["poll"] for t in result["teams"]}):
        for flag in ("qb_changed", "top_rb_missing", "top_wr_missing", "top_tackler_missing", "kicker_changed",
                     "usage_drop", "big_production_gap"):
            for lost in (False, True):
                yes, no = [], []
                for t in result["teams"]:
                    if t["poll"] != poll or t["lost"] != lost:
                        continue
                    v = t["production_missing_pct"] if flag == "big_production_gap" else t[flag]
                    if v != v:
                        continue
                    hit = v >= 0.3 if flag == "big_production_gap" else v == 1.0
                    (yes if hit else no).append(t["actual"] - t["predicted"])
                (my, sy), (mn, sn) = _mean_se(yes), _mean_se(no)
                lines.append(f"| {poll} | {flag} | {'lost' if lost else 'won'} | {len(yes)} | {my:+.2f} ± {sy:.2f} | "
                             f"{len(no)} | {mn:+.2f} ± {sn:.2f} |")

    share = sum(v for k, v in result["importance"].items() if k in AVAILABILITY_FEATURES)
    lines.append(f"\nShare of the model's total gain that came from the availability columns: {share:.2%}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3])
    ap.add_argument("--trees", type=int, default=600)
    ap.add_argument("--committee", type=int, default=3, help="models averaged per batch, as in the real Stage 2 model")
    ap.add_argument("--threads", type=int, help="LightGBM threads. Use 1 when running several seeds side by side")
    ap.add_argument("--out", type=Path, help="write raw rows as JSON")
    ap.add_argument("--merge", type=Path, nargs="+", help="skip the run; report on these --out files instead")
    args = ap.parse_args()
    if args.merge:
        parts = [json.loads(p.read_text()) for p in args.merge]
        result = {"rows": [r for p in parts for r in p["rows"]], "teams": parts[0]["teams"],
                  "test_seasons": parts[0]["test_seasons"], "importance": parts[0]["importance"]}
    else:
        if args.threads:
            SETTINGS["num_threads"] = args.threads
        result = run(args.seeds, trees=args.trees, committee=args.committee)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result))
    print(report(result))


if __name__ == "__main__":
    main()
