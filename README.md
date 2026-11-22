# CFP Ranking Predictions

Machine-learning models that predict each week's **AP Top 25**, **Coaches Poll**, and **College Football Playoff** rankings, using data from [CollegeFootballData](https://collegefootballdata.com) (games, polls, sportsbook lines, ratings).

## Security first

This repo is public and is worked on by AI agents, so it ships with a security harness. The short version: **agents never hold the API key.** They call read-only data tools, and a small trusted server (or the network proxy) adds the key where the agent can't see it.

- How it works and why: [docs/security/secrets-design.md](docs/security/secrets-design.md)
- **Add your key:** [docs/security/setup-your-key.md](docs/security/setup-your-key.md)
- Personal data rules: [docs/security/pii-policy.md](docs/security/pii-policy.md)

## Layout

```
mcp_servers/cfbd/     Read-only CFBD MCP server (holds the key so agents don't)
.mcp.json             Registers that server with Claude Code
.claude/settings.json Agent permissions, sandbox, and the guard hook
.claude/hooks/        PreToolUse guard (blocks secret access and harness tampering)
tests/harness/        Tests for the guard
docs/security/        Design, key setup, PII policy
```
