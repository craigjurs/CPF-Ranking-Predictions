"""Team-level "was a key player missing?" flags, read off the box scores.

Analogy: a box score is an **attendance sheet**. If the passer who threw
nearly every ball through week 6 has no passes in week 7, his seat was empty.
We never learn *why* (injury, suspension, benching), and we never store *who*.
The output is one row per team and game that says things like "the usual
quarterback did not start" and "a fifth of this team's usual production was
absent".

How "usual" is defined: the **season to date, before this game**. So a team's
first game of a season has no flags (they are blank), and a flag can only use
box scores that were public once the game had ended. Each flag row travels
with its game through ``Snapshot``, so a model can see it exactly when it can
see the game's score, never earlier.

The flags
---------
``qb_changed``            today's leader in pass attempts is not the season leader
``top_rb_missing``        the season leader in carries (quarterback aside) had none
``top_wr_missing``        the season leader in catches had none
``top_tackler_missing``   the season leader in tackles made none
``kicker_changed``        today's kicker is not the season's usual kicker
``production_missing_pct``  share of the team's season-to-date yards and tackles
                          that belonged to players who did not appear at all
``usage_drop``            the usual quarterback or runner did play, but with
                          under half his normal workload (hurt early, or pulled)

Flags are 1.0 or 0.0, the share is 0 to 1, and a blank (NaN) means "cannot
tell", for example when that part of the box score is missing.

Player ids are used only inside this module, to tell one seat from another.
Nothing here writes or returns a player id or name.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path

from cfp_rankings.pull_players import DATASET, STATS

NAN = float("nan")
PASS_ATT, PASS_YDS, CARRIES, RUSH_YDS, CATCHES, REC_YDS, TACKLES, KICKS = range(len(STATS))
USAGE_DROP_BELOW = 0.5  # "far less than usual" = under half the player's normal workload


@dataclass(frozen=True)
class Availability:
    """One team's flags for one game. See the module docstring."""

    qb_changed: float = NAN
    top_rb_missing: float = NAN
    top_wr_missing: float = NAN
    top_tackler_missing: float = NAN
    kicker_changed: float = NAN
    production_missing_pct: float = NAN
    usage_drop: float = NAN


FLAGS = tuple(f.name for f in fields(Availability))


def _leader(totals: dict[str, list[float]], stat: int, skip: str | None = None) -> str | None:
    """The player with the most of a stat so far. Ties go to the lower id, so it is repeatable."""
    best = max(((row[stat], -int(pid) if pid.isdigit() else 0, pid) for pid, row in totals.items()
                if pid != skip and row[stat] > 0), default=None)
    return best[2] if best else None


def _flag(condition: bool) -> float:
    return 1.0 if condition else 0.0


def game_flags(today: dict[str, list[float]], totals: dict[str, list[float]], played: dict[str, list[int]]) -> Availability:
    """Compare one game's box score with the season so far.

    ``today``   this game: player id -> stat row
    ``totals``  earlier games this season, summed: player id -> stat row
    ``played``  earlier games this season: player id -> number of games with
                at least one of each stat (so we can work out a per-game norm)
    """
    if not totals:
        return Availability()  # first game of the season: nothing to compare with

    def team_total(stat: int) -> float:
        return sum(row[stat] for row in today.values())

    def got(pid: str | None, stat: int) -> float:
        return today[pid][stat] if pid in today else 0.0

    def usual(pid: str, stat: int) -> float:
        return totals[pid][stat] / max(1, played[pid][stat])

    qb = _leader(totals, PASS_ATT)
    rb = _leader(totals, CARRIES, skip=qb)
    wr = _leader(totals, CATCHES)
    tackler = _leader(totals, TACKLES)
    kicker = _leader(totals, KICKS)

    qb_today = _leader(today, PASS_ATT)
    kicker_today = _leader(today, KICKS)
    has_rushing, has_catches, has_tackles = team_total(CARRIES) > 0, team_total(CATCHES) > 0, team_total(TACKLES) > 0

    # Share of what the team has produced so far that belongs to players who
    # are nowhere in today's box score. Offence and defence count equally.
    def missing_share(value) -> float:
        whole = sum(value(row) for row in totals.values())
        gone = sum(value(row) for pid, row in totals.items() if pid not in today)
        return gone / whole if whole > 0 else NAN

    offence = missing_share(lambda r: max(r[PASS_YDS], 0) + max(r[RUSH_YDS], 0) + max(r[REC_YDS], 0)) if has_rushing else NAN
    defence = missing_share(lambda r: r[TACKLES]) if has_tackles else NAN
    shares = [s for s in (offence, defence) if s == s]

    # A leader who appears but does far less than his norm.
    drops = []
    if qb and qb_today and got(qb, PASS_ATT) > 0:
        drops.append(got(qb, PASS_ATT) < USAGE_DROP_BELOW * usual(qb, PASS_ATT))
    if rb and has_rushing and got(rb, CARRIES) > 0:
        drops.append(got(rb, CARRIES) < USAGE_DROP_BELOW * usual(rb, CARRIES))

    return Availability(
        qb_changed=_flag(qb_today != qb) if qb and qb_today else NAN,
        top_rb_missing=_flag(got(rb, CARRIES) == 0) if rb and has_rushing else NAN,
        top_wr_missing=_flag(got(wr, CATCHES) == 0) if wr and has_catches else NAN,
        top_tackler_missing=_flag(got(tackler, TACKLES) == 0) if tackler and has_tackles else NAN,
        kicker_changed=_flag(kicker_today != kicker) if kicker and kicker_today else NAN,
        production_missing_pct=sum(shares) / len(shares) if shares else NAN,
        usage_drop=_flag(any(drops)) if qb and qb_today else NAN,
    )


def season_flags(box_rows: list[dict], game_order: dict[int, int]) -> dict[tuple[int, str], Availability]:
    """Flags for every (game id, team) of one season.

    ``box_rows``    slim box scores (see ``pull_players.slim``), any order
    ``game_order``  game id -> position in kickoff order. Box scores for
                    games not listed here are ignored.
    """
    by_team: dict[str, list[dict]] = {}
    for row in box_rows:
        if row["game_id"] in game_order and row["players"]:
            by_team.setdefault(row["team"], []).append(row)

    out: dict[tuple[int, str], Availability] = {}
    for team, rows in by_team.items():
        totals: dict[str, list[float]] = {}
        played: dict[str, list[int]] = {}
        for row in sorted(rows, key=lambda r: game_order[r["game_id"]]):
            today = row["players"]
            out[(row["game_id"], team)] = game_flags(today, totals, played)
            for pid, stats in today.items():  # only now does this game join "the season so far"
                tot = totals.setdefault(pid, [0.0] * len(STATS))
                cnt = played.setdefault(pid, [0] * len(STATS))
                for i, v in enumerate(stats):
                    tot[i] += v
                    cnt[i] += 1 if v > 0 else 0
    return out


def load_box_rows(year: int, raw_dir: Path) -> list[dict] | None:
    """Every cached slim box score of a season, or None if none were pulled."""
    folder = raw_dir / DATASET / str(year)
    files = sorted(folder.glob("*.json")) if folder.is_dir() else []
    if not files:
        return None
    return [row for f in files for row in json.loads(f.read_text())]
