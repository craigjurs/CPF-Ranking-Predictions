# Security policy

## Reporting a vulnerability

Please **don't open a public issue** for security problems, especially anything involving a leaked credential. Use GitHub's private **Report a vulnerability** (Security tab → Advisories) instead.

## How secrets are handled

- No secrets live in this repository, ever. `gitleaks` runs on every commit (pre-commit) and on every push and PR (CI), and GitHub push protection is enabled.
- The CollegeFootballData API key is read only by the `mcp_servers/cfbd` server, from a network secret, a vault, or the OS keychain. AI agents call read-only tools and never receive the key.

The full design and the reasoning behind it: [docs/security/secrets-design.md](docs/security/secrets-design.md). Key setup: [docs/security/setup-your-key.md](docs/security/setup-your-key.md). Personal data: [docs/security/pii-policy.md](docs/security/pii-policy.md).
