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

    # COMMAND actions this service owns (others belong to the strategy-engine).
    OWNED = {"pause", "resume", "set_profile", "force_trade"}

    async def commands():
        async for cmd in bus.subscribe(Channels.COMMANDS):
            action = cmd.get("action")
            try:
                if action == "pause":
                    rm.pause(cmd.get("reason", "telegram"))
                    await bus.publish(Channels.ALERTS, {"level": "info", "text": "Agent paused"})
                elif action == "resume":
                    rm.resume()
                    await bus.publish(Channels.ALERTS, {"level": "info", "text": "Agent resumed"})
                elif action == "set_profile":
                    ok = rm.set_profile(cmd.get("profile", ""))
                    await bus.publish(Channels.ALERTS, {
                        "level": "info" if ok else "critical",
                        "text": (f"Risk profile set to {cmd.get('profile')}" if ok
                                 else f"Rejected unknown profile {cmd.get('profile')!r}")})
                elif action == "force_trade":
                    await _force_trade(cmd)
                # else: not ours — the strategy-engine handles other actions.
            except Exception as exc:
                log.warning("risk command %r failed: %s", action, exc)

    async def _force_trade(cmd: dict) -> None:
        from apex.core.models import Side, SignalAction
        symbol = cmd.get("symbol", "")
        price = rm.pf._marks.get(symbol)
        if not price:
            await bus.publish(Channels.ALERTS, {"level": "critical",
                "text": f"force_trade {symbol}: no live price, ignored"})
            return
        sig = Signal(strategy="manual_override", symbol=symbol,
                     side=Side(cmd.get("side", "buy")), action=SignalAction.OPEN,
                     confidence=1.0, target_pct=float(cmd.get("pct", 0.01)),
                     price_hint=price, rationale="manual override (Telegram)")
        order, reason = rm.evaluate(sig)
        if order:
            await bus.publish(Channels.ORDERS, order.to_dict())
            await bus.publish(Channels.ALERTS, {"level": "trade",
                "text": f"⚡ Manual {sig.side.value} {symbol} accepted ({order.amount:.6f})"})
        else:
            await bus.publish(Channels.ALERTS, {"level": "critical",
                "text": f"⚠️ Manual {symbol} REJECTED by risk: {reason}"})

    async def heartbeat():
        # Distributed-deployment parity: publish portfolio state on the bus so
        # Telegram/dashboard/metrics work without the single-process orchestrator.
        while True:
            await bus.publish(Channels.HEARTBEAT, {
                "type": "portfolio", "paused": rm.paused, "reason": rm.pause_reason,
                "snapshot": rm.pf.snapshot()})
            await asyncio.sleep(5)

    await asyncio.gather(signals(), ticks(), fills(), commands(), heartbeat())
