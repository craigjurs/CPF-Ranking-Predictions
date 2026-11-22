"""Point-in-time snapshots: what was knowable just before a poll came out.

The danger this module exists to prevent is *leakage*: accidentally letting a
model see information from after the moment it is supposed to be predicting.

Analogy: a sealed newspaper archive. To predict the poll released on a given
Sunday, you may read every paper printed up to that Sunday morning and nothing
after. ``Snapshot`` is the librarian: you tell it which poll you are about to
predict, and it hands over only the papers that existed by then. Models get a
``Snapshot`` and nothing else, so they cannot peek even by accident.

How CFBD numbers things (checked against the data):

* The "week N" poll is released *before* week N's games and reflects games
  through week N-1. Week 1 is the preseason poll.
* The final AP and Coaches polls (after the bowls) are stored as postseason
  week 1.
* The CFP committee publishes on Tuesday, two days after that week's AP and
  Coaches polls. So when predicting the week N CFP ranking, the week N AP and
  Coaches polls are already public. The reverse is not true.

Timeline for one week::

    Sat           Sun                    Tue                Sat
    week N-1  ->  AP + Coaches week N -> CFP week N    ->   week N games
    games         (sees games < N)       (sees games < N,
                                          plus Sunday's polls)
"""

from __future__ import annotations

import datetime as dt
import json
import statistics
from dataclasses import dataclass
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

POLL_NAMES = {"AP Top 25": "ap", "Coaches Poll": "coaches", "Playoff Committee Rankings": "cfp"}
POLLS = ("ap", "coaches", "cfp")

# A "slot" puts every poll release of a season on one number line.
# Regular-season week N is slot N. The final (post-bowl) poll is slot 100.
FINAL_SLOT = 100


def slot_of(season_type: str, week: int) -> int | None:
    if season_type == "regular":
        return week
    if season_type == "postseason":
        return FINAL_SLOT
    return None  # e.g. 2020 "spring_regular" games; not part of the FBS poll season


@dataclass(frozen=True)
class Game:
    id: int
    season: int
    slot: int  # the week it was played in, as a slot
    start: dt.datetime
    home: str
    away: str
    home_points: int
    away_points: int
    neutral: bool
    home_fbs: bool
    away_fbs: bool
    # Sportsbook closing spread from the home team's side: -7 means the home
    # team was favored by 7. Set before kickoff, so it is safe to use once
    # the game has been played.
    spread_home: float | None = None
    spread_open_home: float | None = None
    over_under: float | None = None
    home_elo_pre: float | None = None
    away_elo_pre: float | None = None
    home_elo_post: float | None = None
    away_elo_post: float | None = None

    @property
    def winner(self) -> str | None:
        if self.home_points == self.away_points:
            return None
        return self.home if self.home_points > self.away_points else self.away

    @property
    def loser(self) -> str | None:
        if self.home_points == self.away_points:
            return None
        return self.away if self.home_points > self.away_points else self.home

    def teams(self) -> tuple[str, str]:
        return (self.home, self.away)


@dataclass(frozen=True)
class RankedTeam:
    rank: int
    team: str
    points: int | None = None
    first_place_votes: int | None = None


@dataclass(frozen=True)
class PollRelease:
    season: int
    poll: str  # "ap", "coaches" or "cfp"
    slot: int
    ranks: tuple[RankedTeam, ...]  # sorted best first

    def teams(self) -> list[str]:
        return [r.team for r in self.ranks]

    def rank_of(self) -> dict[str, int]:
        return {r.team: r.rank for r in self.ranks}


def _parse_time(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


def _median(values) -> float | None:
    values = [v for v in values if isinstance(v, (int, float))]
    return statistics.median(values) if values else None


class Season:
    """One season of raw data, parsed. This object knows the future.

    Models must never be handed a ``Season``. They get ``season.snapshot(...)``.
    """

    def __init__(self, year: int, games: list[Game], polls: list[PollRelease], week_starts: dict[int, dt.datetime]):
        self.year = year
        self.games = sorted(games, key=lambda g: (g.start, g.id))
        self.polls = sorted(polls, key=lambda p: (p.slot, POLLS.index(p.poll)))
        self.week_starts = week_starts  # slot -> first moment of that week

    # ---------- loading ----------
    @classmethod
    def load(cls, year: int, raw_dir: Path = RAW_DIR) -> "Season":
        def read(dataset):
            return json.loads((raw_dir / dataset / f"{year}.json").read_text())

        return cls.from_raw(year, read("games"), read("lines"), read("rankings"), read("calendar"))

    @classmethod
    def from_raw(cls, year: int, raw_games, raw_lines, raw_rankings, raw_calendar) -> "Season":
        lines = {row["id"]: row.get("lines") or [] for row in raw_lines}
        games = []
        for g in raw_games:
            slot = slot_of(g["seasonType"], g["week"])
            if slot is None or not g.get("completed") or g.get("homePoints") is None or g.get("awayPoints") is None:
                continue
            books = lines.get(g["id"], [])
            games.append(
                Game(
                    id=g["id"],
                    season=year,
                    slot=slot,
                    start=_parse_time(g["startDate"]),
                    home=g["homeTeam"],
                    away=g["awayTeam"],
                    home_points=g["homePoints"],
                    away_points=g["awayPoints"],
                    neutral=bool(g.get("neutralSite")),
                    home_fbs=g.get("homeClassification") == "fbs",
                    away_fbs=g.get("awayClassification") == "fbs",
                    spread_home=_median(b.get("spread") for b in books),
                    spread_open_home=_median(b.get("spreadOpen") for b in books),
                    over_under=_median(b.get("overUnder") for b in books),
                    home_elo_pre=g.get("homePregameElo"),
                    away_elo_pre=g.get("awayPregameElo"),
                    home_elo_post=g.get("homePostgameElo"),
                    away_elo_post=g.get("awayPostgameElo"),
                )
            )

        polls = []
        for week in raw_rankings:
            slot = slot_of(week["seasonType"], week["week"])
            if slot is None:
                continue
            for p in week["polls"]:
                kind = POLL_NAMES.get(p["poll"])
                if kind is None or not p["ranks"]:
                    continue
                if kind == "cfp" and slot == FINAL_SLOT:
                    # The committee publishes nothing after the bowls. CFBD's
                    # postseason "CFP" rows are not a real release, so skip them.
                    continue
                ranks = tuple(
                    RankedTeam(r["rank"], r["school"], r.get("points"), r.get("firstPlaceVotes"))
                    for r in sorted(p["ranks"], key=lambda r: (r["rank"], r["school"]))
                )
                polls.append(PollRelease(year, kind, slot, ranks))

        week_starts = {}
        for c in raw_calendar:
            slot = slot_of(c["seasonType"], c["week"])
            if slot is not None:
                week_starts[slot] = _parse_time(c["startDate"])
        return cls(year, games, polls, week_starts)

    # ---------- the one door models are allowed through ----------
    def releases(self, poll: str) -> list[PollRelease]:
        return [p for p in self.polls if p.poll == poll]

    def release(self, poll: str, slot: int) -> PollRelease | None:
        return next((p for p in self.polls if p.poll == poll and p.slot == slot), None)

    def games_known_at(self, slot: int) -> list[Game]:
        """Games already played when the slot's polls came out.

        Two locks on the door, both must open:
        1. the game's week is earlier than the poll's week, and
        2. the game kicked off before that poll week began (guards against a
           game that was labelled with an early week but played late).
        """
        if slot == FINAL_SLOT:
            return list(self.games)
        cutoff = self.week_starts.get(slot)
        return [g for g in self.games if g.slot < slot and (cutoff is None or g.start < cutoff)]

    def polls_known_at(self, poll: str, slot: int) -> list[PollRelease]:
        """Poll releases already public when (poll, slot) came out."""
        known = [p for p in self.polls if p.slot < slot]
        if poll == "cfp":  # Tuesday release: Sunday's AP and Coaches are out
            known += [p for p in self.polls if p.slot == slot and p.poll in ("ap", "coaches")]
        return known

    def snapshot(self, poll: str, slot: int) -> "Snapshot":
        return Snapshot(self.year, poll, slot, tuple(self.games_known_at(slot)), tuple(self.polls_known_at(poll, slot)))


@dataclass(frozen=True)
class Snapshot:
    """Everything knowable just before one poll release. Nothing else."""

    season: int
    poll: str  # the poll being predicted
    slot: int  # the release being predicted
    games: tuple[Game, ...]
    polls: tuple[PollRelease, ...]

    def latest(self, poll: str, before_slot: int | None = None) -> PollRelease | None:
        """Most recent known release of ``poll`` (optionally strictly before a slot)."""
        options = [p for p in self.polls if p.poll == poll and (before_slot is None or p.slot < before_slot)]
        return max(options, key=lambda p: p.slot) if options else None

    def games_since(self, slot: int) -> list[Game]:
        """Games played after the poll at ``slot`` came out (week >= slot)."""
        return [g for g in self.games if g.slot >= slot]

    def records(self) -> dict[str, tuple[int, int]]:
        """Season (wins, losses) for every team that has played."""
        rec: dict[str, list[int]] = {}
        for g in self.games:
            if g.winner is None:
                continue
            rec.setdefault(g.winner, [0, 0])[0] += 1
            rec.setdefault(g.loser, [0, 0])[1] += 1
        return {t: (w, l) for t, (w, l) in rec.items()}

    def elo(self) -> dict[str, float]:
        """Each team's Elo rating after its most recent known game."""
        out: dict[str, float] = {}
        for g in self.games:  # already in kickoff order
            if g.home_elo_post is not None:
                out[g.home] = g.home_elo_post
            if g.away_elo_post is not None:
                out[g.away] = g.away_elo_post
        return out

    def fbs_teams(self) -> set[str]:
        return {g.home for g in self.games if g.home_fbs} | {g.away for g in self.games if g.away_fbs}


def load_seasons(years, raw_dir: Path = RAW_DIR) -> dict[int, Season]:
    return {y: Season.load(y, raw_dir) for y in years}
