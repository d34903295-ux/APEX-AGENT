"""Execution-gateway service loop.

Subscribes: ORDERS (to execute), TICKS (marks for paper fills).
Publishes:  FILLS, ALERTS (on trade open/close).
"""
from __future__ import annotations

import asyncio

from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.core.logging import get_logger
from apex.core.models import MarketTick, Order
from apex.execution.gateway import ExecutionGateway

log = get_logger("apex.svc.exec")


async def run(gw: ExecutionGateway | None = None) -> None:
    gw = gw or ExecutionGateway()
    bus = await make_bus()
    log.info("Execution-gateway up (live=%s)", gw.s.is_live)

    async def orders():
        async for msg in bus.subscribe(Channels.ORDERS):
            order = Order.from_dict(msg)
            for fill in gw.execute(order):
                await bus.publish(Channels.FILLS, fill.to_dict())
                await bus.publish(Channels.ALERTS, {
                    "level": "trade",
                    "text": (f"{'🟢' if fill.side.value=='buy' else '🔴'} "
                             f"{fill.side.value.upper()} {fill.amount:.6f} {fill.symbol} "
                             f"@ {fill.price:.4f} [{fill.strategy}]"),
                })

    async def ticks():
        async for msg in bus.subscribe(Channels.TICKS):
            t = MarketTick.from_dict(msg)
            gw.update_mark(t.symbol, t.price)

    await asyncio.gather(orders(), ticks())
