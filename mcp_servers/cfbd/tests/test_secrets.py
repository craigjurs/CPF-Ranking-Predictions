import pytest

from cfbd_mcp.secrets import Secret, SecretError, SecretSource


def test_secret_never_prints_itself():
    s = Secret("super-secret-value")
    for text in (str(s), repr(s), f"{s}", f"{s!r}", str([s]), str({"k": s})):
        assert "super-secret-value" not in text
    assert s.reveal() == "super-secret-value"


def test_env_provider_refused_outside_ci(monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("CFBD_API_KEY", "abcdefghijkl")
    with pytest.raises(SecretError, match="only works in CI"):
        SecretSource(provider="env").get()


def test_env_provider_in_ci(fake_key):
    assert SecretSource().get().reveal() == fake_key


def test_unknown_provider():
    with pytest.raises(SecretError, match="Unknown"):
        SecretSource(provider="dotenv")


def test_onepassword_ref_validated():
    with pytest.raises(SecretError, match="op://"):
        SecretSource(provider="onepassword", ref="; rm -rf /").get()


def test_ttl_cache_and_clear(monkeypatch):
    calls = []
    monkeypatch.setitem(
        __import__("cfbd_mcp.secrets", fromlist=["PROVIDERS"]).PROVIDERS,
        "keychain",
        lambda ref: calls.append(ref) or "value-from-vault",
    )
    src = SecretSource(provider="keychain", ref="svc/user", ttl=60)
    src.get(); src.get()
    assert len(calls) == 1
    src.clear(); src.get()
    assert len(calls) == 2


def test_auto_picks_network_secret_in_cloud(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    monkeypatch.delenv("CFBD_SECRET_PROVIDER", raising=False)
    src = SecretSource()
    assert src.provider == "network_secret"
    assert src.get() is None  # nothing to hold: the proxy attaches the key


def test_auto_picks_vault_locally(monkeypatch):
    for var in ("CLAUDE_CODE_REMOTE", "CI", "CFBD_SECRET_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    assert SecretSource().provider == "onepassword"
