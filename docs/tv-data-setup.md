# TV data setup

*Set up Nov 23, 2026. This is step 6 of the plan in [money-and-politics-in-rankings.md](research/money-and-politics-in-rankings.md). It prepares the data. The test itself ("does TV pull buy a better ranking?") is the next step.*

## What this adds

Think of the CFBD server as a restaurant with a fixed menu: the project can order only what is printed on it. This step prints two new dishes, both approved by Sammy on Nov 22, 2026.

| New menu item | What it returns | How it is used |
|---|---|---|
| `get_game_media` | The TV network and kickoff time of each game | How often each team is on national TV |
| `get_venues` | Every stadium with its capacity | How big each team's home crowd can be |

Both are read-only and team-level. Neither touches any personal data.

## What was pulled

- TV listings for 2003 to 2025, one file per season in `data/raw/media/`. CFBD has nothing for 2000 to 2002.
- The stadium list, once, in `data/raw/venues.json`.
- Cost: 27 CFBD calls in total. Re-running the pull costs nothing, because cached files are never fetched again.

## The measures

`src/cfp_rankings/tv.py` turns the listings into one row per team and season, counting regular-season games only:

| Measure | Meaning |
|---|---|
| National TV games | Games on ABC, CBS, FOX, NBC, ESPN, ESPN2 or FS1 |
| On free broadcast | Games on ABC, CBS, FOX or NBC only |
| National primetime | National games kicking off at 7 PM Eastern or later |
| Home crowd | Average announced attendance at true home games |
| Stadium | Capacity of the stadium the team used most |

**Every score is an average over the three seasons before the one being studied.** The reason is the window table problem. A restaurant seats its best-dressed guests in the window, so you cannot tell whether the window made them noticed or they got the window because they were already noticed. Networks likewise pick the games they expect to be good, so this season's TV slots are partly a *result* of this season's ranking. Last season's slots cannot be.

Bowls and playoff games are left out for the same reason: a bowl slot is a reward for the ranking.

## Does it look right?

Going into 2023, the most-televised teams were:

| Team | National TV games a year | On free broadcast | National primetime | Home crowd | Stadium |
|---|---|---|---|---|---|
| Notre Dame | 10.7 | 10.7 | 4.0 | 74,375 | 80,795 |
| Oklahoma | 10.0 | 8.0 | 3.3 | 80,583 | 86,112 |
| Oklahoma State | 10.0 | 5.7 | 3.3 | 53,874 | 55,509 |
| Alabama | 9.3 | 6.3 | 4.3 | 98,851 | 101,821 |
| TCU | 9.3 | 5.0 | 2.7 | 42,775 | 46,000 |
| Texas | 9.3 | 6.3 | 1.7 | 96,410 | 100,119 |
| Oregon | 9.0 | 5.3 | 4.7 | 51,998 | 54,000 |
| Michigan | 9.0 | 8.3 | 2.7 | 109,554 | 107,601 |

At the other end, Massachusetts, Rice, North Texas, Old Dominion and Liberty had no national TV games at all. Notre Dame at the top is the expected answer: NBC shows every home game. See any season with `uv run python -m cfp_rankings.tv --season 2019`.

## What to know before using it

1. **The "national" count flatters the Big 12.** Oklahoma State, TCU and Baylor sit near the top because the Big 12 had no channel of its own, so its smaller games landed on ESPN and FS1. The SEC and Big Ten put their smaller games on SEC Network and Big Ten Network, which do not count as national here. **The free-broadcast count is the fairer measure of "the network wanted this team."** Both are kept so the test can try each.
2. **TV, money and crowds are close to the same list.** Across FBS teams the TV score moves with athletic revenue (correlation about 0.6 to 0.8, depending on the season) and with home crowd size (about 0.8 to 0.85). This is the bundle problem from the research plan: expect a clear answer to "does the bundle matter" and a blurry one to "which part."
3. **Coverage is partial.** CFBD lists a network for about two games in three from 2012 on. The rest were streaming or regional. Before 2012 the listings are thin and uneven (176 of 792 games in 2007). That is fine for the CFP era, which starts in 2014, and shaky for the BCS years.
4. **Slots are not viewers.** A noon game on ABC and a primetime game on ABC count the same in the first two measures. Real audience numbers would need Sports Media Watch, and the plan says to ask them before collecting.
5. **Stadium capacity is today's figure**, not the figure in each past season.

## What came of it

The test was run the same day. TV exposure and crowd size add nothing once league is held fixed. See "TV and crowds against league" in [clout-step-1-results.md](clout-step-1-results.md).
