"""Fetch the CFBD API key from a vault, at call time, inside this process only.

Analogy: this module is the bank teller walking back to the vault. The
customer (the agent) stays at the window. The teller fetches the key, uses
it, and the customer only ever receives the result.

Configuration is by *pointer*, never by value. These environment variables
are safe to commit or show to an agent because they say *where* the secret
lives, not *what* it is:

    CFBD_SECRET_PROVIDER   auto | network_secret | onepassword | bitwarden | keychain | env
    CFBD_SECRET_REF        provider-specific pointer, for example
                           op://cfbd-agent/CFBD API/credential   (1Password)
                           <secret uuid>                         (Bitwarden)
                           cfbd-mcp/api_key                      (keychain service/user)

``network_secret`` is for Claude Code cloud sessions (the iPad / browser
setup). The key is stored as a *network secret* on the cloud environment and
the session's egress proxy attaches it to requests for
api.collegefootballdata.com after they leave the VM. Nothing in the VM, this
server included, ever holds the value. ``auto`` (the default) picks
``network_secret`` in a cloud session, ``env`` in CI, and ``onepassword``
everywhere else.

The ``env`` provider reads ``CFBD_API_KEY`` and is refused unless running in
CI (``CI=true``), where GitHub injects the value from an encrypted secret.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field

from cfbd_mcp.redact import register_secret, scrub

DEFAULT_TTL_SECONDS = 15 * 60
_SUBPROCESS_TIMEOUT = 60  # long enough for a Touch ID prompt

_OP_REF = re.compile(r"^op://[^\s/]+/[^/]+/[^/]+(/[^/]+)?$")
_BWS_ID = re.compile(r"^[0-9a-fA-F-]{36}$")
_KEYCHAIN_REF = re.compile(r"^[\w.-]+/[\w.-]+$")


class SecretError(RuntimeError):
    """Raised with a message that never contains secret material."""


@dataclass(frozen=True)
class Secret:
    """A string that refuses to print itself.

    ``repr()``, ``str()`` and f-strings all show ``Secret(****)``. The only
    way to get the value is ``reveal()``, which makes accidental leaks
    (logging, exceptions, debugging output) much harder.
    """

    _value: str = field(repr=False)

    def reveal(self) -> str:
        return self._value

    def __str__(self) -> str:  # pragma: no cover - trivial
        return "Secret(****)"

    __repr__ = __str__

    def __format__(self, spec: str) -> str:
        return "Secret(****)"


def _run(cmd: list[str], env: dict[str, str] | None = None) -> str:
    """Run a vault CLI without a shell. Errors are scrubbed and generic."""
    exe = shutil.which(cmd[0])
    if not exe:
        raise SecretError(f"'{cmd[0]}' CLI is not installed or not on PATH")
    try:
        proc = subprocess.run(
            [exe, *cmd[1:]],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SecretError(f"'{cmd[0]}' timed out (was the unlock prompt dismissed?)") from exc
    if proc.returncode != 0:
        # stderr can echo arguments; scrub and trim before surfacing.
        detail = scrub(proc.stderr.strip())[:200]
        raise SecretError(f"'{cmd[0]}' failed (exit {proc.returncode}): {detail}")
    return proc.stdout.strip()


def _from_onepassword(ref: str) -> str:
    if not _OP_REF.match(ref):
        raise SecretError("CFBD_SECRET_REF must look like op://<vault>/<item>/<field>")
    # With the 1Password desktop app integration, this triggers Touch ID /
    # Windows Hello. No master password or token is stored anywhere.
    env = {k: v for k, v in os.environ.items() if k != "OP_SERVICE_ACCOUNT_TOKEN"}
    if os.environ.get("CI") == "true" and "OP_SERVICE_ACCOUNT_TOKEN" in os.environ:
        env["OP_SERVICE_ACCOUNT_TOKEN"] = os.environ["OP_SERVICE_ACCOUNT_TOKEN"]
    return _run(["op", "read", "--no-newline", ref], env=env)


def _from_bitwarden(ref: str) -> str:
    if not _BWS_ID.match(ref):
        raise SecretError("CFBD_SECRET_REF must be a Bitwarden secret UUID")
    # The machine access token is itself a secret ("secret zero"). Keep it in
    # the OS keychain and hand it only to the bws child process.
    import keyring

    token = keyring.get_password("cfbd-mcp", "bws_access_token")
    if not token:
        raise SecretError("No Bitwarden access token in the OS keychain (service 'cfbd-mcp', user 'bws_access_token')")
    register_secret(token)
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), "BWS_ACCESS_TOKEN": token}
    import json

    raw = _run(["bws", "secret", "get", ref, "--output", "json"], env=env)
    try:
        return json.loads(raw)["value"]
    except (ValueError, KeyError) as exc:
        raise SecretError("Unexpected response from bws") from exc


def _from_keychain(ref: str) -> str:
    if not _KEYCHAIN_REF.match(ref):
        raise SecretError("CFBD_SECRET_REF must look like <service>/<username>")
    import keyring

    service, user = ref.split("/", 1)
    value = keyring.get_password(service, user)
    if not value:
        raise SecretError(f"No keychain entry for service '{service}', user '{user}'")
    return value


def _from_env(_ref: str) -> str:
    if os.environ.get("CI") != "true":
        raise SecretError(
            "The 'env' provider only works in CI. Locally, keep the key in a vault "
            "so it is not sitting in a shell environment the agent can read."
        )
    value = os.environ.get("CFBD_API_KEY", "")
    if not value:
        raise SecretError("CFBD_API_KEY is not set in the CI environment")
    return value


def _from_network_secret(_ref: str) -> str:
    # Sentinel: the proxy injects the header, so there is nothing to fetch.
    return ""


def resolve_auto() -> str:
    if os.environ.get("CLAUDE_CODE_REMOTE") == "true":
        return "network_secret"
    if os.environ.get("CI") == "true":
        return "env"
    return "onepassword"


PROVIDERS = {
    "network_secret": _from_network_secret,
    "onepassword": _from_onepassword,
    "bitwarden": _from_bitwarden,
    "keychain": _from_keychain,
    "env": _from_env,
}


class SecretSource:
    """Fetches the key lazily and keeps it in memory for a short TTL only."""

    def __init__(self, provider: str | None = None, ref: str | None = None, ttl: float | None = None):
        self.provider = (provider or os.environ.get("CFBD_SECRET_PROVIDER", "auto")).strip().lower()
        if self.provider == "auto":
            self.provider = resolve_auto()
        self.ref = (ref or os.environ.get("CFBD_SECRET_REF", "op://cfbd-agent/CFBD API/credential")).strip()
        self.ttl = float(ttl if ttl is not None else os.environ.get("CFBD_SECRET_TTL", DEFAULT_TTL_SECONDS))
        if self.provider not in PROVIDERS:
            raise SecretError(f"Unknown CFBD_SECRET_PROVIDER '{self.provider}'. Use one of: {', '.join(PROVIDERS)}")
        self._cached: Secret | None = None
        self._fetched_at = 0.0
        self._lock = threading.Lock()

    @property
    def injected_by_proxy(self) -> bool:
        return self.provider == "network_secret"

    def get(self) -> Secret | None:
        """Return the key, or None when the network proxy attaches it for us."""
        if self.injected_by_proxy:
            return None
        with self._lock:
            if self._cached and (time.monotonic() - self._fetched_at) < self.ttl:
                return self._cached
            value = PROVIDERS[self.provider](self.ref)
            if not value:
                raise SecretError("Vault returned an empty value")
            register_secret(value)
            self._cached = Secret(value)
            self._fetched_at = time.monotonic()
            return self._cached

    def clear(self) -> None:
        with self._lock:
            self._cached = None
