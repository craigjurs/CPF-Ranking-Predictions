# Player availability flags: built, tested, and not (yet) worth switching on

This is step 1 of the plan in [research/news-and-player-headlines-sources.md](research/news-and-player-headlines-sources.md): read "a key player was missing" off CFBD box scores, per team and week, with no player names, and test whether it helps the Stage 2 poll model from [stage-1-2-results.md](stage-1-2-results.md).

## The one-paragraph version

The flags work and match real events. But adding them to the model changes almost nothing: the AP miss stays at **0.96 spots** per team, and the Coaches miss moves from **0.86 to 0.85**. The AP change is smaller than the wobble you get from re-running the same model with a different random seed. So the flags are in the codebase, tested, and **switched off by default**.

**Analogy:** we gave the forecaster a new instrument, a barometer. It reads correctly. But the forecast barely changes, because the forecaster was already looking out of the window: when a star quarterback is out, the team usually wins by less or loses, and the model already sees the score, the spread and the surprise against expectation. The barometer mostly repeats what the window shows.

## What was built

| File | Job |
|---|---|
| `src/cfp_rankings/pull_players.py` | Pulls box scores one week per API call and **drops every player name before saving**. Only CFBD's numeric athlete id and eight counting stats reach the disk |
| `src/cfp_rankings/availability.py` | Turns box scores into flags, one row per team and game |
| `src/cfp_rankings/features.py`, `poll_model.py` | `PollRanker(availability=True)` adds nine columns to the scouting card |
| `src/cfp_rankings/availability_eval.py` | The side-by-side test below |
| `src/cfp_rankings/export.py` | Also writes `data/processed/availability.csv`, team-level, no names or ids |

### The flags

Think of the box score as an **attendance sheet**. "Usual" always means *this season, before this game*.

| Flag | Fires when | How often (FBS team-games, 2023) |
|---|---|---|
| `qb_changed` | Today's leader in pass attempts is not the season leader | 22% |
| `top_rb_missing` | The season leader in carries (quarterback aside) had none | 9% |
| `top_wr_missing` | The season leader in catches had none | 10% |
| `top_tackler_missing` | The season leader in tackles made none | 5% |
| `kicker_changed` | A different player did the kicking | 6% |
| `production_missing_pct` | Share of season-to-date yards and tackles belonging to players who did not appear at all | 20% on average |
| `usage_drop` | The usual quarterback or runner played, but with under half his normal workload | 18% |

The model also gets two facts about the **opponent** (`opp_qb_changed`, `opp_production_missing_pct`), in case voters discount a win over a short-handed team.

**A real example, with no names needed.** Florida State, 2023. The flags are quiet from week 3 to week 11. In the week 12 game `qb_changed` and `usage_drop` both fire: the usual passer left early. Weeks 13 and 14 show `qb_changed` with 37% to 40% of production missing. In the bowl, all four position flags fire and 67% of production is missing. That is exactly the season as it happened: quarterback injured in mid-November, then a wave of bowl opt-outs.

### What the data covers

- **Route confirmed.** `/games/players` works through `get_game_player_stats`, including for a whole week at a time.
- **Seasons pulled:** 2013 to 2023 without 2020. 165 API calls, all through the MCP server, inside its 200-a-day cap. Re-running the pull costs zero calls.
- **Coverage:** passing, rushing and receiving are present for essentially every FBS team-game in every pulled season (only 3 of about 16,500 team-games have no box score). Kicking is present for 99%.
- **Tackles only exist from 2016.** CFBD has no defensive box scores for 2013 to 2015, so `top_tackler_missing` is blank there and `production_missing_pct` counts offence only.
- **2005 to 2012 were not pulled.** It would take about 135 more calls. Given the result below, that is not worth the quota right now.

### What the flags cannot see

Same limits the research doc predicted: no reason for the absence, no offensive linemen, no way to know how long it will last, and nothing for a team's first game of the season. `qb_changed` at 22% is also a reminder that it catches quarterback *competitions* and blowout garbage time shared between two passers, not only injuries.

## The test

**Analogy:** two cooks, same recipe, and one also gets a new spice. Both cook the same 137 dishes (polls). Each cooks four times (four random seeds), because two batches from the *same* cook never taste identical. The spice only counts if the gap between the cooks is clearly bigger than the gap between one cook's own batches.

Walk-forward, as before: to grade a season both models study only earlier seasons (from 2005; the flag columns are blank before 2013). Graded seasons are 2014 to 2023 without 2020. 2024 and 2025 stay sealed.

### Average miss, in spots per team (lower is better)

| Poll | Polls | Plain model | With flags | Change | Seed-to-seed wobble of the plain model | Polls where flags did better / worse |
|---|---|---|---|---|---|---|
| AP | 137 | 0.963 | 0.965 | +0.002 | 0.017 | 65 / 61 |
| Coaches | 137 | 0.857 | 0.847 | -0.010 | 0.002 | 66 / 50 |

Per seed, AP: plain 0.960, 0.974, 0.959, 0.958 against flags 0.971, 0.962, 0.959, 0.970. Coaches: plain 0.855, 0.858, 0.858, 0.856 against flags 0.843, 0.845, 0.842, 0.857.

(The plain numbers are a little lower than the 0.98 and 0.88 in the Stage 2 doc only because this test grades 2014 on, not 2006 on.)

Teams right out of 25 barely moves either: AP 23.68 against 23.67, Coaches 23.77 against 23.79.

### How to read it

- **AP: no effect.** A change of 0.002 is one eighth of the wobble between seeds.
- **Coaches: a small, plausible gain of about 1%.** It shows up in three of four seeds and in eight of nine seasons, with the largest piece in the final poll (1.03 to 1.00), where bowl opt-outs make `production_missing_pct` large. But 0.010 of a spot is tiny, and the fourth seed shows nothing.
- **The trees hardly use the flags.** The nine columns account for 0.11% of everything the model learned. `production_missing_pct` and its opponent version are almost all of that. `qb_changed` is at 0.002%.

### Is there any signal at all? A model-free check

For teams ranked last week that played, compare where voters put them with where the *plain* model expected them. A positive number means voters ranked the team lower than the model expected. AP poll, 2014 to 2023:

| After a win | Team-weeks | Voters minus model |
|---|---|---|
| Top receiver missing | 161 | +0.42 ± 0.14 |
| Quarterback changed | 183 | +0.28 ± 0.08 |
| Top runner missing | 131 | +0.24 ± 0.11 |
| Flag not raised (typical, each flag) | about 1,800 | +0.03 to +0.05 ± 0.03 |

So there is a real nudge: a ranked team that wins without its usual quarterback or top receiver ends up roughly a quarter to four tenths of a spot lower than the model expects. The Coaches poll shows the same direction at about half the size. After a **loss** there is no consistent pattern, which fits the barometer analogy: the loss itself already says everything.

Why doesn't that lift the overall score? It is about a quarter of a spot, on roughly one ranked team in ten, and ranks only move in whole spots. Spread over a 25-team poll that is around 0.005 of a spot per team, below what this test can measure.

## Decision and what would change it

- `PollRanker()` is unchanged. `PollRanker(availability=True)` turns the flags on.
- The flags are more likely to earn their place in two places not tested here: the **CFP committee** model (the committee says out loud that it considers player availability), and the **final poll**, where opt-outs are large.
- A sharper version worth trying later: "weeks in a row without the usual quarterback" and a preseason "returning production" number, which targets the early-season weeks where the model is weakest.

## Privacy

Approved by Sammy on 2026-11-22 under `docs/security/pii-policy.md`: team-level flags, no names. In practice:

- Player names are discarded in memory, before the first write to disk. Tests check this.
- Numeric athlete ids exist only in `data/raw/player_stats/` (gitignored) and are used only to tell one seat from another.
- Flags, features, the exported CSV and this doc contain no names and no ids.

## Run it yourself

```sh
uv run python -m cfp_rankings.pull_players --dry-run        # how many calls a pull would cost (0 once cached)
uv run python -m cfp_rankings.pull_players                  # 2013 to 2023, names dropped before saving
uv run python -m cfp_rankings.export                        # also writes data/processed/availability.csv
uv run python -m cfp_rankings.availability_eval --seeds 0   # the comparison, one seed (about 15 minutes)
```

To run several seeds side by side, start one process per seed with `--threads 1 --out <file>` and combine them with `--merge <files>`. Without `--threads 1`, parallel runs fight over the CPU and crawl.
