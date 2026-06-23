"""Risk-manager service loop.

Subscribes: SIGNALS (to gate), TICKS (marks/regime), FILLS (portfolio mirror),
            COMMANDS (pause/resume/risk_profile).
Publishes:  ORDERS (approved), RISK_EVENTS + ALERTS (rejections, auto-pauses).
"""
from __future__ import annotations

import asyncio

from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.core.logging import get_logger
from apex.core.models import Fill, MarketTick, Signal
from apex.risk.manager import RiskManager

log = get_logger("apex.svc.risk")


async def run(rm: RiskManager | None = None) -> None:
    rm = rm or RiskManager()
    bus = await make_bus()
    log.info("Risk-manager service up (profile=%s, live=%s)",
             rm.s.risk_profile.value, rm.s.is_live)

    async def signals():
        async for msg in bus.subscribe(Channels.SIGNALS):
            sig = Signal.from_dict(msg)
            order, reason = rm.evaluate(sig)
            if order:
                await bus.publish(Channels.ORDERS, order.to_dict())
            else:
                await bus.publish(Channels.RISK_EVENTS,
                                  {"type": "reject", "strategy": sig.strategy,
                                   "symbol": sig.symbol, "reason": reason})

    async def ticks():
        async for msg in bus.subscribe(Channels.TICKS):
            t = MarketTick.from_dict(msg)
            for event in rm.on_tick_price(t.symbol, t.price):
                await bus.publish(Channels.ALERTS, {"level": "critical", "text": event})
                await bus.publish(Channels.RISK_EVENTS, {"type": "pause", "reason": event})

    async def fills():
        async for msg in bus.subscribe(Channels.FILLS):
            rm.on_fill(Fill.from_dict(msg))

    async def commands():
        async for cmd in bus.subscribe(Channels.COMMANDS):
            action = cmd.get("action")
            if action == "pause":
                rm.pause(cmd.get("reason", "telegram"))
                await bus.publish(Channels.ALERTS, {"level": "info", "text": "Agent paused"})
            elif action == "resume":
                rm.resume()
                await bus.publish(Channels.ALERTS, {"level": "info", "text": "Agent resumed"})

    await asyncio.gather(signals(), ticks(), fills(), commands())
