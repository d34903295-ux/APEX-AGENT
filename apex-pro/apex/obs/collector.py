"""Bus-driven metrics collector.

Subscribes to every relevant channel and updates the global REGISTRY. Runs
inside the dashboard process (which serves /metrics) and/or the orchestrator.
Fully decoupled — services don't import metrics, they just publish events.
"""
from __future__ import annotations

import asyncio

from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.core.logging import get_logger
from apex.obs import metrics as M

log = get_logger("apex.obs.collector")


async def collect() -> None:
    bus = await make_bus()
    log.info("metrics collector running")

    async def ticks():
        async for _ in bus.subscribe(Channels.TICKS):
            M.TICKS.inc()

    async def signals():
        async for msg in bus.subscribe(Channels.SIGNALS):
            M.SIGNALS.inc(strategy=msg.get("strategy", "?"))

    async def orders():
        async for _ in bus.subscribe(Channels.ORDERS):
            M.ORDERS.inc()

    async def fills():
        async for msg in bus.subscribe(Channels.FILLS):
            M.FILLS.inc(strategy=msg.get("strategy", "?"), side=msg.get("side", "?"))

    async def risk():
        async for msg in bus.subscribe(Channels.RISK_EVENTS):
            t = msg.get("type")
            if t == "reject":
                M.REJECTIONS.inc(strategy=msg.get("strategy", "?"))
            elif t == "pause":
                M.PAUSES.inc()

    async def heartbeat():
        async for msg in bus.subscribe(Channels.HEARTBEAT):
            snap = msg.get("snapshot") or {}
            if "equity" in snap:
                M.EQUITY.set(snap["equity"])
            if "cash" in snap:
                M.CASH.set(snap["cash"])
            if "drawdown" in snap:
                M.DRAWDOWN.set(snap["drawdown"])
            M.OPEN_POSITIONS.set(len(snap.get("positions", {})))
            M.PAUSED.set(1 if msg.get("paused") else 0)

    await asyncio.gather(ticks(), signals(), orders(), fills(), risk(), heartbeat())
