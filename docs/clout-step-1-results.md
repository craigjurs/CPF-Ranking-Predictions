# Clout study: does the name or the league buy a better ranking?

Results so far for the plan in [research/money-and-politics-in-rankings.md](research/money-and-politics-in-rankings.md): step 1 (the gap), step 4 (the acid test), a look at conference championships, and step 3 (school money). Everything except the money section uses only data we already had. Code: `src/cfp_rankings/clout.py`.

## The one-paragraph version

**The famous name does not seem to buy anything. The league does.** After allowing for what teams did on the field, programs with a strong recent brand were not ranked higher by the CFP committee. But teams from the five power conferences were: for the same team in the same week, **the committee ranked power-conference teams about 2 spots more favorably than the AP voters did, relative to everyone else.** That held in all nine seasons tested. The acid test asked whether the committee was right to do that. **There are too few games to settle it, but nothing in them says the committee was right:** ranked small-league teams won 15 of their 26 later games against power-conference teams. Conference championships matter, but modestly: about one extra spot beyond the win itself, and the committee treats them the same way AP voters do. And when money is added, **it is the league badge that counts, not the bank balance**: once we know a team's league, knowing how rich the school is tells us nothing more.

**Analogy.** Back to the gymnasts. We checked two things about the judges. Do they score a famous gymnast higher for the same routine? No sign of it. Do they score gymnasts from the big-name gyms higher than gymnasts from small gyms? Yes. The judges would say big-gym gymnasts face tougher competition every week, so the same routine *means* more. The acid test is sending both to the same meet and seeing who wins. We only have 26 such meets, and the small-gym gymnasts held their own.

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
| Committee against the **betting-market** rank | -9.6 (-12.4 to -7.1) | **+3.7** (+1.9 to +5.6) |
| Committee, for teams with the same résumé rank, power rank and losses | +0.5 (-0.7 to +1.6) | **+6.6** (+5.4 to +7.7) |
| The same, and also the same conference title game result | +0.5 (-0.6 to +1.6) | **+6.8** (+5.6 to +8.0) |
| **Committee against AP voters, same team, same week** | -0.7 (-1.2 to -0.2) | **+2.0** (+1.5 to +2.6) |
| For comparison: AP voters against the résumé rank | +0.5 (-1.1 to +2.0) | +3.3 (+1.8 to +4.6) |

### Finding 1: brand buys nothing extra

Against the résumé rank the brand effect is zero within the margin of error. Against the AP voters it is slightly *negative*: the committee is a little less kind to famous programs than sportswriters are.

The betting-market rank is a rating built from sportsbook point spreads, so it is the bettors' opinion of how strong each team is. The large -9.6 there says bettors rate famous programs far higher than the committee does. Whatever the committee is doing, it is not inflating big names. If anything it holds them to their record.

Likewise, the -3.1 against the power rank is not the committee punishing big names. The power rank keeps 80% of last season's rating, so it stays high on perennial powers even after they lose. The committee cares more about this season's wins and losses, so it sits below the power rank for those teams.

One caution. "Brand" here means success in the last five years. It does not measure money, TV audience or long-run prestige. Those are steps 2, 3 and 6.

### Finding 2: the league matters, by somewhere between 1 and 5 spots

Adding the conference title game result as a control does not shrink it (6.6 becomes 6.8), so championships are not what is driving the league effect.

The size depends heavily on which measuring stick is used:

| Measuring stick | Power-conference edge |
|---|---|
| Résumé rank (wins and who they came against) | about 5 spots |
| Blend | about 2.5 spots |
| Power rank (margins) | about 1 spot, and possibly zero |
| Betting-market rank | about 4 spots when brand is held fixed, about 1.5 on its own |
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

## The acid test: what happened next

A gap is only bias if the judges were wrong. So for every game played after a committee ranking came out (later regular-season weeks, title games and bowls), I tied the game to the latest ranking before it and looked at who won.

### Which ranking calls winners best?

"Pick the better-ranked team to win", scored on games where the ranking separates the two teams.

| Ranking | All later games | Games between a power-conference team and a small-league team |
|---|---|---|
| CFP committee | 73.6% (693 of 941) | 78% (36 of 46) |
| AP voters | 72.9% (691 of 948) | 78% (38 of 49) |
| Stage 1 résumé rank | 73.2% (711 of 971) | 75% (40 of 53) |
| Stage 1 power rank | 75.4% (700 of 928) | 79% (38 of 48) |
| Betting-market rank | 75.8% (612 of 807) | 80% (36 of 45) |

All five are within a couple of points of each other. The committee is no better at calling winners than the AP voters or our own scoreboard-only ratings. When the committee and the AP ordered two teams differently, the committee's pick won 11 of 19, which is a coin flip at that sample size.

### The direct test: small league against big league

These are the games that matter most: a small-league team ranked by the committee or the AP, playing a power-conference team after the ranking came out. There were 26 of them in nine seasons, 23 of them bowls.

| | Result |
|---|---|
| Small-league team won | **15 of 26** |
| Small-league team beat the point spread | 14 of 26 |
| Average result against the spread | -0.3 points (range -5.1 to +5.1) |
| When the committee ranked the power-conference team **higher**, the small-league team still won | **4 of 9** |

Read the last row carefully. Across all later games, the committee's higher-ranked team wins about 74% of the time. In these nine games it won 56%. That leans toward "the committee ranked the small-league teams too low", and the four upsets are well known: Boise State over Arizona (2014), Houston over Florida State (2015), UCF over Auburn (2017) and Tulane over USC (2022).

**But nine games cannot prove anything.** Flip two results and the story changes. The fair summary is:

- There is **no sign** the committee's markdown of small-league teams was earned. If those teams were truly weaker than their records, they should have lost most of these games, and they won more than half.
- There is **not enough evidence** to say the markdown was wrong.
- The sportsbooks, who have money at stake, were not fooled either way: small-league teams landed almost exactly on the spread on average.

### Why this is hard to settle

The teams the committee marks down almost never get to play the teams it favors. That is partly the point: with a four-team playoff, only one small-league team (Cincinnati, 2021) ever got in. The 12-team playoff from 2024 creates more of these games every year, so the sealed 2024 and 2025 seasons will be the best new evidence when we open them.

## Conference championships

Title games are played the week before the final ranking, so the final ranking is the only one that can react to them. That gives nine final rankings and 67 title-game winners in the sample. (Title games are found by rule, because the data only labels them in recent seasons. The Big 12 from 2014 to 2016 had no title game and is correctly left out.)

### How far teams move in the final ranking

For teams that were ranked going into title week:

| | Committee | AP voters |
|---|---|---|
| Won a title game | up 1.3 spots | up 1.6 spots |
| Lost a title game | down 2.1 spots | down 3.0 spots |
| Did not play | up 0.2 spots | up 0.4 spots |

### Is there a bonus beyond the win itself?

Winning a title game is also just a win over a good team, which the Stage 1 ratings already count. The question is whether "champion" is worth extra. Comparing teams with the same résumé rank, power rank and number of losses:

| | Committee | AP voters |
|---|---|---|
| Extra spots for the title-game **winner** | +1.1 (+0.1 to +2.0) | +1.0 (-0.1 to +2.1) |
| Extra spots for the title-game **loser** | +2.5 (+1.6 to +3.4) | +2.0 (+1.0 to +3.0) |

Three things stand out:

1. **The champion's bonus is real but small**, about one spot. In the four-team era it was a tiebreaker, not a trump card.
2. **Losing a title game is forgiven.** A title-game loser sits about 2.5 spots higher than another team with the same record and ratings. The judges seem to treat it as an extra game that other teams did not have to risk, and the committee is a little more forgiving than the AP (down 2.1 spots against down 3.0).
3. **The committee and AP voters treat champions alike.** Head to head on the same teams, the difference is -0.2 spots (range -0.7 to +0.2). The committee's stated emphasis on championships does not show up as anything the AP voters were not already doing.

One spot can still decide everything when it is the line between 4th and 5th. And the rules changed in 2024: the 12-team playoff gives the top conference champions automatic places, so championships now matter by rule and not just by judgment. That era is sealed for now.

## Money against league

Power-conference schools are also the rich ones, so "league" in the findings above could really have been "money" in disguise. To pull them apart I added each school's athletic department revenue from the federal EADA survey (the one free source that includes private schools such as Notre Dame, USC and Stanford). Code: `src/cfp_rankings/finance.py`.

**How money is measured.** Total athletic department revenue from the year before each season, so nothing from the future leaks in. It is put on a "doublings" scale: +1 means twice the revenue of the average team in the study, -1 means half. Finance data was found for 346 of the 354 team-seasons. The three service academies do not file and are left out.

The typical power-conference team has about 1.5 times the average revenue. The typical team from another league has about 0.55 times. That is a gap of nearly three to one.

### Results

Extra spots per doubling of revenue, with the margin of error in brackets.

| | Committee against AP, same team and week | Committee, same résumé, power rank and losses |
|---|---|---|
| Money on its own | **+0.7** (+0.4 to +1.0) | **+2.8** (+2.2 to +3.5) |
| Money, comparing teams in the same kind of league | -0.3 (-0.8 to +0.2) | -0.1 (-1.1 to +1.0) |
| League, comparing teams with the same money | **+2.6** (+1.7 to +3.5) | **+6.7** (+4.9 to +8.6) |
| Money, among power-conference teams only | -0.5 (-0.9 to 0.0) | -0.7 (-1.7 to +0.4) |
| Money, among other leagues only | +0.2 (-1.3 to +1.7) | **+2.3** (+0.2 to +4.3) |

How to read it:

1. **On its own, money looks like it matters.** Richer schools are ranked higher than their results justify. This is the "bundle" effect.
2. **Add the league and money vanishes.** Among teams in the same kind of league, a richer school gets no better treatment. The league effect does not shrink at all when money is held fixed (2.0 becomes 2.6).
3. **Inside the power conferences, being richer does not help.** Ohio State is not treated better than Wake Forest for the same results. If anything the sign is slightly negative.
4. **Inside the smaller leagues there is a hint that money helps.** Comparing teams with the same on-field numbers, a small-league school with twice the revenue sits about 2 spots higher. That fits the idea that the better-funded outsiders (BYU, UCF, SMU, Cincinnati) are taken more seriously than the rest. But it does not show up in the comparison with AP voters, and it rests on only 66 team-seasons, so treat it as a lead and not a finding.

**Analogy.** Think of an exclusive club. What gets you the good table is the membership card, not the size of your wallet. A millionaire member and a merely comfortable member are seated the same. A wealthy non-member still waits at the bar, though perhaps a little closer to the front than the other non-members.

### The big caveat: the two groups barely overlap

There is almost no such thing as a rich small-league school or a poor power-conference one. The poorest power-conference team in the study still has more revenue than every small-league team except BYU. Only two small-league team-seasons (BYU in 2015 and 2021) fall inside the power-conference money range at all.

So the statistics above are mostly comparing rich with richer inside one group, and poor with poorer inside the other. They can say "money does not matter within a league". They cannot fully rule out "you need a certain level of money, and every power-conference school is above it".

The way around that is **realignment**. When a school changes league (TCU and Utah earlier, then Cincinnati, UCF, Houston and BYU joining the Big 12 in 2023, and SMU joining the ACC in 2024), its league changes overnight while its budget barely moves. That is the cleanest test left, and most of the useful moves fall in the sealed 2024 and 2025 seasons.

### About the data

- Schools have leeway in how they fill in the federal form, so the figures are a good ranking of who is rich, not audited accounts.
- The 2020-21 year shows a COVID dip for everyone. Measuring each school against that season's average removes it.
- Raw files stay in `data/raw/eada/` and are not committed. The repo holds only the list matching each team to its federal school number.
- Getting the files needed one new allowed website, ope.ed.gov, which Sammy approved.

## What this does and does not show

- **It shows a pattern, not a motive.** The committee is consistently harder on small-league teams than AP voters are. That fits the "politics" idea, since the committee is largely made up of power-conference athletic directors. It also fits a plain football explanation: the committee weighs schedule strength more heavily, and may be right to.
- **The acid test leans against the committee but is far too small to settle it.** Twenty-six games, nine of them true upset chances.
- **League and money are mostly untangled, with one gap.** Within a league, money does not matter. But the two groups barely overlap in wealth, so a "minimum money to be taken seriously" story cannot be ruled out.
- **The margin of error treats each team-season as one unit**, because the same team appears week after week with almost the same rank. There are still only nine seasons, so a few unusual years carry weight.

## What I suggest next

1. **Feed what we learned into the CFP prediction model.** League, title-game result and the brand measure are now known to shape the committee's ranking in specific ways, which is exactly what the CFP correction model on the ideas list needs.
2. **Add long-run prestige and committee ties** (steps 2 and 5), which are cheap.
3. **Run the realignment test when the sealed seasons are opened.** It is the cleanest way to separate league from money, but 2024 and 2025 are also the prediction model's final exam, so opening them is Sammy's call.

## Run it yourself

```sh
uv run --extra finance python -m cfp_rankings.finance   # download the federal finance files (once, about 3 minutes)
uv run python -m cfp_rankings.clout                      # every number above (under a minute)
```
