# Core data and the naive baseline

This is step 3 (pull the core data) and step 4 (build the bar to beat) of the plan.

## The one-paragraph version

Voters don't rank teams from scratch each week. They take last week's ballot and edit it. So the simplest sensible forecast is "last week's poll, with the losers pushed down". That rule, with no machine learning at all, already gets about **23 of the 25 teams right** and is off by about **1.4 spots per team**. That is the bar. Any ML model we build next has to beat it to be worth having.

**Analogy:** forecasting tomorrow's weather as "same as today" is right most of the time. A meteorologist only earns a salary by beating that. This PR builds our "same as today", plus the fair test that measures it.

## What was pulled

Twelve seasons, 2014 to 2025 (2014 is the first CFP season), four files each:

| Dataset | What it is | Rows per season |
|---|---|---|
| `rankings` | Every weekly AP, Coaches and CFP poll | 15 to 17 poll weeks |
| `games` | Every game with an FBS team, regular season and bowls, with scores | about 900 |
| `lines` | Sportsbook spreads, totals and moneylines | about 900 to 1,600 |
| `calendar` | Start date of each week | 16 or so |

**Quota used: 49 API calls** (48 files, plus one test call), out of roughly 1,000 a month. Pulling a whole season per call instead of week by week is what keeps this small. Everything is cached in `data/raw/` (gitignored), and re-running the pull makes zero calls.

The 2026 season in progress was not pulled. A cached file of a half-finished season would go stale, so that needs a small "refresh this week" step when we start live predictions.

## No peeking: point-in-time snapshots

The biggest way to fool yourself in this project is **leakage**: letting the model see something that wasn't known yet when the poll came out. A leaky model looks brilliant in testing and then fails live.

**Analogy:** a sealed newspaper archive. To predict Sunday's poll you may read every paper printed up to Sunday morning, and nothing after. The `Snapshot` class is the librarian. You say which poll you're about to predict, and it hands over only what existed by then. Models receive a `Snapshot` and nothing else, so they can't peek even by accident.

The timeline for one week:

```
Sat            Sun                     Tue                 Sat
week N-1   ->  AP + Coaches, week N -> CFP, week N     ->  week N games
games          (sees games before N)   (sees games before N,
                                        plus Sunday's two polls)
```

Three rules, each backed by a test in `tests/pipeline/test_snapshots.py`:

1. **A poll sees only games from earlier weeks**, and only if they kicked off before that poll's week began. The second lock caught a real case: the 2019 Army-Navy game is labelled "week 15" but was played a week after the final rankings.
2. **A poll never sees itself or any later poll.**
3. **The CFP ranking may see that week's AP and Coaches polls** (Tuesday comes after Sunday). AP and Coaches may not see each other's same-week release.

Sportsbook spreads are attached only to games already played. A closing spread is set before kickoff, so once the game is over it is safe history ("they were favored by 7 and lost"). Next week's opening lines are deliberately left out for now, because CFBD doesn't timestamp them and we can't prove they were posted before the poll.

`python -m cfp_rankings.export` writes two spreadsheets (`games.csv`, `polls.csv`) to `data/processed/`. Every game row has a `known_from_slot` stamp: the first poll allowed to see it.

## The baselines

| Baseline | In plain words |
|---|---|
| **Same as last week** | Copy last week's poll unchanged. The floor. |
| **Win/loss rule, fixed** | Copy last week's poll. A ranked team that loses to a ranked team drops 5.5 spots, or 9.5 if it loses to an unranked team. Beating a ranked team gains 1.5. Unranked teams that didn't lose line up just outside the top 25, fewest losses first, and fill the gaps. |
| **Win/loss rule, tuned** | The same rule, but those numbers are chosen from earlier seasons instead of by hand. |
| **Copy this week's AP** (CFP only) | The committee's Tuesday ranking = Sunday's AP poll. |

For the CFP, the first ranking of each season has no "last week", so the carry-forward baselines start from that Sunday's AP poll.

### One real week, to make it concrete

AP poll, week 2 of 2023, win/loss rule. LSU (5th) lost to ranked Florida State, Clemson (9th) lost to unranked Duke.

| Team | Last week | Rule predicted | Actually |
|---|---|---|---|
| Florida State (beat LSU) | 8 | 6 | 4 |
| LSU (lost to a ranked team) | 5 | 9 | 14 |
| Clemson (lost to an unranked team) | 9 | 17 | 25 |
| Duke (unranked, beat Clemson) | none | 23 | 21 |
| Colorado (unranked, beat TCU) | none | 24 | 22 |

The rule picked all 25 teams that week but under-reacted every time: voters punished the losers and rewarded the winners more than a flat number of spots. *How much* voters react (blowout or close game, strong or weak opponent, early or late season) is exactly what an ML model can learn and this rule can't.

## The fair test: walk-forward backtest

**Analogy:** a flight simulator that replays history. To grade the 2019 season the model may study 2014 to 2018 only, then it "flies" 2019 one poll at a time, seeing only that morning's snapshot. Then 2020 with 2014 to 2019 as study material, and so on. It never trains on the future.

Test seasons are 2015 to 2023 (2014 has nothing earlier to study). **2024 and 2025 are the sealed final exam** and were not scored. The backtest refuses to touch them without an explicit `--include-holdout` flag.

How to read the columns: `teams right` is how many of the 25 teams we picked, ignoring order. `average miss` is how many spots off we were per team (lower is better, a team missing from one list counts as 26th). `exact` is how many teams landed in exactly the right spot. `top 4` and `top 12` are the playoff cut lines.

### AP Top 25 (136 polls)

| Baseline | Teams right (of 25) | Average miss | Exact spot | Top 4 right | Top 12 right |
|---|---|---|---|---|---|
| Same as last week | 22.25 | 2.73 | 5.68 | 3.38 | 10.53 |
| **Win/loss rule, fixed** | **23.17** | **1.47** | **9.15** | 3.63 | 11.33 |
| Win/loss rule, tuned | 23.25 | 1.50 | 8.40 | 3.63 | 11.20 |

### Coaches Poll (136 polls)

| Baseline | Teams right (of 25) | Average miss | Exact spot | Top 4 right | Top 12 right |
|---|---|---|---|---|---|
| Same as last week | 22.49 | 2.68 | 5.74 | 3.46 | 10.54 |
| Win/loss rule, fixed | 23.22 | 1.39 | 9.35 | 3.69 | 11.32 |
| **Win/loss rule, tuned** | 23.22 | **1.36** | 9.23 | 3.67 | 11.29 |

### CFP rankings (51 rankings)

| Baseline | Teams right (of 25) | Average miss | Exact spot | Top 4 right | Top 12 right |
|---|---|---|---|---|---|
| Copy this week's AP | 23.49 | 1.61 | 8.47 | 3.67 | 11.35 |
| Same as last week's CFP | 22.94 | 2.26 | 6.49 | 3.25 | 10.84 |
| **Last week's CFP + win/loss rule, fixed** | 23.35 | **1.43** | 8.78 | 3.57 | 11.45 |
| Last week's CFP + win/loss rule, tuned | 23.47 | 1.47 | 8.02 | 3.49 | 11.45 |

## What the numbers say

1. **Adjusting for wins and losses roughly halves the error.** For AP, the average miss falls from 2.73 to 1.47 spots, and the rule beat "same as last week" in 135 of 136 polls. So win/loss carries most of the week-to-week signal, as expected.
2. **Tuning the knobs bought nothing.** The tuned and hand-set versions are within noise of each other (each wins about half the weeks). That is a useful finding: the remaining error is not about picking better constants. It is about things this rule cannot see, such as margin of victory, opponent quality and time of season.
3. **For the CFP, the answer depends on the week.** In the first ranking of a season, copying AP is all we have, and it is the weakest spot (average miss 1.99, and only 3.1 of the top 4 right). The committee starts from its own blank sheet. In later weeks, last week's CFP plus the win/loss rule (1.31) beats copying AP (1.53). So the committee is more consistent with *itself* than with the AP voters. That supports the plan to model the CFP on top of the AP and Coaches models rather than as a copy of them.
4. **Early season and the final poll are the hard parts.** For AP the average miss is 1.93 in weeks 2 to 5, about 1.25 mid-season, and 1.80 for the post-bowl final poll, where several weeks of bowl results land at once.

**The bar for the ML models:** about 1.4 to 1.5 spots of average miss and about 9 exact placements for AP and Coaches, and about 1.4 for the CFP.

## Known gaps

- **The preseason poll is not predicted.** There is no "last week" to start from. It needs its own approach (last season's final poll, returning talent).
- **No "others receiving votes".** CFBD returns only the top 25, so we can't see who was 26th to 35th. The rule orders newcomers by fewest losses, then Elo.
- **2020** was a broken season (staggered conference starts, a missing week 2 poll). It is kept in, and its scores are the worst of any season, as you'd expect.
- **CFBD has no CFP ranking for 2019 week 14.** The code steps over missing weeks by using the most recent earlier release.
- **51 CFP rankings is a small sample.** Differences of 0.1 between CFP baselines are not meaningful.

## Run it yourself

```sh
uv run python -m cfp_rankings.pull --dry-run   # how many API calls would this cost? (0 once cached)
uv run python -m cfp_rankings.pull             # fetch anything missing, through the CFBD MCP server
uv run python -m cfp_rankings.export           # write the tidy CSVs
uv run python -m cfp_rankings.backtest         # print the tables above
uv run --extra dev python -m pytest -q         # pipeline tests (no network)
```
