"""Auto-recovery: retry with exponential backoff (+ jitter-free determinism).

Wraps flaky I/O (exchange REST, RPC, HTTP feeds) so a transient failure doesn't
kill a service. Used by adapters/sources; also handy standalone.

    data = await retry_async(lambda: fetch(...), attempts=4, base=2.0)
    val  = retry_sync(do_thing, attempts=3)

Backoff is 0, base, base*2, base*4 ... seconds. Deterministic (no random) so it
stays compatible with workflow-style replay; add jitter at the call site if you
need it for thundering-herd avoidance.
"""
from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable, TypeVar

from apex.core.logging import get_logger

log = get_logger("apex.obs.retry")
T = TypeVar("T")


async def retry_async(fn: Callable[[], Awaitable[T]], *, attempts: int = 4,
                      base: float = 2.0, max_delay: float = 30.0,
                      exceptions: tuple = (Exception,), label: str = "op") -> T:
    last: Exception | None = None
    for i in range(attempts):
        try:
            return await fn()
        except exceptions as exc:  # noqa: BLE001
            last = exc
            if i == attempts - 1:
                break
            delay = min(max_delay, base * (2 ** i) - base) if i else 0.0
            log.warning("%s failed (attempt %d/%d): %s; retry in %.1fs",
                        label, i + 1, attempts, exc, delay)
            if delay:
                await asyncio.sleep(delay)
    raise last  # type: ignore[misc]


def retry_sync(fn: Callable[[], T], *, attempts: int = 4, base: float = 2.0,
               max_delay: float = 30.0, exceptions: tuple = (Exception,),
               label: str = "op", _sleep=time.sleep) -> T:
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except exceptions as exc:  # noqa: BLE001
            last = exc
            if i == attempts - 1:
                break
            delay = min(max_delay, base * (2 ** i) - base) if i else 0.0
            log.warning("%s failed (attempt %d/%d): %s; retry in %.1fs",
                        label, i + 1, attempts, exc, delay)
            if delay:
                _sleep(delay)
    raise last  # type: ignore[misc]
