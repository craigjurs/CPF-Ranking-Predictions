# Research: data sources for pundit opinions

*Research only. Nothing here has been pulled, signed up for, or wired into the pipeline. Checked on 2026-11-22.*

## The short answer

**Start with what pundits write down as rankings, not with what they say on air.** Three free sources of "ranked opinion" cover most of the value and need no API key:

1. **Individual AP voter ballots** (College Poll Tracker, roughly 2014 onward)
2. **The r/CFB poll** (every ballot public, running since 2010)
3. **Media power rankings** (ESPN, CBS Sports, The Athletic, Fox's Joel Klatt), collected going forward

Treat **Pat McAfee-style talk** (YouTube and podcast transcripts, X posts) as a later, smaller experiment for recent seasons only. It is the most expensive data to get, has the shallowest history, and carries the most terms-of-service risk.

**Analogy.** Think of predicting what a jury will decide. You could record every talk-radio host discussing the case and try to measure the mood, or you could simply read the notes that individual jurors published last week. The AP ballots are the jurors' notes. McAfee is the talk radio. Both tell you something, but the notes are cheaper, cleaner and closer to the verdict.

## Why pundit data could help at all

The model's target is a vote. AP voters are 60-odd sportswriters and broadcasters, and the coaches and the CFP committee all watch the same shows and read the same columns. Stats explain most of a ranking, but the leftover part ("everyone agrees this two-loss team is still elite") is exactly what pundit opinion measures.

One caution to keep expectations honest: last week's poll already contains most of last week's opinion. Pundit features only earn their place if they explain the *change* from last week to this week better than the baselines in [baseline-results.md](../baseline-results.md).

## The timing rule every source must pass

A feature may only use information published **before** the poll it predicts.

| Poll | Released | Safe cutoff for features |
|---|---|---|
| AP Top 25, Coaches | Sunday, around midday Eastern | Saturday games ending, plus anything published before Sunday morning |
| CFP rankings | Tuesday evening Eastern | Monday night |

This creates a useful split:

- **Predicting Sunday's AP poll:** most media power rankings come out Sunday through Tuesday, so the freshest version available is *last week's*. GameDay picks (Saturday morning) are available in time.
- **Predicting Tuesday's CFP ranking:** this week's AP poll, this week's individual AP ballots, the r/CFB poll and the Sunday and Monday power rankings are all fair game. This is where pundit data should help the most.

Every row we store needs a `published_at` timestamp so the snapshot code can enforce the cutoff, the same way the existing point-in-time snapshots work.

## Sources compared

Cost and terms notes are what I could confirm from each site. "Not stated" means the site says nothing either way, which is not the same as permission.

### Tier 1: ranked opinions (recommended)

| Source | What it is | History | Cost and key | Terms and risk | Verdict |
|---|---|---|---|---|---|
| [College Poll Tracker](https://collegepolltracker.com/about/) | Every AP voter's individual ballot, by week, team and voter | Site founded 2014. Start season for ballots not stated on the About page; needs a spot check | Free, no key, no API or download | Fan-run, ad-supported, no reuse terms stated. Scraping needs a polite, low-rate approach and ideally an email asking permission | **Best single source.** It is the electorate itself |
| [r/CFB poll](https://poll.redditcfb.com/about) | Weekly top 25 from about 300 to 400 vetted fan voters | Continuous since 2010; every ballot public | Free, no key. No data API, but the site code is open source (MIT) | No reuse terms stated | **Strong.** A "wisdom of the crowd" ranking with long history |
| Media power rankings: [ESPN](https://www.espn.com/college-football/rankings), [CBS Sports 136](https://www.cbssports.com/college-football/news/college-football-rankings-ohio-state-unanimous-no-1-cbs-sports-136), The Athletic, Fox (Joel Klatt) | A named outlet's own weekly ranking | No tidy archive. Old weeks exist only as scattered articles | Free to read (The Athletic is paywalled) | Copyrighted articles. Storing just the rank numbers is low risk; storing article text is not | **Collect going forward**, about 5 minutes a week by hand or a small parser. Backfill is a slog and not worth it yet |
| [Massey Ranking Comparison](https://masseyratings.com/cf/aboutcomp.htm) | Side-by-side ordinal ranks from roughly 100 computer systems plus AP and Coaches | Weekly archives exist for past seasons, but I could not confirm the start year | Free, no key | No reuse terms stated | **Useful, but it is "computer opinion", not pundits.** Worth a separate look |
| ESPN FPI | ESPN's computer rating that their analysts cite constantly | 2005 onward | **Already available through CFBD**, so no new key | Covered by our existing CFBD use | **Free win.** But it looks season-level, not weekly, so check for leakage before using in-season |

Poll history itself (AP since 1936, Coaches since 2007, CFP since 2014) is also on [College Poll Archive](https://www.collegepollarchive.com/) and [cfbtrack](https://www.cfbtrack.com/rankings), but we already have that from CFBD.

### Tier 2: picks (cheap, but a weak signal for rankings)

| Source | What it is | History | Cost and key | Verdict |
|---|---|---|---|---|
| [Cole's Gameday Blog](https://gamedaycole.com/college-gameday/) | Tracks College GameDay picks by Corso, Herbstreit, Howard, McAfee, Saban and guest pickers, plus other ESPN voices | Posts from October 2010 to now | Free. Has a "Data requests" page, so ask rather than scrape | **The GameDay picks archive exists, and this is it.** Whether it offers per-game rows or only records needs a closer look |
| [GameDay guest picker repo](https://github.com/nikhilchandrashaker/college-gameday-guest-picker-analysis) | A GitHub project analyzing guest picker accuracy game by game | Unknown (could not load the page) | Free | Check the license and data before relying on it |

Picks answer "who wins Saturday?", which the betting line already answers better. Their one useful angle is **surprise**: when a team wins a game that every GameDay picker picked against it, voters tend to reward it more. That is a small feature, so this tier is a "nice to have".

### Tier 3: talk (McAfee, podcasts, X) — expensive and shallow

| Source | What it is | History | Cost and key | Terms and risk | Verdict |
|---|---|---|---|---|---|
| YouTube transcripts (Pat McAfee Show, GameDay clips, Josh Pate, Joel Klatt) | Auto-captions of shows | Only as far back as each channel's uploads. McAfee's college football role is recent | Official API needs a **Google API key** (free quota). The official caption download is meant for a video's owner | YouTube's [developer policies](https://developers.google.com/youtube/terms/developer-policies) prohibit scraping and limit storing API data to about 30 days. The popular unofficial transcript libraries work by scraping, so they sit outside those terms | **Hold.** Fine for a small personal experiment, risky to build a public repo on |
| [Taddy podcast API](https://taddy.org/developers/podcast-api/episode-transcripts) | Transcripts with speakers and timestamps for any podcast episode on request | Any episode in their directory | **Needs a key and a paid plan** for on-demand transcripts (Pro includes 100 a month; Business 2,000; extra at about 2.5 cents each) | A normal commercial API, so the cleanest legal route to transcripts | **Best option if we do transcripts**, but only after Tier 1 proves pundit data helps |
| Podchaser | Transcripts for about 150,000 shows | Back to January 2021 only | Needs a key; pricing by quote | Commercial API | Second choice. I only saw this on a staging copy of their announcement, so confirm on the live site |
| [X API](https://docs.x.com/x-api/getting-started/pricing) | Posts from pundits and AP voters | Deep in theory, but full-archive search pricing is not listed on the pay-per-use page | **Needs a key and a card.** Pay per use at $0.005 per post read, with no free reading tier | Commercial API with its own storage and display rules | **Skip for now.** 50,000 posts would be about $250, and turning posts into team opinions is noisy work |
| TV closed captions (GDELT and Internet Archive TV News) | Searchable captions of TV news | Decades | Free | Built for news channels. I found no sign that ESPN or Fox Sports are included | **Probably a dead end** for sports shows |

**Analogy for Tier 3.** Tier 1 hands you a finished scorecard. Tier 3 hands you forty hours of people talking over each other and asks you to work out the scorecard yourself. You need a second model just to turn "I'm telling you, that Texas defense is REAL" into a number, and that model makes its own mistakes.

## Turning this into features

All features are **team-week** rows, aggregated across pundits. None of them need a pundit's name in the final feature table.

| Feature | Built from | What it captures |
|---|---|---|
| `ballot_rank_mean`, `ballot_rank_median` | AP ballots | The centre of voter opinion, which is close to the poll itself |
| `ballot_rank_std` | AP ballots | **Disagreement.** Teams the voters argue about tend to move more next week |
| `ballot_share_top10`, `ballot_share_unranked` | AP ballots | How solid a team's support is at the edges |
| `rcfb_rank_minus_ap_rank` | r/CFB poll | Where fans are ahead of or behind the writers. A gap often closes the following week |
| `media_pr_rank_mean`, `media_pr_minus_ap` | Media power rankings | "Power ranking" opinion (who is best) versus the poll (who has earned it) |
| `fpi_rank_minus_ap_rank` | CFBD | Whether ESPN's on-air numbers say a team is over or under-ranked |
| `gameday_pick_share`, `won_against_consensus` | GameDay picks | Surprise wins and losses |
| `mention_count`, `sentiment_mean` | Transcripts or X (later) | Buzz and tone. Only for recent seasons |

For the CFP target, the strongest version is likely the simplest: this week's ballot spread and the r/CFB gap, both known by Sunday, used to predict Tuesday.

## How this fits the project's rules

- **Keys.** Tier 1 and Tier 2 need none. A Google key, Taddy key or X key would each need the same treatment as the CFBD key (held by a trusted server, never by an agent). See [setup-your-key.md](../security/setup-your-key.md). No keys were requested or added for this research.
- **Personal data.** The [PII policy](../security/pii-policy.md) already covers AP voters: they are public in their professional role, to be used for modeling and not for profiling. Aggregating to team-week features keeps us inside that. Per-voter "bias" features are possible but should be a deliberate choice.
- **Raw data.** Scraped pages and ballots belong in `data/raw/` (gitignored). Commit only derived team-level features.
- **History gap.** Modeling runs from 2005, but ballots start around 2014 and r/CFB in 2010. Earlier seasons would have missing values for these features. Tree models handle that fine, or pundit features can be limited to the CFP era (2014 onward), which is the era they matter most for anyway.

## Suggested order of work

1. **Spot-check College Poll Tracker and the r/CFB poll**: confirm the first season available, the page structure and that timestamps can be recovered. Email both to ask about reuse. (About an hour.)
2. **Backfill ballots and r/CFB ballots** into `data/raw/`, then build the ballot spread and gap features and run them through the existing walk-forward backtest against the baselines.
3. **Start a weekly log of media power rankings** now, so that a season from today there is a clean dataset.
4. **Decide on Tier 3 only if step 2 shows a real gain.** If so, trial Taddy on one season of two or three shows before spending on anything bigger.

## What I could not confirm

- The first season of ballots on College Poll Tracker, and whether Coaches ballots are archived anywhere (coaches' ballots are generally only public for the final poll).
- The start year and format of Massey's weekly archives.
- Whether Cole's Gameday Blog has per-game pick rows, and the contents and license of the GameDay GitHub repo.
- Whether CFBD's FPI data is point-in-time by week.
- X full-archive search pricing, and YouTube's exact position on caption files (the policy page I read does not name captions specifically).
- Podchaser details, which came from a staging copy of their announcement.
