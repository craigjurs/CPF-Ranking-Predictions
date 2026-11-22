# CFP Ranking Predictions

Machine-learning models that predict each week's **AP Top 25**, **Coaches Poll**, and **College Football Playoff** rankings, using data from [CollegeFootballData](https://collegefootballdata.com) (games, polls, sportsbook lines, ratings).

## Security first

This repo is public and is worked on by AI agents, so it ships with a security harness. The short version: **agents never hold the API key.** They call read-only data tools, and a small trusted server (or the network proxy) adds the key where the agent can't see it.

- How it works and why: [docs/security/secrets-design.md](docs/security/secrets-design.md)
- **Add your key:** [docs/security/setup-your-key.md](docs/security/setup-your-key.md)
- Personal data rules: [docs/security/pii-policy.md](docs/security/pii-policy.md)

## Where things stand

- Core data pulled for 2000 to 2025 and stored as point-in-time snapshots. Modeling uses 2005 onward, without 2020.
- Naive baselines and a walk-forward backtest are in place. Results and a plain-language walkthrough: [docs/baseline-results.md](docs/baseline-results.md)

```sh
uv run python -m cfp_rankings.pull       # fetch anything not cached yet (through the CFBD MCP server)
uv run python -m cfp_rankings.backtest   # score the baselines
uv run --extra dev python -m pytest -q   # pipeline tests
```

## Layout

```
src/cfp_rankings/     Data pull, snapshots, baselines, metrics, backtest
tests/pipeline/       Tests for the above (no network needed)
data/raw/             Cached CFBD pulls (gitignored)
mcp_servers/cfbd/     Read-only CFBD MCP server (holds the key so agents don't)
.mcp.json             Registers that server with Claude Code
.claude/settings.json Agent permissions, sandbox, and the guard hook
.claude/hooks/        PreToolUse guard (blocks secret access and harness tampering)
tests/harness/        Tests for the guard
docs/security/        Design, key setup, PII policy
```
