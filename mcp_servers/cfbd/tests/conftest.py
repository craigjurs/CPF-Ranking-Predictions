import pytest

from cfbd_mcp import redact


# Built at runtime so no key-shaped literal sits in the repo for scanners to trip on.
FAKE_KEY = "FAKE-CFBD-KEY-" + "x7" * 16


@pytest.fixture
def fake_key(monkeypatch):
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("CFBD_SECRET_PROVIDER", "env")
    monkeypatch.setenv("CFBD_API_KEY", FAKE_KEY)
    yield FAKE_KEY
    redact.forget_secrets()
