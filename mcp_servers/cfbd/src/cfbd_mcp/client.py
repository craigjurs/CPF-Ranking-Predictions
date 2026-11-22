"""HTTP client for CFBD with rate limits, caching, and strict network rules."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import OrderedDict, deque

import httpx

from cfbd_mcp.endpoints import ALLOWED_HOST, BASE_URL, build_query
from cfbd_mcp.redact import scrub, scrub_obj
from cfbd_mcp.secrets import SecretSource

log = logging.getLogger("cfbd_mcp")

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_ITEMS = int(os.environ.get("CFBD_MAX_ITEMS", "500"))


class CFBDError(RuntimeError):
    pass


class RateLimiter:
    """Sliding-window limits: per minute and per day.

    CFBD's free tier is about 1,000 calls a month, so the daily cap protects
    the quota if an agent gets stuck in a loop or a prompt injection tells it
    to hammer the API.
    """

    def __init__(self, per_minute: int, per_day: int, clock=time.monotonic):
        self.per_minute, self.per_day, self.clock = per_minute, per_day, clock
        self._minute: deque[float] = deque()
        self._day: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = self.clock()
            for window, span in ((self._minute, 60), (self._day, 86400)):
                while window and now - window[0] >= span:
                    window.popleft()
            if len(self._minute) >= self.per_minute:
                raise CFBDError(f"Rate limit: at most {self.per_minute} CFBD calls per minute")
            if len(self._day) >= self.per_day:
                raise CFBDError(f"Rate limit: daily cap of {self.per_day} CFBD calls reached")
            self._minute.append(now)
            self._day.append(now)


class TTLCache:
    def __init__(self, ttl: float = 3600, size: int = 256):
        self.ttl, self.size = ttl, size
        self._data: OrderedDict[str, tuple[float, object]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            hit = self._data.get(key)
            if hit and time.monotonic() - hit[0] < self.ttl:
                self._data.move_to_end(key)
                return hit[1]
            self._data.pop(key, None)
            return None

    def put(self, key: str, value) -> None:
        with self._lock:
            self._data[key] = (time.monotonic(), value)
            self._data.move_to_end(key)
            while len(self._data) > self.size:
                self._data.popitem(last=False)


class CFBDClient:
    def __init__(self, secrets: SecretSource | None = None, transport: httpx.BaseTransport | None = None):
        self.secrets = secrets or SecretSource()
        self.limiter = RateLimiter(
            int(os.environ.get("CFBD_RATE_PER_MINUTE", "30")),
            int(os.environ.get("CFBD_RATE_PER_DAY", "200")),
        )
        self.cache = TTLCache()
        # follow_redirects=False: the Authorization header must never be
        # carried to another host by a redirect.
        self.http = httpx.Client(
            base_url=BASE_URL,
            timeout=httpx.Timeout(20.0),
            follow_redirects=False,
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": "cfbd-mcp/0.1"},
        )

    def fetch(self, endpoint: str, args: dict) -> dict:
        path, query = build_query(endpoint, args)
        cache_key = json.dumps([path, sorted(query.items())])
        cached = self.cache.get(cache_key)
        if cached is not None:
            log.info("cache hit %s %s", path, query)
            return cached

        self.limiter.acquire()
        key = self.secrets.get()
        log.info("GET %s %s", path, query)  # audit trail: endpoint + params, never headers
        try:
            headers = {} if key is None else {"Authorization": f"Bearer {key.reveal()}"}
            resp = self.http.get(path, params=query, headers=headers)
        except httpx.ProxyError:
            raise CFBDError(
                "The network proxy refused api.collegefootballdata.com. In a cloud session, add the CFBD key as a "
                "network secret for that host (this also allows the host)."
            ) from None
        except httpx.HTTPError as exc:
            raise CFBDError(scrub(f"Network error talking to CFBD: {type(exc).__name__}")) from None

        if resp.url.host != ALLOWED_HOST:
            raise CFBDError("Refused: response came from an unexpected host")
        if resp.is_redirect:
            raise CFBDError(f"Refused to follow redirect (HTTP {resp.status_code})")
        if resp.status_code == 401:
            self.secrets.clear()
            if self.secrets.injected_by_proxy:
                raise CFBDError(
                    "CFBD returned HTTP 401. In a cloud session the key comes from a network secret: "
                    "check that the cloud environment has one for api.collegefootballdata.com (type Bearer)."
                )
            raise CFBDError("CFBD rejected the API key (HTTP 401). Check or rotate it in your vault.")
        if resp.status_code == 429:
            raise CFBDError("CFBD says the quota or rate limit is exhausted (HTTP 429)")
        if resp.status_code >= 400:
            raise CFBDError(f"CFBD returned HTTP {resp.status_code}")
        if len(resp.content) > MAX_RESPONSE_BYTES:
            raise CFBDError("Response too large; narrow the query (add week, team, or conference)")

        try:
            data = resp.json()
        except ValueError:
            raise CFBDError("CFBD returned non-JSON data") from None

        result = {"endpoint": path, "params": query}
        if isinstance(data, list):
            result["count"] = len(data)
            if len(data) > MAX_ITEMS:
                result["truncated"] = True
                result["note"] = f"Showing first {MAX_ITEMS} rows; narrow the query for the rest."
                data = data[:MAX_ITEMS]
        result["data"] = data
        result = scrub_obj(result)
        self.cache.put(cache_key, result)
        return result
