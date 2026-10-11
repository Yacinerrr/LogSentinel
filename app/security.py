import hashlib
import hmac
import math
import threading
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request


class RateLimiter:
    """In-memory sliding window, per API key. Per-process: use Redis if you scale to many workers."""

    def __init__(self, limit_per_min: int, window_s: float = 60.0):
        self.limit, self.window = limit_per_min, window_s
        self.hits: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key_id: str) -> float | None:
        """Return None if allowed, else seconds to wait."""
        now = time.monotonic()
        with self.lock:
            q = self.hits[key_id]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return self.window - (now - q[0])
            q.append(now)
            return None


def key_fingerprint(key: str) -> str:
    """Short, non-reversible id for logs and rate limiting. Never log the key itself."""
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def make_auth_dependency(settings, limiter: RateLimiter):
    keys = settings.api_key_list

    def auth(request: Request, x_api_key: str | None = Header(default=None)):
        if not settings.auth_enabled:
            request.state.key_id = "anon"
            return
        valid = False
        for k in keys:  # no early exit: constant-time per key
            valid |= hmac.compare_digest((x_api_key or "").encode(), k.encode())
        if not (x_api_key and valid):
            raise HTTPException(401, "Invalid or missing API key", headers={"WWW-Authenticate": "ApiKey"})
        key_id = key_fingerprint(x_api_key)
        request.state.key_id = key_id
        wait = limiter.check(key_id)
        if wait is not None:
            raise HTTPException(429, "Rate limit exceeded", headers={"Retry-After": str(math.ceil(wait))})

    return auth


_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value: str) -> str:
    """Neutralize spreadsheet formula injection in cells that will be opened in Excel/Sheets."""
    return "'" + value if value.startswith(_FORMULA_PREFIXES) else value
