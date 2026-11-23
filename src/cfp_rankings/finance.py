"""School money: athletic department finances from the federal EADA survey.

Every college that takes federal student aid must report what its athletic
department earns and spends, sport by sport. The US Department of Education
publishes the files for free, and unlike the newspaper databases they include
private schools such as Notre Dame, USC and Stanford.

This module downloads one file per academic year, keeps four numbers per
school (football revenue and spending, and the whole department's revenue and
spending) and stores them in ``data/raw/eada/`` (gitignored).

Caution: schools have leeway in how they fill the form in, so treat the
figures as a good ranking of who is rich, not as audited accounts.

Reading the spreadsheets needs ``openpyxl``, which is in the ``finance`` extra::

    uv run --extra finance python -m cfp_rankings.finance
"""

from __future__ import annotations

import io
import json
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from cfp_rankings.snapshots import RAW_DIR

EADA_DIR = RAW_DIR / "eada"
BASE = "https://ope.ed.gov/athletics/api/dataFiles/"
TEAM_IDS = Path(__file__).with_name("eada_teams.json")  # CFBD team name -> federal school id


def _rows(workbook_bytes: bytes):
    import openpyxl

    sheet = openpyxl.load_workbook(io.BytesIO(workbook_bytes), read_only=True).worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    header = [str(h) for h in next(rows)]
    for row in rows:
        yield dict(zip(header, row))


def _member(archive: zipfile.ZipFile, name: str) -> bytes:
    match = next(n for n in archive.namelist() if n.lower().split("/")[-1] == name)
    return archive.read(match)


def parse(archive_bytes: bytes) -> dict[str, dict]:
    """Four money figures per school, keyed by the federal school id."""
    archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    out: dict[str, dict] = {}
    for row in _rows(_member(archive, "instlevel.xlsx")):
        out[str(row["unitid"])] = {
            "name": row["institution_name"],
            "level": row.get("classification_name"),
            "total_revenue": row.get("GRND_TOTAL_REVENUE"),
            "total_expense": row.get("GRND_TOTAL_EXPENSE"),
        }
    for row in _rows(_member(archive, "schools.xlsx")):
        if row.get("Sports") == "Football" and str(row["unitid"]) in out:
            out[str(row["unitid"])].update(football_revenue=row.get("REV_MEN"), football_expense=row.get("EXP_MEN"))
    return out


def pull(years, out_dir: Path = EADA_DIR) -> None:
    """Download and trim each academic year not already cached.

    ``year`` is the year the academic year ends: 2022 means 2021-22.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(BASE + "fileList", timeout=60) as response:
        listing = json.load(response)
    for year in years:
        path = out_dir / f"{year}.json"
        if path.exists():
            continue
        name = next(f["FileName"] for f in listing if f["Year"] == year and "Combined" not in f["FileName"])
        with urllib.request.urlopen(BASE + "file?fileName=" + urllib.parse.quote(name), timeout=300) as response:
            path.write_text(json.dumps(parse(response.read())))
        print(f"saved {path.name} from {name}")


def load(year: int, raw_dir: Path = RAW_DIR) -> dict[str, dict]:
    return json.loads((raw_dir / "eada" / f"{year}.json").read_text())


def team_money(season: int, raw_dir: Path = RAW_DIR, ids: dict[str, str] | None = None) -> dict[str, dict]:
    """Each team's finances as known before ``season`` kicked off.

    The 2021-22 academic year is reported in early 2023, so the newest file a
    2023 ranking could have known about is the one ending in 2022: ``season - 1``.
    A school missing from that file falls back to its most recent earlier one.
    The three service academies do not file and are left out.
    """
    ids = ids if ids is not None else json.loads(TEAM_IDS.read_text())
    out: dict[str, dict] = {}
    years = sorted((int(p.stem) for p in (raw_dir / "eada").glob("*.json") if int(p.stem) < season), reverse=True)
    for year in years:
        schools = load(year, raw_dir)
        for team, uid in ids.items():
            if team not in out and schools.get(uid, {}).get("total_revenue"):
                out[team] = schools[uid]
    return out


def money_scores(season: int, raw_dir: Path = RAW_DIR, field: str = "total_revenue") -> dict[str, float]:
    """Money on a "doublings" scale, centred on the average team that season.

    +1 means twice the athletic revenue of the typical team in the study,
    -1 means half. Using doublings keeps one giant budget from dominating,
    and centring each season removes inflation and the 2020-21 COVID dip.
    """
    import math

    logs = {t: math.log2(v[field]) for t, v in team_money(season, raw_dir).items() if v.get(field)}
    if not logs:
        return {}
    mean = sum(logs.values()) / len(logs)
    return {t: x - mean for t, x in logs.items()}


if __name__ == "__main__":
    pull(range(2013, 2023))
