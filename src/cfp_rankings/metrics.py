"""Score a predicted top 25 against the real one.

Three questions, from forgiving to strict:

* ``teams_right``   Did we pick the right 25 teams, ignoring order? (out of 25)
* ``avg_miss``      How many spots off were we, on average? Lower is better.
                    A team missing from one list is treated as rank 26.
* ``exact``         How many teams did we put in exactly the right spot?

Plus ``top4_right`` and ``top12_right``: the playoff cut lines (4 teams
through 2023, 12 from 2024).

Analogy: grading a bracket. ``teams_right`` asks whether you picked the right
teams to advance, ``exact`` asks whether you also nailed every seed, and
``avg_miss`` gives partial credit for being close.
"""

from __future__ import annotations

UNRANKED = 26


def score(predicted: list[str], actual: dict[str, int]) -> dict[str, float]:
    """``predicted`` is ordered best first. ``actual`` maps team -> real rank."""
    pred_rank = {team: i + 1 for i, team in enumerate(predicted[:25])}
    union = set(pred_rank) | set(actual)
    misses = [abs(pred_rank.get(t, UNRANKED) - actual.get(t, UNRANKED)) for t in union]

    def top_n(n: int) -> int:
        return len({t for t, r in pred_rank.items() if r <= n} & {t for t, r in actual.items() if r <= n})

    return {
        "teams_right": len(set(pred_rank) & set(actual)),
        "avg_miss": sum(misses) / len(misses),
        "exact": sum(1 for t, r in pred_rank.items() if actual.get(t) == r),
        "top4_right": top_n(4),
        "top12_right": top_n(12),
    }


METRICS = ("teams_right", "avg_miss", "exact", "top4_right", "top12_right")


def average(rows: list[dict[str, float]]) -> dict[str, float]:
    return {m: sum(r[m] for r in rows) / len(rows) for m in METRICS} if rows else {}
