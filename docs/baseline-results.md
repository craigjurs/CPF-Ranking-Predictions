# Core data and the naive baseline

This is step 3 (pull the core data) and step 4 (build the bar to beat) of the plan.

## The one-paragraph version

Voters don't rank teams from scratch each week. They take last week's ballot and edit it. So the simplest sensible forecast is "last week's poll, with the losers pushed down". That rule, with no machine learning at all, already gets about **23 of the 25 teams right** and is off by about **1.4 spots per team**, tested on 17 seasons. That is the bar. Any ML model we build next has to beat it to be worth having.

**Analogy:** forecasting tomorrow's weather as "same as today" is right most of the time. A meteorologist only earns a salary by beating that. This PR builds our "same as today", plus the fair test that measures it.

## What was pulled

Twenty-six seasons, 2000 to 2025:

| Dataset | What it is | Seasons | Rows per season |
|---|---|---|---|
| `rankings` | Every weekly AP, Coaches and CFP poll | 2000 to 2025 | 14 to 17 poll weeks |
| `games` | Every game with an FBS team, regular season and bowls, with scores | 2000 to 2025 | 700 to 930 |
| `lines` | Sportsbook spreads, totals and moneylines | 2013 to 2025 | 850 to 1,600 |
| `calendar` | Start date of each week | 2002 to 2025 | 16 or so |

**Quota used: 94 API calls**, out of roughly 1,000 a month. Pulling a whole season per call instead of week by week is what keeps this small. Everything is cached in `data/raw/` (gitignored), and re-running the pull makes zero calls.

The 2026 season in progress was not pulled. A cached file of a half-finished season would go stale, so that needs a small "refresh this week" step when we start live predictions.

## How far back is the data good?

The decision was to go back as far as data quality allows. Here is what the data itself says.

**The check:** a ranked team that loses almost always drops in the next poll. So for each season, count the ranked teams that lost and see how many dropped. If CFBD's poll weeks and game weeks line up, that share should be near 100%. If it is much lower, some polls are stapled to the wrong week of games, like a photo album where the captions have slipped down one page.

| Seasons | Ranked losers that dropped (AP) | Verdict |
|---|---|---|
| 2005 to 2023 | 96% to 100% every season | Clean. Used. |
| 2003 | 99% | Clean, but an island between two shaky seasons |
| 2000, 2001, 2002, 2004 | 84% to 90% | Weeks don't line up reliably. Also missing poll weeks (2001 has no weeks 4, 5 or 9), no Coaches poll in 2000, and no calendar dates for 2000 and 2001. |

**So training starts in 2005.** The 2000 to 2004 files are on disk and can be repaired later if we want them, but feeding misaligned weeks to a model would teach it wrong lessons.

Three more things the pull revealed, each of which shapes the next step:

1. **Sportsbook lines start in 2013.** CFBD has none earlier (2005 and 2012 came back empty). A model that uses spreads can only train on 2013 onward, or has to treat the spread as "missing" before that.
2. **Vote points: yes, ranks can be rebuilt from them, but AP points only exist from 2014.** Sorting by points reproduced the published order in 529 of 531 polls (I haven't dug into the other two). CFBD has Coaches points from 2001 but AP points only from 2014. The CFP committee publishes no points at all, only an order.
3. **CFBD only returns the top 25.** There are no "others receiving votes" rows, so points can't tell us who was 26th to 35th.

What that means for "predict points, then sort": it works for Coaches (2005 on) and AP (2014 on). For older AP seasons and for the CFP we only have ranks, so the model needs a rank-shaped target there. One way to get both is to predict a *share of the maximum points*, and convert old ranks to an approximate share. That is a decision for the modeling step.

**Eras.** Rather than cutting history at a rule change, each season is labelled with its championship system (`era()` in `snapshots.py`): `bcs` through 2013, `cfp4` for 2014 to 2023, `cfp12` from 2024. Later models get that as a feature. The baseline scored about the same in the BCS and four-team eras (see below), so voter habits look stable across that change. The twelve-team era is entirely inside the sealed holdout, so we can't say yet.

**2020 is dropped**, both as study material and as a test season.

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
| **Win/loss rule, tuned** | The same rule, but those numbers are chosen from earlier seasons instead of by hand. (The 2014 CFP has no earlier CFP seasons to learn from, so it uses the hand-set numbers.) |
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

**Analogy:** a flight simulator that replays history. To grade the 2019 season the model may study 2005 to 2018 only, then it "flies" 2019 one poll at a time, seeing only that morning's snapshot. Then the next season with everything earlier as study material, and so on. It never trains on the future.

Test seasons are 2006 to 2023 without 2020, which is 17 seasons. **2024 and 2025 are the sealed final exam** and were not scored. The backtest refuses to touch them without an explicit `--include-holdout` flag.

How to read the columns: `teams right` is how many of the 25 teams we picked, ignoring order. `average miss` is how many spots off we were per team (lower is better, a team missing from one list counts as 26th). `exact` is how many teams landed in exactly the right spot. `top 4` and `top 12` are the playoff cut lines.

### AP Top 25 (256 polls)

| Baseline | Teams right (of 25) | Average miss | Exact spot | Top 4 right | Top 12 right |
|---|---|---|---|---|---|
| Same as last week | 22.38 | 2.74 | 5.40 | 3.33 | 10.52 |
| Win/loss rule, fixed | 23.24 | 1.40 | **9.19** | 3.67 | 11.36 |
| **Win/loss rule, tuned** | **23.36** | **1.37** | 8.84 | 3.65 | 11.32 |

### Coaches Poll (256 polls)

| Baseline | Teams right (of 25) | Average miss | Exact spot | Top 4 right | Top 12 right |
|---|---|---|---|---|---|
| Same as last week | 22.53 | 2.71 | 5.39 | 3.35 | 10.51 |
| Win/loss rule, fixed | 23.18 | 1.32 | 9.34 | 3.67 | 11.40 |
| **Win/loss rule, tuned** | **23.27** | **1.24** | **9.87** | 3.67 | 11.38 |

### CFP rankings (54 rankings, 2014 to 2023 without 2020)

| Baseline | Teams right (of 25) | Average miss | Exact spot | Top 4 right | Top 12 right |
|---|---|---|---|---|---|
| Copy this week's AP | 23.52 | 1.53 | 8.50 | 3.61 | 11.41 |
| Same as last week's CFP | 22.94 | 2.31 | 6.06 | 3.19 | 10.80 |
| **Last week's CFP + win/loss rule, fixed** | 23.33 | **1.41** | 8.59 | 3.52 | 11.41 |
| Last week's CFP + win/loss rule, tuned | 23.48 | 1.43 | 7.91 | 3.44 | 11.41 |

### Did the era matter? (win/loss rule, fixed, average miss)

| Poll | BCS era, 2006 to 2013 | Four-team CFP era, 2014 to 2023 |
|---|---|---|
| AP | 1.37 | 1.42 |
| Coaches | 1.32 | 1.33 |

## What the numbers say

1. **Adjusting for wins and losses halves the error.** For AP, the average miss falls from 2.74 to 1.40 spots, and the rule beat "same as last week" in all 256 polls. So win/loss carries most of the week-to-week signal, as expected.
2. **Tuning the knobs helps a little, and only with enough history.** With nine seasons of data the tuned and hand-set rules were tied. With seventeen, tuning gives a small real gain for the Coaches poll (1.24 against 1.32, better in 156 polls and worse in 81) and almost nothing for AP. The tuned rule settles on bigger penalties than my guesses: about 7.5 spots for losing to a ranked team and 11.5 for losing to an unranked one. But six dials can only do so much. The remaining error is about things this rule cannot see, such as margin of victory, opponent quality and time of season.
3. **For the CFP, the answer depends on the week.** In the first ranking of a season, copying AP is all we have, and it is the weakest spot (average miss 1.93, and only 3.0 of the top 4 right). The committee starts from its own blank sheet. In later weeks, last week's CFP plus the win/loss rule (1.31) beats copying AP (1.45). So the committee is more consistent with *itself* than with the AP voters. That supports the plan to model the CFP on top of the AP and Coaches models rather than as a copy of them.
4. **Early season and the final poll are the hard parts.** For AP the average miss is 1.63 in weeks 2 to 5, 1.19 in weeks 11 to 16, and 1.72 for the post-bowl final poll, where several weeks of bowl results land at once.
5. **Voter behavior looks stable from the BCS era into the four-team CFP era.** The same fixed rule scores about the same in both, which is a good sign that the older seasons are useful training data.

**The bar for the ML models:** an average miss of about 1.4 for AP, 1.25 for Coaches and 1.4 for the CFP, with about 9 to 10 exact placements.

## Known gaps

- **The preseason poll is not predicted.** There is no "last week" to start from. It needs its own approach (last season's final poll, returning talent).
- **No "others receiving votes".** CFBD returns only the top 25, so we can't see who was 26th to 35th. The rule orders newcomers by fewest losses, then Elo.
- **2020 is dropped** for now. If we bring it back it needs special handling (staggered conference starts, a missing week 2 poll).
- **2000 to 2004 are pulled but unused** until the week alignment is repaired.
- **CFBD has no CFP ranking for 2019 week 14.** The code steps over missing weeks by using the most recent earlier release.
- **54 CFP rankings is a small sample.** Differences of 0.1 between CFP baselines are not meaningful.

## Run it yourself

```sh
uv run python -m cfp_rankings.pull --dry-run   # how many API calls would this cost? (0 once cached)
uv run python -m cfp_rankings.pull             # fetch anything missing, through the CFBD MCP server
uv run python -m cfp_rankings.export           # write the tidy CSVs
uv run python -m cfp_rankings.backtest         # print the tables above
uv run --extra dev python -m pytest -q         # pipeline tests (no network)
```
