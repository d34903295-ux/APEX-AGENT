"""Smart DCA with adaptive moving averages.

Instead of buying blindly on a fixed schedule, this accumulates harder when
price is below an adaptive mean (discount) and throttles when extended above
it. A long EMA defines the trend; deviations from it size the buys.
"""
from __future__ import annotations

from apex.core.indicators import RollingSeries
from apex.core.models import MarketTick, Side, Signal, SignalAction
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies.base import Strategy


@STRATEGY_REGISTRY.register("dca")
class SmartDCAStrategy(Strategy):
    name = "dca"

    def __init__(self, symbols=None, fast: int = 20, slow: int = 100,
                 base_buy_pct: float = 0.01, max_buy_pct: float = 0.05,
                 cooldown_ticks: int = 30, **params):
        super().__init__(symbols, **params)
        self.fast = fast
        self.slow = slow
        self.base_buy_pct = base_buy_pct
        self.max_buy_pct = max_buy_pct
        self.cooldown = cooldown_ticks
        self._series: dict[str, RollingSeries] = {}
        self._since: dict[str, int] = {}

    def on_tick(self, tick: MarketTick) -> list[Signal]:
        if self.symbols and tick.symbol not in self.symbols:
            return []
        s = self._series.setdefault(tick.symbol, RollingSeries(maxlen=self.slow * 3))
        s.push(tick.price)
        self._since[tick.symbol] = self._since.get(tick.symbol, self.cooldown) + 1
        if self._since[tick.symbol] < self.cooldown:
            return []

        slow = s.ema(self.slow)
        if slow is None:
            return []
        deviation = (tick.price - slow) / slow  # negative = discount

        if deviation < 0:
            # The deeper the discount, the bigger the buy (bounded).
            size = min(self.max_buy_pct, self.base_buy_pct * (1 + abs(deviation) * 10))
            self._since[tick.symbol] = 0
            return [self._signal(
                symbol=tick.symbol, side=Side.BUY, action=SignalAction.INCREASE,
                confidence=min(0.9, 0.5 + abs(deviation)), target_pct=size,
                price_hint=tick.price,
                rationale=f"DCA buy: {deviation:.2%} below EMA{self.slow}",
            )]
        return []
