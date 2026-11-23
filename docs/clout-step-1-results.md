# Clout study, step 1: does the name or the league buy a better ranking?

This is step 1 of the plan in [research/money-and-politics-in-rankings.md](research/money-and-politics-in-rankings.md). It uses only data we already had. Code: `src/cfp_rankings/clout.py`.

## The one-paragraph version

**The famous name does not seem to buy anything. The league does.** After allowing for what teams did on the field, programs with a strong recent brand were not ranked higher by the CFP committee. But teams from the five power conferences were, and the cleanest comparison says so plainly: for the same team in the same week, **the committee ranked power-conference teams about 2 spots more favorably than the AP voters did, relative to everyone else.** That held in all nine seasons tested. What this step cannot tell us is whether the committee is *wrong* to do that. That is the acid test, and it should come next.

**Analogy.** Back to the gymnasts. We checked two things about the judges. Do they score a famous gymnast higher for the same routine? No sign of it. Do they score gymnasts from the big-name gyms higher than gymnasts from small gyms? Yes. But the judges would say big-gym gymnasts face tougher competition every week, so the same routine *means* more. Whether they are right is a separate question with a separate test.

## What was measured

Every CFP committee ranking from 2014 to 2023, without 2020. The sealed 2024 and 2025 seasons were not loaded.

| | Count |
|---|---|
| Committee rankings | 54 |
| Team-weeks | 1,722 |
| Team-seasons | 354 (280 power conference, 74 others) |

A team is included in a week if it was in the committee's top 25, the AP top 25, or the top 25 of a Stage 1 rating. Any team outside a top 25 is counted as 26th in it.

For each team and week:

> **gap = on-field rank minus committee rank**

A gap of +3 means the committee had the team three spots higher than its results justify.

Two clout measures, both free:

- **Brand**: how often the program finished in the final AP poll over the previous five seasons, on a 0 to 1 scale. Alabama is near 1, a newcomer is 0.
- **Power conference**: ACC, Big 12, Big Ten, Pac-12 or SEC, plus Notre Dame.

The tests below were chosen before looking at any result.

## Results

Read each cell as "extra spots in the ranking". The range in brackets is the margin of error (a 95% range). If the range includes zero, we cannot say there is an effect.

| Test | Brand, from 0 to 1 | Power conference |
|---|---|---|
| Committee against the **résumé** rank (main test) | -0.2 (-1.6 to +1.1) | **+5.3** (+4.0 to +6.6) |
| Committee against the **power** rank | -3.1 (-5.3 to -1.2) | +1.3 (-0.2 to +2.7) |
| Committee against a blend of the two | -2.3 (-3.6 to -1.2) | **+2.4** (+1.2 to +3.6) |
| Committee, for teams with the same résumé rank, power rank and losses | +0.5 (-0.7 to +1.6) | **+6.6** (+5.4 to +7.7) |
| **Committee against AP voters, same team, same week** | -0.7 (-1.2 to -0.2) | **+2.0** (+1.5 to +2.6) |
| For comparison: AP voters against the résumé rank | +0.5 (-1.1 to +2.0) | +3.3 (+1.8 to +4.6) |

### Finding 1: brand buys nothing extra

Against the résumé rank the brand effect is zero within the margin of error. Against the AP voters it is slightly *negative*: the committee is a little less kind to famous programs than sportswriters are.

The -3.1 against the power rank is not the committee punishing big names. The power rank keeps 80% of last season's rating, so it stays high on perennial powers even after they lose. The committee cares more about this season's wins and losses, so it sits below the power rank for those teams.

One caution. "Brand" here means success in the last five years. It does not measure money, TV audience or long-run prestige. Those are steps 2, 3 and 6.

### Finding 2: the league matters, by somewhere between 1 and 5 spots

The size depends heavily on which measuring stick is used:

| Measuring stick | Power-conference edge |
|---|---|
| Résumé rank (wins and who they came against) | about 5 spots |
| Blend | about 2.5 spots |
| Power rank (margins) | about 1 spot, and possibly zero |
| AP voters | about 2 spots |

Why such a spread? Teams from different leagues rarely play each other, so any rating has only a few games to judge how much weaker the smaller leagues are. The résumé rank is cautious and treats leagues as closer to equal than they probably are, which makes an unbeaten team from a small league look great. The power rank uses margins and more history, and it rates small-league teams lower to begin with. The truth is likely in between.

That is why the comparison with AP voters is the one to trust. Both groups watched the same games and neither depends on our rating. On average:

| | Committee rank compared with AP rank |
|---|---|
| Power-conference teams | 0.3 spots **higher** than AP |
| Everyone else | 1.6 spots **lower** than AP |

And it is steady. Teams outside the power conferences were ranked lower by the committee than by the AP in every season:

| Season | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|---|
| Spots below AP | 1.7 | 0.8 | 1.2 | 1.5 | 2.3 | 0.8 | 1.7 | 1.1 | 2.7 |

Another way to see it is who gets the 25 seats:

| Ranking | Share of top 25 seats held by power-conference teams |
|---|---|
| Stage 1 résumé | 82% |
| AP voters | 85% |
| CFP committee | 89% |
| Stage 1 power | 90% |

### The teams behind the numbers

Team-seasons ranked furthest from their résumé rank, averaged over the season. This uses the résumé measuring stick, which is the one most generous to small-league teams, so read it as "who drives the result" and not as a verdict on any team.

| Ranked furthest **above** résumé | Spots | Ranked furthest **below** résumé | Spots |
|---|---|---|---|
| 2016 Oklahoma State | +13.0 | 2023 James Madison | -17.0 |
| 2021 Oregon | +11.5 | 2019 SMU | -13.2 |
| 2015 Baylor | +10.0 | 2016 Boise State | -12.5 |
| 2019 Alabama | +8.8 | 2023 Liberty | -12.2 |
| 2023 Oregon State | +8.3 | 2019 Cincinnati | -11.8 |
| 2015 Florida State | +8.0 | 2021 UTSA | -11.0 |
| 2017 Auburn | +7.8 | 2016 Western Michigan | -10.8 |
| 2016 Oklahoma | +7.7 | 2017 UCF | -9.5 |

Every team on the left is from a power conference. Every team on the right is not. (James Madison in 2023 is a special case: it was in its transition to the top division and was not eligible for a bowl through the normal route.)

## What this does and does not show

- **It shows a pattern, not a motive.** The committee is consistently harder on small-league teams than AP voters are. That fits the "politics" idea, since the committee is largely made up of power-conference athletic directors. It also fits a plain football explanation: the committee weighs schedule strength more heavily, and may be right to.
- **It cannot yet say who is right.** If small-league teams the committee marked down go on to lose their big games, the committee was right. If they hold their own, it was biased.
- **League and money are tangled together.** Power-conference schools are also the rich ones. This step cannot separate "league" from "wealth".
- **The margin of error treats each team-season as one unit**, because the same team appears week after week with almost the same rank. There are still only nine seasons, so a few unusual years carry weight.

## What I suggest next

Do the **acid test** (step 4) now, ahead of steps 2 and 3. Step 1 found a real, steady tilt, and the acid test is what tells us whether it is bias or good judgment. It needs no new data: take the teams the committee ranked well below their results, and check how they did afterwards against the sportsbook's expectations.

## Run it yourself

```sh
uv run python -m cfp_rankings.clout   # every number above (a few seconds)
```
