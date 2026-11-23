"""Walk-forward backtest.

    uv run python -m cfp_rankings.backtest

Analogy: a flight simulator that replays history one week at a time. To grade
the 2019 season the model may study 2005 to 2018 only. Then it "flies" 2019
poll by poll, and before each poll it sees only what was public that morning
(a ``Snapshot``). Then 2021 with everything earlier as study material, and so
on. It never trains on the future and never sees the answer it is graded on.

    study 2005            -> fly 2006
    study 2005-2006       -> fly 2007
    ...
    study 2005-2022       -> fly 2023      (2020 is skipped throughout)

Which seasons are used:

* 2005 is the first season. 2000 to 2004 are on disk but CFBD's poll weeks and
  game weeks don't line up reliably there (see docs/baseline-results.md).
* 2020 is dropped, both as study material and as a test. COVID schedules made
  it unlike any other season.
* 2024 and 2025 are the final exam. They stay in a sealed envelope: this
  script refuses to score them unless you pass ``--include-holdout``, and that
  should happen once, at the very end, for the model we finally pick.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cfp_rankings.baselines import CopyPoll, Example, Persistence, WinLossRule
from cfp_rankings.metrics import METRICS, average, score
from cfp_rankings.snapshots import Season, era, load_seasons

FIRST_SEASON = 2005  # first season with reliably aligned poll and game weeks
DROPPED = (2020,)  # COVID season
HOLDOUT = (2024, 2025)
DEV_SEASONS = tuple(y for y in range(FIRST_SEASON, HOLDOUT[0]) if y not in DROPPED)


def examples(season: Season, poll: str) -> list[Example]:
    """(snapshot, answer) pairs for every release of ``poll`` in a season."""
    return [(season.snapshot(poll, rel.slot), rel) for rel in season.releases(poll)]


def walk_forward(seasons: dict[int, Season], poll: str, make_model, test_seasons) -> list[dict]:
    """Return one row per predicted poll release."""
    rows = []
    for test_year in test_seasons:
        if not seasons[test_year].releases(poll):
            continue  # e.g. no CFP rankings before 2014
        train = [ex for y in sorted(seasons) if y < test_year for ex in examples(seasons[y], poll)]
        model = make_model()
        model.fit(train)  # past seasons only
        for snap, actual in examples(seasons[test_year], poll):
            predicted = model.predict(snap)  # the model never sees `actual`
            if predicted is None:
                continue  # nothing to start from (the preseason poll)
            rows.append({"season": test_year, "slot": snap.slot, "poll": poll, "model": model.name,
                         **score(predicted, actual.rank_of())})
        knobs = getattr(model, "knobs", None)
        if knobs is not None and getattr(model, "tune", False) and rows:
            rows[-1]["knobs"] = knobs.__dict__
    return rows


def model_menu(poll: str, baselines_only: bool = False, cache: dict | None = None) -> list:
    """Factories for the models that make sense for each poll.

    ``cache`` is shared by every learned model so that scouting cards and
    Stage 3's editors are built once, not once per test season.
    """
    if poll == "cfp":
        # The first CFP ranking of a season has no "last week", so the
        # carry-forward models start from that Sunday's AP poll.
        return [
            lambda: CopyPoll("ap"),
            lambda: Persistence(fallback="ap"),
            lambda: WinLossRule(fallback="ap"),
            lambda: WinLossRule(tune=True, fallback="ap"),
        ]
    menu = [lambda: Persistence(), lambda: WinLossRule(), lambda: WinLossRule(tune=True)]
    if not baselines_only:
        # Imported here so the baselines still run without numpy or LightGBM.
        from cfp_rankings.poll_model import PollRanker

        menu.append(lambda: PollRanker(cache=cache))
    return menu


def run(seasons: dict[int, Season], test_seasons, baselines_only: bool = False) -> list[dict]:
    rows = []
    cache: dict = {}
    for poll in ("ap", "coaches", "cfp"):
        menu = model_menu(poll, baselines_only, cache)
        if poll == "cfp" and not baselines_only:
            # Imported here so the baselines still run without numpy.
            from cfp_rankings.cfp_model import CarryForward, CfpRanker

            # AP history for every season, used only for what carries over
            # between years. The model never reads a season it is predicting.
            background = [ex for y in sorted(seasons) for ex in examples(seasons[y], "ap")]
            menu += [CarryForward, lambda: CfpRanker(background, cache=cache)]
        for make_model in menu:
            rows += walk_forward(seasons, poll, make_model, test_seasons)
    return rows


def summarize(rows: list[dict], by=("poll", "model")) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(tuple(r[k] for k in by), []).append(r)
    return [{**dict(zip(by, key)), "polls": len(g), **average(g)} for key, g in groups.items()]


def format_table(summary: list[dict], by=("poll", "model")) -> str:
    head = [*by, "polls", *METRICS]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for s in summary:
        cells = [str(s[k]) for k in by] + [str(s["polls"])] + [f"{s[m]:.2f}" for m in METRICS]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Walk-forward backtest of the baselines, the Stage 2 poll model and the Stage 3 CFP model.")
    ap.add_argument("--baselines-only", action="store_true", help="skip the learned model (much faster)")
    ap.add_argument("--include-holdout", action="store_true", help="also score 2024-2025 (the sealed final exam)")
    ap.add_argument("--out", type=Path, help="write per-poll rows as JSON")
    args = ap.parse_args()

    years = DEV_SEASONS + (HOLDOUT if args.include_holdout else ())
    seasons = load_seasons(years)
    # The first season has nothing to study from, so testing starts one later.
    test_seasons = [y for y in years if y > FIRST_SEASON]
    rows = run(seasons, test_seasons, args.baselines_only)
    for r in rows:
        r["era"] = era(r["season"])
    print(f"Walk-forward test seasons: {test_seasons[0]}-{test_seasons[-1]}, without {DROPPED}\n")
    print(format_table(summarize(rows)))
    print("\nBy era:\n")
    print(format_table(summarize(rows, by=("poll", "era", "model")), by=("poll", "era", "model")))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
