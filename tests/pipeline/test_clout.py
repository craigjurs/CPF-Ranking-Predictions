"""The clout study: the gap between a ranking and on-field results."""

import numpy as np

from cfp_rankings.clout import CAP, Row, _capped, biggest_gaps, brand_scores, effect, team_seasons


def _row(season, team, cfp, resume, brand, power_conf, slot=10):
    return Row(season, slot, team, cfp, cfp, resume, resume, resume, 0, brand, power_conf)


def test_unranked_teams_count_as_26th():
    assert _capped({"A": 3}, "A") == 3
    assert _capped({"A": 3}, "B") == CAP
    assert _capped({"A": 90}, "A") == CAP


def test_brand_only_uses_earlier_seasons():
    finals = {2010: {"A": 1}, 2011: {"A": 1, "B": 26}, 2012: {"C": 1}}
    brand = brand_scores(finals, 2012)
    assert brand["A"] == 1.0  # first in both earlier seasons
    assert "C" not in brand  # 2012's own final poll is in the future


def test_effect_recovers_a_planted_tilt():
    # The judges give power-conference teams 3 extra spots and ignore brand.
    rng = np.random.default_rng(1)
    rows = []
    for i in range(200):
        brand, power_conf = float(rng.random()), bool(i % 2)
        resume = int(rng.integers(8, 20))
        rows.append(_row(2020 + i % 3, f"T{i}", resume - (3 if power_conf else 0), resume, brand, power_conf))
    result = effect(rows, lambda r: r.resume - r.cfp, draws=200)
    assert abs(result["power_conf"][0] - 3.0) < 1e-9
    assert abs(result["brand"][0]) < 1e-9
    assert team_seasons(rows) == 200


def test_biggest_gaps_needs_three_weeks():
    rows = [_row(2021, "Often", 5, 15, 0.0, True, slot=s) for s in (10, 11, 12)]
    rows.append(_row(2021, "Once", 1, 25, 0.0, True))
    over, _ = biggest_gaps(rows)
    assert [team for _, (_, team) in over] == ["Often"]
