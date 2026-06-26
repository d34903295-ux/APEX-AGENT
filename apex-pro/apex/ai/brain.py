"""ai-brain service: feature-driven prediction with walk-forward AutoML.

Pipeline:
  ticks -> per-symbol price history -> (periodically) AutoML.select walk-forward
        -> active model predicts direction/confidence -> PREDICTIONS channel.

Predictions carry a `facts` dict the symbolic planner consumes, so the creative
planner can react to model output (e.g. "if pred_confidence > 0.7 and ...").

Backwards-compatible: `Predictor`, `MomentumPredictor`, `AutoML` and `run` are
re-exported here so existing imports keep working.
"""
from __future__ import annotations

import asyncio

from apex.ai.automl import AutoML, evaluate  # noqa: F401
from apex.ai.base import Predictor  # noqa: F401
from apex.ai.models import MomentumPredictor, SklearnPredictor  # noqa: F401
from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.core.indicators import RollingSeries
from apex.core.logging import get_logger
from apex.core.models import MarketTick

log = get_logger("apex.ai")

MIN_TRAIN = 150  # bars before we attempt model selection


async def run(symbols: list[str], interval: float = 5.0, retrain_every: int = 60) -> None:
    bus = await make_bus()
    series: dict[str, RollingSeries] = {}
    prices: dict[str, list[float]] = {}
    selectors: dict[str, AutoML] = {}
    log.info("ai-brain running (walk-forward AutoML, retrain every %d cycles)", retrain_every)

    async def ingest():
        async for msg in bus.subscribe(Channels.TICKS):
            t = MarketTick.from_dict(msg)
            series.setdefault(t.symbol, RollingSeries(maxlen=2000)).push(t.price)
            prices.setdefault(t.symbol, []).append(t.price)
            if len(prices[t.symbol]) > 5000:
                prices[t.symbol] = prices[t.symbol][-3000:]

    from apex.ai.llm_planner import LLMRuleProposer
    proposer = LLMRuleProposer()
    if proposer.available:
        log.info("LLM rule proposer ENABLED (model=%s)", proposer.model)
    last_facts: dict = {}

    async def emit():
        cycle = 0
        while True:
            await asyncio.sleep(interval)
            cycle += 1
            for sym, s in series.items():
                hist = prices.get(sym, [])
                automl = selectors.setdefault(sym, AutoML())
                # Periodic walk-forward model selection on recent history.
                if len(hist) >= MIN_TRAIN and (cycle % retrain_every == 1):
                    automl.select(hist)
                pred = automl.active.predict(sym, s)
                fact = {"price": s.values[-1] if s.values else 0,
                        "pred_direction": pred["direction"],
                        "pred_confidence": pred["confidence"]}
                last_facts[sym] = fact
                await bus.publish(Channels.PREDICTIONS, {
                    "symbol": sym, "model": automl.active.name, **pred,
                    "facts": {sym: fact},
                })
            # LLM-assisted creativity: occasionally propose sandboxed rules.
            if proposer.available and last_facts and cycle % retrain_every == 0:
                for rule in proposer.propose(dict(last_facts)):
                    await bus.publish(Channels.COMMANDS,
                                      {"action": "add_planner_rule", "rule": rule})

    await asyncio.gather(ingest(), emit())
