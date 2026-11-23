# The first real model: Stage 1 and Stage 2

> **Update.** A second round added five inputs and seed averaging. AP is now 0.95 and Coaches 0.85. See [round-2-results.md](round-2-results.md). The numbers below are round one's.

This is step 1 (build the model) and step 2 (settle the target) of the modeling plan. The baselines it has to beat are in [baseline-results.md](baseline-results.md).

## The one-paragraph version

The model beats the bar in every one of the 17 test seasons, for both polls. For the AP poll the average miss falls from **1.37 spots to 0.98**. For the Coaches poll it falls from **1.24 to 0.88**. That is roughly 30% less error than the best no-ML rule. It does it in two stages: Stage 1 rates every team from scores alone, and Stage 2 learns how voters edit last week's ballot given what just happened.

**Analogy:** think of a wine competition. Stage 1 is the blind tasting: labels covered, judge only what is in the glass. Stage 2 is predicting how the actual judges will vote, and they *can* see the labels. They remember last year's vintage, they anchor on their previous scores, and they react to the latest sip. To predict the judges you need both: what is really in the glass, and how these particular judges behave.

## Stage 1: the blind taste test

`src/cfp_rankings/power.py`

Every game gives one clue: *home team's rating, minus away team's rating, plus a home edge, should equal the final margin*. With about 800 games a season that is 800 clues about 130 unknown ratings. Stage 1 finds the ratings that fit all the clues best at once. A rating is in points: a team rated 10 should beat a team rated 3 by about 7 on a neutral field.

Because the clues link up, the rating sees through schedules. If A beat B and B beat C, A gets credit over C without ever playing them.

Three guard rails:

| Guard rail | What it does | Everyday version |
|---|---|---|
| **Capped margins** | Winning by 60 counts the same as winning by 28 | You can't buy a rating by running up the score on a weak team |
| **Shrinkage** | Each team carries two "imaginary games" at its starting guess | A batting average after ten at-bats: believe it a little, not a lot |
| **Starting guess** | 80% of last season's final rating | Rosters change, but programs don't transform overnight |

There are two versions of the rating, from the same maths:

- **Power**: uses the margin. Answers "how good is this team?"
- **Résumé**: every game counts as won or lost by one point, so only *who you beat* matters. Answers "what has this team accomplished?"

Voters care about both, and often more about the second.

### Is Stage 1 any good?

A rating that cannot pick winners is not measuring strength. So the check: each week, rate teams on earlier games only, then pick the winner of every FBS game that week (12,704 games, 2006 to 2023 without 2020).

| Who is picking | Winners picked |
|---|---|
| Stage 1 power rating | 72.8% |
| CFBD's own Elo rating | 72.6% |
| Sportsbook closing spread (2013 on) | 74.5% |
| Stage 1, on those same 2013-on games | 72.3% |

So Stage 1 is level with CFBD's published Elo, and about two points behind the betting market. That gap is expected: the market knows about injuries, transfers and weather, and Stage 1 knows only scores. It is a sound measuring stick.

Run it with `uv run python -m cfp_rankings.power`.

## Step 2: what exactly should the model predict?

The options were "predict each team's vote points", "predict each team's rank", or "predict which of two teams ranks higher". The model uses the third.

**Analogy:** rating chess players. Nobody scores a player "7 out of 10". You only see who beat whom, and from thousands of those results you work out a strength number for each player. Here, one "result" is *team A finished above team B in a real poll*. A single poll of 25 teams plus the outsiders gives a couple of thousand such results. The model learns a scoring function so that the higher score belongs to the team the voters put higher, as often as possible. To predict a poll: score every candidate, sort, keep 25.

Why this target:

1. **It works everywhere.** Vote points exist only from 2014 for AP, and never for the CFP. An order always exists. One method for all polls and all seasons.
2. **It is honest about teams outside the top 25.** All we know about them is "below the 25 who made it". As pairs, that is exactly what gets said: a ranked team beats an unranked one, and two unranked teams are never compared.
3. **Rank is zero-sum.** One team moving up pushes others down. Sorting scores respects that automatically.

**Where vote points come in.** They are used as inputs: last week's share of the maximum points, and the gap to the team just above and just below. That tells the model whether #6 was breathing down #5's neck or a mile behind. I also tested points as the *target* for the Coaches poll (which has points for every season). Predicting points and sorting scored 0.90, about the same as the pairwise model, and averaging the two gained about 0.01. That is too small to justify a second model, so it is left out for now.

## Stage 2: how voters edit the ballot

`src/cfp_rankings/features.py` builds a scouting card for every candidate team. `src/cfp_rankings/poll_model.py` learns from the cards.

**Who is a candidate?** Last week's 25, plus every FBS team that has not lost since that poll. About 80 teams a week. (In 2005 to 2023, one newcomer out of 709 entered the AP poll in a week it lost.)

**What is on the card?** 37 facts in five groups:

| Group | Examples |
|---|---|
| Where the team stood | Last week's rank and share of points, gap to the neighbours, rank in the *other* poll last week, preseason rank, brand |
| Traffic | How many teams above it just lost, and where it would land if only the losers dropped |
| What it just did | Won or lost, by how much, opponent's rank, home or away, result against the sportsbook spread and against Stage 1's expectation |
| The season so far | Record, wins over ranked teams, schedule strength |
| Stage 1 | Power and résumé ratings, their rank, and how much they moved this week |

*Brand* is how often the program finished in the final poll over the previous five seasons, on a 0 to 1 scale. *Spread* facts are blank before 2013, and the model handles blanks natively.

**What does the learning?** Gradient-boosted trees (LightGBM): 600 small decision trees, each one correcting the mistakes of those before it. Trees suit voter logic because it is full of "it depends". A loss in week 3 is not a loss in week 13, and a loss to #2 is not a loss to a nobody.

### One real week, to make it concrete

Same week as the baseline doc: AP poll, week 2 of 2023. LSU (5th) lost to Florida State, Clemson (9th) lost to unranked Duke. The model studied 2005 to 2022 only.

| Team | Last week | Win/loss rule | Stage 2 model | Actually |
|---|---|---|---|---|
| Florida State (beat LSU) | 8 | 6 | 5 | 4 |
| LSU (lost to a ranked team) | 5 | 9 | 15 | 14 |
| Clemson (lost to an unranked team) | 9 | 17 | 24 | 25 |
| Duke (unranked, beat Clemson) | none | 23 | 17 | 21 |
| Colorado (unranked, beat TCU) | none | 24 | not in | 22 |
| **Average miss, all teams** | | **1.52** | **1.00** | |

The rule under-reacted every time. The model has learned how hard voters punish an early loss, so LSU and Clemson land within a spot of the truth. It also shows two honest misses: it was too excited about Duke, and it left Colorado out.

## Results

Same walk-forward test as the baselines: to grade a season the model studies only earlier seasons, then predicts that season one poll at a time. Test seasons are 2006 to 2023 without 2020. **2024 and 2025 are still sealed** and were not loaded.

### AP Top 25 (256 polls)

| Model | Teams right (of 25) | Average miss | Exact spot | Top 4 right | Top 12 right |
|---|---|---|---|---|---|
| Same as last week | 22.38 | 2.74 | 5.40 | 3.33 | 10.52 |
| Win/loss rule, tuned (the bar) | 23.36 | 1.37 | 8.84 | 3.65 | 11.32 |
| **Stage 2 model** | **23.73** | **0.98** | **10.97** | **3.71** | **11.57** |

### Coaches Poll (256 polls)

| Model | Teams right (of 25) | Average miss | Exact spot | Top 4 right | Top 12 right |
|---|---|---|---|---|---|
| Same as last week | 22.53 | 2.71 | 5.39 | 3.35 | 10.51 |
| Win/loss rule, tuned (the bar) | 23.27 | 1.24 | 9.87 | 3.67 | 11.38 |
| **Stage 2 model** | **23.71** | **0.88** | **12.41** | **3.79** | **11.63** |

### How consistent is the win?

| | AP | Coaches |
|---|---|---|
| Polls where the model beat the tuned rule | 218 of 256 | 223 of 256 |
| Polls where it was worse | 27 | 32 |
| Seasons where it was better on average | 17 of 17 | 17 of 17 |

### By part of the season (average miss)

| | Weeks 2 to 5 | Weeks 6 to 10 | Weeks 11 to 16 | Final poll |
|---|---|---|---|---|
| AP, tuned rule | 1.55 | 1.25 | 1.24 | 1.91 |
| AP, Stage 2 | 1.14 | 0.93 | 0.87 | 1.17 |
| Coaches, tuned rule | 1.25 | 1.22 | 1.15 | 1.73 |
| Coaches, Stage 2 | 0.94 | 0.83 | 0.82 | 1.16 |

### By era (average miss, Stage 2)

| Poll | BCS era, 2006 to 2013 | Four-team CFP era, 2014 to 2023 |
|---|---|---|
| AP | 1.00 | 0.96 |
| Coaches | 0.91 | 0.85 |

## What the numbers say

1. **The model clears the bar comfortably and consistently.** About 30% less error, more teams in exactly the right spot (11 instead of 9 for AP, 12 instead of 10 for Coaches), and better in every single test season.
2. **The biggest gain is the final poll.** After the bowls, several weeks of results land at once, and a flat "drop 7.5 spots" rule cannot weigh them. The model's miss there is 1.17 against the rule's 1.91.
3. **Voters are mostly inertia.** Here is how much the trees leaned on each input, as a share of the total (model trained on 2005 to 2022, AP):

   | Input | Share |
   |---|---|
   | Last week's rank | 60% |
   | Where it would land if only the losers dropped | 10% |
   | Last week's rank in the Coaches poll | 9% |
   | Stage 1 résumé rating and its rank | 7% |
   | Rank of the team it lost to | 3% |
   | Stage 1 power rating and its rank | 3% |
   | Everything else | 8% |

   So about 80% of a ballot is "last week, plus traffic". Read these shares as a rough guide, not exact weights, because related inputs share credit.
4. **Voters reward accomplishment more than strength.** The résumé rating (wins and who they came against) matters about twice as much as the power rating (margins). That fits the folk wisdom that polls rank who *deserves* it, not who would win on a neutral field.
5. **The two polls watch each other.** Last week's Coaches rank is the third most useful input for predicting the AP poll. When the two polls disagree about a team, they tend to drift together.
6. **Early season is still the hardest regular-season stretch**, at 1.14 for AP. That is where outside information such as returning talent and recruiting would most plausibly help.

## How much to trust this

- **The comparison is fair.** Model and baselines are scored on the same 256 polls with the same no-peeking snapshots.
- **One caveat on the exact number.** I chose between a few model variants (the pairwise target against two alternatives, and 300 trees against 600) by looking at these same test seasons. That makes 0.98 a little optimistic, like picking your best golf round and calling it your average. The margin is not in doubt, though: the worst variant I tried scored 1.10 for AP, still far below 1.37. The sealed 2024 and 2025 seasons will give the clean number.
- **No leakage tests.** New tests check that the scouting cards cannot see the week being predicted.

## Known gaps

- **The preseason poll is still not predicted.** There is no "last week" to start from.
- **A team that loses while unranked is never a candidate.** It cost one team in 709, so it is left alone.
- **Only the top 25 is visible.** With no "others receiving votes" data, the model has to guess who is 26th to 35th from the scouting card alone. Getting the last few spots right is where most of the remaining "teams right" error lives.
- **The CFP ranking is not modeled yet.** That is the next step, built as a correction on top of these predictions.
- **The backtest is slow**, about 15 minutes, because it retrains for each of 17 seasons and both polls. `--baselines-only` skips the model.

## Run it yourself

```sh
uv run python -m cfp_rankings.power                      # Stage 1: how often does it pick the winner?
uv run python -m cfp_rankings.backtest                   # every table above (about 9 minutes)
uv run python -m cfp_rankings.backtest --baselines-only  # just the baselines (seconds)
uv run --extra dev python -m pytest -q                   # pipeline tests (no network)
```
