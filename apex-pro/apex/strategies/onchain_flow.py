"""On-chain flow strategy: whales, stablecoin flows, Open Interest, CVD.

Consumes 'onchain' items from the NEWS channel (produced by the on-chain
source: exchange netflows, large transfers, aggregated CVD, perp OI/funding).
Emits directional signals when flows confirm a bias.
"""
from __future__ import annotations

from apex.core.models import MarketTick, Side, Signal, SignalAction
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies.base import Strategy


@STRATEGY_REGISTRY.register("onchain")
class OnchainFlowStrategy(Strategy):
    name = "onchain"

    def __init__(self, symbols=None, size_pct: float = 0.04, **params):
        super().__init__(symbols, **params)
        self.size_pct = size_pct

    def on_news(self, item: dict) -> list[Signal]:
        if item.get("type") != "onchain":
            return []
        symbol = item.get("symbol")
        if not symbol or (self.symbols and symbol not in self.symbols):
            return []

        # Composite bias from independent flow signals (each in -1..1).
        netflow = float(item.get("exchange_netflow_z", 0))   # +inflow (bearish)
        cvd = float(item.get("cvd_slope", 0))                # + buy pressure
        funding = float(item.get("funding_rate", 0))         # + crowded longs
        bias = cvd - 0.5 * netflow - 0.3 * (funding * 100)

        if abs(bias) < 0.5:
            return []
        side = Side.BUY if bias > 0 else Side.SELL
        return [self._signal(
            symbol=symbol, side=side, action=SignalAction.OPEN,
            confidence=min(0.85, 0.5 + abs(bias) / 4), target_pct=self.size_pct,
            rationale=f"onchain bias={bias:+.2f} (cvd={cvd} netflow={netflow} fund={funding})",
        )]

    def on_tick(self, tick: MarketTick) -> list[Signal]:
        return []
