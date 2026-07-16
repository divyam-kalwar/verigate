"""In-memory TPS rate limiter for VeriGate.

Owns all per-client rate-limiting logic (CLAUDE.md: business logic belongs in
services, routes stay thin). It implements the Fixed Window Counter algorithm in
process memory and does NOT touch MongoDB — the TPS limit is read from the
authenticated client document already stored on Flask `g` during authentication.

Why in-memory:
    The assignment explicitly scopes this to a single application instance
    ("in-memory per-client TPS limiter"). CLAUDE.md also requires the design to
    stay modular so it can later be swapped for Redis. Keeping the counter state
    inside the service instance (rather than scattered globals) makes that swap a
    one-file change.

Why time.monotonic():
    Window math measures *elapsed* time, so a monotonic clock is correct and
    immune to wall-clock adjustments (NTP, DST). It satisfies "current time" for
    interval comparisons.

Limitation (documented, by design):
    A single Python dict is shared only within one process. With multiple
    Gunicorn workers or pods the windows are not coordinated; a Redis-backed
    implementation would be required for distributed accuracy. This is noted in
    the README per the assignment and is intentionally out of scope here.
"""

import time
from typing import Dict

from ..exceptions.api_exception import RateLimitExceededException


class RateLimiterService:
    """Per-client Fixed Window Counter rate limiter (single instance)."""

    def __init__(self) -> None:
        # client_id -> {"count": int, "window_start": float(monotonic seconds)}
        self._store: Dict[str, Dict[str, float]] = {}

    def check(self, client_id: str, tps_limit: int) -> None:
        """Allow or reject a request for the given client.

        Args:
            client_id: The authenticated client identifier (the limiter key).
            tps_limit: Maximum allowed requests per rolling 1-second window,
                taken from the client document (g.client["tps_limit"]).

        Raises:
            RateLimitExceededException: When the client has already consumed its
                full TPS budget in the current window (VP4029 / HTTP 429).
        """
        now = time.monotonic()
        entry = self._store.get(client_id)

        if entry is None:
            self._store[client_id] = {"count": 1, "window_start": now}
            return

        if now - entry["window_start"] >= 1.0:
            entry["count"] = 1
            entry["window_start"] = now
            return

        entry["count"] += 1
        if entry["count"] > tps_limit:
            raise RateLimitExceededException()
