# Round two: tightening Stage 2 and Stage 3

This round improves the two learned models using only the open seasons. **2024 and 2025 are still sealed** and were not loaded. Round one is described in [stage-1-2-results.md](stage-1-2-results.md) and [cfp-model-results.md](cfp-model-results.md).

## The one-paragraph version

All three polls got a little better, and the gains held up on seasons the changes were not chosen on.

| Poll | Average miss before | Average miss now | Change |
|---|---|---|---|
| AP | 0.98 | **0.95** | 3% less error |
| Coaches | 0.88 (0.89 unrounded) | **0.85** | 4% less error |
| CFP committee | 1.14 | **1.08** | 6% less error |

These are small steps, not leaps. The models were already close to the ceiling for the information they have: most of what is left is voters changing their minds for reasons that are not in the box score. The backtest also runs in about 9 minutes instead of 15, and now gives exactly the same numbers every run.

## How this round guarded against fooling ourselves

The worry with any tuning is the golfer who plays twenty rounds and reports the best one. Try enough ideas on the same seasons and some will look good by luck.

So this round split the open seasons in two, **before** trying anything:

- **Practice seasons.** Every idea was tried and compared here, and only here. For Stage 2 that was 2006 to 2016. For Stage 3 it was 2015 to 2018.
- **Check seasons.** Once a recipe was chosen it was frozen and scored once on the later seasons. For Stage 2 that was 2017 to 2023. For Stage 3 it was 2019 to 2023.

**Analogy.** A student does practice problems with the answer key open, and that is fine. But the grade comes from a quiz they have not seen. The check seasons are the quiz. The sealed 2024 and 2025 seasons are still the final exam, untouched.

Both stages use the usual walk-forward rule throughout: to predict a season, a model studies only earlier seasons.

## Stage 2: the AP and Coaches model

### What changed

**1. Five new facts on the scouting card** (42 now, up from 37).

| New fact | What it tells the model | Everyday version |
|---|---|---|
| Rank two polls ago, and last week's move | Momentum. A team that just jumped five spots is treated differently from one that has sat still | A stock's price yesterday tells you more when you also know which way it was heading |
| Power conference: yes or no | Voters give a 9-1 SEC team and a 9-1 Sun Belt team different amounts of credit | The clout study found the same tilt in the committee |
| Place in the queue (two versions) | Among the teams *outside* last week's 25, who has the best résumé, second best, and so on | When two ranked teams lose, two seats open. What matters is not that your résumé is "31st in the country" but that you are first in line |

The queue is the one worth dwelling on. A decision tree looks at one team at a time. It could already see "résumé rank 31", but it could not see "nobody else waiting has a better one". The new input hands it that comparison directly.

**2. A small committee instead of one judge.** The model has some randomness in how it is trained. Before, we trained it once. Now we train it three times with different random draws and average the three scores. One judge's quirks wash out.

**3. Faster training.** The training signal compares pairs of teams. Two unranked teams were never compared anyway, so the code now builds only the pairs where the upper team is ranked. Same maths, about a seventh of the work. Scouting cards are also written once and reused, instead of being rebuilt for every test season.

### What was tried and left out

Nine groups of new inputs and six training settings were compared on the practice seasons.

| Idea | Result on practice seasons | Decision |
|---|---|---|
| Momentum, power conference, queue | Each cut the miss by about 0.015 on its own, about 0.03 together | **Kept** |
| Averaging three seeds | About 0.01 better | **Kept** |
| Teams around you that lost or sat idle | Under 0.01 | Left out |
| The other poll's vote points; CFBD's Elo; an "unbeaten" flag | Under 0.005 | Left out |
| Head-to-head wins over nearby teams | Slightly worse | Left out |
| Stage 1 rank of the team you beat or lost to | Slightly worse | Left out |
| Bigger or smaller trees, more or fewer trees, slower learning | No better, or worse | Left as they were |
| One shared model for both polls, with more trees | Best on practice seasons, but on the check seasons it was no better than the simpler version (it helped AP and hurt Coaches) | Left out |

Head-to-head was a surprise. Fans argue about it constantly, but voters have mostly already acted on a head-to-head result in the week it happened, so last week's rank already carries it.

### Results

Walk-forward over 2006 to 2023 without 2020, 256 polls per poll.

| | Teams right (of 25) | Average miss | Exact spot | Top 4 right | Top 12 right |
|---|---|---|---|---|---|
| AP, round one | 23.73 | 0.98 | 10.97 | 3.71 | 11.57 |
| **AP, round two** | **23.75** | **0.95** | **11.34** | **3.73** | **11.58** |
| Coaches, round one | 23.71 | 0.88 | 12.41 | 3.79 | 11.63 |
| **Coaches, round two** | **23.79** | **0.85** | **12.57** | **3.78** | **11.64** |

Split by practice and check seasons (average miss):

| | Practice seasons, 2006 to 2016 | Check seasons, 2017 to 2023 |
|---|---|---|
| AP, round one | 1.01 | 0.93 |
| AP, round two | 0.97 | 0.91 |
| Coaches, round one | 0.92 | 0.84 |
| Coaches, round two | 0.89 | 0.79 |

How consistent is it?

| | AP | Coaches |
|---|---|---|
| Polls where round two beat round one | 127 of 256 | 136 of 256 |
| Polls where it was worse | 75 | 70 |
| Seasons where it was better on average | 13 of 17 | 16 of 17 |

By part of the season (average miss, round two): AP is 1.10 in weeks 2 to 5, 0.89 in weeks 6 to 10, 0.84 in weeks 11 to 16 and 1.18 for the final poll. Coaches is 0.92, 0.81, 0.79 and 1.13.

### How much to trust this

- **The check seasons agree on direction, less on size.** On AP the gain shrank from about 4% on the practice seasons to about 2% on the check seasons. On Coaches it grew, from 3% to 7%. Taken together the improvement is real but small, somewhere around 3% to 4%.
- **One choice was made after seeing the check seasons.** The frozen recipe included the shared two-poll model. On the check seasons it scored the same as the simpler version on average (0.85 against 0.85 across the two polls), so the simpler one was shipped. Because the two were level, this choice does not flatter the numbers, but it is said here so nothing is hidden.
- **Early season is still the hardest stretch.** Nothing in this round is aimed at it. Recruiting and returning talent are the natural next inputs.

## Stage 3: the CFP committee model

### What changed: the editor

The committee has published 54 rankings. AP voters have published hundreds, and Stage 2 has learned from those how a ballot gets edited after a week of football: how far a loss drops a team, who climbs into the gap, how much a big win is worth.

Editing a ballot is much the same craft whoever holds the pen. So Stage 3 now hands the Stage 2 AP model **last week's committee ranking** and asks: *if this were your ballot, how would you edit it after this week's games?* The answer becomes one new input, called `edited`.

**Analogy.** A new restaurant critic has written only 54 reviews. That is too few to learn their habits from scratch. But you have read thousands of reviews by other critics, and all critics react to a burnt steak in roughly the same way. So you borrow the general habits from the crowd, and spend the 54 reviews learning only what makes this critic different.

Round one already had a crude version of this: "last week's committee rank, plus however many spots AP moved the team". The editor is a sharper version of the same thought. It knows, for example, that a loss costs the 3rd-ranked team more spots than the 20th, where the crude rule copies AP's move spot for spot even when the team sits somewhere quite different on the committee's list.

**No peeking.** The editor that helps with season Y has studied AP polls from seasons before Y only. That holds both when Y is a season Stage 3 is learning from and when it is the season being predicted.

### Results

All 54 committee rankings, 2014 to 2023 without 2020.

| Model | Teams right (of 25) | Average miss | Exact spot | Top 4 right | Top 12 right |
|---|---|---|---|---|---|
| Win/loss rule (the old bar) | 23.33 | 1.41 | 8.59 | 3.52 | 11.41 |
| Stage 3, round one | 23.63 | 1.14 | 10.43 | 3.69 | 11.46 |
| **Stage 3, round two** | **23.80** | **1.08** | **10.93** | **3.74** | **11.59** |

By part of the committee's season (average miss):

| Model | First ranking | Middle rankings | Final ranking |
|---|---|---|---|
| Stage 3, round one | 1.80 | 1.08 | 0.73 |
| Stage 3, round two | 1.77 | 0.99 | 0.78 |

The gain is in the middle rankings, which is where the editor has something to edit. The first ranking has no "last week", so the editor is silent there. The final ranking is slightly worse, but there are only nine of those, so that difference is well inside the noise.

Practice and check seasons (average miss):

| | Practice, 2015 to 2018 | Check, 2019 to 2023 |
|---|---|---|
| Round one | 1.21 | 1.07 |
| Round two | 1.16 | 0.99 |

On the check seasons round two was better in 3 of the 4 seasons (2023 was slightly worse). The practice figures are from the test bench, where the editor used round one's Stage 2 inputs; the check figure for round two is from the finished code.

The weights, studied on every season:

| Input | Weight |
|---|---|
| **The editor's ranking** | **-2.16** |
| The step 1 guess | -1.20 |
| AP rank this week | -1.19 |
| First week: power conference | +1.01 |
| Last week's committee rank | -0.96 |
| Coaches rank this week | -0.94 |
| First week: losses | +0.56 |
| First week: résumé rank | -0.53 |
| First week: power rank | -0.23 |
| Last week's gap between AP and committee | +0.21 |
| First week: brand | -0.18 |

The editor is now the heaviest input, and it took weight mostly from the crude rule and the raw AP rank. (Rank inputs are negative because a bigger rank number is a worse rank.)

### How much to trust this

- **Only one new idea was tried for Stage 3**, with three settings of the one knob. That keeps the golfer's-best-round problem small this time.
- **The sample is tiny.** The check seasons are 23 rankings. Round two was better in 11 of them, worse in 4 and tied in 8 (on the test bench). Encouraging, not proof.
- **Round one's caveat still stands.** The rest of the model was picked from about a dozen versions on these same seasons. The sealed seasons will give the clean number.

## What is still open

- **Recruiting and roster talent** are not wired in, and cannot be yet: CFBD's recruiting and team-talent endpoints are not on the allowlist in `mcp_servers/cfbd/src/cfbd_mcp/endpoints.py`, which is part of the security harness and is the owner's to edit. They are the best candidates for the early-season weakness.
- **The first committee ranking** is still the weakest spot at 1.77.
- **The 12-team era** needs the sealed seasons.

## Run it yourself

```sh
uv run python -m cfp_rankings.backtest    # all three stages (about 9 minutes)
uv run python -m cfp_rankings.cfp_model   # Stage 3 tables and weights (about 4 minutes)
```
