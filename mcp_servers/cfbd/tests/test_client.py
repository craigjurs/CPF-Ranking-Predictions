import json
import logging

import httpx
import pytest
import respx

from cfbd_mcp import redact
from cfbd_mcp.client import CFBDClient, CFBDError, RateLimiter
from cfbd_mcp.endpoints import BASE_URL


@respx.mock
def test_key_sent_only_in_header_and_scrubbed_from_output(fake_key):
    route = respx.get(f"{BASE_URL}/rankings").mock(
        return_value=httpx.Response(200, json=[{"poll": "AP Top 25", "echo": f"key was {fake_key}"}])
    )
    out = CFBDClient().fetch("rankings", {"year": 2024, "week": 1})
    req = route.calls.last.request
    assert req.headers["Authorization"] == f"Bearer {fake_key}"
    assert fake_key not in str(req.url)
    assert fake_key not in json.dumps(out)
    assert out["data"][0]["poll"] == "AP Top 25"


@respx.mock
def test_redirects_are_not_followed(fake_key):
    respx.get(f"{BASE_URL}/games").mock(
        return_value=httpx.Response(302, headers={"Location": "https://attacker.example/steal"})
    )
    evil = respx.get("https://attacker.example/steal").mock(return_value=httpx.Response(200, json=[]))
    with pytest.raises(CFBDError, match="redirect"):
        CFBDClient().fetch("games", {"year": 2024, "week": 1})
    assert not evil.called


@respx.mock
def test_401_drops_cached_key(fake_key):
    respx.get(f"{BASE_URL}/games").mock(return_value=httpx.Response(401))
    c = CFBDClient()
    with pytest.raises(CFBDError, match="401"):
        c.fetch("games", {"year": 2024, "week": 1})
    assert c.secrets._cached is None


@respx.mock
def test_cache_avoids_second_call(fake_key):
    route = respx.get(f"{BASE_URL}/calendar").mock(return_value=httpx.Response(200, json=[]))
    c = CFBDClient()
    c.fetch("calendar", {"year": 2024})
    c.fetch("calendar", {"year": 2024})
    assert route.call_count == 1


def test_rate_limiter():
    t = [0.0]
    rl = RateLimiter(per_minute=2, per_day=3, clock=lambda: t[0])
    rl.acquire(); rl.acquire()
    with pytest.raises(CFBDError, match="per minute"):
        rl.acquire()
    t[0] = 61
    rl.acquire()
    t[0] = 122
    with pytest.raises(CFBDError, match="daily"):
        rl.acquire()


def test_log_filter_scrubs(fake_key, caplog):
    redact.register_secret(fake_key)
    logger = logging.getLogger("cfbd_mcp.test")
    logger.addFilter(redact.RedactingFilter())
    with caplog.at_level(logging.INFO):
        logger.info("oops %s and Authorization: Bearer %s", fake_key, fake_key)
    assert fake_key not in caplog.text


@respx.mock
def test_network_secret_mode_sends_no_key(monkeypatch):
    monkeypatch.setenv("CFBD_SECRET_PROVIDER", "network_secret")
    route = respx.get(f"{BASE_URL}/rankings").mock(return_value=httpx.Response(200, json=[]))
    CFBDClient().fetch("rankings", {"year": 2024})
    assert "Authorization" not in route.calls.last.request.headers
