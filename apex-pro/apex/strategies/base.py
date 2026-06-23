"""Base class for all trading strategies.

A strategy is a pure(ish) signal generator: it receives market data (and
optionally predictions / news) and emits `Signal`s. It NEVER touches an
exchange directly — the risk-manager and execution-gateway do that. This keeps
strategies easy to backtest, unit-test and hot-swap.

Add a new strategy in three steps:
    1. subclass `Strategy`
    2. implement `on_tick` (and optionally `on_news` / `on_prediction`)
    3. decorate with `@STRATEGY_REGISTRY.register("my-name")`
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from apex.core.models import MarketTick, Signal


class Strategy(ABC):
    #: human-readable, unique. Override in subclass.
    name: str = "base"

    def __init__(self, symbols: list[str] | None = None, **params: Any) -> None:
        self.symbols = symbols or []
        self.params = params
        self.enabled = True

    # --- lifecycle hooks (override what you need) ---------------------------
    @abstractmethod
    def on_tick(self, tick: MarketTick) -> list[Signal]:
        """Return zero or more signals for a price update."""
        raise NotImplementedError

    def on_news(self, item: dict) -> list[Signal]:  # noqa: D401
        return []

    def on_prediction(self, prediction: dict) -> list[Signal]:
        return []

    # --- helpers -----------------------------------------------------------
    def _signal(self, **kwargs: Any) -> Signal:
        kwargs.setdefault("strategy", self.name)
        return Signal(**kwargs)

    def __repr__(self) -> str:
        return f"<Strategy {self.name} symbols={self.symbols} enabled={self.enabled}>"
