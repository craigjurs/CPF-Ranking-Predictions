# Adding your CFBD API key (you do this, not the agent)

**Never paste the key into a chat, an issue, a commit, or a file in this repo.** Each path below puts it somewhere an agent can't read.

## A. Cloud sessions on iPad, browser or phone (do this now)

1. In the Claude app, open your project's **Project settings**, then **Cloud environment**, then the **gear** next to the selected environment.
2. Under **Network secrets** (called **API credentials** in older app versions), add a secret:
   - **Allowed websites / host:** `api.collegefootballdata.com`
   - **Type:** `Bearer` (CFBD expects `Authorization: Bearer <your key>`)
   - **Value:** paste your CFBD key here, and only here.
3. Save. You can't view it again afterwards. That's by design. To change it, delete it and add it again.
4. Start a **new** session. The proxy now attaches the key to requests for that host, which also allows the host through the network policy.
5. Check: ask Claude to "use the cfbd tool to get the 2024 week 1 AP poll". If you see data, you're done.

**Secret zero here is your claude.ai account.** Turn on two-factor authentication or a passkey for it.

**Do not** add the key as an *environment variable* on the cloud environment. Every command in the session can read environment variables, so the agent could see it.

## B. Your own laptop (later)

### Option 1: 1Password (recommended for a laptop)

1. Install the 1Password desktop app and the `op` CLI. In the app, go to **Settings → Developer** and turn on **Integrate with 1Password CLI**, so Touch ID unlocks it.
2. Create a vault called `cfbd-agent`. Add an **API Credential** item named `CFBD API` and paste the key into its `credential` field.
3. Install `uv` (https://docs.astral.sh/uv/). Claude Code starts the server from `.mcp.json`.
4. When Claude first calls a CFBD tool, approve the Touch ID prompt. If a Touch ID prompt ever appears when you *didn't* expect a CFBD call, deny it.

The server picks 1Password automatically (`CFBD_SECRET_PROVIDER=auto`). To use a different item, set `CFBD_SECRET_REF=op://<vault>/<item>/<field>` in your shell profile. It's a pointer, not a secret.

### Option 2: Bitwarden Secrets Manager (free tier)

1. Create a project and a secret holding the key, plus a **machine account** with *read* access to that project only. Generate an access token.
2. Store the access token in your OS keychain. Type the command yourself, not through an agent:
   ```sh
   python3 -m keyring set cfbd-mcp bws_access_token
   ```
3. Set `CFBD_SECRET_PROVIDER=bitwarden` and `CFBD_SECRET_REF=<the secret's UUID>`.

### Option 3: OS keychain only (simplest, weakest)

```sh
python3 -m keyring set cfbd-mcp api_key     # type this yourself; it prompts for the value
export CFBD_SECRET_PROVIDER=keychain CFBD_SECRET_REF=cfbd-mcp/api_key
```

Any program running as you can ask the keychain for the key, so rely on the sandbox and guard hook here.

### Turn on the local guardrails (once per laptop)

```sh
uv tool install pre-commit
pre-commit install        # gitleaks now scans every commit before it is created
```

## C. GitHub (do this once, in the browser)

1. **Settings → Code security** (Advanced Security): turn on **Secret scanning** and **Push protection**. Both are free for public repos. Push protection rejects a push that contains a recognised token.
2. **Settings → Branches:** protect `main` and require the `security` workflow to pass.
3. Only if you later automate data pulls in Actions: **Settings → Environments → New environment** `cfbd`, add yourself as a required reviewer, then add the secret `CFBD_API_KEY` there. Don't use repository-wide secrets.

## If the key ever leaks

1. Get a new key from CollegeFootballData and revoke the old one. **Do this first.**
2. Put the new key in the vault or network secret.
3. Then clean up wherever it leaked. If it was a git commit, rewriting history is optional once the key is dead.
