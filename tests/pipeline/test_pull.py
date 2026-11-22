from cfp_rankings.pull import DATASETS, plan, raw_path


def test_cached_files_are_never_fetched_again(tmp_path):
    years = [2022, 2023]
    assert len(plan(years, tmp_path)) == len(years) * len(DATASETS)
    path = raw_path("games", 2022, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("[]")
    todo = plan(years, tmp_path)
    assert ("games", 2022) not in todo and len(todo) == len(years) * len(DATASETS) - 1
    assert len(plan(years, tmp_path, refresh=True)) == len(years) * len(DATASETS)
