# Research: do money, prestige and politics move the rankings?

*Research and a test design only. Nothing here has been pulled, signed up for, or wired into the pipeline. Checked on 2026-11-22.*

## The short answer

**The question is testable, and most of the data is free.** The cleanest way to ask it is not "do rich schools rank higher?" (of course they do, money buys good teams) but:

> When two teams have done the same things on the field, does the richer, more famous, better-connected one get ranked higher?

**Analogy.** Two gymnasts perform the same routine. If the famous one keeps scoring a tenth higher, the judges are scoring the name and not the routine. Our Stage 1 rating is the "routine": it sees only scores and schedules, with the names covered. The committee's ranking is the judges' score. The gap between the two is what we study.

Three things to know up front:

1. **Earlier studies already found this kind of bias in the AP and Coaches polls**, including a dollar figure for the Coaches poll. Nobody appears to have tested the CFP committee the same way. That is the opening.
2. **"Money", "prestige" and "TV" are nearly the same list of schools.** Ohio State is rich, famous and always on in primetime. We can measure whether that bundle (call it *clout*) matters much more easily than we can say which part of it is responsible.
3. **A gap is not proof of a thumb on the scale.** The committee is told to weigh things Stage 1 ignores, and rich teams may truly be better than their scores show. The design below includes a check for that (section "The acid test").

## What earlier research found

| Study | What they looked at | What they found |
|---|---|---|
| [Campbell, Rogers and Finney, 2007](https://econpapers.repec.org/RePEc:sae:jospec:v:8:y:2007:i:4:p:425-434), *Journal of Sports Economics* | AP poll, 2003 and 2004 seasons | Teams with more TV exposure gained more votes, after allowing for results on the field |
| [Coleman, Gallo, Mason and Steagall, 2010](https://econpapers.repec.org/RePEc:sae:jospec:v:11:y:2010:i:4:p:397-417), same journal | Every AP voter's weekly ballot, 2007 | Voters favored teams from their own state, big-conference teams and teams in televised games, even after allowing for 16 computer rankings |
| [Witte and Mirabile, 2010](https://econpapers.repec.org/RePEc:sae:jospec:v:11:y:2010:i:4:p:443-455), same journal | AP and Coaches polls, 2004 to 2008 | Coaches ranked recent opponents about 4 places higher than their peers did. Both polls over-rated certain big conferences |
| [Kotchen and Potoski, 2011](https://www.nber.org/papers/w17628.pdf), NBER working paper | Coaches' final ballots, 2005 to 2010 | Coaches ranked their own team more than two spots higher and their own conference almost one spot higher. They also favored bubble teams whose bowl berth would pay their own school more |
| [Coleman and others, 2024](https://ideas.repec.org/a/taf/apeclt/v31y2024i11p1045-1048.html), *Applied Economics Letters* | AP ballots, 2018 and 2019, against 2007 | Home-state bias had faded, but the tilt toward Notre Dame and Power 5 teams had grown |
| [Lucas, 2024](https://arxiv.org/html/2403.03862v1), preprint | CFP picks against Elo, 2014 to 2023 | The committee's top four never matched Elo's top four. It did not test *why* |

I read the abstracts and summaries, not the full papers (most are paywalled), so treat the exact numbers as reported rather than checked.

Two lessons carry over. First, the effects that were found were real but modest: a spot or two, not ten. Second, the strongest studies had **ballots from individual voters**, so they could compare one judge with another on the same team in the same week. The CFP committee publishes only one combined ranking, which makes our job harder.

## Data sources for each force

"Team-level only" applies throughout. Nothing below needs data about individual players, recruits or donors.

### School wealth and athletic budgets

| Source | What it has | Years | Cost | Catch | Verdict |
|---|---|---|---|---|---|
| [Knight-Newhouse College Athletics Database](https://www.knightnewhousedata.org/about-the-data) | Athletic department revenue and spending by category for each school: football spending, football coaching pay, donor contributions, media and conference money, school subsidy | Fiscal 2005 to about 2025 | Free to browse. I could not confirm a bulk download, the report tool sits behind a CAPTCHA | **Public schools only** (about 230). Notre Dame, USC, Stanford, Miami and other private schools are missing. Self-reported. No reuse terms stated beyond "used with permission from USA TODAY" | **Best detail**, but the private-school hole matters because several are big brands |
| [EADA, US Department of Education](https://ope.ed.gov/athletics/#/datafile/list) | Revenue and expenses per school, with a record per sport from 2008 on | 2002 to 2023 in one archive | Free. Government data, downloadable as one file ([archived copy](https://www.datalumos.org/datalumos/project/218162/version/V1/view)) | Coarser than Knight-Newhouse, and schools have leeway in how they report, so football numbers are not perfectly comparable | **Start here.** It is the only free source that **includes private schools** |
| [Sportico College Sports Finances Database](https://d3data.sportico.com/NCAADatabase/index.html) | Public FBS athletic department financials | 2017-18 to 2024-25 | Appears free | Shorter history, public schools only | Backup and cross-check |
| USA Today NCAA finances | The original public-records collection | 2005 on | Free | It is the same underlying data that Knight-Newhouse now hosts | No need to collect separately |

Whole-university wealth (endowment size, from federal IPEDS data) is a possible extra. I did not check it in this pass.

### Boosters and NIL collectives

This is the weakest area for data, and it is worth being blunt about that.

| Source | What it has | Years | Cost | Verdict |
|---|---|---|---|---|
| Knight-Newhouse "donor contributions" line | Money given to the athletic department each year | Fiscal 2005 on, public schools | Free | **The usable measure of booster money.** A long, consistent series |
| [On3 collective estimates](https://www.on3.com/nil/news/on3s-top-15-nil-collectives-in-college-sports) and similar press reports | Rough dollar estimates for a handful of collectives | About 2022 on | Free | Scattered, unaudited, different years and definitions per school. **Not a dataset** |
| [Opendorse annual NIL report](https://frontofficesports.com/article/college-sports-roster-spending-soars-beyond-20-5m-rev-share-cap/) | Market-wide estimates (for example, Power 4 schools averaging about $13.5M in outside NIL on top of the cap) | 2021 on | Free summary | Averages only, no per-school numbers that I could find |
| [StickToTheModel roster spend](https://sticktothemodel.com/college-roster-spend) | Per-school football roster spending estimates | 2026 only | Free page, paid tiers exist | It is *modeled from athletic revenue*, so it is the wealth data again under another name. Adds nothing new |

NIL only became legal in mid-2021 and collectives are private, so there is no trustworthy per-school history. From 2025-26 schools may also pay players directly up to a cap (about $20.5M in the first year), which makes the top programs look more alike on paper. **Recommendation: use donor contributions as the booster measure and treat NIL as a footnote**, unless verified per-school figures become public.

### Prestige and brand

We already have most of this, with no new source needed.

| Measure | Source | Status |
|---|---|---|
| Recent-success brand (share of the last five seasons finishing ranked) | Our own poll data | **Already a feature** in the Stage 2 model |
| Long-run prestige (weeks ranked in the AP poll over the previous 20 or 50 years) | CFBD poll history, which goes back to 1936 | Easy to build from data we can already pull |
| Fan base size (stadium size, average attendance) | CFBD venues and game attendance | The venues tool is not on our allowed list yet. Adding it means a change to `endpoints.py`, which needs your OK |
| "Blue blood" yes or no | A hand-made list of 8 to 12 programs | Simple, but the list itself is an opinion. Use only as a cross-check |

### Conference power

| Source | What it has | Years | Cost | Verdict |
|---|---|---|---|---|
| Conference tax filings (IRS Form 990), via [ProPublica Nonprofit Explorer](https://projects.propublica.org/nonprofits/) or the yearly [AP and USA Today write-ups](https://www.foxsports.com/articles/cfb/tax-filings-acc-paid-average-of-471m-to-fullshare-member-schools-big-12-paid-average-of-395m) | Total conference revenue and the payout to each school | Roughly 2001 on for electronic filings; about 10 conferences a year | Free | **Good and cheap.** Only about 120 numbers for the whole CFP era, so it can be typed in by hand |
| Conference membership by season | CFBD teams | Already pulled | Free | Needed for the realignment test below |

To give a feel for the spread: for the 2024-25 year the average full-share payout was about $79.9M in the Big Ten, $72.4M in the SEC, $47.1M in the ACC and $39.5M in the Big 12.

### TV ratings and network deals

| Source | What it has | Years | Cost | Catch | Verdict |
|---|---|---|---|---|---|
| [Sports Media Watch](https://www.sportsmediawatch.com/college-football-tv-ratings/) | Viewers per game, with teams and network | Season pages back to about 2013 (start year not confirmed) | Free to read | Much of it is in chart images, so collecting it is slow. No reuse terms stated, so ask before scraping. Games on SEC Network, ACC Network and streaming have no Nielsen number | **Best free source**, with effort |
| Network and kickoff slot for every game | CFBD game media | 2000s on | Free with our key | Not on our allowed list yet (needs your OK) | **The cheap stand-in.** "How many games on ABC, CBS, Fox or NBC in primetime" is close to what the 2007 study used |
| Nielsen directly | Complete ratings | Everything | Paid, enterprise pricing | | Not worth it |

A warning that applies to TV more than anything else: **networks pick the games they expect to be good.** A highly ranked team gets the primetime slot *because* it is highly ranked. So TV must be measured from earlier seasons (a team's average audience over the previous three years), never from the current one.

### Committee member ties

| Source | What it has | Years | Cost | Verdict |
|---|---|---|---|---|
| [CFP recusal lists](https://collegefootballplayoff.com/sports/2016/10/24/selection-committee-protocol) | Each season, which of the 13 members is recused from which school, and whether fully or partly | Published for 2025 and 2026 on the CFP site. Press coverage exists for earlier years (for example [2019](https://africa.espn.com/college-football/story/_/id/27396060/10-cfp-committee-members-get-voting-recusals), when 10 of 13 members had a recusal). Not confirmed for every year back to 2014 | Free | **The most interesting source here**, see below |
| Committee rosters by season | Who served and their day job (many are sitting athletic directors) | 2014 on | Free, from CFP press releases | Gives each member's conference |

How recusal works: a member paid by a school, or with close family in its football program, cannot vote on that team and must leave the room when it is discussed. So a direct vote for your own school is already blocked. The question worth asking is the softer one: does a school with a friend on the committee, or a *conference* with more seats at the table, do better anyway?

**Privacy note.** Committee members are public figures in this role, the same as AP voters under our [PII policy](../security/pii-policy.md). We would still store this as team-level numbers only, for example "this school has a recused member this season: yes or no" and "committee seats held by this team's conference: 3". No per-person files.

## How to test for bias

### Step 1: build the gap

For every team in every CFP ranking:

> **gap = where on-field performance says the team should rank, minus where the committee ranked it**

A gap of +3 means the committee put the team three spots higher than its results justify.

"Where on-field performance says" should not rest on one yardstick, because every yardstick has its own quirks. Use four and see whether they agree:

| Yardstick | What it captures | Already have it? |
|---|---|---|
| Stage 1 **résumé** rating | What the team has accomplished (wins and who they came against) | Yes |
| Stage 1 **power** rating | How strong the team looks (margins) | Yes |
| Sportsbook market rating | What people betting real money think | Lines are pulled; needs a small rating built from them |
| The committee's own stated criteria | Record, schedule strength, head-to-head, conference titles | Buildable from games |

The fourth one matters for fairness. The committee is *instructed* to reward conference champions and head-to-head wins. If we don't allow for that, we would be accusing them of bias for following their own rulebook.

### Step 2: ask whether clout explains the gap

Fit a simple model: gap explained by the off-field measures, each taken from **before** the season (last year's budget, the previous three years' TV audience, and so on). Then read off, in plain units: "an extra $50M of athletic revenue goes with X extra spots, for the same on-field record."

Because wealth, prestige and TV travel together, run it two ways:

- **One combined clout score.** Answers "does the bundle matter?" This is the test most likely to give a clear answer.
- **Each factor on its own.** Answers "which part?" Expect blurry results here, and say so.

### Step 3: three sharper tests

These look for situations where one thing changes while the team stays the same, which is as close as we get to a real experiment.

1. **Committee against AP voters, same team, same week.** Both sets of judges watched the same games. If the committee ranks rich teams higher than the AP does, that points at the committee specifically. If both do it equally, it is a habit all human rankers share.
2. **A friend on the committee.** Compare the same school in seasons when it has a recused member with seasons when it does not. Same school, same brand, same budget; only the connection changes. Also count whether teams gain when their conference holds more seats.
3. **Realignment.** When a team changes conference (Texas and Oklahoma to the SEC, USC and Oregon to the Big Ten), its conference clout jumps overnight while the program is the same. Does its gap change?

### The acid test: were the favored teams actually better?

This is what separates **bias** from **the judges knowing something the scores don't**.

Take the teams the committee ranked well above their on-field numbers. Then watch what they did next: later games, the conference title game, the bowl or playoff.

- If they **lost more often than their ranking implied** (and failed to cover the spread), the committee was fooled by the name. That is bias.
- If they **lived up to the ranking**, the committee saw real quality that Stage 1 missed. Rich programs have more talented rosters, and talent can show up later than the scoreboard.

Back to the gymnast: if the famous one keeps getting generous scores and then falls at the next meet, the judges were wrong. If she keeps winning, they were right to believe in her.

### How much data is there?

- CFP rankings: about 6 a season since 2014. Through 2023 that is roughly 54 rankings and about 1,350 team-rows.
- But the same team shows up week after week with nearly the same rank, so those are not 1,350 independent facts. It is closer to **250 team-seasons**. That is enough to detect an effect of about a spot, and not enough for fine detail.
- The AP and Coaches polls have 256 polls each back to 2005. Running the same test there gives far more power, and tells us whether the committee is better or worse than the voters.
- **2024 and 2025 stay sealed.** This study should use 2014 to 2023 only, like the rest of the modeling. The 12-team era would be a separate, later look.

## Honest limits

- **This can show a pattern, not a motive.** "Richer teams rank about one spot higher than results justify" is a finding. "The committee is bought" is not something data like this can show.
- **The private-school gap.** Notre Dame is the single most-cited example of brand favoritism and it is missing from the best finance database. EADA fills the hole with rougher numbers.
- **Money moves slowly.** A school's budget rank barely changes year to year, so in practice "wealth" acts like a fixed label on the school. That is why the three sharper tests matter: they find the rare cases where something does change.
- **Many hypotheses, one small dataset.** Test enough factors and one will look significant by luck. The guard is to write down the handful of tests above *before* looking, and report all of them, including the ones that find nothing.
- **Timing.** Finance data for a fiscal year arrives a year or more later. Always use the previous year's figures so nothing from the future leaks in.

## A second payoff: better predictions

Even if the answer to "is it biased?" turns out to be "a little", these same measures are candidate inputs for the CFP correction model on the [ideas list](../IDEAS.md). If the committee reliably treats clout a certain way, the prediction model should know it, whatever we think of the fairness.

## Recommended order of work

| Step | Work | New data | Needs your OK? |
|---|---|---|---|
| 1 | Build the gap from Stage 1 and existing polls, and run the "committee against AP" comparison using the brand feature we already have | None | No |
| 2 | Add the long-run prestige measure from AP history | None | No |
| 3 | Add EADA finances and conference payouts | Two free downloads, kept in `data/raw/` | No |
| 4 | Run the acid test | None | No |
| 5 | Add committee ties from recusal lists | Hand-typed, about 16 rows a season | No |
| 6 | Add TV (network slots from CFBD, then Sports Media Watch audiences) | CFBD media and venues tools | **Yes**: an `endpoints.py` change, and a note to Sports Media Watch before collecting |

Steps 1 and 2 cost nothing and would show within a day of work whether there is a signal worth chasing.

## Decisions so far

Answered by Sammy on 2026-11-22.

| Question | Answer |
|---|---|
| Which ranking is the main target? | **The CFP committee.** AP and Coaches are the comparison group |
| Is "does clout matter?" enough, or do we need "which factor?" | **"Does clout matter?" is enough for now.** The combined clout score is the main test. The factor-by-factor split is a later extra |

What "does clout matter?" will produce is not a bare yes or no. It is a size with a margin of error, for example "a high-clout team is ranked about 1.2 spots higher than its results justify, give or take 0.5". The yes or no falls out of that: if the range sits clearly away from zero, the answer is yes. The clout score itself is also a sliding scale and not a 0 or 1 label, so a mid-sized program sits between Ohio State and a small school.

## Still open

- **Adding the CFBD media and venues tools** for step 6 (TV). Not approved yet. It means a change to `endpoints.py`, so it waits for Sammy's OK.
