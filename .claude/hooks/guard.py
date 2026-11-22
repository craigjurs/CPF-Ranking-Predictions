#!/usr/bin/env python3
"""PreToolUse guard: a deterministic bouncer in front of every agent action.

Claude Code runs this script before Bash, Read, Edit, Write and WebFetch
calls. It reads the planned call as JSON on stdin. Exit code 2 blocks the
call and the message on stderr is shown to the agent; exit 0 lets it through.

Analogy: the permission rules in settings.json are the guest list at the
door. This hook is the bouncer who also checks pockets. Neither is a wall:
the real walls are the sandbox and the vault's biometric unlock. This layer
exists to catch mistakes and prompt-injection attempts early, loudly, and
with an explanation the agent can act on.

Standard library only, so it runs before any project dependencies exist.
"""

from __future__ import annotations

import json
import re
import sys

# --- Bash commands that touch secret stores, leak environments, or bypass
# --- the harness. Each entry: (pattern, reason shown to the agent).
BASH_RULES: list[tuple[str, str]] = [
    (r"(^|[\s;&|(`$])op(\s|$)", "1Password CLI is reserved for the CFBD MCP server; use the mcp__cfbd__* tools"),
    (r"(^|[\s;&|(`$])bws(\s|$)", "Bitwarden CLI is reserved for the CFBD MCP server"),
    (r"\bsecurity\s+(find|dump|export)-", "macOS Keychain reads are not allowed for the agent"),
    (r"\bsecret-tool\b|\bkeyring\s+(get|set|del)\b|import\s+keyring|\bcmdkey\b", "OS keychain access is not allowed for the agent"),
    (r"(^|[;&|(]\s*)vault\s|\baws\s+secretsmanager\b|\bgcloud\s+secrets\b|\baz\s+keyvault\b", "Secret-manager CLIs are not allowed for the agent"),
    (r"(^|[\s;&|(])(printenv|env|set|export\s+-p|declare\s+-x)\s*($|[;&|>])", "Dumping the environment is blocked"),
    (r"/proc/[^/\s]+/(environ|mem|maps)", "Reading another process's environment or memory is blocked"),
    (r"\b(gdb|lldb|strace|ltrace|dtrace|ptrace)\b", "Debuggers and tracers can read the MCP server's memory"),
    (r"(^|[\s'\"=/])\.env(\.(?!example\b)[\w-]+)?($|[\s'\";|&])", "Do not read or write .env files; secrets live in the vault"),
    (r"api\.collegefootballdata\.com", "Call CFBD only through the mcp__cfbd__* tools, which hold the key"),
    (r"\bgit\s+push\b.*(\s--force\b|\s-f\b|\s--force-with-lease\b|\s\+\S)", "Force-push is blocked"),
    (r"\bgit\s+(commit|push)\b.*--no-verify\b", "Skipping the secret-scanning pre-commit hook is blocked"),
    (r"\bgit\s+config\b.*core\.hooksPath", "Changing git hook paths is blocked"),
    (r"\bpre-commit\s+uninstall\b", "Removing the secret-scanning hook is blocked"),
    (r"\bgh\s+secret\b", "Managing GitHub secrets is for the human, in the GitHub UI"),
    (r"\b(curl|wget)\b[^|]*\|\s*(ba|z|k)?sh\b", "Piping downloads into a shell is blocked"),
    (r"\brm\s+-[a-z]*r[a-z]*f?\s+(/|~|\$HOME)(\s|$)", "Recursive delete of / or home is blocked"),
    (r"\bchmod\s+(-R\s+)?777\b", "World-writable permissions are blocked"),
    (r"\bbase64\b.*\b(-d|--decode)\b.*\|\s*(ba|z)?sh\b", "Decoding into a shell is blocked"),
]

# --- Files the agent may not read or change.
SECRET_PATHS = re.compile(
    r"(^|/)(\.env(\.(?!example$)[\w.-]+)?|[^/]*\.(pem|key|p12|pfx)|credentials[^/]*\.json"
    r"|service-account[^/]*\.json|\.netrc|\.npmrc|\.pypirc)$"
    r"|(^|/)(\.ssh|\.aws|\.gnupg|\.config/op|\.config/gh|\.docker|secrets|\.secrets)/"
    r"|Library/Keychains/|Group Containers/[^/]*1password"
)

# The harness itself: changing these would let the agent remove its own fence.
PROTECTED_FOR_WRITE = re.compile(
    r"(^|/)\.claude/(settings\.json|hooks/)|(^|/)\.mcp\.json$|(^|/)\.gitleaks\.toml$"
    r"|(^|/)\.pre-commit-config\.yaml$|(^|/)\.github/workflows/|(^|/)mcp_servers/cfbd/src/cfbd_mcp/(secrets|redact|endpoints)\.py$"
)

# Content that looks like a live credential should never be written to disk.
SECRET_CONTENT = [
    re.compile(r"(?i)cfbd[_-]?(api[_-]?)?key\s*[:=]\s*[\"']?(?!\$|\{|<|FAKE)[A-Za-z0-9+/=_-]{20,}"),
    re.compile(r"(?i)authorization\s*[:=]\s*[\"']?bearer\s+(?!\{|\$|<|FAKE)[A-Za-z0-9+/=_.-]{20,}"),
    re.compile(r"\bops_[A-Za-z0-9_-]{40,}"),          # 1Password service-account token
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),       # GitHub tokens
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),               # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]

DENY_FETCH_HOSTS = re.compile(r"^api\.collegefootballdata\.com$")


def block(reason: str) -> None:
    print(f"Blocked by project security harness: {reason}. See docs/security/secrets-design.md.", file=sys.stderr)
    sys.exit(2)


def check_bash(cmd: str) -> None:
    for pattern, reason in BASH_RULES:
        if re.search(pattern, cmd):
            block(reason)
    for token in re.split(r"[\s'\"<>|;&()=]+", cmd):
        if token and SECRET_PATHS.search(token):
            block(f"'{token}' is a secret file")


def check_path(path: str, writing: bool) -> None:
    if SECRET_PATHS.search(path):
        block(f"'{path}' is a secret file")
    if writing and PROTECTED_FOR_WRITE.search(path):
        block(f"'{path}' is part of the security harness; a human must change it")


def check_content(text: str) -> None:
    for pattern in SECRET_CONTENT:
        if pattern.search(text or ""):
            block("the content looks like a real credential; never write secrets to files")


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        block("could not parse the tool call")
    tool = event.get("tool_name", "")
    args = event.get("tool_input", {}) or {}

    if tool == "Bash":
        check_bash(args.get("command", ""))
    elif tool in ("Read", "Grep", "Glob", "NotebookRead"):
        check_path(str(args.get("file_path") or args.get("path") or args.get("pattern") or ""), writing=False)
    elif tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        check_path(str(args.get("file_path") or args.get("notebook_path") or ""), writing=True)
        check_content(json.dumps(args))
    elif tool == "WebFetch":
        host = re.sub(r"^\w+://", "", args.get("url", "")).split("/")[0].split(":")[0].lower()
        if DENY_FETCH_HOSTS.search(host):
            block("call CFBD only through the mcp__cfbd__* tools")
    sys.exit(0)


if __name__ == "__main__":
    main()
