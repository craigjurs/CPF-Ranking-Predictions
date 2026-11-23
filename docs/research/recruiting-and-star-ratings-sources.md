# Data sources: recruiting and high school star ratings

Research date: 2026-11-22. Scope: two ideas from the to-do list.

1. **Recruiting efforts**: class rankings, star ratings, transfer portal.
2. **High school stars per player**: for example "a 5-star QB", and how that rolls up into team features.

## Short answer

**Use CFBD for all of it. No new vendor, no scraping, no extra cost.** CFBD already carries per-recruit stars and ratings back to the 2000 class, which is deeper than the 2005 target. The only thing in the way is that this repo's CFBD tool does not have the recruiting endpoints on its menu yet, and that file is one only Sammy may change (see "What has to happen first").

**Analogy.** Think of a recruit's star rating as the resume a job candidate shows up with, and game results as the performance reviews that come later. A preseason poll is a hiring decision made on resumes alone. By November, voters have a stack of performance reviews and the resume matters much less. So expect these features to help most in the preseason and September polls, and to fade as the season goes on. That is a hypothesis to test, not a result.

## What CFBD covers

Coverage is from CFBD's own data availability page (last verified by CFBD on 2026-09-03).

| Dataset | CFBD endpoint | First year | What you get | Fits the idea |
|---|---|---|---|---|
| Player recruits | `/recruiting/players` | 2000 class | Per recruit: stars, rating (0 to 1 scale), national ranking, position, committed school, class year | Stars per player (idea 2) |
| Team recruiting rankings | `/recruiting/teams` | 2000 class | Per team per class: rank and points | Recruiting efforts (idea 1) |
| Position group ratings | `/recruiting/groups` | 2000 class | Per team per position group: rating over a range of class years | "How good is their QB room on paper" |
| Team talent composite | `/talent` | 2015 | One number per team per season for the talent actually on the roster | Roster talent after attrition and transfers |
| Returning production | `/player/returning` | 2014 | Share of last year's production coming back | Experience (see the note on "starts" below) |
| Transfer portal | `/player/portal` | 2021 | Per transfer: origin, destination, stars, rating, eligibility | Portal half of idea 1 |
| Rosters | `/roster` | 2004 | Who is on each team each season | Needed only for the roster-matched features below |

Junior college recruits start with the 2002 class. Prep school recruits cover 2012 to 2022 only.

CFBD warns that a listed year does not guarantee every team or field is complete, so early years (2000 to about 2005) should be spot-checked for missing teams before they are trusted.

### Cost and terms

- **Cost:** free tier is 1,000 calls a month. Paid tiers start at $1 a month for 5,000 calls. Nothing here needs a paid tier.
- **Terms (effective 2026-08-12):** model training, backtesting, feature engineering and private caching are explicitly allowed. Commercial use is allowed. The one firm restriction is that raw API data may not be republished as a standalone dataset, which this project already respects by keeping `data/raw/` out of git.
- **Where CFBD's recruiting numbers come from:** the terms do not say. My understanding is that they mirror the 247Sports Composite, but I could not confirm that from the pages I read.

### Call budget

A full one-time backfill is small. These counts assume one call returns a whole class year, which I have not been able to test (see "What I could not verify").

| Pull | Calls |
|---|---|
| Team recruiting rankings, 2000 to 2026 | 27 |
| Player recruits, 2000 to 2026 | 27 |
| Position groups (takes a start and end year) | 1 to 7 |
| Talent composite, 2015 to 2026 | 12 |
| Returning production, 2014 to 2026 | 13 |
| Transfer portal, 2021 to 2026 | 6 |
| **Total** | **about 90** |

That fits inside one day's cap of 200 and under a tenth of the monthly quota. After the backfill it is roughly 6 calls a year to stay current.

## Timing: is it known before each poll?

Yes, and this is the easy case. Recruiting data is a **once-a-year, preseason fact**, not a weekly one.

- A class is signed in December and February before the players' first season. By the preseason poll in August it is fixed.
- The talent composite and returning production are published before the season.
- Portal moves mostly finish before the season starts.

So every one of these is a constant for a team across all weeks of a season, and can be joined to the existing point-in-time snapshots by `(team, season)`.

Two leakage traps to avoid:

1. **Use the class year, not the calendar year.** The 2027 class is being recruited right now, during the 2026 season. It is incomplete and those players are not on the field. A feature for the 2026 season should only use classes 2026 and earlier.
2. **CFBD gives today's version of old numbers, not what was published at the time.** Recruit ratings are locked when a class signs, so that is low risk. The talent composite is the one to watch, since I could not confirm the exact date it is published each year. If it has ever come out after week 1, the preseason poll row should not use that season's value.

## Turning player stars into team features

Polls rank teams, so player stars have to be rolled up. Ordered from cheapest to most work:

**Level 1: class-based, no roster matching (2000 onward).** Uses only recruits and the school they signed with.

- Average recruit rating over the last four classes, with more weight on the classes that are now juniors and seniors.
- **Blue-chip ratio:** share of 4-star and 5-star signees over the last four classes. A well known rule of thumb is that national champions sit above 50 percent.
- Count of 5-stars signed in the last four classes.
- Team recruiting rank, and its change from the four-year average (is recruiting trending up or down).

**Level 2: position-aware (2000 onward).** Same data, grouped by position.

- Best quarterback rating signed in the last four classes, and a flag for "has a 5-star QB".
- Position group ratings for QB, offensive line, defensive line and so on.

**Level 3: who is actually on the roster.** Level 1 and 2 count everyone who signed, including players who transferred out or left early. Think of it as counting everyone a company ever hired instead of who is at their desk today.

- From 2015: the talent composite already does this in one number. Use it.
- From 2021: add net portal talent (rating of transfers in minus transfers out).
- For 2004 to 2014: recruits could be matched to rosters by CFBD's athlete id. This is the most work and the most error-prone step. I would only do it if Level 1 and 2 show real value in the backtest.

Because the talent composite only starts in 2015 and portal data in 2021, those columns will be empty for earlier seasons. The model needs to handle missing values, or those features get tested only on the modern era that `docs/baseline-results.md` already labels.

## Privacy

Recruits are often minors, and `docs/security/pii-policy.md` already sets the rule. The CFBD recruit record includes fields this project should not keep: name, high school, city, state, country, hometown details, height and weight.

- Keep only: class year, stars, rating, ranking, position, committed school, recruit type.
- Drop the rest at pull time, before anything is written, rather than filtering later.
- Commit only team-level aggregates. Never publish per-recruit rows.
- Level 3 roster matching needs the athlete id. Use the id for the join and do not carry names through.

## Outside sources, and why not

| Source | What it has | Why I would not use it |
|---|---|---|
| 247Sports | The Composite rating that the industry treats as the standard, plus its own ratings | No public API. Its terms limit content to personal, non-commercial viewing and bar redistribution. Getting it means scraping, and CFBD appears to carry the same numbers already |
| On3 and Rivals | Their own ratings and an industry average. On3 is strong on portal and NIL coverage | No public API. On3 only launched in 2021, so no history for its own ratings. Third-party scrapers exist but they collect per-recruit profiles, which collides with the privacy policy |
| ESPN | ESPN 300 and its own grades | No supported API for recruiting. Covers fewer players than the Composite |
| MaxPreps | High school game stats | It is a database about high school students. It adds privacy risk and nothing a poll voter looks at. Skip |
| Sportradar and other paid feeds | Licensed portal and roster feeds | Enterprise pricing, and nothing here that CFBD lacks for this purpose |

Dates and ownership details for On3 and Rivals are from my own background knowledge, not from a page I checked.

The one real gap CFBD has is **pre-2021 transfers** and **pre-2015 roster talent**. No source I found fills those cleanly. Transfers were rare enough before the portal that I would accept the gap.

## What has to happen first

The repo's CFBD tool works from a fixed menu in `mcp_servers/cfbd/src/cfbd_mcp/endpoints.py`. Today that menu has games, rankings, lines, records, teams, calendar and three ratings. **None of the recruiting, talent, returning production, portal or roster endpoints are on it**, so agents cannot pull this data yet.

That file is part of the security harness, so agents must not edit it. Sammy would need to add entries along these lines, in the same style as the existing ones:

| Tool name | Path | Parameters |
|---|---|---|
| `recruiting_teams` | `/recruiting/teams` | `year`, `team` |
| `recruiting_players` | `/recruiting/players` | `year`, `team` |
| `recruiting_groups` | `/recruiting/groups` | `start_year` to `startYear`, `end_year` to `endYear`, `team`, `conference` |
| `talent` | `/talent` | `year` |
| `returning_production` | `/player/returning` | `year`, `team`, `conference` |
| `transfer_portal` | `/player/portal` | `year` |

`recruiting_groups` has no single `year`, so it needs its own `required` setting. Rosters can wait until Level 3 is on the table.

## Recommended order

1. Sammy adds `recruiting_teams`, `recruiting_players` and `talent` to the allowlist.
2. Backfill those three (about 65 calls), dropping personal fields at pull time.
3. Build Level 1 features and the talent composite, join by `(team, season)`, and rerun the existing backtest against the baselines.
4. If they help, add position groups, returning production and portal.
5. Consider Level 3 roster matching only if the earlier steps earn it.

## A note on "starts"

This research first read idea 2 as "starts" before Sammy corrected it to "stars", so the starts angle was dropped. If experience becomes interesting later, CFBD's returning production (2014 onward) is the nearest ready-made measure. The classic "career offensive line starts" numbers come from Phil Steele's preseason magazine and are not available as a dataset.

## What I could not verify

- **No CFBD calls were made for this research**, because the endpoints are not on the allowlist. Everything about CFBD comes from its documentation, not from looking at real responses.
- Whether one call to `/recruiting/players` returns a full class or is paged. This changes the call budget.
- How complete the 2000 to 2005 classes are.
- The exact date the talent composite is published each year.
- The field list comes from an older client library's docs and may have changed.

## Sources

- CFBD data availability: https://api.collegefootballdata.com/data-availability.md
- CFBD API tiers: https://collegefootballdata.com/api-tiers
- CFBD terms: https://collegefootballdata.com/terms
- CFBD recruiting endpoints and recruit fields (cfb.js 4.1.4 docs): https://app.unpkg.com/cfb.js@4.1.4/files/docs/RecruitingApi.md
- 247Sports terms of use: https://legal.paramount.com/us/en/cbsi/247sports-terms-of-use
