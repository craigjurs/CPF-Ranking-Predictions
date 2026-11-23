# Player availability flags: built, tested, and not (yet) worth switching on

This is step 1 of the plan in [research/news-and-player-headlines-sources.md](research/news-and-player-headlines-sources.md): read "a key player was missing" off CFBD box scores, per team and week, with no player names, and test whether it helps the Stage 2 poll model from [stage-1-2-results.md](stage-1-2-results.md).

## The one-paragraph version

The flags work and match real events. But adding them to the model changes almost nothing. On the current (round two) model the AP miss stays at **0.93 spots** per team, the Coaches miss moves from **0.81 to 0.80**, and the CFP committee model does not move at all (**1.08**). The AP change is smaller than the wobble you get from re-running the same model with different random seeds. So the flags are in the codebase, tested, and **switched off by default**.

*Re-checked on Nov 23, 2026 against the round two models ([round-2-results.md](round-2-results.md)). The first version of this test used the round one model. The answer is the same.*

**Analogy:** we gave the forecaster a new instrument, a barometer. It reads correctly. But the forecast barely changes, because the forecaster was already looking out of the window: when a star quarterback is out, the team usually wins by less or loses, and the model already sees the score, the spread and the surprise against expectation. The barometer mostly repeats what the window shows.

## What was built

| File | Job |
|---|---|
| `src/cfp_rankings/pull_players.py` | Pulls box scores one week per API call and **drops every player name before saving**. Only CFBD's numeric athlete id and eight counting stats reach the disk |
| `src/cfp_rankings/availability.py` | Turns box scores into flags, one row per team and game |
| `src/cfp_rankings/features.py`, `poll_model.py` | `PollRanker(availability=True)` adds nine columns to the scouting card |
| `src/cfp_rankings/availability_eval.py` | The side-by-side test below, for AP and Coaches |
| `src/cfp_rankings/availability_cfp_eval.py` | The same test for the CFP committee model |
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

**Analogy:** two cooks, same recipe, and one also gets a new spice. Both cook the same 137 dishes (polls). Each cooks four batches, because two batches from the *same* cook never taste identical. The spice only counts if the gap between the cooks is clearly bigger than the gap between one cook's own batches.

Since round two, the Stage 2 model is a committee of three judges (three random seeds, averaged). So each batch here is a full committee of three, and the four batches use four different committees. Batch one is exactly the model the backtest runs.

Walk-forward, as before: to grade a season both models study only earlier seasons (from 2005; the flag columns are blank before 2013). Graded seasons are 2014 to 2023 without 2020. 2024 and 2025 stay sealed.

### AP and Coaches: average miss, in spots per team (lower is better)

| Poll | Polls | Plain model | With flags | Change | Batch-to-batch wobble of the plain model | Polls where flags did better / worse |
|---|---|---|---|---|---|---|
| AP | 137 | 0.934 | 0.929 | -0.004 | 0.012 | 60 / 49 |
| Coaches | 137 | 0.812 | 0.805 | -0.007 | 0.007 | 65 / 43 |

Per batch, AP: plain 0.930, 0.940, 0.928, 0.936 against flags 0.936, 0.923, 0.921, 0.937. Coaches: plain 0.814, 0.808, 0.815, 0.811 against flags 0.806, 0.802, 0.801, 0.810.

(The plain numbers differ a little from the round two doc only because this test grades 2014 on, not 2006 on.)

Teams right out of 25 does not move: AP 23.71 against 23.71, Coaches 23.86 against 23.87.

### How to read it

- **AP: no effect.** A change of 0.004 is a third of the wobble between batches, and the flags helped in two batches and hurt in two.
- **Coaches: a small, plausible gain of just under 1%.** It shows up in all four batches and in six of nine seasons, with the largest piece in the final poll (1.00 to 0.97), where bowl opt-outs make `production_missing_pct` large. But 0.007 of a spot is tiny, and it is only as big as the wobble itself.
- **The trees hardly use the flags.** The nine columns account for 0.10% of everything the model learned. `production_missing_pct` and its opponent version are most of that. `qb_changed` is at 0.004%.

### The CFP committee model

The committee says out loud that it considers player availability, so this was the flags' best chance. Two ways of handing them over were tried: **directly**, as extra inputs to the small Stage 3 model, and **through the editor**, by giving the flag columns to the Stage 2 AP model that Stage 3 borrows.

Stage 3 has no dice of its own, but its editor does. So the second row re-runs the unchanged model with different editor seeds, to show how much the score moves when nothing real has changed.

| Version | Average miss | Change | Rankings better / worse (of 54) | Seasons better / worse (of 9) |
|---|---|---|---|---|
| Stage 3 as it is | 1.084 | | | |
| Same model, other editor seeds (the wobble) | 1.079 | -0.005 | 10 / 8 | 4 / 3 |
| Plus two flags, direct (`qb_changed`, `production_missing_pct`) | 1.086 | +0.001 | 8 / 9 | 3 / 4 |
| Plus all nine flags, direct | 1.122 | +0.037 | 9 / 21 | 1 / 7 |
| Editor reads the flags | 1.087 | +0.002 | 9 / 9 | 4 / 4 |
| Editor reads the flags, plus two direct | 1.082 | -0.003 | 14 / 12 | 4 / 4 |

**No effect.** Every sensible version lands within the wobble, and none is better in more seasons than it is worse. Handing over all nine flags makes the model clearly worse: with only 54 rankings to learn from, nine extra dials is too many, and it starts fitting noise. The weights it learns for the two direct flags are the smallest of all its inputs.

Why, if the committee says availability matters? Most likely the same barometer story. By the time the committee meets on Tuesday, AP voters have already reacted to the injury on Sunday, and Stage 3 starts from the AP poll. The flag has nothing left to add.

### Is there any signal at all? A model-free check

For teams ranked last week that played, compare where voters put them with where the *plain* (round two) model expected them. A positive number means voters ranked the team lower than the model expected. AP poll, 2014 to 2023:

| After a win | Team-weeks | Voters minus model |
|---|---|---|
| Top receiver missing | 161 | +0.40 ± 0.14 |
| Quarterback changed | 183 | +0.24 ± 0.08 |
| Top runner missing | 131 | +0.21 ± 0.11 |
| Flag not raised (typical, each flag) | about 1,800 | +0.04 to +0.06 ± 0.03 |

So there is a real nudge: a ranked team that wins without its usual quarterback or top receiver ends up roughly a fifth to four tenths of a spot lower than the model expects. The Coaches poll shows the same direction at a somewhat smaller size. After a **loss** there is no consistent pattern, which fits the barometer analogy: the loss itself already says everything.

Why doesn't that lift the overall score? It is about a quarter of a spot, on roughly one ranked team in ten, and ranks only move in whole spots. Spread over a 25-team poll that is around 0.005 of a spot per team, below what this test can measure.

## Decision and what would change it

- `PollRanker()` is unchanged. `PollRanker(availability=True)` turns the flags on.
- The **CFP committee** model was the likeliest place for the flags to matter, and they do not help there either (see above).
- The one hint worth following is the **final poll**, where opt-outs are large and the Coaches miss fell from 1.00 to 0.97. A feature built only for bowl-season opt-outs might earn its place.
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
uv run python -m cfp_rankings.availability_eval --seeds 0   # AP and Coaches, one batch of three models (about 50 minutes on one core)
uv run python -m cfp_rankings.availability_cfp_eval         # the CFP model (about 30 minutes)
```

To run several batches side by side, start one process per batch (`--seeds 0`, `--seeds 1`, ...) with `--threads 1 --out <file>` and combine them with `--merge <files>`. Without `--threads 1`, parallel runs fight over the CPU and crawl.
