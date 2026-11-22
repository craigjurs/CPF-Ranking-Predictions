# Personal data (PII) policy

Most of what this project uses is public sports data: scores, polls, betting lines and team ratings. But "public" isn't the same as "no rules", so here is how personal data is handled.

**Analogy:** a newspaper box score names players, and that's fine. Building a file on one person by gathering their hometown, high school, social media and family isn't fine, even if every piece was public on its own.

## What counts as personal data here

| Data | Example | Rule |
|---|---|---|
| Team-level stats, scores, polls, lines | "Georgia 34, Texas 31" | No restrictions |
| Player names and stats | Player box scores, rosters | OK for modeling. Don't enrich them with outside sources |
| **Recruits** | Recruiting rankings, high school, hometown | **Many recruits are minors.** Store only what modeling needs (rating, position, school). Never hometown or high school beyond aggregate features. Never publish per-recruit outputs |
| Coaches and poll voters | AP voter ballots | Public in their professional role. Use them for modeling only, not for profiling individuals |
| Your own info | Email, API keys, account names | Never in the repo, prompts, logs, or notebooks |

## Rules

1. **Collect the minimum.** Pull only the fields a model uses. Prefer team-level aggregates.
2. **No enrichment.** Don't join player data with social media, news scraping, or other personal sources.
3. **Keep raw pulls out of git.** `data/raw/` and `data/cache/` are gitignored. Commit only derived, team-level features if anything.
4. **No secrets or personal info in prompts, logs or outputs.** The MCP server logs endpoint and parameters only. Error messages are scrubbed.
5. **Notebooks:** clear outputs before committing if they show player-level rows.
6. **Retention:** delete raw player and recruit pulls when a season's models are final.
7. **Removal requests:** if anyone asks to have their data removed from anything this project published, remove it promptly.

## Agents

Agents follow the same rules (see `CLAUDE.md`). They work through the read-only `mcp__cfbd__*` tools and must not scrape personal sources or write player-level data to committed files.
