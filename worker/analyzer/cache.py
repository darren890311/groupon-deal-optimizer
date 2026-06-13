"""Optional Redis-backed cache for expensive *sub-results* (the direct-booking
price lookup and the competitor-discovery scrape), so different deals from the
same merchant / category reuse them instead of re-running Tavily + Playwright
every time.

This is separate from the gateway's per-URL "analysis:" cache, which only helps
when the exact same deal is re-analyzed. This layer helps across *different*
deals that share a merchant or a category.

Fully optional and fail-safe: if REDIS_URL is unset or Redis is unreachable,
every call is a graceful no-op and the pipeline runs exactly as before. Short
socket timeouts ensure a slow/unreachable Redis can't add latency.
"""

import json
import re
from typing import Any

from .config import REDIS_URL

_client = None
_initialized = False


def _get_client():
    global _client, _initialized
    if _initialized:
        return _client
    _initialized = True
    if not REDIS_URL:
        return None
    try:
        import redis

        c = redis.from_url(REDIS_URL, socket_timeout=2, socket_connect_timeout=2)
        c.ping()
        _client = c
    except Exception as e:
        print(f"  sub-cache disabled (redis init failed): {e}")
        _client = None
    return _client


def norm(s: str | None) -> str:
    """Normalize a key part so trivial casing/whitespace differences still hit."""
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def get(key: str) -> Any | None:
    c = _get_client()
    if not c:
        return None
    try:
        v = c.get(key)
        return json.loads(v) if v else None
    except Exception:
        return None


def put(key: str, value: Any, ttl: int) -> None:
    c = _get_client()
    if not c:
        return
    try:
        c.set(key, json.dumps(value), ex=ttl)
    except Exception:
        pass
