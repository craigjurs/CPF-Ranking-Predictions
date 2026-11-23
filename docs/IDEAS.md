# Ideas list

A running list of things we might try. Think of it as the whiteboard in the hallway: anyone can add a line, and nothing here is a commitment until it moves to "In progress".

## How to use it

- **Add an idea** as a new row in the section that fits, with status `Not started`. A rough one-liner is fine.
- **Status** is one of `Not started`, `In progress`, `Done` or `Parked` (looked at, not worth it for now).
- **Leakage risk** means: how easy is it to accidentally use something that wasn't known yet when the poll came out? See "No peeking" in [baseline-results.md](baseline-results.md).
- **Tier** is the expected value for predicting next week's poll, taken from the data plan where it rated the idea. `?` means nobody has rated it yet.

One rule of thumb from the data plan helps sort new ideas. Voters see the final score. So anything that only *causes* a result (weather, injuries, travel) is mostly already baked into the score. An idea is most valuable when it changes how voters *read* a result, or when it tells us something the score can't.

## Already built or under way

Listed so they don't get added twice.

| Item | Status |
|---|---|
| Polls, games, sportsbook lines and calendar pulled for 2000 to 2025 | Done |
| Point-in-time snapshots and walk-forward backtest | Done |
| Naive baselines (same as last week, win/loss rule) | Done |
| First ML model for AP and Coaches: Stage 1 power rating and Stage 2 poll model | Done |
| Round two: momentum, power conference and queue inputs, seed averaging, and the Stage 3 "editor". Results: [round-2-results.md](round-2-results.md) | Done |

## Media and off-field signals

These are the ideas added on Nov 22, 2026. The first three share one big caution: a story written *after* the poll explains the poll. Every article, clip or post needs a publish time, and anything after the poll's cutoff must be thrown out.

| Idea | Status | Possible data source | Leakage risk | Tier | Notes |
|---|---|---|---|---|---|
| **News cycles: good and bad stories about a team** | Not started | GDELT or a news API: count and tone of articles per team per day | High. Needs strict publish-time cutoffs | Low | Already in the data plan. Expect it to mostly mirror the results. The useful question is whether a bad-news week moves a team *beyond* what its score explains. |
| **Pundit opinion (Pat McAfee and others)** | Not started | Published expert power rankings and "projected top 25" columns are the easy version. Show transcripts or video captions are the hard version | High. Pundits talk about the poll after it comes out, and same-day takes must be timestamped | ? | New. Many AP voters are media members themselves, so pundit consensus may be a preview of the ballot. Start with written rankings, which are already a number. Turning a talk show into a number is a project of its own. |
| **Player headlines: arrests, injuries, conflicts, domestic issues, commercials, professionalism** | Not started | Injuries: conference availability reports (recent seasons only). Everything else: news search | High. Stories are often published or backdated after the poll | Low | **Needs a decision first.** The [PII policy](security/pii-policy.md) currently forbids joining player data with news or other personal sources. See the note below the table. |
| **Recruiting efforts** | Not started | CFBD recruiting and team talent endpoints (not pulled yet, and not yet on the MCP server's allowlist, which the owner has to edit) | Low, if we use the class as it stood before the season. Ratings get revised later | Medium | Already in the data plan as part of "brand" and roster strength. Mostly drives the preseason poll. Many recruits are minors, so we keep team-level totals only (class rank, average rating), never per-recruit rows. |
| **High school star ratings of the players on the roster (for example, a 5-star QB)** | Not started | CFBD team talent composite as the quick version. CFBD recruiting ratings joined to rosters for the detailed version (neither pulled yet) | Low. A star rating is fixed when the player signs, long before any poll. The roster must be the one for that season | Medium | Close cousin of the recruiting row above: that one is about incoming classes, this one is about the talent actually on the field. Typical features: number of 5-star and 4-star players, share of the roster that is 4-star or better (the "blue-chip ratio"), and the star rating at key positions such as quarterback. Kept as team-level numbers, with rating and position only and no per-player files. |
| **Money, prestige and politics: do off-field forces tilt the rankings?** | In progress | Finances: EADA (all schools) and Knight-Newhouse (public schools). Conference payouts: tax filings. TV: Sports Media Watch and CFBD network slots. Committee ties: CFP recusal lists. Prestige: our own poll history | Low to medium. Use the previous year's figures. TV slots follow rank, so use past seasons only | ? | Added Nov 22, 2026. Test whether school wealth, booster money, brand, conference power, TV pull and committee ties explain the gap between a team's rank and what its on-field results justify. Team-level numbers only. Research and test design: [money-and-politics-in-rankings.md](research/money-and-politics-in-rankings.md). Results so far (the gap, the acid test, championships, money): [clout-step-1-results.md](clout-step-1-results.md). TV exposure and crowd size were tested on Nov 23, 2026 and add nothing once league is held fixed, the same answer as money. Committee ties (a school's own member, and league-mates on the committee) were tested the same day and also add nothing. What remains is a steady 2-spot tilt toward power conferences that looks like a shared belief, not favors. |

**Note on player headlines.** A model feature like "starting quarterback is out this week: yes or no" or "players listed out on the availability report: 4" is a team-level fact and fits the current policy. A table of which named player was arrested for what does not, and arguably shouldn't, since an arrest is not a conviction and these are college students. So the suggested shape is: team-level counts and flags only, nothing stored per named player. Anything beyond that means changing the PII policy on purpose first.

## Markets and odds

| Idea | Status | Possible data source | Leakage risk | Tier | Notes |
|---|---|---|---|---|---|
| **Log Kalshi AP ranking market prices each week** | Not started | Kalshi API price history, snapshotted at our poll cutoff | Medium. Use the price at the cutoff. Prices right before release may reflect leaked ballots | Medium as a benchmark | Markets only began in 2026, so this is a bar to beat, not training data. Worth starting soon because history we don't log is gone. |
| Log next week's opening lines on Sunday and Monday | Not started | Our own logging, or a paid odds-history vendor for past seasons | Medium. Only lines posted before the poll count | Medium | "How much did the market re-rate this team overnight?" CFBD doesn't timestamp lines, which is why they are left out today. |
| Title and playoff futures | Not started | Sportsbook futures (patchy history), Kalshi and Polymarket for recent seasons | Medium. Price at the cutoff only | Medium | Season-long strength signal, and a check on the CFP model. |

## Models and targets

| Idea | Status | Notes |
|---|---|---|
| **CFP correction model** | Done | Built as Stage 3: last week's committee ranking moved the way AP moved, plus learned weights and the committee's tastes in the first week. Average miss 1.14 against 1.41 for the old bar, then 1.08 after round two ([round-2-results.md](round-2-results.md)). The 12-team era (2024 on) still needs its own treatment. Results: [cfp-model-results.md](cfp-model-results.md) |
| CFP model for the 12-team era | Not started | From 2024 the top conference champions get automatic places, so the committee's ranking and the bracket follow different rules. Needs an era input and the sealed seasons. |
| Preseason poll model | Not started | There is no "last week" in August. Needs last season's final poll, returning talent and recruiting. |
| Multi-step forecast | Not started | Start from the preseason poll and feed the model its own predictions forward, to see how errors pile up. |
| In-season learning | Not started | Let the model also study the current season's earlier weeks. Keep it only if it beats the frozen version. |
| Live weekly run for 2026 | Not started | A small "refresh this week" pull plus a weekly prediction, scored as each poll comes out. |
| Model individual voter ballots | Not started | AP ballots are public in recent years. Shows where voters disagree. Voters are public in their professional role, so use for modeling only. |

## Game context features

Mostly things that cause a result rather than things voters react to, so they rank lower for now. They become more valuable if we forecast several weeks ahead.

| Idea | Status | Possible data source | Leakage risk | Tier | Notes |
|---|---|---|---|---|---|
| **Weather against a team's home climate** | Not started | Historical weather by venue and kickoff hour (Open-Meteo, Meteostat) | Low | Low for polls, Medium for game outcomes | Do voters forgive a loss in a snowstorm? |
| **Injury log for the current season** | Not started | Availability reports, logged live | High | Low for now | No good history exists, so the only way to get it is to start logging. Team-level counts only. |
| **Conference championships** | Done | Title games found by rule from CFBD games (no new data) | Low. The result is known before the final ranking | Medium | Added Nov 22, 2026. Measured in the clout study for the four-team era: about one extra spot for the winner beyond the win itself, and a title-game loss is partly forgiven. Tried as inputs to the CFP model and they did not help, because AP voters already react to title games the same way. The 12-team era gives champions automatic places, so it needs its own treatment. Results: [clout-step-1-results.md](clout-step-1-results.md) |
| **Realignment test for league against money** | Not started | Conference membership by season (already pulled) plus EADA finances (already pulled) | Low | ? | Added Nov 22, 2026. When a school changes league, its league changes overnight and its budget does not. Does the committee's treatment change? Most useful moves are in 2023 to 2025, so it largely waits on opening the sealed seasons. Background: [clout-step-1-results.md](clout-step-1-results.md) |
| Brand or prestige index | Not started | All-time weeks ranked, recruiting, attendance, school finances | Low | High | Do blue bloods fall less after a loss? Rated high in the data plan. |
| Transfer portal | Not started | CFBD transfer portal, roughly 2021 on | Medium | Medium | Net talent gained, mainly for the preseason poll. NIL money is not public. |
| Coaching changes | Not started | CFBD coaches | Low. Mid-season firings must be dated | Medium | First-year coach flag. |
| TV network and kickoff time | Data ready | CFBD games and media | Low | Medium | A primetime win is seen by more voters. TV listings for 2003 to 2025 are pulled and scored per team: [tv-data-setup.md](tv-data-setup.md). Tested in the clout study: past TV exposure does not explain the committee's ranking beyond league, so it is unlikely to help a model. The same-week version (was last Saturday's win in primetime?) is untested. |
| Computer ratings (SP+, FPI) | Not started | CFBD ratings | High. Some endpoints return season-final values | Medium | Pregame Elo is already in the games data and is safe. |
| Home, away, neutral and travel distance | Not started | CFBD games and venues | Low | Medium | |
| Rivalry games | Not started | Hand-built list of about 100 games | Low | Low | Are rivalry losses forgiven more? |
| Indoor or outdoor stadium | Not started | CFBD venues | Low | Low | |
| Referee crews | Parked | Sparsely published | Low | Low | Voters don't see crews, and penalties are already in the stats. |

## Data repairs

| Idea | Status | Notes |
|---|---|---|
| Repair 2000 to 2004 week alignment | Not started | Pulled but unused because polls and game weeks don't line up. |
| Bring back 2020 | Not started | Needs special handling for staggered conference starts. |
| Find "others receiving votes" | Not started | CFBD returns only the top 25, so teams ranked 26th to 35th are invisible. Needs another source. |
