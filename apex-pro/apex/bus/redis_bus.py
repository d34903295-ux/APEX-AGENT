"""Event bus abstraction with two backends:

* RedisBus      — real Redis Pub/Sub (multi-process / multi-host deployment).
* InProcessBus  — pure-asyncio fallback (single-process, zero infra, great for
                  tests and "just run it on my laptop" mode).

`make_bus()` auto-selects: Redis if REDIS_URL is set and reachable, else
in-process. Both share the same async API:

    await bus.publish(channel, dict_payload)
    async for msg in bus.subscribe(channel): ...
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import AsyncIterator

from apex.config import get_settings
from apex.core.logging import get_logger

log = get_logger("apex.bus")


class InProcessBus:
    """A lightweight asyncio pub/sub. Same host only, but needs no Redis."""

    def __init__(self) -> None:
        self._subs: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def publish(self, channel: str, payload: dict) -> None:
        for q in list(self._subs.get(channel, [])):
            await q.put(payload)

    async def subscribe(self, channel: str) -> AsyncIterator[dict]:
        q: asyncio.Queue = asyncio.Queue(maxsize=10_000)
        self._subs[channel].append(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._subs[channel].remove(q)

    async def close(self) -> None:  # noqa: D401 - parity with RedisBus
        self._subs.clear()


class RedisBus:
    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis  # lazy import

        self._redis = aioredis.from_url(url, decode_responses=True)

    async def publish(self, channel: str, payload: dict) -> None:
        await self._redis.publish(channel, json.dumps(payload))

    async def subscribe(self, channel: str) -> AsyncIterator[dict]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    async def close(self) -> None:
        await self._redis.close()


_SINGLETON: InProcessBus | RedisBus | None = None


async def make_bus() -> InProcessBus | RedisBus:
    """Process-wide bus. Within one process the in-proc bus must be a singleton
    so publishers and subscribers share queues."""
    global _SINGLETON
    if _SINGLETON is not None:
        return _SINGLETON

    url = get_settings().redis_url
    if url:
        try:
            bus = RedisBus(url)
            await bus._redis.ping()
            log.info("[green]Connected to Redis bus[/green] at %s", url)
            _SINGLETON = bus
            return bus
        except Exception as exc:  # pragma: no cover - infra dependent
            log.warning("Redis unavailable (%s); falling back to in-process bus", exc)

    log.info("Using in-process async bus (single-host mode)")
    _SINGLETON = InProcessBus()
    return _SINGLETON
