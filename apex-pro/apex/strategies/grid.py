"""Dynamic grid trading.

Classic grid, but the grid spacing auto-adapts to recent volatility: wider
grids in choppy/volatile regimes, tighter grids when calm. Re-centres when
price drifts outside the band.
"""
from __future__ import annotations

from apex.core.indicators import RollingSeries
from apex.core.models import MarketTick, Side, Signal, SignalAction
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies.base import Strategy


@STRATEGY_REGISTRY.register("grid")
class GridStrategy(Strategy):
    name = "grid"

    def __init__(self, symbols=None, levels: int = 6, vol_lookback: int = 50,
                 base_spacing: float = 0.005, per_level_pct: float = 0.02, **params):
        super().__init__(symbols, **params)
        self.levels = levels
        self.vol_lookback = vol_lookback
        self.base_spacing = base_spacing
        self.per_level_pct = per_level_pct
        self._series: dict[str, RollingSeries] = {}
        self._center: dict[str, float] = {}
        self._last_level: dict[str, int] = {}

    def _spacing(self, sym: str) -> float:
        vol = self._series[sym].returns_volatility(self.vol_lookback)
        if vol is None:
            return self.base_spacing
        # spacing scales with volatility, bounded to a sane range.
        return max(self.base_spacing, min(0.05, vol * 4))

    def on_tick(self, tick: MarketTick) -> list[Signal]:
        if self.symbols and tick.symbol not in self.symbols:
            return []
        s = self._series.setdefault(tick.symbol, RollingSeries(maxlen=max(200, self.vol_lookback * 2)))
        s.push(tick.price)
        if tick.symbol not in self._center:
            self._center[tick.symbol] = tick.price
            self._last_level[tick.symbol] = 0
            return []

        spacing = self._spacing(tick.symbol)
        center = self._center[tick.symbol]
        level = int((tick.price - center) / (center * spacing))
        level = max(-self.levels, min(self.levels, level))

        out: list[Signal] = []
        prev = self._last_level[tick.symbol]
        if level != prev:
            # Crossed a grid line: buy lower lines, sell higher lines.
            side = Side.BUY if level < prev else Side.SELL
            out.append(self._signal(
                symbol=tick.symbol, side=side, action=SignalAction.OPEN,
                confidence=0.55, target_pct=self.per_level_pct, price_hint=tick.price,
                rationale=f"grid level {prev}->{level} spacing={spacing:.4f}",
            ))
            self._last_level[tick.symbol] = level

        # Re-centre if price escaped the grid entirely.
        if abs(level) >= self.levels:
            self._center[tick.symbol] = tick.price
            self._last_level[tick.symbol] = 0
        return out
