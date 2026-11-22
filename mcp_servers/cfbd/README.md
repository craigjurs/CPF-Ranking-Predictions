# cfbd-mcp

A read-only [MCP](https://modelcontextprotocol.io) server for the CollegeFootballData API. The agent calls tools and gets JSON. The API key stays outside the agent's reach.

| Tool | CFBD endpoint |
|---|---|
| `get_games` | `/games` |
| `get_rankings` | `/rankings` (AP, Coaches, CFP) |
| `get_betting_lines` | `/lines` |
| `get_team_records` | `/records` |
| `get_fbs_teams` | `/teams/fbs` |
| `get_calendar` | `/calendar` |
| `get_sp_ratings` / `get_srs_ratings` / `get_elo_ratings` | `/ratings/*` |

Where the key comes from (`CFBD_SECRET_PROVIDER`, default `auto`):

| Provider | When | Key lives in |
|---|---|---|
| `network_secret` | Claude cloud sessions (auto) | Cloud environment network secret. The proxy attaches it, so this process never sees it |
| `onepassword` | Laptop (auto) | 1Password, unlocked by Touch ID (`op read`) |
| `bitwarden` | Laptop | Bitwarden Secrets Manager. Its access token is in the OS keychain |
| `keychain` | Laptop | OS keychain via `keyring` |
| `env` | CI only (auto when `CI=true`) | GitHub Actions secret |

Safety features: endpoint and parameter allowlist, no redirects, host check, rate limits (`CFBD_RATE_PER_MINUTE`=30, `CFBD_RATE_PER_DAY`=200), a 1-hour response cache, a 500-row cap (`CFBD_MAX_ITEMS`), and scrubbing of the key from every output and log line.

```sh
uv run --extra dev python -m pytest -q   # tests
uv run cfbd-mcp                          # run over stdio (Claude Code does this via .mcp.json)
```

See [../../docs/security/secrets-design.md](../../docs/security/secrets-design.md).
