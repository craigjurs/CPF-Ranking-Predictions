# How this project keeps secrets away from agents

This document explains the security design for the CollegeFootballData (CFBD) API key, and for any secret added later. It is written to teach the ideas, not just list the settings.

## The one rule

**An AI agent never holds a secret.** It can ask for *data*, and a trusted, deterministic piece of code fetches that data using the key. The agent never touches the key itself.

### The bank teller analogy

Picture a bank. You (the agent) stand at the counter and ask for your account balance. The teller (the **MCP server**) walks back to the vault, uses a key you never see, and comes back with a printed balance. You can ask for many things, but only what is on the teller's menu. You can't say "hand me the vault key" or "go open someone else's box". If you try to sneak behind the counter (run `op read` or `cat .env`), a guard stops you, and the vault door won't open for you anyway.

| Bank | This project |
|---|---|
| Customer at the counter | The Claude agent |
| Teller | `mcp_servers/cfbd` (the MCP server) |
| The menu of services | The 9 read-only tools in `endpoints.py` (allowlist) |
| The vault | A network secret, 1Password, Bitwarden, or the OS keychain |
| The key to the vault ("secret zero") | Your claude.ai login, or your fingerprint (Touch ID) |
| Security guard | `.claude/hooks/guard.py` and the permission rules |
| Walls and locked doors | The cloud VM boundary, the sandbox, and the vault's own unlock |
| Security cameras | Server audit log, vault activity log, CFBD usage dashboard |
| Alarm on the exit | gitleaks pre-commit, CI scan, GitHub push protection |

## The hard part: "secret zero"

Every vault has a key to open it. If you store *that* key in a file, you have only moved the problem. This is called the **secret zero** problem: where does the first secret live?

The answer is to make secret zero something that **is not a file an agent could read**:

- **Something you are.** A fingerprint (Touch ID or Windows Hello) unlocking 1Password on your laptop.
- **Something a platform vouches for.** Your claude.ai login, which is protected by your password, passkey or 2FA. The cloud environment stores the key on your behalf, so you never type it into a session.
- **Something that is short-lived.** In GitHub Actions, OpenID Connect (OIDC) lets a workflow prove "I am this repo's workflow" and get a token that expires in minutes. Nothing is stored at all.

## How it works in each place you work

### 1. Cloud sessions (iPad, browser, phone): network secret. This is the default today.

On an iPad, Claude runs in a cloud computer (a VM), not on your device. The key is stored as a **network secret** on your Claude cloud environment.

**Analogy: an E-ZPass toll tag.** The agent drives the car and sends a request to `api.collegefootballdata.com`. The toll booth (the session's egress proxy) attaches the key *after the request leaves the car*. The key never enters the car: it is not in environment variables, not in files, and not in the MCP server's memory. You cannot even read it back in settings.

What this gives you:

- **Nothing to steal inside the VM.** There is no environment variable, file, or process memory holding the key, so a prompt-injected agent has nothing to exfiltrate.
- **Usable from anywhere.** The secret is attached to the environment, not a device, so it works from the iPad today and from claude.ai/code on a laptop later.
- **Secret zero is your claude.ai account.** Turn on 2FA or a passkey for it.

What it doesn't do: the agent can still *use* the key, because any request to that host gets it attached. That's why the harness also routes CFBD calls through the MCP server (rate limits, allowlist), and the guard blocks direct `curl` to the API. The worst case is that someone burns your monthly CFBD quota on read-only public sports data. Nobody can steal the key itself.

### 2. Your own laptop (later): 1Password with Touch ID

The MCP server runs `op read op://cfbd-agent/CFBD API/credential`. The 1Password desktop app asks for **Touch ID** and the server holds the key in memory for 15 minutes, then forgets it. No master password or token is stored on disk.

Extra walls on a laptop:

- **The sandbox** (`sandbox` in `.claude/settings.json`) runs the agent's shell commands inside an OS sandbox. It can't read `~/.config/op` or the 1Password app's folder, and it can't reach 1Password, Bitwarden or CFBD over the network. The MCP server is started by Claude Code itself, *outside* that sandbox, so it can still do its job. **Analogy:** the teller works behind bullet-resistant glass, and the customer's side of the room has no door to the vault.
- **The doorbell.** If anything on the agent's side ever did manage to call `op`, 1Password would pop up a Touch ID prompt you didn't expect. Deny it, and treat it as a sign that something tried.
- **Process boundary (optional, strongest).** For maximum isolation, run the MCP server as a separate OS user or in a container, so the agent's user can't inspect its memory. That's overkill for public sports data, but it's the right pattern for anything sensitive.

Bitwarden Secrets Manager and the OS keychain also work (`CFBD_SECRET_PROVIDER=bitwarden` or `keychain`). For Bitwarden, the machine access token (its secret zero) goes in the OS keychain, never in a file.

### 3. GitHub Actions (only if you automate data pulls)

- **Simple:** store the key as an *Actions secret* inside a GitHub *Environment* named `cfbd`, with yourself as a required reviewer. Set `CFBD_SECRET_PROVIDER=env`. The server only accepts `env` when `CI=true`.
- **Best:** use OIDC to a cloud secret manager (for example GCP Secret Manager with Workload Identity Federation), so there's no long-lived secret even in GitHub.
- **Never** use `pull_request_target` or `workflow_run` in this public repo. They can run fork code with your secrets. CI fails if either appears.

## The layers, and what each one stops

Security here is like a castle: moat, wall, gate, guards. Each layer catches what the one before missed. No single layer is perfect, and the notes below are honest about the gaps.

| Layer | Where | Stops | Gap |
|---|---|---|---|
| Key never in agent context | MCP design | Agent reading, logging or pasting the key | — |
| Network secret | Cloud environment | Key existing anywhere in the VM | Agent can still *use* it via the host |
| Vault with biometric unlock | Laptop | Key at rest in files or env vars | Same-user malware outside Claude |
| Allowlisted tools and validated params | `endpoints.py` | Arbitrary URLs, header injection, path tricks | — |
| No redirects, host check | `client.py` | Key forwarded to another host | — |
| Rate limits (30/min, 200/day) and cache | `client.py` | Runaway loops burning the ~1,000 calls/month quota | Limits reset when the server restarts |
| Output and log scrubbing | `redact.py` | Key echoed in errors, responses, logs | Only known values and key-like shapes |
| `Secret` wrapper | `secrets.py` | Accidental `print`/`repr` of the key | — |
| Permission rules | `.claude/settings.json` | Reading `.env` and credentials, force push, vault CLIs | Prefix rules can be sidestepped |
| Guard hook | `.claude/hooks/guard.py` | Vault CLIs, env dumps, `/proc` reads, debuggers, `--no-verify`, edits to the harness, writing key-shaped text | Regexes can be sidestepped. It's a guard, not a wall |
| Sandbox | `.claude/settings.json` | Shell access to vault files and vault hosts (laptop) | Not available in cloud VMs, which isolate the key with the network secret instead |
| `disableBypassPermissionsMode` | `.claude/settings.json` | Turning the whole harness off with one flag | — |
| gitleaks pre-commit | `.pre-commit-config.yaml` | Committing a secret | Can be skipped with `--no-verify` (the guard blocks agents from doing that) |
| CI secret scan | `.github/workflows/security.yml` | Secret anywhere in history reaching `main` | — |
| GitHub push protection | Repo settings | A known token format being pushed at all | Only known provider formats |

## Rotation and audit

- **Rotate** the CFBD key every 90 days, and immediately if you ever see it outside the vault (in chat, a log, a commit, a screenshot). Request a new key at collegefootballdata.com, update the vault or network secret, then revoke the old key.
- **If a key leaks in git:** rotate first. Then clean history. Deleting the commit doesn't un-leak it, because public repos are cloned and scraped within minutes.
- **Look at the logs:** the MCP server writes every call (endpoint and parameters, never headers) to stderr, which Claude Code keeps in its MCP logs. 1Password and Bitwarden have activity logs. CFBD shows your usage on your account page. A surprise spike means something is calling more than you expected.
- **Least privilege:** keep the CFBD key in its own vault (`cfbd-agent`) holding nothing else. Then even a mistakenly broad token can't see your other passwords.

## Changing the harness

The guard blocks agents from editing `.claude/settings.json`, `.claude/hooks/`, `.mcp.json`, the gitleaks and pre-commit configs, the CI workflows, and the server's `secrets.py`, `redact.py` and `endpoints.py`. **A human changes these, on purpose, in a reviewed PR.** That's the point: a lock the burglar can unscrew from the inside isn't a lock.

To add a new CFBD endpoint, add one entry to `ENDPOINTS` in `endpoints.py`, add a tool in `server.py`, and add a test.
