from cfp_rankings.pull import DATASETS, ONE_OFF, plan, raw_path


def test_cached_files_are_never_fetched_again(tmp_path):
    years = [2022, 2023]
    assert len(plan(years, tmp_path)) == len(years) * len(DATASETS) + len(ONE_OFF)
    path = raw_path("games", 2022, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("[]")
    todo = plan(years, tmp_path)
    assert ("games", 2022) not in todo and len(todo) == len(years) * len(DATASETS) + len(ONE_OFF) - 1
    assert len(plan(years, tmp_path, refresh=True)) == len(years) * len(DATASETS) + len(ONE_OFF)


def test_lines_are_not_requested_before_they_exist(tmp_path):
    assert ("lines", 2005) not in plan([2005], tmp_path)
    assert ("lines", 2013) in plan([2013], tmp_path)


def test_tv_listings_are_not_requested_before_they_exist(tmp_path):
    assert ("media", 2002) not in plan([2002], tmp_path)
    assert ("media", 2003) in plan([2003], tmp_path)


def test_the_venue_list_is_pulled_once_not_once_per_season(tmp_path):
    assert plan([2022, 2023], tmp_path).count(("venues", None)) == 1
    raw_path("venues", None, tmp_path).write_text("[]")
    assert ("venues", None) not in plan([2022, 2023], tmp_path)
