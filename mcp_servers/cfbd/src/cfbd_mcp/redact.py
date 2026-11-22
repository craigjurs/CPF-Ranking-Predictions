"""Output scrubbing: the last line of defense.

Analogy: a mail room that holds every outgoing letter up to the light and
blacks out anything that looks like a key before it leaves the building.
Even if some code path accidentally put the key into an error message, the
scrubber removes it before the text reaches the agent or a log file.
"""

from __future__ import annotations

import logging
import re
import threading

REDACTED = "[REDACTED]"

# Values registered at runtime (the actual secret once it is fetched).
_known: set[str] = set()
_lock = threading.Lock()

# Shapes that look like credentials even when we do not know the exact value.
_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?[^\s'\",}]+"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"(?i)((?:api[_-]?key|token|secret|password)\s*[\"']?\s*[:=]\s*[\"']?)[^\s'\",}]{6,}"),
    re.compile(r"\bops_[A-Za-z0-9_-]{20,}"),  # 1Password service-account tokens
]


def register_secret(value: str) -> None:
    """Remember a live secret so every later output is scrubbed of it."""
    if value and len(value) >= 6:
        with _lock:
            _known.add(value)


def forget_secrets() -> None:
    with _lock:
        _known.clear()


def scrub(text: str) -> str:
    if not text:
        return text
    with _lock:
        known = sorted(_known, key=len, reverse=True)
    for value in known:
        text = text.replace(value, REDACTED)
    for pattern in _PATTERNS:
        if pattern.groups:
            text = pattern.sub(lambda m: (m.group(1) or "") + REDACTED, text)
        else:
            text = pattern.sub(REDACTED, text)
    return text


def scrub_obj(obj):
    """Recursively scrub strings inside JSON-like data."""
    if isinstance(obj, str):
        return scrub(obj)
    if isinstance(obj, list):
        return [scrub_obj(v) for v in obj]
    if isinstance(obj, dict):
        return {scrub_obj(k): scrub_obj(v) for k, v in obj.items()}
    return obj


class RedactingFilter(logging.Filter):
    """Logging filter that scrubs every record before it is written."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = scrub(record.getMessage())
        record.args = ()
        return True
