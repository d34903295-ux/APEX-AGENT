"""Cross-exchange and triangular arbitrage detection.

This module *detects* opportunities and emits paired signals. Real execution
requires atomic-ish placement on both legs (handled by the execution-gateway's
smart router) and pre-funded balances on each venue. Fees + slippage are
modelled before anything is emitted — most "arbs" vanish once you subtract
them, so we are strict.
"""
from __future__ import annotations

from apex.core.models import MarketTick, Side, Signal, SignalAction
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies.base import Strategy

# Conservative default taker fees per venue (override via params).
DEFAULT_FEES = {"binance": 0.001, "bybit": 0.001, "okx": 0.0008, "kraken": 0.0016}


@STRATEGY_REGISTRY.register("arbitrage")
class CrossExchangeArbitrage(Strategy):
    name = "arbitrage"

    def __init__(self, symbols=None, min_edge: float = 0.0015,
                 slippage: float = 0.0005, fees: dict | None = None,
                 size_pct: float = 0.05, **params):
        super().__init__(symbols, **params)
        self.min_edge = min_edge
        self.slippage = slippage
        self.fees = {**DEFAULT_FEES, **(fees or {})}
        self.size_pct = size_pct
        # latest price per (symbol -> exchange -> price)
        self._book: dict[str, dict[str, float]] = {}

    def on_tick(self, tick: MarketTick) -> list[Signal]:
        if self.symbols and tick.symbol not in self.symbols:
            return []
        venues = self._book.setdefault(tick.symbol, {})
        venues[tick.exchange] = tick.price
        if len(venues) < 2:
            return []

        cheap_ex = min(venues, key=venues.get)
        rich_ex = max(venues, key=venues.get)
        buy_px, sell_px = venues[cheap_ex], venues[rich_ex]
        if buy_px <= 0:
            return []

        gross_edge = (sell_px - buy_px) / buy_px
        cost = self.fees.get(cheap_ex, 0.001) + self.fees.get(rich_ex, 0.001) + 2 * self.slippage
        net_edge = gross_edge - cost
        if net_edge < self.min_edge:
            return []

        meta = {"net_edge": net_edge, "leg": "arb"}
        return [
            self._signal(symbol=tick.symbol, side=Side.BUY, action=SignalAction.OPEN,
                         exchange=cheap_ex, confidence=min(0.95, 0.6 + net_edge * 20),
                         target_pct=self.size_pct, price_hint=buy_px,
                         rationale=f"arb buy@{cheap_ex} net={net_edge:.4f}", meta=meta),
            self._signal(symbol=tick.symbol, side=Side.SELL, action=SignalAction.OPEN,
                         exchange=rich_ex, confidence=min(0.95, 0.6 + net_edge * 20),
                         target_pct=self.size_pct, price_hint=sell_px,
                         rationale=f"arb sell@{rich_ex} net={net_edge:.4f}", meta=meta),
        ]
