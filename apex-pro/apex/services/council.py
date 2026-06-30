"""Optional 'more brains' service: the Council on the live bus.

Subscribes to PREDICTIONS (emitted by ai-brain), accumulates per-symbol price
history + facts, and periodically runs a full multi-brain deliberation. When
the council returns a VERIFIED proposal it publishes an `add_planner_rule`
COMMAND (the planner already consumes these) plus an ALERT — so the brains'
collaborative output flows into the existing pipeline with zero breaking
changes. Disabled by default (APEX_ENABLE_COUNCIL); off == current behaviour.

Backward compatibility: this only ADDS sandboxed planner rules, which the
risk-manager already blocks from live capital until they pass backtest + paper.
"""
from __future__ import annotations

import asyncio

from apex.brains import Council, Risk
from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.core.logging import get_logger

log = get_logger("apex.svc.council")

MIN_HISTORY = 60


async def run(council: Council | None = None, interval: float = 10.0,
              deliberate_every: int = 6) -> None:
    council = council or Council()
    bus = await make_bus()
    prices: dict[str, list[float]] = {}
    facts: dict[str, dict] = {}
    log.info("Council service up (brains=%s)", [b.name for b in council.router.brains])

    async def ingest():
        async for msg in bus.subscribe(Channels.PREDICTIONS):
            sym = msg.get("symbol")
            f = (msg.get("facts") or {}).get(sym, {})
            if not sym:
                continue
            facts[sym] = f
            px = f.get("price")
            if px:
                prices.setdefault(sym, []).append(float(px))
                if len(prices[sym]) > 3000:
                    prices[sym] = prices[sym][-2000:]

    async def think():
        cycle = 0
        while True:
            await asyncio.sleep(interval)
            cycle += 1
            if cycle % deliberate_every != 0:
                continue
            for sym, series in list(prices.items()):
                if len(series) < MIN_HISTORY:
                    continue
                conf = facts.get(sym, {}).get("pred_confidence", 0.0)
                risk = Risk.HIGH if conf >= 0.7 else Risk.MEDIUM
                decision = await council.deliberate(sym, {sym: facts.get(sym, {})},
                                                    series, risk=risk)
                if decision.output.get("action") == "propose_rule" and decision.verified:
                    rule = decision.output["rule"]
                    await bus.publish(Channels.COMMANDS,
                                      {"action": "add_planner_rule", "rule": rule})
                    await bus.publish(Channels.ALERTS, {
                        "level": "info",
                        "text": (f"🧠 Council proposed VERIFIED rule for {sym} "
                                 f"(consensus={decision.consensus}, brains={decision.brains_used})"),
                    })

    await asyncio.gather(ingest(), think())


if __name__ == "__main__":
    asyncio.run(run())
