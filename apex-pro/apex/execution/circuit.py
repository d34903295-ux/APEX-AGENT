"""Per-venue circuit breaker + multi-exchange failover.

If a venue starts failing (API down, rejects, timeouts), its breaker OPENS and
the gateway routes the same pair to the next healthy venue automatically. After
a cooldown the breaker goes HALF-OPEN to probe recovery.

States:  closed -> (failures >= threshold) -> open -> (cooldown) -> half_open
         half_open -> success -> closed ;  half_open -> failure -> open

Clock is injectable (time.monotonic by default) so tests are deterministic.
"""
from __future__ import annotations

import time
from enum import Enum


class State(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, threshold: int = 3, cooldown: float = 30.0, clock=time.monotonic):
        self.threshold = threshold
        self.cooldown = cooldown
        self._clock = clock
        self.failures = 0
        self.state = State.CLOSED
        self.opened_at = 0.0

    def allow(self) -> bool:
        """May we send to this venue right now?"""
        if self.state is State.OPEN:
            if self._clock() - self.opened_at >= self.cooldown:
                self.state = State.HALF_OPEN
                return True          # allow a single probe
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.state = State.CLOSED

    def record_failure(self) -> None:
        self.failures += 1
        if self.state is State.HALF_OPEN or self.failures >= self.threshold:
            self.state = State.OPEN
            self.opened_at = self._clock()


class VenueFailover:
    def __init__(self, threshold: int = 3, cooldown: float = 30.0, clock=time.monotonic):
        self._mk = lambda: CircuitBreaker(threshold, cooldown, clock)
        self.breakers: dict[str, CircuitBreaker] = {}

    def breaker(self, venue: str) -> CircuitBreaker:
        b = self.breakers.get(venue)
        if b is None:
            b = self.breakers[venue] = self._mk()
        return b

    def record_success(self, venue: str) -> None:
        self.breaker(venue).record_success()

    def record_failure(self, venue: str) -> None:
        self.breaker(venue).record_failure()

    def candidates(self, primary: str, alternates: list[str]) -> list[str]:
        """Ordered, de-duplicated list of healthy venues to try (primary first)."""
        ordered, seen = [], set()
        for v in [primary, *alternates]:
            if v and v not in seen and self.breaker(v).allow():
                ordered.append(v)
                seen.add(v)
        return ordered
