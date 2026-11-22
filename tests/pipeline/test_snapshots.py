"""The leakage tests: a snapshot must never contain the future."""

from cfp_rankings.snapshots import FINAL_SLOT, era


def test_week2_poll_sees_only_week1_games(season):
    snap = season.snapshot("ap", 2)
    assert {g.id for g in snap.games} == {1, 2}


def test_game_labelled_early_but_played_late_is_hidden(season):
    # Game 4 says "week 1" but kicked off after week 2 began.
    assert 4 not in {g.id for g in season.snapshot("ap", 2).games}
    assert 4 in {g.id for g in season.snapshot("ap", FINAL_SLOT).games}


def test_snapshot_never_contains_the_poll_being_predicted(season):
    for rel in season.polls:
        snap = season.snapshot(rel.poll, rel.slot)
        assert not any(p.poll == rel.poll and p.slot >= rel.slot for p in snap.polls)


def test_no_poll_from_a_later_week_is_visible(season):
    for rel in season.polls:
        snap = season.snapshot(rel.poll, rel.slot)
        assert all(p.slot <= rel.slot for p in snap.polls)


def test_cfp_sees_same_week_ap_but_ap_does_not_see_cfp_or_coaches(season):
    cfp = season.snapshot("cfp", 2)
    assert {(p.poll, p.slot) for p in cfp.polls} >= {("ap", 2), ("coaches", 2)}
    ap = season.snapshot("ap", 2)
    assert all(p.slot < 2 for p in ap.polls)


def test_every_game_in_a_snapshot_kicked_off_before_the_week_began(season):
    for rel in season.polls:
        if rel.slot == FINAL_SLOT:
            continue
        for g in season.snapshot(rel.poll, rel.slot).games:
            assert g.start < season.week_starts[rel.slot]


def test_only_the_three_fbs_polls_load_and_postseason_cfp_is_dropped(season):
    assert {p.poll for p in season.polls} == {"ap", "coaches", "cfp"}
    assert season.release("cfp", FINAL_SLOT) is None
    assert season.release("ap", FINAL_SLOT) is not None


def test_spread_is_the_median_across_books(season):
    g = next(g for g in season.games if g.id == 1)
    assert g.spread_home == -11
    assert g.spread_open_home == -9


def test_records(season):
    rec = season.snapshot("ap", 2).records()
    assert rec["Team 26"] == (1, 0) and rec["Team 03"] == (0, 1)


def test_era():
    assert [era(y) for y in (2013, 2014, 2023, 2024)] == ["bcs", "cfp4", "cfp4", "cfp12"]
