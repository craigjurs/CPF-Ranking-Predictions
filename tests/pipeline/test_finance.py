"""School finances from the federal EADA files."""

import io
import json
import zipfile

import pytest

from cfp_rankings.finance import money_scores, parse, team_money


def _write(raw_dir, year, schools):
    (raw_dir / "eada").mkdir(exist_ok=True)
    (raw_dir / "eada" / f"{year}.json").write_text(json.dumps(schools))


def test_parse_keeps_football_and_department_totals():
    openpyxl = pytest.importorskip("openpyxl")

    def sheet(rows):
        book = openpyxl.Workbook()
        for row in rows:
            book.active.append(row)
        out = io.BytesIO()
        book.save(out)
        return out.getvalue()

    inst = sheet([["unitid", "institution_name", "classification_name", "GRND_TOTAL_REVENUE", "GRND_TOTAL_EXPENSE"],
                  [1, "Big State", "NCAA Division I-FBS", 200, 180]])
    sports = sheet([["unitid", "Sports", "REV_MEN", "EXP_MEN"], [1, "Football", 120, 60], [1, "Golf", 1, 2]])
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("InstLevel.xlsx", inst)
        z.writestr("Schools.xlsx", sports)
    assert parse(archive.getvalue()) == {"1": {"name": "Big State", "level": "NCAA Division I-FBS", "total_revenue": 200,
                                               "total_expense": 180, "football_revenue": 120, "football_expense": 60}}


def test_team_money_never_uses_a_file_from_the_future(tmp_path):
    _write(tmp_path, 2021, {"1": {"total_revenue": 100}})
    _write(tmp_path, 2022, {"1": {"total_revenue": 200}})
    _write(tmp_path, 2023, {"1": {"total_revenue": 999}})
    ids = {"Big State": "1"}
    assert team_money(2023, tmp_path, ids)["Big State"]["total_revenue"] == 200  # the file ending 2022
    assert team_money(2022, tmp_path, ids)["Big State"]["total_revenue"] == 100


def test_team_money_falls_back_to_an_earlier_year(tmp_path):
    _write(tmp_path, 2021, {"1": {"total_revenue": 100}})
    _write(tmp_path, 2022, {"2": {"total_revenue": 50}})
    money = team_money(2023, tmp_path, {"Big State": "1", "Small Tech": "2", "Academy": "3"})
    assert money["Big State"]["total_revenue"] == 100
    assert "Academy" not in money  # never filed


def test_money_scores_are_doublings_around_the_average(tmp_path, monkeypatch):
    import cfp_rankings.finance as finance

    ids = tmp_path / "ids.json"
    ids.write_text(json.dumps({"Rich": "1", "Poor": "2"}))
    monkeypatch.setattr(finance, "TEAM_IDS", ids)
    _write(tmp_path, 2022, {"1": {"total_revenue": 400}, "2": {"total_revenue": 100}})
    scores = money_scores(2023, tmp_path)
    assert scores == pytest.approx({"Rich": 1.0, "Poor": -1.0})  # four times apart is two doublings


def test_every_mapped_team_has_a_school_id():
    from cfp_rankings.finance import TEAM_IDS

    ids = json.loads(TEAM_IDS.read_text())
    assert len(ids) > 80 and all(uid.isdigit() for uid in ids.values())
    assert len(set(ids.values())) == len(ids)  # no two teams share a school
