"""Symbolic micro-strategy planner — the "creativity" engine.

Lets the agent compose ad-hoc strategies from declarative rules without code
changes. A rule is `WHEN <conditions> THEN <action>`, e.g. the prompt's
example:

    WHEN btc.change_1h < -0.05 AND binance.cvd_buy rising
    THEN buy ETH leverage 2x take_profit R1

Rules are evaluated against a live `MarketContext` (facts published by the
data-feeder + ai-brain). Optionally, an LLM (config.llm_model) can *propose*
new candidate rules from the current regime; every LLM-proposed rule is
sandboxed: it must pass the backtester and 24h paper trading before the
risk-manager will ever let it touch real capital.
"""
from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Any, Callable

from apex.core.models import MarketTick, Side, Signal, SignalAction
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies.base import Strategy

_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "<": operator.lt, "<=": operator.le, ">": operator.gt,
    ">=": operator.ge, "==": operator.eq, "!=": operator.ne,
}


@dataclass
class Condition:
    fact: str          # dotted key into the context, e.g. "btc.change_1h"
    op: str
    value: float

    def eval(self, ctx: dict[str, Any]) -> bool:
        cur = ctx
        for part in self.fact.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return False
            cur = cur[part]
        try:
            return _OPS[self.op](cur, self.value)
        except Exception:
            return False


@dataclass
class Rule:
    name: str
    conditions: list[Condition]
    symbol: str
    side: Side
    leverage: float = 1.0
    target_pct: float = 0.02
    take_profit: float | None = None
    stop_loss: float | None = None
    sandboxed: bool = True   # True until it passes backtest + paper trading
    meta: dict = field(default_factory=dict)

    def matches(self, ctx: dict[str, Any]) -> bool:
        return all(c.eval(ctx) for c in self.conditions)


@STRATEGY_REGISTRY.register("planner")
class SymbolicPlanner(Strategy):
    name = "planner"

    def __init__(self, symbols=None, rules: list[dict] | None = None, **params):
        super().__init__(symbols, **params)
        self.rules: list[Rule] = []
        for r in (rules or []):
            self.add_rule(r)
        self.context: dict[str, Any] = {}

    def add_rule(self, spec: dict) -> Rule:
        rule = Rule(
            name=spec["name"],
            conditions=[Condition(**c) for c in spec.get("conditions", [])],
            symbol=spec["symbol"], side=Side(spec.get("side", "buy")),
            leverage=spec.get("leverage", 1.0), target_pct=spec.get("target_pct", 0.02),
            take_profit=spec.get("take_profit"), stop_loss=spec.get("stop_loss"),
            sandboxed=spec.get("sandboxed", True), meta=spec.get("meta", {}),
        )
        self.rules.append(rule)
        return rule

    def update_context(self, facts: dict[str, Any]) -> None:
        """Merge new facts (called by the engine on ticks/predictions/news)."""
        for k, v in facts.items():
            self.context[k] = v

    def _evaluate(self) -> list[Signal]:
        out = []
        for rule in self.rules:
            if rule.matches(self.context):
                out.append(self._signal(
                    symbol=rule.symbol, side=rule.side, action=SignalAction.OPEN,
                    confidence=0.65, target_pct=rule.target_pct, leverage=rule.leverage,
                    take_profit=rule.take_profit, stop_loss=rule.stop_loss,
                    rationale=f"planner rule '{rule.name}' fired",
                    meta={"sandboxed": rule.sandboxed, "rule": rule.name, **rule.meta},
                ))
        return out

    def on_tick(self, tick: MarketTick) -> list[Signal]:
        # Cheap fact updates; richer facts come from ai-brain/onchain via engine.
        self.update_context({tick.symbol: {"price": tick.price}})
        return self._evaluate()

    def on_prediction(self, prediction: dict) -> list[Signal]:
        self.update_context(prediction.get("facts", {}))
        return self._evaluate()
