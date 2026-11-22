# Research: data sources for news cycles and player headlines

Researched 2026-11-22. This is research only. Nothing was signed up for, no keys were added, and no data was pulled.

It covers two ideas from the ideas list:

1. **News cycles**: good and bad stories about a team.
2. **Player headlines**: arrests, injuries, conflicts, domestic issues, commercials and NIL, professionalism.

## The short answer

| Idea | Best source | History | Cost | Verdict |
|---|---|---|---|---|
| News volume and mood per team | **GDELT** (free news index) | 2015 on (2017 on through the easy API) | Free | Worth a small pilot |
| Public attention per team, back to 2005 | **Google Trends** | 2004 on | Free, but no stable official access for old data | Second choice, fragile |
| "A key player is out" | **CFBD player box scores we can already reach** | Same as our game data | Free, uses existing quota | Best first step for player headlines |
| Arrests, domestic issues, conflicts, NIL | No clean historical source exists | Patchy | n/a | Don't build per player. Team-level counts from GDELT at most |

**No free source gives team news with good timestamps back to 2005.** Good coverage starts in 2015. So news features can only be tested on roughly the last ten seasons, as an optional add-on to the main model, not as part of its 2000 to 2025 backbone.

**Recommended order of work:**

1. Derive a team-level "starting QB changed" flag from CFBD box scores. It needs no new vendor and no privacy-policy change.
2. Run a one-season GDELT pilot to see if news volume and tone explain anything the baseline model misses.
3. Only if the pilot shows signal, backfill GDELT to 2015 and consider Google Trends for the older seasons.

## An analogy for what we are trying to measure

Our current data is the **scoreboard**: who won, by how much, against whom. News is the **weather report around the stadium**. Voters are people, and people are swayed by the mood around a team, not only by the score.

The catch is that most weather is caused by the scoreboard. A team that loses gets bad press, and the model already knows it lost. News only helps where it carries something the score doesn't: a star quarterback hurt in a win, a coach fired on Sunday morning, a week of "this team is a fraud" talk after an ugly win. So the question for every source below is whether it adds anything beyond the result we already have.

## Idea 1: news cycles

### GDELT (recommended)

GDELT is a free, open index of world news. Think of it as a **library card catalog** for news: it doesn't hand you the articles, but for each one it records when it was published, which outlet ran it, which organizations and people it mentions, and a mood score ("tone").

| Question | Answer |
|---|---|
| History | GDELT 2.0 data starts 2015-02-19. The simple search API ("DOC 2.0") searches from 2017-01-01 on |
| Timestamps | Updated every 15 minutes, so we can cut off cleanly before each poll |
| Cost and license | Free for any use, including commercial. Any use or redistribution must cite the GDELT Project and link to its site |
| Key needed | DOC API: no key mentioned in its docs. BigQuery route: needs a Google Cloud account, which would go through the secrets harness |
| Full article text | Not included. We get metadata, tone and links |

There are two ways in:

- **DOC 2.0 API (start here).** One web request returns a daily time series for a search such as `"Penn State" football`. The useful modes are `TimelineVolRaw` (article count per day, plus the total number of articles monitored, so we can compute a share) and `TimelineTone` (average tone per day). Roughly 136 teams times 2 modes times 9 seasons is about 2,500 requests in total, done once and saved to `data/raw/`.
- **BigQuery (`gdelt-bq.gdeltv2.gkg`), only if needed.** This reaches back to 2015 and allows filtering by theme. The table is very large, so careless queries can cost real money once Google's free monthly query allowance is used up. Use it only with date-partitioned queries and a spending cap.

**Features to build, per team and poll week:**

- `news_volume_z`: this week's article share compared with the team's own normal level. Comparing a team with itself matters because Ohio State always gets more coverage than Toledo, and we don't want to just re-measure brand size.
- `news_tone_z`: this week's average tone compared with the team's own normal.
- `news_volume_nongame`: volume on Monday through Friday only, which is the part least explained by Saturday's score.

**Known problems:**

- **Tone misreads sports writing.** GDELT's tone comes from a general word list. "Georgia crushes, destroys, hammers Florida" reads as negative, even though it is great news for Georgia. Treat raw tone with suspicion and check it in the pilot. A later upgrade would be scoring headlines with our own small classifier.
- **Team names are ambiguous.** "Washington", "Miami", "Georgia" and "USC" all match non-football news. Queries need the word "football" or the nickname, and a spot check per team.
- **Coverage grows over time.** GDELT monitored fewer outlets in 2015 than now. Using a share of all articles, not a raw count, corrects for this.

### Google Trends (second choice, for depth back to 2005)

Trends measures how much people **search** for a team, not what the press wrote. It is the only free signal here that reaches back to 2004.

- **Official API (alpha, announced July 2025):** access is by application, and it only offers a rolling window of the last 5 years. That doesn't solve our history problem.
- **Website and unofficial libraries such as pytrends:** reach back to 2004, but unofficial access is rate limited and breaks without notice.
- **Leakage trap:** the website rescales every chart to 0 to 100 using the peak of the whole window. If the window includes future weeks, a past week's value changes depending on what happened later. Each pull would have to end at the poll date, which multiplies the number of requests.
- Long windows return monthly, not weekly, values, so weekly history requires stitching overlapping windows.

It has no tone at all, only attention. Worth trying only if the GDELT pilot shows that attention matters.

### Evaluated and not recommended

| Source | Why not |
|---|---|
| **Event Registry / NewsAPI.ai** | The best paid option: archive since 2014 with sentiment included. Paid plans start at $90 a month, the free tier covers only the last 30 days, and the archive is no deeper than free GDELT |
| **NewsAPI.org** | Free tier is 100 requests a day with a 1-month archive, for development only. A 5-year archive costs $449 a month |
| **NewsData.io, GNews, NewsCatcher, Webz.io** | Free tiers reach back 30 days at most. Paid history is 5 years or less (NewsCatcher from 2019), or priced by sales call |
| **Media Cloud** | Free and open, 4,000 API requests a week. Coverage starts per outlet whenever they began collecting it, there is no stated start year, and it has no tone score. A possible fallback for counts |
| **New York Times Archive API** | Free key, headline metadata going back well before 2005. But it is one outlet with thin college football coverage, and its terms need checking. Details here are from memory, not verified in this research |
| **Wikipedia pageviews** | Free and needs no key, but per-article daily data only starts in mid-2015 (start date from memory, not verified). It measures attention only, so it adds little over GDELT |

## Idea 2: player headlines

### First, a policy conflict to settle

`docs/security/pii-policy.md` rule 2 says: "Don't join player data with social media, news scraping, or other personal sources." A per-player feed of arrests or domestic issues is exactly that, so it can't be built under today's policy.

| Option | What is stored | Policy change needed? |
|---|---|---|
| **A. Team-level flags from CFBD box scores** | "Starting QB changed: yes/no" per team and week | No |
| **B. Team-level news counts from GDELT** | "Articles this week mentioning Team X plus an arrest or suspension theme: 7". No names | Probably not, since no player data is stored. Sammy should confirm, because it is still news-derived |
| **C. Per-player incident records** | Named player, incident type, date | **Yes**, rules 1 and 2 would have to change |

**Recommendation: do A, pilot B, and don't do C.** Beyond policy, C has practical problems: an arrest is an accusation, not a finding; many are later dismissed; some players are minors; and the labels would have to be collected by hand or by an unreliable scraper.

### Injuries and availability

Official injury reports are new in college football, so there is almost no history:

| Who | Started | Notes |
|---|---|---|
| Big Ten | 2023 | Published on game day |
| SEC | 2024 | Wednesday, Thursday and Friday before conference games, final report 90 minutes before kickoff |
| College Football Playoff | 2025 season | Playoff games only |
| Big 12 | "This season" in an undated AP story, most likely 2026 | Daily from three days before conference games |
| ACC | Not confirmed in this research | |

Two to three seasons, for some conferences, for conference games only, is far too little to train on. There is also no free API. The reports are PDFs and web pages on conference sites.

**The better route is to infer absences from data we already have access to.** A box score is an **attendance sheet**: if the quarterback who threw every pass through week 6 has no passes in week 7, he was out. CFBD publishes per-game player stats (endpoint name and year coverage to be confirmed through the MCP tools). From that we can derive team-level flags with the same history as our game data:

- `qb_changed`: the leading passer differs from the team's season-to-date leading passer.
- `top_rusher_missing`, `top_receiver_missing`: the same idea for other positions.

This flag is known by Saturday night, before the Sunday poll, so there is no leakage. The output is a yes/no per team and week, with no player names stored.

One setup step is needed: the CFBD MCP server currently allows only games, rankings, lines, records, teams, calendar and ratings. Adding a player-stats endpoint means editing `mcp_servers/cfbd/src/cfbd_mcp/endpoints.py`, which is part of the security harness, so **Sammy has to make that change**. Per-game player pulls also use more quota than team pulls, so plan them by week and conference.

### Arrests, conflicts and domestic issues

- **ArrestNation.com** tracked media reports of athlete arrests around 2011 to 2016. A newspaper recount found 37 arrests where the site listed 31 for one school, so its accuracy was shaky. Whether it still exists wasn't confirmed. Not usable as a data feed.
- No maintained, licensed, historical database of college athlete arrests turned up.
- **Team-level proxy (option B):** GDELT tags articles with themes such as arrests. Counting articles that mention a team together with such a theme gives a "trouble in the news" count per team and week, from 2015 on, with no names stored. Expect noise, since a team's name appears in stories about opponents and alumni too.

### Commercials, NIL and professionalism

NIL only became legal in July 2021. Valuation lists such as On3's are proprietary estimates and were not evaluated in depth. With about five seasons of history and no clear link to weekly poll movement, this is the lowest priority. "Professionalism" has no data source. It would have to be approximated by the team-level news counts above.

## Getting the timing right

The rule is to use only what was known before each poll came out.

- AP and Coaches polls come out on **Sunday**. The feature window should run from the previous poll's release to early Sunday morning.
- CFP rankings come out on **Tuesday** evening. The window can run through Tuesday morning.
- **Stop the window before the release.** Once a poll is out, the news fills with stories about the poll itself ("Oregon jumps to No. 3"). Letting those into the features would be like studying with the answer key open.
- GDELT's 15-minute timestamps make this cutoff easy. Google Trends' rescaling makes it hard, as explained above.

## Suggested pilot

Cheap, free, and enough to decide whether to continue.

1. Pick one recent season. For teams that appeared in the top 25 or "others receiving votes", pull GDELT `TimelineVolRaw` and `TimelineTone`. That is about 100 to 150 requests, saved to `data/raw/`.
2. Build `news_volume_z` and `news_tone_z` with the Sunday cutoff.
3. Take the baseline model's errors (where it ranked a team too high or too low) and check whether the news features line up with them.
4. If they don't, stop and write that down. If they do, backfill to 2017 with the API, then decide about BigQuery for 2015 and 2016.

## Keys and accounts this would need

| Source | Needs |
|---|---|
| GDELT DOC API | Nothing, as far as its docs say. Outbound access to `api.gdeltproject.org` must be allowed in the environment |
| GDELT on BigQuery | A Google Cloud account and credentials, through the secrets harness |
| Google Trends official API | An approved alpha application |
| Media Cloud | A free account and key, through the secrets harness |
| Paid news APIs | A paid key. Not recommended |
| CFBD player stats | No new key. Needs an endpoint added to the MCP allowlist by Sammy |

## How sure are these facts

Checked against the source's own pages during this research: GDELT's start dates, 15-minute updates, license terms and API modes; the Google Trends alpha's 5-year window; Event Registry's prices; Media Cloud's quota; the SEC's report schedule.

Taken from secondary articles, so less certain: prices for NewsAPI.org, NewsData.io, GNews, NewsCatcher and Webz.io; injury report start years for the Big Ten, Big 12 and CFP.

From memory and not verified: the New York Times API details, the Wikipedia pageviews start date, the existence of a free BigQuery monthly allowance and its size, and that CFBD's per-game player stats cover the years we need. GDELT's DOC API description comes from its 2017 and 2018 announcements, so current limits should be confirmed with one test request before building on it.

## Sources

- GDELT: [terms of use](https://gdeltproject.org/about.html), [data overview](https://gdeltproject.org/data.html), [GDELT 2.0 launch](https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/), [DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/), [search from 2017](https://blog.gdeltproject.org/doc-2-0-updates-1-5-year-searching-and-updated-mobile-interface/)
- Google Trends: [API alpha](https://developers.google.com/search/apis/trends)
- News APIs: [Event Registry plans](https://newsapi.ai/plans), [comparison by Thunderbit](https://thunderbit.com/blog/best-news-apis-compared), [comparison on DEV](https://dev.to/timhkelly/10-best-news-apis-in-2026-58e3)
- Media Cloud: [FAQ](https://mediacloud.org/documentation/faqs), [story guide](https://www.mediacloud.org/documentation/story-guide)
- Injury reports: [SEC, CBS Sports](https://www.cbssports.com/college-football/news/sec-institutes-player-availability-injury-reports-for-all-teams-during-2024-college-football-season/), [CFP, CBS Sports](https://www.cbssports.com/college-football/news/college-football-playoff-will-require-teams-to-provide-player-availability-reports-beginning-with-2025-season/), [Big 12, AP via theScore](https://www.thescore.com/ncaaf/news/3324733)
- Arrests: [Spokesman-Review on ArrestNation](https://www.spokesman.com/stories/2016/sep/18/website-wsu-leads-nation-in-arrests-of-student-ath/), [Fox Sports](https://www.foxsports.com/stories/other/the-most-arrested-college-football-teams-in-america)
