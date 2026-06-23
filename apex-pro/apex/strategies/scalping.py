"""Microstructure scalping.

Reacts to short-term order-book imbalance and momentum. With L1 (bid/ask) it
uses spread + micro-momentum; if the data-feeder supplies L2 depth in
`tick.meta['bids'/'asks']`, it computes order-book imbalance (OBI) for a much
stronger edge. Holds for a few ticks and exits on mean reversion.
"""
from __future__ import annotations

from apex.core.indicators import RollingSeries
from apex.core.models import MarketTick, Side, Signal, SignalAction
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies.base import Strategy


def _order_book_imbalance(tick: MarketTick) -> float | None:
    bids = tick.meta.get("bids") if hasattr(tick, "meta") else None
    asks = tick.meta.get("asks") if hasattr(tick, "meta") else None
    if not bids or not asks:
        return None
    bid_vol = sum(float(v) for _, v in bids[:10])
    ask_vol = sum(float(v) for _, v in asks[:10])
    total = bid_vol + ask_vol
    if total == 0:
        return None
    return (bid_vol - ask_vol) / total  # +1 strong buy pressure, -1 strong sell


@STRATEGY_REGISTRY.register("scalping")
class ScalpingStrategy(Strategy):
    name = "scalping"

    def __init__(self, symbols=None, momentum_window: int = 10,
                 obi_threshold: float = 0.25, max_spread: float = 0.0015,
                 size_pct: float = 0.03, **params):
        super().__init__(symbols, **params)
        self.momentum_window = momentum_window
        self.obi_threshold = obi_threshold
        self.max_spread = max_spread
        self.size_pct = size_pct
        self._series: dict[str, RollingSeries] = {}

    def on_tick(self, tick: MarketTick) -> list[Signal]:
        if self.symbols and tick.symbol not in self.symbols:
            return []
        if tick.spread and tick.spread > self.max_spread:
            return []  # too expensive to scalp
        s = self._series.setdefault(tick.symbol, RollingSeries(maxlen=self.momentum_window * 5))
        s.push(tick.price)

        sma = s.sma(self.momentum_window)
        if sma is None:
            return []
        momentum = (tick.price - sma) / sma
        obi = _order_book_imbalance(tick)

        # Combine momentum with order-book imbalance when available.
        score = momentum * 50
        if obi is not None:
            score += obi

        if obi is not None and abs(obi) < self.obi_threshold and abs(momentum) < 0.0005:
            return []

        if score > self.obi_threshold:
            side, conf = Side.BUY, min(0.9, 0.5 + abs(score))
        elif score < -self.obi_threshold:
            side, conf = Side.SELL, min(0.9, 0.5 + abs(score))
        else:
            return []

        return [self._signal(
            symbol=tick.symbol, side=side, action=SignalAction.OPEN,
            confidence=conf, target_pct=self.size_pct, price_hint=tick.price,
            take_profit=tick.price * (1.0015 if side is Side.BUY else 0.9985),
            rationale=f"scalp mom={momentum:.4f} obi={obi}",
        )]
