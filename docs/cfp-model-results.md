# Stage 3: predicting the CFP committee's ranking

This is the CFP correction model from the [ideas list](IDEAS.md), built on what the [clout study](clout-step-1-results.md) learned about the committee. Code: `src/cfp_rankings/cfp_model.py`.

## The one-paragraph version

The model predicts the committee's top 25 with an average miss of **1.14 spots**, against **1.41** for the best simple rule we had. That is about 19% less error, and it was better in all nine seasons. Most of the gain comes from one idea: **start from last week's committee ranking and move each team the way AP voters just moved it.** The committee's known tastes (the league tilt above all) add a further improvement in the one week where they can: the first ranking of the season, when there is no "last week" to lean on.

**Analogy.** Think of forecasting a food critic you have read for years. You do not start from a blank page. You start from what the crowd of other reviewers said this week (the AP poll), plus what this critic wrote last time. Only when the critic has not written anything yet do you need to fall back on what you know about their tastes.

## How it works

The committee publishes on Tuesday, two days after the AP and Coaches polls, so those are already public when we predict.

**Step 1: a simple rule.** Take last week's committee rank and add however many spots AP voters moved the team this week. If the committee had a team 10th and AP dropped it three spots after a loss, guess 13th. In the first week there is no committee rank yet, so the guess is just the AP rank.

**Step 2: learned weights.** The model takes that guess plus a few other inputs and learns how much weight each deserves, by studying earlier seasons. Like Stage 2, it learns from pairs ("the committee put A above B") and then sorts.

| Input | What it tells the model |
|---|---|
| The step 1 guess | The single best starting point |
| This week's AP rank and Coaches rank | What the crowd thinks right now |
| Last week's committee rank | Where the committee had the team |
| Last week's gap between AP and the committee | Whether the committee likes this team more or less than voters do |
| **First week only:** power conference, brand, losses, Stage 1 résumé rank and power rank | The committee's tastes, used when it has not spoken yet |

**Why so small?** There are only 54 committee rankings in history. The Stage 2 model for AP has 256 polls and uses 600 decision trees. Here that would be like fitting a tailored suit from three measurements. So Stage 3 has just ten weights. For 2014, the first year of the committee, there is nothing to study, so the model uses the step 1 rule as it is.

## Results

Same walk-forward test as everything else: to grade a season the model studies only earlier seasons. All 54 committee rankings from 2014 to 2023, without 2020. **2024 and 2025 are still sealed.**

| Model | Teams right (of 25) | Average miss | Exact spot | Top 4 right | Top 12 right |
|---|---|---|---|---|---|
| Copy this week's AP poll | 23.52 | 1.53 | 8.50 | 3.61 | 11.41 |
| Win/loss rule (the old bar) | 23.33 | 1.41 | 8.59 | 3.52 | 11.41 |
| Step 1 rule: last week's CFP, moved like AP | 23.56 | 1.32 | 9.24 | 3.65 | 11.44 |
| **Stage 3 model** | **23.63** | **1.14** | **10.43** | **3.69** | **11.46** |

### By part of the committee's season (average miss)

| Model | First ranking | Middle rankings | Final ranking |
|---|---|---|---|
| Copy this week's AP poll | 1.93 | 1.51 | 1.21 |
| Win/loss rule (the old bar) | 1.93 | 1.35 | 1.14 |
| Step 1 rule | 1.93 | 1.29 | 0.84 |
| **Stage 3 model** | **1.80** | **1.08** | **0.73** |

The first ranking is the hard one, because it is the committee's opening statement. Every simple rule can only copy the AP poll there and scores 1.93. The model's tastes bring that down to 1.80.

### Season by season (average miss)

| Season | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|---|
| Old bar | 1.38 | 1.85 | 1.76 | 1.21 | 1.48 | 1.39 | 1.36 | 1.18 | 1.13 |
| Stage 3 | 1.15 | 1.38 | 1.41 | 1.10 | 0.95 | 1.19 | 1.25 | 0.91 | 0.96 |

Better in 9 of 9 seasons, and in 40 of the 54 individual rankings (worse in 11, tied in 3).

### One real week

The first committee ranking of 2023. The model studied 2014 to 2022 only. Its average miss was 1.38, against 1.69 for copying the AP poll.

| Team | AP that week | Stage 3 model | Committee |
|---|---|---|---|
| Tulane (small league) | 21 | 24 | 24 |
| Air Force (small league) | 17 | 20 | 25 |
| James Madison (small league) | 23 | 25 | not ranked |
| USC | 24 | 22 | 20 |
| Kansas State | 25 | 23 | 23 |
| Ohio State | 3 | 4 | 1 |

The league tilt at work: the model moved every small-league team down and the power-conference teams up, and each move was in the right direction. It also shows an honest miss. Nothing in the inputs said the committee would put Ohio State first.

## Did the clout findings help?

You asked for league, title games and brand to be fed in. Here is what each was worth, by adding or removing it.

| Version | Average miss | First ranking | Final ranking |
|---|---|---|---|
| **Stage 3 as built** (tastes in the first week only) | **1.14** | **1.80** | **0.73** |
| Without the first-week tastes | 1.16 | 1.94 | 0.74 |
| Tastes used in every week | 1.16 | 1.82 | 0.81 |
| Plus title-game results | 1.15 | 1.80 | 0.78 |
| Everything at once | 1.16 | 1.82 | 0.84 |

What that says:

1. **League helps in the first week, and only there.** It is the heaviest of the first-week inputs by a wide margin. After the first week it adds nothing, because last week's committee ranking *already contains* the committee's opinion of each team. Once the critic has reviewed the restaurant, you do not need to guess their taste.
2. **Title games did not improve the prediction.** This fits what the clout study found: AP voters and the committee treat champions the same way. So when a team wins its title game, AP's move already carries the news, and adding it a second time just adds noise. There are also only nine final rankings to learn from.
3. **Brand adds nothing**, again matching the clout study.

So the bias study and the prediction model agree, which is reassuring. The findings were real, and the model confirms where they matter and where they are already baked in.

### The weights

Studied on all nine seasons. Positive means a higher value moves a team up. Rank inputs are negative because a bigger rank number is a worse rank.

| Input | Weight |
|---|---|
| The step 1 guess | -1.85 |
| AP rank this week | -1.81 |
| Coaches rank this week | -1.46 |
| First week: power conference | **+0.95** |
| Last week's committee rank | -0.94 |
| First week: résumé rank | -0.53 |
| First week: losses | +0.51 |
| Last week's gap between AP and committee | +0.32 |
| First week: power rank | -0.22 |
| First week: brand | -0.16 |

The "losses" weight looks odd at first. It does not mean the committee likes losses. The AP rank has already marked the team down for them. The positive weight says the committee marks a team down for its losses a little *less* than AP does, when the résumé is good.

## How much to trust this

- **The comparison is fair.** Every model is scored on the same 54 rankings with the same no-peeking snapshots.
- **The exact number is a little optimistic.** I compared about a dozen versions (the five in the table above, a few other mixes of inputs, and a few settings of one knob) on these same seasons before choosing. They all landed between 1.13 and 1.20, so the choice among them is close to a coin flip, and the margin over the old bar (1.41) is not in doubt. The sealed seasons will give the clean number.
- **It is a small sample.** Nine seasons, and only nine first rankings.
- **It leans on the AP poll.** Run live, it needs Sunday's real AP and Coaches polls. Chaining it to our own Stage 2 predictions of those polls would add their error on top.

## Known gaps

- **The 12-team era is different.** From 2024 the playoff takes 12 teams and gives the top conference champions automatic places, so championships matter by rule. The model has not seen that era. When the sealed seasons are opened it will probably need an era input, as Stage 2 has.
- **The first ranking is still the weakest spot**, at 1.80.
- **The top 4 barely improved** (3.65 to 3.69). The model's gains are mostly further down the ranking.

## Run it yourself

```sh
uv run python -m cfp_rankings.cfp_model   # every table above (about a minute)
uv run python -m cfp_rankings.backtest    # all three stages together (about 15 minutes)
```
